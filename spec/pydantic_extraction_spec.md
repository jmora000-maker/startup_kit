# Pydantic Validation for Document Extraction

Status: Proposed implementation specification (Enhanced & Ready for Implementation)
Date: 2026-09-27
Target: `src/extractors/pdf_extractor.py`, `src/core/models.py`, and `src/core/pdf_models.py`
Baseline application version: 0.1.1

---

## 1. Purpose

Introduce robust runtime validation and strict schema enforcement at the document ingestion boundary while preserving existing extraction output formatting and backward-compatible dictionary metadata access. PDF page metadata and document consistency are the first format-specific validation targets.

The Startup Kit Generator ingests PDF, DOCX, PPTX, and TXT files, extracts structured project data through LangChain, and generates Word reports and optional CSV/JSON exports. Downstream domain schemas already use Pydantic v2. The extraction boundary currently uses standard Python dataclasses with untyped dictionaries, leaving malformed extraction records undetected until downstream consumers process them.

This specification defines the complete technical design, reference models, validation algorithms, serialization contracts, acceptance test matrix, and migration pathway. It does not alter PyMuPDF text extraction logic, text normalization, or require OCR dependencies.

---

## 2. Current behavior & Problem Statement

- `requirements.txt` specifies `pydantic>=2.0`.
- `src/core/models.py` defines `DocumentSection` and `ExtractedDocument` as standard dataclasses with unrestricted `Dict[str, Any]` metadata dictionaries.
- `PDFExtractor.extract()` checks the input file via `_validate_file()`, opens it with PyMuPDF (`fitz.open()`), creates one `DocumentSection` per page, and joins nonempty page texts with `--- Page N ---` markers.
- Each PDF section stores `page_number` and a four-element `rect` coordinate list. Document metadata stores `total_pages`, `title`, `author`, and `subject`.
- Missing PyMuPDF metadata keys receive empty-string defaults; explicit `None` values are currently preserved as `None` or omitted.
- The PDF handle is closed in a `finally` block.
- `IngestionService.ingest_file()` logs and re-raises extraction errors; `ingest_directory()` logs and skips failed files.
- Existing tests and downstream pipelines access metadata dictionaries directly (e.g., `document.metadata["total_pages"]`, `section.metadata["page_number"]`) and support custom extractor extensions (e.g., `.log` extractor).

**Identified Vulnerabilities:**
1. Invalid page numbers (e.g., `0`, `-1`, `"1"`, `True`), corrupted bounding boxes (e.g., `[0, 0, -100, 50]`, `NaN`, `inf`, non-numeric strings), and mismatched page counts pass unnoticed through ingestion.
2. Section ordering anomalies (reordered, duplicated, or missing pages) can silently corrupt downstream LLM prompt context and citation mappings.
3. Lack of strict schema boundaries on extraction objects allows misspelled fields or unexpected attributes to silently propagate.

---

## 3. Scope and Priorities

### Required (In Scope)

1. **Typed PDF Metadata Schemas**: Define `PDFPageMetadata` and `PDFDocumentMetadata` in `src/core/pdf_models.py` with strict Pydantic v2 constraints.
2. **Pydantic Extraction Models**: Migrate `DocumentSection` and `ExtractedDocument` in `src/core/models.py` from dataclasses to `BaseModel` with `ConfigDict(extra="forbid")`.
3. **Authoritative PDF Invariant Validation**: Enforce document-level consistency (page count alignment, strict 1-based page sequence, and metadata schema validation) inside `ExtractedDocument` via a `@model_validator(mode="after")`.
4. **Side-Effect-Free Failure Isolation**: Ensure failed validation leaves caller inputs unmutated.
5. **Metadata Dictionary Compatibility**: Maintain `dict[str, Any]` interface on extraction models populated with validated, normalized metadata.
6. **Robust Serialization**: Guarantee loss-free JSON round-tripping (`model_dump()`, `model_dump(mode="json")`, `model_dump_json()`, `model_validate()`, `model_validate_json()`).
7. **Comprehensive Test Suite**: Implement unit, boundary, invariant, error isolation, resource cleanup, and regression tests.

### Deferred (Out of Scope for this Change)

- Typed metadata schemas for DOCX, PPTX, TXT, and custom third-party extractors (designed to follow the same pattern in subsequent phases).
- Replacing public `dict` metadata with typed nested model instances in public interfaces.
- Real-time mutation monitoring of extraction records after initial construction.
- OCR, PDF password/encryption handling, visual layout reconstruction, or semantic text cleanup changes.
- Refactoring downstream LLM schemas or changing LLM provider interfaces.
- Application settings migration to `pydantic-settings` (detailed in Section 11 as a standalone follow-up).

