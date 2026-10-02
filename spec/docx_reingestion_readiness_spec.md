# Software Specification: Startup Kit DOCX Re-ingestion & Readiness Recalculation

## 1. Executive Summary

This specification defines the architectural design, functional requirements, and implementation plan for adding a dedicated **DOCX Re-ingestion and Readiness Score Recalculation Pipeline** to the Toptal PMO Startup Kit Generator.

Currently, the generator ingests raw Statement of Work (SOW) documents (PDF, DOCX), presentation decks (PPTX), and context notes (TXT) to produce an initial `[Project_Name]_Startup_Kit.docx` report with an initial Startup Readiness Score and G-01 Gate Decision. In standard PMO governance workflows, the PMO Lead, Delivery Manager, and project stakeholders subsequently review and edit the generated `.docx` file—filling in previously unassigned leadership names, confirming milestone delivery dates, establishing objective acceptance criteria, assigning RAID log owners, and resolving open contract questions.

This feature introduces an execution mode allowing users to re-ingest an updated `*_Startup_Kit.docx` file **exclusively** (bypassing all other input documents in `inputs/`), deterministically parse the updated project baseline, recalculate the Startup Readiness Score and dimensional breakdowns, re-evaluate the G-01 Gate Decision status, and regenerate an updated, fully synchronized Word report and downstream PMO toolkits.

---

## 2. Problem Statement & Business Objectives

### 2.1 Problem Statement
1. **Unclosed Feedback Loop**: When teams update the generated `*_Startup_Kit.docx` report to resolve gaps identified during the initial gate review, there is no automated mechanism to re-evaluate the document and recalculate the readiness score without re-ingesting the original input SOWs/decks.
2. **Redundant Processing & Non-Determinism**: Ingesting the entire `inputs/` folder again causes unnecessary LLM extraction passes, potential token costs, and risks overwriting manual refinements made directly in the Word report.
3. **Workflow Friction**: Delivery teams lack an interactive CLI option to specify a target `*_Startup_Kit.docx` file for rapid re-evaluation during G-01 Mobilization Gate reviews.

### 2.2 Business & Operational Objectives
- **Targeted Single-File Ingestion**: Ingest *only* the user-specified `*_Startup_Kit.docx` document without scanning or reading other files in `inputs/`.
- **Deterministic Baseline Extraction**: Extract structured data (charter, deliverables, milestones, RAID log, talent roster, checklist items, and open questions) directly from the `.docx` tables and structured sections without mandatory LLM calls.
- **Accurate Readiness Recalculation**: Recompute the 4 readiness dimensions (`mandatory_g01_controls`, `deliverable_acceptance_rigor`, `talent_staffing_readiness`, `commercial_risk_mitigation`), apply open exception penalties, and determine the updated G-01 Gate mobilization decision (Green, Amber, Red).
- **Interactive & Headless CLI Support**: Provide an interactive prompt in the CLI to enter the path and name of the file to ingest, alongside non-interactive CLI flags for CI/CD automation.
- **Artifact Synchronization**: Update the generated Word document and optionally re-export downstream PMO workbook payloads (CSV/JSON).

---

## 3. Architectural Principles (SOLID)

The implementation must strictly adhere to object-oriented SOLID principles:

- **Single Responsibility Principle (SRP)**:
  - `StartupKitDocxParser` has the sole responsibility of reading a `*_Startup_Kit.docx` file and deserializing its structured tables and paragraphs into domain models.
  - `BaselineAggregator` retains sole responsibility for business rules, score calculation, and gate decision logic.
  - `DocxGenerator` retains sole responsibility for formatting and rendering the Word document.
  - `StartupKitController` orchestrates the workflow.
- **Open/Closed Principle (OCP)**:
  - The ingestion architecture is extended with a specialized `IDocxBaselineParser` interface without modifying the existing multi-format document extractors (`PdfExtractor`, `PptxExtractor`, `TxtExtractor`).
- **Liskov Substitution Principle (LSP)**:
  - Extracted baselines from `.docx` adhere strictly to the existing `StartupKitBaseline` schema, ensuring downstream consumers (`DocxGenerator`, `export_all_pmo_tools`) operate without modification.
- **Interface Segregation Principle (ISP)**:
  - Define a narrow `IStartupKitDocxParser` interface specific to baseline extraction from `.docx`, keeping it segregated from generic document text extractors.
- **Dependency Inversion Principle (DIP)**:
  - High-level orchestration controllers depend on the `IStartupKitDocxParser` and `IDocumentWriter` abstractions rather than concrete parsing implementations.

