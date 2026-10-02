# Software Specification: Toptal PMO Startup Kit Generator

## 1. Executive Summary
This application is a Python-based backend/CLI tool designed to automate the creation of the Toptal PMO Project Startup Kit. It ingests Statement of Work (SOW) documents (PDF, DOCX), pre-sales presentations (PPTX), and optional context files (TXT). Utilizing a Large Language Model (LLM) for textual fluency, data extraction, and synthesis, it generates standardized project management artifacts in Microsoft Word (`.docx`) format, saved to a designated `output/` directory.

This specification is explicitly driven by the business and functional requirements defined in the `startup_1.md` file, incorporating governance context from `PMO_Governance_Dual_Audience_v3_review.pptx` and the procedural format of the `G-01_On-Board_Talent_PM_DM_PMO_Checklist.docx`.

## 2. Architectural Principles (SOLID)
The application must strictly adhere to SOLID object-oriented design principles. The PyCharm coding agent must structure the codebase accordingly:

*   **Single Responsibility Principle (SRP):** Classes must have only one reason to change. 
    *   *Implementation:* Separate modules for `Ingestion`, `TextExtraction`, `LLMOrchestration`, `DataValidation` (Pydantic), and `DocumentGeneration`. 
*   **Open/Closed Principle (OCP):** Software entities should be open for extension, but closed for modification.
    *   *Implementation:* Use a base `DocumentExtractor` class. To support a new file type in the future, create a new subclass (e.g., `MarkdownExtractor`) rather than modifying the core ingestion engine.
*   **Liskov Substitution Principle (LSP):** Objects of a superclass shall be replaceable with objects of its subclasses without breaking the application.
    *   *Implementation:* Any subclass of `DocumentExtractor` must return a standard `ExtractedText` object, ensuring the `IngestionService` doesn't need to know the specific subclass type.
*   **Interface Segregation Principle (ISP):** No client should be forced to depend on methods it does not use.
    *   *Implementation:* Define narrow abstract base classes (ABCs) or Protocols. For example, `IDocumentWriter` should only contain `write_docx()`, separating it from logging or API interfaces.
*   **Dependency Inversion Principle (DIP):** High-level modules should not depend on low-level modules. Both should depend on abstractions.
    *   *Implementation:* The `StartupKitController` should depend on an `ILLMClient` interface, not a concrete implementation like `OpenAIClient`. Dependencies should be injected via constructors.

## 3. Tech Stack & Dependencies
*   **Language:** Python 3.11+
*   **Data Validation:** `pydantic` (v2)
*   **Document Parsing:** `PyMuPDF` or `pdfplumber` (PDF), `python-docx` (DOCX), `python-pptx` (PPTX).
*   **Document Generation:** `python-docx`
*   **LLM Integration:** `langchain` or native API clients (e.g., `openai`, `google-genai`), utilizing structured outputs (JSON schema) to map directly to Pydantic models.

## 4. Directory Structure
```text
project_root/
├── src/
│   ├── core/               # Interfaces (ABCs) and Pydantic models
│   ├── extractors/         # Concrete extractors (PDF, DOCX, PPTX)
│   ├── llm/                # LLM client implementation and prompt templates
│   ├── generators/         # Word document generation logic
│   └── orchestrator.py     # Main application workflow (Controller)
├── inputs/                 # Drop folder for SOWs, context.txt, and PMO_Governance_Dual_Audience_v3_review.pptx
├── output/                 # STRICT REQUIREMENT: All generated .docx files go here
├── tests/
└── main.py                 # Application entry point
```

## 5. Core Data Models (Pydantic)
Based on `startup_1.md` Section 6, the following Pydantic models must be implemented in `src/core/models.py`.

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

class SourceReference(BaseModel):
    document_name: str
    clause_or_slide: Optional[str]
    confidence_score: float = Field(ge=0.0, le=1.0)

class Deliverable(BaseModel):
    id: str
    description: str
    source_reference: SourceReference
    owner: str = "Unassigned"
    acceptance_criteria: Optional[str]

class Milestone(BaseModel):
    id: str
    description: str
    external_date: Optional[date]
    internal_buffer_date: Optional[date]
    source_reference: SourceReference

class RiskAssumption(BaseModel):
    type: str = Field(pattern='^(Risk|Assumption|Issue|Dependency)$')
    description: str
    owner: str
    status: str
    source_reference: SourceReference

class StartupKitBaseline(BaseModel):
    project_name: str
    governance_tier: str = Field(pattern='^(Guided|Partnered|Elevated)$')
    contract_type: str
    deliverables: List[Deliverable]
    milestones: List[Milestone]
    raid_items: List[RiskAssumption]
    open_questions: List[str]
```

## 6. System Workflow & LLM Integration

### 6.1. Ingestion Phase
*   The `IngestionService` scans the `inputs/` directory.
*   **PDF/DOCX Extractor:** Extracts raw text from SOWs.
*   **PPTX Extractor:** Specifically targets files like `PMO_Governance_Dual_Audience_v3_review.pptx` to extract governance context, speaker notes, and slide text.
*   **TXT Extractor:** Reads `context.txt` for ad-hoc instructions or clarifications.

### 6.2. LLM Processing Phase
*   The raw text is chunked and passed to the `ILLMClient`.
*   **System Prompt:** Must instruct the LLM to act as a PMO Startup Kit generator, strictly adhering to the extraction rules from `startup_1.md`. It must prioritize finding missing data and explicitly tagging it as placeholders rather than hallucinating details.
*   The LLM must be forced to output valid JSON matching the Pydantic `StartupKitBaseline` schema (using function calling or JSON mode).

### 6.3. Generation Phase (`output/` directory)
*   The `DocumentGenerator` implements `IDocumentWriter`.
*   It takes the validated Pydantic models and uses `python-docx` to generate formatted Word documents.
*   **Output File:** The system generates a single, consolidated Word document in the `output/` directory named `[Project_Name]_Startup_Kit.docx`.
*   **Checklist Alignment:** The generated document must include a formatted section mirroring the `G-01_On-Board_Talent_PM_DM_PMO_Checklist.docx` to facilitate the On-Board Talent PM / DM gate review.

## 7. Business Rules Enforcement
The PyCharm agent must ensure the logic handles these rules from `startup_1.md`:
1.  **No Hallucination:** If a deliverable's acceptance criteria are missing from the SOW, the LLM must map `acceptance_criteria` to `None`, which the Generator will render as `[CONFIRMATION REQUIRED]`.
2.  **Traceability:** Every item extracted must populate the `SourceReference` Pydantic model.
3.  **Tier Tailoring:** The application must adjust the generated output based on the extracted Governance Tier (Guided, Partnered, Elevated) defined in the inputs.