---

## 4. Shared Extraction Models (`src/core/models.py`)

Convert `DocumentSection` and `ExtractedDocument` in `src/core/models.py` from `@dataclass` to Pydantic `BaseModel`. Preserve their class names, module location, field names, and export interfaces.

### Model Field Contracts

| Model | Field | Type | Default | Constraint / Contract |
| --- | --- | --- | --- | --- |
| **`DocumentSection`** | `title` | `str` | `""` | String title; empty string allowed |
| | `content` | `str` | `""` | String content; empty string allowed |
| | `metadata` | `dict[str, Any]` | `Field(default_factory=dict)` | Independent dict; extra custom keys permitted |
| **`ExtractedDocument`** | `file_name` | `str` | *Required* | Non-empty file name string |
| | `file_type` | `str` | *Required* | Open format string (e.g., `"pdf"`, `"docx"`, `"pptx"`, `"txt"`, `"log"`) |
| | `file_path` | `Path` | *Required* | `pathlib.Path` instance; string paths automatically coerced |
| | `text_content` | `str` | `""` | Combined extracted text; empty string allowed |
| | `sections` | `list[DocumentSection]` | `Field(default_factory=list)` | Independent list of section instances |
| | `metadata` | `dict[str, Any]` | `Field(default_factory=dict)` | Independent dict; validated per format type |

### Configuration & Design Rules

```python
class DocumentSection(BaseModel):
    """Represents an extracted structural section or slide of a document."""
    model_config = ConfigDict(extra="forbid")

    title: str = ""
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractedDocument(BaseModel):
    """Represents normalized extracted content from a single input file."""
    model_config = ConfigDict(extra="forbid")

    file_name: str
    file_type: str
    file_path: Path
    text_content: str = ""
    sections: list[DocumentSection] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

1. **Top-Level Field Safety (`extra="forbid"`)**: Prevents misspelled attributes during construction (e.g., `filename` instead of `file_name`), while generic `metadata` dictionaries continue accepting arbitrary format-specific or integration keys.
2. **Coercion & Flexibility**: Keep `file_path` typed as `Path` (not `FilePath`). Deserialization from JSON automatically converts path strings to `Path` objects without requiring the underlying physical file to exist on the current filesystem.
3. **Open `file_type`**: `file_type` remains open to arbitrary formats (e.g., `"log"`, `"md"`), ensuring the Open-Closed Principle for custom extractors. Format-specific invariant validation executes conditionally when `file_type.lower() == "pdf"`.

---

## 5. PDF Metadata Contracts (`src/core/pdf_models.py`)

Create `src/core/pdf_models.py` defining isolated, typed metadata models. This module MUST NOT import `src/core/models.py`, preventing circular dependencies.

### 5.1 `PDFPageMetadata`

Validates metadata for each individual PDF page / section.

| Field | Type | Default | Validation & Coercion Rules |
| --- | --- | --- | --- |
| `page_number` | `int` | *Required* | Strict integer `>= 1`. Reject boolean values (`True`/`False`), numeric strings (`"1"`), and fractional floats (`1.0`). |
| `rect` | `list[float]` | *Required* | List of exactly 4 finite numbers: `[x0, y0, x1, y1]`. Normalizes integers to floats. Rejects booleans, strings, NaN, Infinity, and invalid lengths. Requires `x1 >= x0` and `y1 >= y0`. |

```python
import math
from typing import Any, List
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PDFPageMetadata(BaseModel):
    """Schema for individual PDF page section metadata."""
    model_config = ConfigDict(extra="allow")

    page_number: int = Field(..., ge=1, strict=True, description="1-based page sequence number")
    rect: List[float] = Field(..., min_length=4, max_length=4, description="Bounding box [x0, y0, x1, y1]")

    @field_validator("rect", mode="before")
    @classmethod
    def validate_rect_elements(cls, v: Any) -> List[float]:
        if not isinstance(v, (list, tuple)):
            raise TypeError(f"rect must be a list or tuple of 4 numbers, got {type(v).__name__}")
        if len(v) != 4:
            raise ValueError(f"rect must contain exactly 4 coordinates, got {len(v)}")
        
        normalized: List[float] = []
        for i, coord in enumerate(v):
            # In Python, bool is a subclass of int (isinstance(True, int) is True). Reject bools explicitly.
            if isinstance(coord, bool) or not isinstance(coord, (int, float)):
                raise TypeError(f"rect coordinate at index {i} must be a finite number, got {type(coord).__name__}")
            if not math.isfinite(coord):
                raise ValueError(f"rect coordinate at index {i} must be finite (got {coord})")
            normalized.append(float(coord))
        return normalized

    @model_validator(mode="after")
    def validate_coordinate_bounds(self) -> "PDFPageMetadata":
        x0, y0, x1, y1 = self.rect
        if x1 < x0:
            raise ValueError(f"Invalid bounding box: x1 ({x1}) must be greater than or equal to x0 ({x0})")
        if y1 < y0:
            raise ValueError(f"Invalid bounding box: y1 ({y1}) must be greater than or equal to y0 ({y0})")
        return self