---

## 4. System Architecture & Workflow Comparison

```text
====================================================================================================
MODE 1: INITIAL GENERATION PIPELINE (From Raw SOWs / Presentations)
====================================================================================================
inputs/ (PDF, DOCX, PPTX, TXT)
   │
   ▼
IngestionService ──► Multi-Pass LLM Extractors ──► BaselineAggregator ──► DocxGenerator ──► *_Startup_Kit.docx
                                                                                               │
                                                                                               ▼
                                                                                   [Human Review & Updates]
                                                                                   (Fill roles, dates, criteria)
                                                                                               │
====================================================================================================           │
MODE 2: RE-INGESTION & RECALCULATION PIPELINE (From Updated Startup Kit DOCX)                  │
====================================================================================================           │
                                                                                               │
Updated *_Startup_Kit.docx ◄───────────────────────────────────────────────────────────────────┘
   │
   ▼
StartupKitDocxParser (Deterministic Table & Section Deserialization - No Raw Ingestion)
   │
   ▼
StartupKitBaseline (Populated with updated roles, acceptance criteria, milestone dates, RAID owners)
   │
   ▼
BaselineAggregator.recalculate()
   ├── Dim 1: Mandatory G-01 Controls (40%) & Exception Deductions
   ├── Dim 2: Deliverable & Acceptance Rigor (25%)
   ├── Dim 3: Talent & Staffing Readiness (20%)
   └── Dim 4: Commercial & Risk Mitigation (15%)
   │
   ▼
GateDecision & ReadinessScore Updated (e.g., Amber 72.5% ──► Green 92.0% Approved for Mobilize)
   │
   ▼
DocxGenerator.write_docx() ──► Updated *_Startup_Kit.docx (and optional PMO export payloads)
```

---

## 5. Detailed Functional Requirements

### 5.1 CLI Interaction & User Experience

#### REC-DOCX-01: Interactive CLI Prompting Flow
When launched in default interactive mode (`python main.py`):
1. **Pipeline Execution Mode Selection**:
   The CLI shall prompt the user to choose the operating mode:
   ```text
   Select Startup Kit execution mode:
     [1] Initial Generation (Ingest raw SOWs/decks from inputs directory)
     [2] Re-evaluate & Ingest updated *_Startup_Kit.docx
   Enter choice [1/2, default: 1]: 
   ```
2. **Re-ingestion File Path Prompt**:
   If Option 2 is selected (or if triggered via flags), the CLI shall prompt:
   ```text
   Enter path to updated *_Startup_Kit.docx file [default: output/Project_Startup_Kit.docx]: 
   ```
   - If the user presses `Enter` on an empty line, the CLI falls back to the default path (or searches `output/` for the most recently modified `*_Startup_Kit.docx`).
   - If a valid relative or absolute file path is entered, the CLI resolves and validates the path.
   - If the file does not exist or does not have a `.docx` extension, a clear validation error is displayed and the prompt re-queries or exits gracefully.
3. **Output Destination Prompt**:
   ```text
   Enter output directory or file path for regenerated report [default: <same as input file>]: 
   ```
4. **Leadership Overrides (Optional)**:
   The CLI allows supplying optional leadership role overrides (`PMO Lead`, `Delivery Lead`, `Talent PM`) or preserving the values parsed directly from the `.docx`.

#### REC-DOCX-02: Command-Line Flags
The CLI shall support dedicated non-interactive command-line arguments:

| Flag | Type | Description | Default |
|---|---|---|---|
| `--reingest-docx` / `--docx-file` | `Path` | Path to an existing `*_Startup_Kit.docx` to re-ingest and recalculate. | `None` |
| `--output-dir` | `Path` | Output directory for regenerated document and exports. | Parent dir of input `.docx` |
| `--output-file` | `Path` | Explicit target path for regenerated `.docx`. | Overwrites input `.docx` |
| `--non-interactive` | `Flag` | Disable prompts; requires `--reingest-docx` when running re-evaluation mode. | `False` |
| `--export-tools` | `Flag` | Re-export downstream PMO CSV/JSON toolkits upon recalculation. | `False` |

#### REC-DOCX-03: Single Document Ingestion Constraint
When re-ingesting a `.docx` file:
- The system **SHALL NOT** scan or ingest any files from `inputs/`.
- The system **SHALL NOT** execute raw document text chunking or multi-pass LLM SOW parsers.
- Only the single specified `.docx` file is opened and processed.

---

### 5.2 DOCX Extraction & Deserialization Engine (`StartupKitDocxParser`)