```

### 5.2 `PDFDocumentMetadata`

Validates document-level PDF metadata dictionary.

| Field | Type | Default | Validation & Coercion Rules |
| --- | --- | --- | --- |
| `total_pages` | `int` | *Required* | Strict integer `>= 0`. Rejects booleans (`True`/`False`), strings, and negative counts. |
| `title` | `str` | `""` | String default `""`. If `None`, normalizes to `""`. Non-string non-None inputs raise validation error. |
| `author` | `str` | `""` | String default `""`. If `None`, normalizes to `""`. Non-string non-None inputs raise validation error. |
| `subject` | `str` | `""` | String default `""`. If `None`, normalizes to `""`. Non-string non-None inputs raise validation error. |

```python
class PDFDocumentMetadata(BaseModel):
    """Schema for document-level PDF metadata."""
    model_config = ConfigDict(extra="allow")

    total_pages: int = Field(..., ge=0, strict=True, description="Total number of pages in document")
    title: str = Field(default="", description="Document title")
    author: str = Field(default="", description="Document author")
    subject: str = Field(default="", description="Document subject")

    @field_validator("title", "author", "subject", mode="before")
    @classmethod
    def normalize_string_or_none(cls, v: Any) -> str:
        if v is None:
            return ""
        if not isinstance(v, str):
            raise TypeError(f"Expected string or None, got {type(v).__name__}")
        return v
```

**Extension Safety (`extra="allow"`)**: Both models use `extra="allow"` so additional metadata keys supplied by custom tools or PyMuPDF extensions (e.g., `creator`, `producer`, `creationDate`, `modDate`, custom tags) are preserved without data loss.

---

## 6. Validation Ownership and PDF Integration

Validation ownership is centralized in an authoritative `@model_validator(mode="after")` on `ExtractedDocument`.

### 6.1 Invariant Validation Algorithm

When an `ExtractedDocument` instance is validated (via constructor, `model_validate()`, or `model_validate_json()`):

1. **Format Check**: If `self.file_type.lower() != "pdf"`, bypass PDF validation and return `self`.
2. **Document Metadata Validation**: Validate `self.metadata` against `PDFDocumentMetadata.model_validate(self.metadata)`.
3. **Total Pages Invariant**: Require `validated_doc_metadata.total_pages == len(self.sections)`. If mismatched, raise `ValueError(f"PDF document '{self.file_name}' total_pages ({validated_doc_metadata.total_pages}) does not match section count ({len(self.sections)})")`.
4. **Page Sequence & Page Metadata Invariants**:
   - For each section index `idx` (0-based) and section `s` in `self.sections`:
     - Validate `s.metadata` against `PDFPageMetadata.model_validate(s.metadata)`.
     - Require `validated_page_metadata.page_number == idx + 1`. If mismatched, raise `ValueError(f"PDF document '{self.file_name}' section {idx} page_number ({validated_page_metadata.page_number}) must equal expected sequence number {idx + 1}")`.
     - Construct a normalized copy of the section: `s.model_copy(update={"metadata": validated_page_metadata.model_dump()})`.
5. **Atomic Assignment**: Assign the validated/normalized metadata dict `self.metadata = validated_doc_metadata.model_dump()` and normalized sections list `self.sections = normalized_sections`.

### 6.2 Reference Validator Implementation (`src/core/models.py`)

```python
from pydantic import model_validator
from src.core.pdf_models import PDFDocumentMetadata, PDFPageMetadata