A new parser class `StartupKitDocxParser` in `src/extractors/startup_kit_docx_parser.py` shall implement deterministic parsing of the standard Section 4 Word document structure.

#### REC-DOCX-04: Metadata & Header Table Extraction
- **Location**: Metadata table preceding Layer 1.
- **Fields Extracted**:
  - `project_name`: Extracted from Subtitle or Metadata row `Project Name`.
  - `client_name`: Extracted from `Client Sponsor`.
  - `governance_tier`: `Guided`, `Partnered`, or `Elevated`.
  - `contract_type`: `Time and Materials`, `Fixed Bid`, etc.
  - `delivery_manager`: Delivery Lead / Manager name.
  - `talent_pm`: Talent PM name.
  - `pmo_lead`: PMO Lead name.
  - `sla_met`: Evaluated from `1-Day SLA Status` (`Met` -> `True`, `Breached` -> `False`).
  - `workflow_state`: Extracted string.

#### REC-DOCX-05: G-01 Checklist Table Extraction
- **Location**: Executive Readiness Gateway table (Section 4).
- **Table Detection**: Identified by header containing `Item ID`, `Gate Criterion`, `Owner`, `Status`.
- **Row Mapping**: For each row (`G01-01` through `G01-15`):
  - `item_id`: e.g., `G01-01`
  - `gate_criterion`: Criterion description.
  - `related_section4_artifact`: Artifact name.
  - `owner`: Assigned owner string.
  - `due_date`: Parsed date or `None`.
  - `status`: Parsed status (`Approved`, `Complete`, `Approved with Exception`, `In Progress`, `Review Required`, `Confirmation Required`, `Exception Required`, `Rework Required`, `Not Started`).
  - `evidence`: Parsed evidence description.
  - `exception_details`: Parsed exception notes.
  - `exception_required`: `True` if `status == "Exception Required"` or if `exception_details` contains text.

#### REC-DOCX-06: Layer 1 – Executive Startup Pack Extraction
- **Project Startup Charter**: Extracted from Charter table (Business Objectives, Success Criteria, Scope Inclusions/Exclusions).
- **SOW Interpretation Summary**: Executive summary, client objectives, and key commercial conditions.
- **Milestone Delivery Plan**:
  - Table columns: `Milestone ID`, `Milestone Description`, `Target Date / Window`, `Internal Buffer Date`, `Owner`, `Status`.
  - Dates mapped to `date` objects. Placeholder strings (`TBD`, `Unassigned`) mapped to `None`.

#### REC-DOCX-07: Layer 2 – Delivery Control Pack Extraction
- **Scope Decomposition / Backlog Seed**: User stories / epics list and out-of-scope boundaries.
- **Deliverables and Acceptance Matrix**:
  - Table columns: `ID`, `Deliverable Name & Description`, `Internal Owner`, `Acceptance Criteria`, `Client Approver Role`, `Sign-off Mechanism`.
  - `acceptance_criteria`: Extracted text. Markers like `[CONFIRMATION REQUIRED]` indicate unconfirmed criteria.
  - `owner`: Extracted string. Values like `[UNASSIGNED - TO BE CONFIRMED]` indicate unassigned status.
  - `client_approver`: Extracted string.
- **RAID Log & Decision Log Seed**:
  - Table columns: `Type`, `ID`, `Description`, `Owner`, `Status`, `Mitigation / Strategy`, `Impact / Severity`.
  - Types mapped to `Risk`, `Assumption`, `Issue`, `Dependency`.
- **Communications and Reporting Plan**: Governance cadence, reporting frequency, and distribution channels.

#### REC-DOCX-08: Layer 3 – Assurance Pack Extraction
- **Stakeholder & RACI Model**: Key stakeholders and decision rights.
- **Commercial & Margin Guardrails**: Contract terms, work-at-risk limits, invoicing rules.
- **Talent Onboarding Record & Delivery Roster**:
  - Leadership roles: `delivery_manager`, `talent_pm`, `pmo_lead`.
  - Talent Roster Table columns: `Role / Title`, `Talent Name`, `Start Date`, `Status` (`Confirmed` vs `Pending`), `Laptop / Access Status`.

#### REC-DOCX-09: Open Questions & Clarifications Extraction
- Parsed from the Open Questions callout box or list items.
- Bullet points without marked resolution are extracted into `open_questions: List[str]`.
- If marked as `[RESOLVED]` or deleted by the user, they are excluded from the active open questions count.

---

### 5.3 Readiness Score Recalculation & Gate Decision Engine