class ExtractedDocument(BaseModel):
    # ... fields as defined in Section 4 ...

    @model_validator(mode="after")
    def validate_pdf_invariants(self) -> "ExtractedDocument":
        if self.file_type.lower() != "pdf":
            return self

        # 1. Validate document-level metadata
        try:
            doc_meta = PDFDocumentMetadata.model_validate(self.metadata)
        except Exception as exc:
            raise ValueError(f"Invalid PDF document metadata in '{self.file_name}': {exc}") from exc

        # 2. Total pages invariant
        if doc_meta.total_pages != len(self.sections):
            raise ValueError(
                f"PDF metadata total_pages ({doc_meta.total_pages}) does not match "
                f"section count ({len(self.sections)}) in '{self.file_name}'"
            )

        # 3. Section page metadata & sequential order invariant
        normalized_sections: list[DocumentSection] = []
        for idx, sec in enumerate(self.sections):
            try:
                page_meta = PDFPageMetadata.model_validate(sec.metadata)
            except Exception as exc:
                raise ValueError(
                    f"Invalid PDF page metadata in '{self.file_name}' at section index {idx}: {exc}"
                ) from exc

            expected_page_num = idx + 1
            if page_meta.page_number != expected_page_num:
                raise ValueError(
                    f"PDF page sequence error in '{self.file_name}': section index {idx} "
                    f"has page_number {page_meta.page_number}, expected {expected_page_num}"
                )

            # Build normalized section copy without mutating caller-owned objects
            normalized_sec = sec.model_copy(update={"metadata": page_meta.model_dump()})
            normalized_sections.append(normalized_sec)

        # 4. Commit validated metadata and sections
        self.metadata = doc_meta.model_dump()
        self.sections = normalized_sections
        return self