The recalculated baseline is processed through `BaselineAggregator.recalculate_readiness()`:

```text
Readiness Score = (0.40 × Dim1 + 0.25 × Dim2 + 0.20 × Dim3 + 0.15 × Dim4) × 100
```

#### REC-DOCX-10: Mathematical Recalculation Rules
1. **Dimension 1 (`mandatory_g01_controls` - 40% Weight)**:
   - Evaluates all 15 checklist items using standard point weights:
     - `Complete` / `Approved`: `1.0`
     - `Approved with Exception`: `0.85`
     - `In Progress` / `Review Required`: `0.50`
     - `Confirmation Required`: `0.30`
     - `Exception Required`: `0.20`
     - `Rework Required` / `Not Started`: `0.0`
   - Applies open exception penalty: `-0.03` ($3\%$) per item with `exception_required == True` or `status == "Exception Required"`.
   - Clamped to $[0.0, 1.0]$.
2. **Dimension 2 (`deliverable_acceptance_rigor` - 25% Weight)**:
   - For each deliverable in `baseline.deliverables`:
     - `+0.40`: Objective acceptance criteria defined (no `[CONFIRMATION REQUIRED]`).
     - `+0.30`: Explicit internal owner assigned (not `UNASSIGNED`).
     - `+0.30`: Explicit client approver role assigned (not `UNASSIGNED`).
   - Dimension score is the mean across all deliverables.
3. **Dimension 3 (`talent_staffing_readiness` - 20% Weight)**:
   - `+0.35`: Confirmed, named `delivery_manager`.
   - `+0.35`: Confirmed, named `talent_pm`.
   - `+0.30`: Proportional to `confirmed_talent / total_talent` in roster (or `0.15` default if no roster).
4. **Dimension 4 (`commercial_risk_mitigation` - 15% Weight)**:
   - `+0.40`: Proportional to `owned_raid_items / total_raid_items`.
   - `+0.30`: Commercial guardrails present and baselined.
   - `+0.30`: Baseline ambiguity credit with `5%` (`-0.05`) penalty per unresolved question:
     $$\text{Penalty} = 0.30 \times \max(0.0, 1.0 - (\text{len}(\text{open\_questions}) \times 0.05))$$

#### REC-DOCX-11: Gate Decision Status Transition
- **`Approved for Mobilize` (Green)**: Score $\ge 85.0\%$ **AND** $0$ open exceptions.
  - `workflow_state`: `"Ready for G-01 Gate Review"` or `"Approved for Mobilize"`.
- **`Approved with Exception` (Amber)**: Score between $70.0\%$ and $84.9\%$ OR Score $\ge 85.0\%$ with $\ge 1$ open exception.
  - `workflow_state`: `"Approved with Exception"`.
- **`Rework Required` (Red)**: Score $< 70.0\%$.
  - `workflow_state`: `"Clarification Pending"` or `"Rework Required"`.

---

### 5.4 Document Synchronization & Re-generation

#### REC-DOCX-12: Document Rewrite & Backup
- **Destination**: Replaces the target `.docx` file (or writes to `--output-dir` / `--output-file`).
- **Backup Option**: If writing in-place to the same file, the controller creates a timestamped backup (e.g., `[Project]_Startup_Kit_backup_YYYYMMDD_HHMMSS.docx`) before overwriting.
- **Visual Updates**:
  - Document Title and Metadata Header updated with recalculated workflow state.
  - Executive Readiness Gateway callout box updated with new Readiness Score percentage, dimensional progress bars, and gate status badge.
  - G-01 Checklist table updated with recalculated statuses and exception counts.
- **PMO Tool Export**: If `--export-tools` is enabled, regenerates the downstream CSV and JSON seed payloads in `output/` with the recalculated data.

---

## 6. Data Models and Interfaces

### 6.1 Parser Interface (`src/core/interfaces.py`)

```python
from abc import ABC, abstractmethod
from pathlib import Path
from src.core.models import StartupKitBaseline

class IStartupKitDocxParser(ABC):
    """Interface for extracting a structured StartupKitBaseline from an existing Startup Kit DOCX."""

    @abstractmethod
    def parse_startup_kit_docx(self, file_path: Path) -> StartupKitBaseline:
        """Parse an existing *_Startup_Kit.docx file into a StartupKitBaseline model."""
        pass
```

### 6.2 Recalculation Interface (`src/llm/aggregator.py`)