```

### 6.3 Side-Effect Isolation & Resource Safety

- **No Partial Mutation**: Normalization occurs in local variables. If any check fails, an exception is raised before `self.metadata` or caller-provided `DocumentSection` instances are modified.
- **Resource Management**: `PDFExtractor.extract()` retains its `try ... finally: doc.close()` construct. When `ExtractedDocument(...)` raises a `ValidationError` during extraction, the `finally` block is guaranteed to close the PyMuPDF document handle.
- **Ingestion Error Handling**: `IngestionService.ingest_file()` catches and logs `ValidationError` as an extraction failure, re-raising for single-file ingestion and skipping the file during directory ingestion.

---

## 7. Content and Serialization Compatibility

### 7.1 Text Extraction & Structure Preservation

- **Blank Pages**: Pages without text must still produce a `DocumentSection` with `content=""`, `title="Page N"`, and valid `page_number` / `rect` metadata. Blank pages continue to be omitted from `full_text_parts` in `combined_text`, preserving existing formatting contracts.
- **Access Parity**: Public access patterns remain identical:
  ```python
  total = doc.metadata["total_pages"]
  page_num = doc.sections[0].metadata["page_number"]
  rect_coords = doc.sections[0].metadata["rect"]  # Returns [x0, y0, x1, y1]
  ```

### 7.2 Serialization Contracts

1. `model_dump()` / `model_dump(mode="python")`: Returns native Python dictionary representation, preserving `Path` objects and metadata dicts.
2. `model_dump(mode="json")` & `model_dump_json()`: Serializes all fields, encoding `Path` objects as string paths without requiring custom JSON encoders.
3. `model_validate_json()` Round-Trip:
   ```python
   # Round-trip guarantee:
   json_data = doc.model_dump_json()
   restored = ExtractedDocument.model_validate_json(json_data)
   assert restored.file_name == doc.file_name
   assert restored.file_path == doc.file_path  # Reconstructed as Path object
   assert restored.metadata == doc.metadata
   assert len(restored.sections) == len(doc.sections)
   ```
4. **Decoupled from Source Filesystem**: `ExtractedDocument` does not require the source file at `file_path` to exist when validating or deserializing saved extraction archives.

### 7.3 Dataclass to Pydantic Migration Notes

| Aspect | Dataclass (`@dataclass`) | Pydantic (`BaseModel`) | Migration Action |
| --- | --- | --- | --- |
| **Dictionary Export** | `dataclasses.asdict(obj)` | `obj.model_dump()` | Replace `asdict()` with `model_dump()`. |
| **Positional Construction** | Supported (`DocumentSection("t", "c")`) | Keyword preferred (`DocumentSection(title="t", content="c")`) | Update any tests/callers relying on positional args. |
| **Equality Comparison** | Value-based on all fields | Value-based on all fields (`__eq__`) | Full parity preserved. |
| **Field Introspection** | `dataclasses.fields(cls)` | `cls.model_fields` | Update schema introspection callers if present. |

---

## 8. Acceptance Test Matrix

| Category | Test Function / Scenario | Input Condition | Expected Behavior |
| --- | --- | --- | --- |
| **Shared Models** | `test_document_section_valid` | Valid `title`, `content`, `metadata` | Initializes cleanly; `model_dump()` matches. |
| | `test_document_section_extra_forbid` | `DocumentSection(title="A", content="B", unknown_field=123)` | Raises `ValidationError` for unexpected top-level field. |
| | `test_extracted_document_path_coercion`| `file_path="C:/docs/test.pdf"` (str) | Automatically coerced to `pathlib.Path` instance. |
| | `test_model_default_isolation` | Instantiate two instances without args | Metadata dicts and sections lists are independent instances. |
| **PDF Page Metadata** | `test_pdf_page_metadata_valid` | `page_number=1`, `rect=[0.0, 0.0, 612.0, 792.0]` | Validation succeeds; rect normalized to floats. |
| | `test_pdf_page_metadata_integers` | `page_number=1`, `rect=[0, 0, 600, 800]` | Validation succeeds; coordinates converted to `float`. |
| | `test_pdf_page_metadata_negative_coords` | `page_number=1`, `rect=[-10.0, -10.0, 500.0, 700.0]` | Validation succeeds (negative coordinates are valid). |
| | `test_pdf_page_metadata_invalid_page_num` | `page_number=0`, `-1`, `"1"`, `1.5`, or `True` | Raises `ValidationError` (strict integer `>= 1`). |
| | `test_pdf_page_metadata_invalid_rect_len`| `rect=[0, 0, 100]` (3 coords) or `[0, 0, 100, 100, 100]` | Raises `ValidationError` (requires exactly 4 coordinates). |
| | `test_pdf_page_metadata_non_numeric_rect`| `rect=[0, 0, "100", 200]` or `[True, 0, 100, 200]` | Raises `ValidationError` (rejects non-numeric & bools). |
| | `test_pdf_page_metadata_non_finite_rect` | `rect=[0, 0, float("nan"), 100]` or `[0, 0, float("inf"), 100]` | Raises `ValidationError` (rejects NaN and infinity). |
| | `test_pdf_page_metadata_inverted_bounds` | `rect=[100.0, 0.0, 50.0, 200.0]` (x1 < x0) | Raises `ValidationError` with descriptive message. |
| | `test_pdf_page_metadata_extra_preserved` | `extra_tag="custom_data"` | Extra field preserved in `model_dump()`. |
| **PDF Doc Metadata** | `test_pdf_doc_metadata_valid` | `total_pages=5`, `title="Doc"`, `author="A"` | Validation succeeds. |
| | `test_pdf_doc_metadata_none_normalization`| `title=None`, `author=None`, `subject=None` | Normalizes all `None` string fields to `""`. |
| | `test_pdf_doc_metadata_invalid_types` | `total_pages=-1`, `total_pages="5"`, `title=123` | Raises `ValidationError`. |
| | `test_pdf_doc_metadata_zero_pages` | `total_pages=0`, empty sections | Validation succeeds (valid schema-level test). |
| **PDF Invariants** | `test_pdf_invariant_total_pages_mismatch`| `total_pages=2` with 1 section | Raises `ValidationError` / `ValueError` with file name. |
| | `test_pdf_invariant_page_sequence_gap` | Sections with `page_number` 1 and 3 (missing 2) | Raises `ValidationError` noting sequence error at index 1. |
| | `test_pdf_invariant_page_sequence_dup` | Sections with `page_number` 1 and 1 | Raises `ValidationError` noting duplicate page number. |
| | `test_pdf_invariant_page_sequence_swap`| Sections with `page_number` 2 and 1 | Raises `ValidationError` noting out-of-order section. |
| | `test_pdf_invariant_zero_indexed_pages`| Sections with `page_number` 0 and 1 | Raises `ValidationError` (rejects 0-based page numbering). |
| **Isolation & Safety**| `test_pdf_validation_mutation_isolation` | Caller passes section; document construction fails | Caller's original `DocumentSection.metadata` unchanged. |
| | `test_pdf_extractor_closes_on_error` | Mock invalid metadata during extraction | PyMuPDF `doc.close()` executed in `finally` block. |
| **Serialization** | `test_pdf_extraction_json_roundtrip` | Serializes valid PDF record to JSON & reloads | Exact match on content, paths, and metadata dicts. |
| | `test_pdf_load_when_source_deleted` | Delete temporary source PDF; parse stored JSON | Deserialization succeeds without filesystem dependency. |
| **Cross-Format** | `test_docx_pptx_txt_log_unaffected` | Construct DOCX, PPTX, TXT, and custom `.log` docs | Unaffected by PDF-specific checks; all tests pass. |

---

## 9. Implementation Sequence & Detailed Steps

1. **Phase 1: PDF Metadata Schemas (`src/core/pdf_models.py`)**
   - Create `src/core/pdf_models.py` with `PDFPageMetadata` and `PDFDocumentMetadata`.
   - Add unit tests in `tests/test_pdf_models.py` covering all coordinate, page number, string normalization, and extension preservation cases.
2. **Phase 2: Shared Extraction Models & Validator (`src/core/models.py`)**
   - Convert `DocumentSection` and `ExtractedDocument` to `BaseModel` with `ConfigDict(extra="forbid")`.
   - Add the `@model_validator(mode="after")` invariant validation method in `ExtractedDocument`.
   - Update `tests/test_models.py` with shared model validation tests and PDF invariant tests.
3. **Phase 3: Repository Caller Audit & Fixes**
   - Audit all usages of `DocumentSection`, `ExtractedDocument`, and `dataclasses.asdict`.
   - Verify `src/extractors/pdf_extractor.py`, `docx_extractor.py`, `pptx_extractor.py`, `txt_extractor.py`, and `service.py`.
4. **Phase 4: Integration, Ingestion, & Error Handling Tests**
   - Add end-to-end PDF extraction and ingestion tests in `tests/test_extractors.py`.
   - Verify resource cleanup on validation failure using mocks or temporary corrupted files.
   - Test JSON round-trip serialization and deserialization.
5. **Phase 5: Full Regression Validation**
   - Run `pytest` across the complete test suite (`test_models.py`, `test_extractors.py`, `test_llm_pipeline.py`, `test_orchestrator.py`, `test_phase2.py`, `test_docx_generator.py`).
   - Confirm zero regressions in non-PDF extractors, LLM parsers, or document generators.

---

## 10. Completion Criteria & Risk Management

### Definition of Done

- All tests in the Acceptance Test Matrix pass with 100% compliance.
- PDF extraction rejects malformed coordinates, non-integer page numbers, page count mismatches, and page ordering anomalies at instantiation / deserialization.
- Non-PDF extractors (`docx`, `pptx`, `txt`, custom `.log`) continue functioning with zero regressions.
- Existing dictionary metadata access patterns (`doc.metadata["total_pages"]`, `sec.metadata["rect"]`) remain 100% compatible.
- JSON serialization/deserialization functions out of the box with built-in Pydantic v2 methods.

### Risk Analysis & Mitigations

1. **Performance Overhead**: Invariant validation executes once per document extraction boundary in $O(N)$ time where $N$ is page count. For a typical 100-page document, Pydantic v2 (Rust core) executes validation in $< 1\text{ ms}$. Redundant validation loops inside extractor loops are avoided.
2. **Custom Metadata Loss**: Third-party plugins or future extractors adding custom keys are safeguarded by `ConfigDict(extra="allow")` on metadata models.
3. **Immutability Assumptions**: While runtime dictionary mutation after creation is not monitored, `ExtractedDocument.model_validate(doc.model_dump())` provides an explicit re-validation mechanism whenever required.

---

## 11. Separate Follow-up: Application Settings Migration (`src/config.py`)

`src/config.py` currently uses a standard Python dataclass with import-time environment variable evaluation. As an independent follow-up, `AppConfig` can be migrated to `pydantic-settings` to provide centralized type casting, validation, and `.env` support.

### Proposed Architecture for Follow-up

```python
from pathlib import Path
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Centralized application settings and environment configuration."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    app_name: str = "Startup Kit Generator"
    version: str = "0.1.1"
    environment: str = "development"
    debug: bool = False

    # Paths
    input_dir: Path = Path("inputs")
    output_dir: Path = Path("output")
    templates_dir: Path = Path("templates")

    # LLM Configuration
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    azure_openai_api_key: Optional[str] = Field(default=None, alias="AZURE_OPENAI_API_KEY")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4000, ge=100)

    # Offline / Gate Controls
    offline_mode: bool = False
    governance_mode: str = "strict"

    @field_validator("output_dir", mode="after")
    def ensure_output_path(cls, v: Path) -> Path:
        return v
```

This follow-up requires adding `pydantic-settings>=2.0` to `requirements.txt` and updating `src/config.py`. It is non-blocking and decoupled from the extraction validation changes.