```python
class BaselineAggregator:
    # Existing aggregate() method ...

    def recalculate_readiness(self, baseline: StartupKitBaseline) -> StartupKitBaseline:
        """Recalculate dimensional readiness scores and G-01 Gate Decision for an existing baseline."""
        # Executes scoring math and gate classification across baseline entities
        ...
```

---

## 7. Error Handling & Edge Cases

| Failure Scenario | System Behavior | Recovery Action |
|---|---|---|
| **File not found** | Raises `FileNotFoundError` with clear path in CLI. | User re-enters valid path in prompt. |
| **Invalid file format (not `.docx`)** | Raises `ValueError: Target file must be a .docx file`. | CLI informs user and requests a `.docx` file. |
| **Non-Startup Kit Word doc ingested** | Parser detects missing metadata table or missing G-01 checklist. | Raises `ValueError: Ingested Word document does not match expected Startup Kit schema`. |
| **Corrupted table or missing columns** | Case-insensitive header matching with fuzzy column detection. | Falls back to default values for missing columns without crashing. |
| **User removed all deliverables/milestones** | Dimension score evaluates safely to `0.0` without division by zero. | Mathematical scoring clamps denominators: `max(1, len(items))`. |
| **Unrecognized checklist status text** | Parser maps unknown strings to `0.5` (`Review Required`) default. | Logs warning and assigns intermediate point weight. |

---

## 8. Implementation Plan & File Modifications

### Phase 1: Core Models & Interfaces
1. **`src/core/interfaces.py`**:
   - Add `IStartupKitDocxParser` interface.
2. **`src/core/models.py`**:
   - Ensure all models support serialization/deserialization with default fallback values.

### Phase 2: DOCX Deserialization Parser
3. **`src/extractors/startup_kit_docx_parser.py`** (New File):
   - Implement `StartupKitDocxParser(IStartupKitDocxParser)`.
   - Implement helper methods: `_parse_metadata_table()`, `_parse_g01_table()`, `_parse_deliverables_table()`, `_parse_milestones_table()`, `_parse_raid_table()`, `_parse_talent_table()`, `_parse_open_questions()`.

### Phase 3: Aggregator Recalculation Logic
4. **`src/llm/aggregator.py`**:
   - Add `recalculate_readiness(baseline: StartupKitBaseline) -> StartupKitBaseline` method to isolate scoring logic for both fresh aggregations and re-ingestions.

### Phase 4: Orchestrator Integration
5. **`src/orchestrator.py`**:
   - Update `StartupKitController` with `run_reingest(docx_path: Path, output_dir: Optional[Path], ...)` method.
   - Enforce single-file ingestion constraint (bypass `IngestionService.ingest_directory()`).

### Phase 5: CLI & Interactive Prompts
6. **`main.py`**:
   - Add `--reingest-docx` / `--docx-file` argument to `parse_args()`.
   - Update interactive prompt workflow to allow selecting between New Generation Mode and DOCX Re-ingestion Mode.
   - Add `prompt_reingest_file()` helper for path resolution.

### Phase 6: Documentation & Testing
7. **`tests/test_docx_reingestion.py`** (New File):
   - Unit tests for table parsing, empty fields, corrupted rows, and status mapping.
   - Integration tests verifying score increases when unassigned roles/dates/criteria are filled.
   - CLI tests verifying interactive and flag-driven re-ingestion.
8. **`README.md`**:
   - Document the DOCX re-evaluation feature, interactive prompts, and CLI flag examples.

---

## 9. Verification & Acceptance Criteria

- [ ] **Single Document Ingestion**: Running re-ingestion does not read any files from `inputs/` or invoke LLM extraction passes.
- [ ] **Interactive CLI**: Interactive prompt allows entering the path/name of `*_Startup_Kit.docx` with default fallback.
- [ ] **Flag Support**: Non-interactive command `python main.py --reingest-docx output/Project_Startup_Kit.docx --non-interactive` successfully re-evaluates the baseline.
- [ ] **Deterministic Score Recalculation**:
  - Replacing `[UNASSIGNED - TO BE CONFIRMED]` with named roles increases Dimension 3.
  - Adding acceptance criteria to deliverables increases Dimension 2.
  - Setting milestone dates increases Dimension 1 compliance.
  - Assigning RAID owners and removing open questions increases Dimension 4.
  - Score reaching $\ge 85.0\%$ with 0 open exceptions transitions gate to `Approved for Mobilize` (Green).
- [ ] **Document Regeneration**: The regenerated Word document reflects the new score, updated checklist table, and refreshed callout badges.
- [ ] **Automated Test Suite**: 100% pass rate across all new unit/integration tests and existing test suite.
