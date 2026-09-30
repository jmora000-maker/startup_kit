# Toptal PMO Startup Kit Generator

Automated project onboarding and readiness toolkit. The PMO Startup Kit Generator ingests project documentation, client agreements, and kickoff presentations to extract structured project management artifacts via LLMs and automatically generate standardized, self-contained Word (`.docx`) Startup Kit reports, companion Startup Readiness Checklist documents, and PMO Operating System seed data.

---

## Key Features

- **Multi-Format Ingestion & Pydantic v2 Validation**: Ingests project inputs across multiple file formats including PDF (`.pdf`), Word (`.docx`), PowerPoint (`.pptx`), and plain text (`.txt`). Enforces strict runtime validation at extraction boundaries, including PDF coordinate geometry and sequential page invariants.
- **Concurrent Multi-Pass Structured LLM Extraction**: Executes independent domain extraction passes concurrently via thread pooling, reducing full baseline extraction runtime from ~9 minutes to under 1 minute.
- **Anthropic Claude Primary Engine with OpenAI Fallback**: Leverages Anthropic Claude (`claude-sonnet-5-5` by default) with automatic model aliasing, thinking-block content filtering, and schema complexity caching. Seamlessly fails over to OpenAI (`gpt-4o`) if network or authentication issues arise.
- **Self-Contained & Concise Report Generation**: Produces clean, concise, and document-agnostic report text. Descriptions and action items are direct and self-contained so that stakeholders can immediately understand the project baseline without requiring access to source contracts or external documents.
- **Comprehensive Project Baseline Domains**:
  - Project Charter & Executive Summary
  - Scope Decomposition & Exclusions (Work Packages)
  - Deliverables & Acceptance Criteria (1-to-1 Traceability)
  - Milestones & Delivery Roadmap (with Internal Buffers)
  - RAID Logs (Risks, Assumptions, Issues, Dependencies)
  - Key Baseline Decisions Log & Scope Rules
  - Stakeholder Matrix & Decision Rights
  - Governance Tiers (Guided, Partnered, Elevated) & Communications Plans
  - Talent Onboarding Checklist & Resourcing Records
- **Authoritative Startup Readiness Scoring Engine**: Centralized, deterministic 4-dimension mathematical engine (`ReadinessScoringEngine`) calculating composite readiness scores, dimensional breakdowns, gate review statuses, and quantified score recovery potential.
- **Structured Action Required Mapping & 1-to-1 In-Artifact Integration**: Generates discrete, 1-to-1 mapped action items (`ACT-01`, `ACT-02`, etc.) for open exceptions and clarifications, embedding yellow-highlighted remediation badges directly inside Section 4 Layer 1, Layer 2, and Layer 3 artifact table cells without cell background shading alteration.
- **Dual Standardized Word Document Generation**: Produces two professionally styled, companion Microsoft Word documents:
  1. `<Project_Name>_Startup_Kit.docx`: Contains the Executive Header Metadata, `Startup Kit Readiness Score: [score]%` banner, and Section 4 Artifacts organized into Layer 1 (Foundational), Layer 2 (Execution), and Layer 3 (Governance & Operational) tables.
  2. `<Project_Name>_Startup_Readiness_Checklist.docx`: Standalone executive governance document housing:
     - **Executive Readiness Gateway**: Gate Decision Dashboard & 15-Row G-01 Checklist Table with remediation guidance.
     - **Commercial and Margin Guardrails Table**: Contract type implications, billing/consumption assumptions, staffing exposure rules, approved/non-approved & work-at-risk rules (PMO Lead owned), change control routing (`PMO Lead leads → DM aligns client → client approves → Contracting issues change order`), budget vs. actuals variance baselines, margin risk indicators, and escalation thresholds.
     - **Actionable Questions Table**: Prioritized actionable clarification questions and target focus areas formed directly from `QUESTIONS_PROMPT`.
     - **Contract Ambiguities Table**: Anomaly tracking, clause citations, risk & margin impact, and recommended client clarifications formed directly from `CONTRACT_CONFLICTS_PROMPT`.
- **Word Re-ingestion & Rescoring Engine**: Re-evaluates edited Word documents (`--reingest-docx`), automatically detecting and synchronizing companion checklist documents, dynamically recalculating scores across all 4 dimensions, and clearing resolved action items without re-running LLM extraction.
- **Executive CLI Readiness Telemetry**: Outputs a formatted, color-coded summary dashboard in the terminal immediately following document generation and re-ingestion passes.
- **Project Delivery Workbook**: Default Excel output with a Project Schedule by phase workstream, a four-level WBS with deliverable work packages and milestone acceptance, and a consolidated delivery RAID Log, all built from the SOW delivery baseline. Word documents are written on request with `--kit`, `--checklist`, or `--all`. *(Note: Generate the Project Delivery Workbook for an approved Kit with `--reingest-docx`, because regenerating from the SOW can renumber deliverables and work packages.)*
- **Offline / Mock Mode**: Fully functional offline mock client for local testing and deterministic validation without requiring LLM API credentials.
- **Automated Versioning**: Configured with `bump-my-version` for semantic versioning.

---

## Project Structure

```text
Startup_Kit/
├── inputs/                 # Input directory for SOWs, decks, and contracts (.pdf, .docx, .pptx, .txt)
├── output/                 # Output directory for generated Word reports and toolkits
├── src/
│   ├── config.py           # Application settings and environment configuration
│   ├── orchestrator.py     # End-to-end pipeline execution controller
│   ├── version.py          # Current application version
│   ├── core/               # Domain interfaces, extraction models, and PDF metadata schemas
│   │   ├── interfaces.py   # Abstract extractor and LLM interfaces
│   │   ├── models.py       # Pydantic domain models, baselines, and action items
│   │   └── pdf_models.py   # PDF page and document coordinate validation models
│   ├── extractors/         # File parsers (PDF, DOCX, PPTX, TXT), Word parser, and ingestion service
│   │   ├── base.py         # Extractor base classes
│   │   ├── docx_extractor.py # Word document extractor
│   │   ├── pdf_extractor.py  # PyMuPDF coordinate-aware PDF extractor
│   │   ├── pptx_extractor.py # PowerPoint presentation extractor
│   │   ├── service.py      # Multi-format ingestion coordinator
│   │   ├── startup_kit_docx_parser.py # Round-trip Word report parser for re-evaluation
│   │   └── txt_extractor.py  # Plain text extractor
│   ├── generators/         # Word document builder, formatting, G-01 checklist, and data exporters
│   │   ├── checklist.py    # Authoritative 15-row G-01 checklist generator
│   │   ├── docx_generator.py # Word document builder and table renderer
│   │   ├── pmo_workbook/   # Excel Project Delivery Workbook generator
│   │   └── formatting.py   # Style and visual formatting utilities
│   ├── llm/                # LangChain LLM client, prompts, parsers, and aggregation logic
│   │   ├── aggregator.py   # Baseline aggregator and readiness scoring bridge
│   │   ├── client.py       # OpenAI LangChain and Mock LLM clients
│   │   ├── parsers.py      # Domain extractors and Pydantic schema parsers
│   │   └── prompts.py      # System and domain-specific extraction prompts
│   └── scoring/            # Centralized readiness scoring engine and CLI telemetry reporter
│       ├── readiness_engine.py  # 4-dimension scoring, action mapping, and gate decision logic
│       └── cli_reporter.py      # Console dashboard and ANSI telemetry output
├── tests/                  # Comprehensive unit, integration, and regression test suite
├── .bumpversion.toml       # Version management configuration
├── main.py                 # CLI entry point
├── requirements.txt        # Python package dependencies
└── README.md               # Project documentation
```

---

## Installation & Setup

### Prerequisites

- Python 3.10+ (Python 3.11+ recommended)
- Git

### 1. Clone the Repository & Set Up Virtual Environment

```bash
# Clone the repository
git clone <repository-url>
cd Startup_Kit

# Create and activate a virtual environment
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# On Linux/macOS:
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the project root directory (or copy from `.env.example`):

```ini
# Primary Provider: Anthropic Claude (Default)
ANTHROPIC_API_KEY=sk-ant-api03-your-anthropic-key-here
ANTHROPIC_MODEL=claude-sonnet-5-5
LLM_PROVIDER=anthropic

# Secondary / Fallback Provider: OpenAI
OPENAI_API_KEY=sk-proj-your-openai-key-here
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.0

# LLM Generation Parameters
TEMPERATURE=0.0
MAX_TOKENS=16384

# Directory Paths (Optional overrides)
INPUTS_DIR=inputs
MOCK_INPUTS_DIR=inputs/SOWs/Test
OUTPUT_DIR=output
MOCK_OUTPUT_DIR=output/Reports/Test

# Governance & Contract Defaults (Optional)
DEFAULT_GOVERNANCE_TIER=Partnered
DEFAULT_CONTRACT_TYPE=Time and Materials
```

#### Provider Precedence & Fallback Architecture
- **Primary Execution**: By default (`LLM_PROVIDER=anthropic`), the system routes extraction passes to Anthropic Claude (`claude-sonnet-5-5`).
- **Automatic Dual-Provider Failover**: If Anthropic encounters network timeouts, rate limits (429), or authentication errors, the client automatically falls back to OpenAI (`gpt-4o`) without halting execution.
- **Offline Mock**: If neither API key is configured or when `--mock` is specified, the system executes using deterministic local mock extraction with zero API cost.

---

## Usage

Place your project documentation (SOWs, presentation decks, contracts) into the `inputs/` folder (or specify a custom path using `--inputs-dir`).

### Run with Anthropic Claude (Default)

```bash
# Uses ANTHROPIC_API_KEY from .env / environment
python main.py

# Or pass Anthropic API key explicitly via CLI
python main.py --anthropic-api-key "sk-ant-api03-your-key-here"
```

### Run with OpenAI LLM

```bash
# Select OpenAI provider via flag
python main.py --openai

# Or specify provider and API key directly
python main.py --provider openai --openai-api-key "sk-proj-your-key-here"
```

### Run in Offline Mock Mode (No API Key Required)

To verify the generation pipeline deterministically without external API calls:

```bash
python main.py --mock
```

### Re-evaluate and Rescore an Updated Word Report

To re-ingest an edited `*_Startup_Kit.docx` and recalculate the Startup Readiness Score:

```bash
python main.py --reingest-docx output/Project_Startup_Kit.docx --non-interactive
```

### Interactive vs Non-Interactive Execution

- **Interactive Mode (Default)**:
  When launched without `--non-interactive` or `--reingest-docx`, the CLI prompts:
  1. `Execution Mode`: Select between `[1] Initial Generation` and `[2] Re-evaluate & Ingest updated *_Startup_Kit.docx`.
  2. If Mode 1:
     - `inputs directory` (default: `inputs/`)
     - `output directory` (default: `output/`)
     - `PMO Lead` name (default: `[UNASSIGNED - TO BE CONFIRMED]`)
     - `Delivery Lead` name (default: `[UNASSIGNED - TO BE CONFIRMED]`)
     - `Talent PM` name (default: `[UNASSIGNED - TO BE CONFIRMED]`)
  3. If Mode 2:
     - `path to updated *_Startup_Kit.docx file` (path/filename is required, no default, or type 'exit' to quit)
     - Optional role name overrides.
  Pressing `Enter` accepts the default value for directory and role prompts. Inverted caps-lock name entries (e.g. `jAMES`, `tINA`) are automatically normalized to title casing.

- **Non-Interactive Mode**:
  Pass `--non-interactive` to disable all terminal prompts and automatically use configured defaults for any unspecified directories or roles.

### Command-Line Arguments

| Flag | Type | Description | Default |
|---|---|---|---|
| `--provider` / `--llm-provider` | Choice | LLM provider to use (`anthropic`, `openai`, `claude`, `gpt`) | `anthropic` (from `LLM_PROVIDER`) |
| `--anthropic` / `--claude` | Flag | Use Anthropic Claude as the LLM provider | `True` (default provider) |
| `--openai` / `--open-ai` | Flag | Use OpenAI as the LLM provider | `False` |
| `--api-key` / `--anthropic-api-key` | String | Anthropic API Key (overrides `ANTHROPIC_API_KEY` in env/`.env`) | `config.anthropic_api_key` |
| `--openai-api-key` | String | OpenAI API Key (overrides `OPENAI_API_KEY` in env/`.env`) | `config.openai_api_key` |
| `--model` | String | LLM model name (e.g., `claude-sonnet-5-5`, `gpt-4o`) | `claude-sonnet-5-5` (Anthropic) / `gpt-4o` (OpenAI) |
| `--reingest-docx` / `--docx-file` | Path | Path to existing `*_Startup_Kit.docx` to re-ingest and recalculate readiness score (bypasses raw ingestion in `inputs/`) | `None` |
| `--output-file` | Path | Explicit destination file path for regenerated Word report | In-place overwrite / parent dir |
| `--inputs-dir` | Path | Path to directory containing input documents | `inputs/` (`inputs/SOWs/Test` for `--mock`) |
| `--output-dir` | Path | Directory where generated reports are saved | `output/` (`output/Reports/Test` for `--mock`) |
| `--tier` | Choice | Override Governance Tier (`Guided`, `Partnered`, `Elevated`) | Extracted / `Partnered` |
| `--contract-type` | String | Override Contract Type (e.g., `'Fixed Bid'`, `'Time and Materials'`) | Extracted |
| `--pmo-lead` | String | Set PMO Lead name | `[UNASSIGNED - TO BE CONFIRMED]` |
| `--delivery-lead` / `--delivery-manager` | String | Set Delivery Lead / Manager name | `[UNASSIGNED - TO BE CONFIRMED]` |
| `--talent-pm` | String | Set Talent PM name | `[UNASSIGNED - TO BE CONFIRMED]` |
| `--non-interactive` | Flag | Disable interactive directory and role prompts (uses defaults) | `False` |
| `--mock` | Flag | Run offline deterministic mock extraction (zero token cost) | `False` |
| `--start-date` | String | Project Start Date in ISO format (`YYYY-MM-DD`); planned dates are derived from this date | First Monday on/after award date |
| `--export-tools` | Flag | Write the Project Delivery Workbook Excel workbook (default when no output flag is given) | `False` |
| `--kit` | Flag | Write the Startup Kit Word document | `False` |
| `--checklist` | Flag | Write the Startup Readiness Checklist Word document | `False` |
| `--all` | Flag | Write the Startup Kit, the Readiness Checklist, and the Project Delivery Workbook | `False` |
| `-v`, `--verbose` | Flag | Enable verbose debug logging | `False` |

With no output flag, only the workbook is written.

### Example Commands

```bash
# Run interactively with default Claude extraction and all outputs:
python main.py --all

# Run non-interactively with Anthropic API key, all outputs, and full leadership assignments:
python main.py --all --anthropic-api-key "sk-ant-api03-..." --pmo-lead "Sarah Connor" --delivery-lead "Jane Doe" --talent-pm "John Smith" --non-interactive

# Run using OpenAI with direct API key and all outputs:
python main.py --all --openai --openai-api-key "sk-proj-..." --non-interactive

# Re-evaluate an updated Word report and recalculate readiness score (non-interactive):
python main.py --reingest-docx output/Project_Startup_Kit.docx --kit --non-interactive

# Re-evaluate and write all three outputs:
python main.py --reingest-docx output/Project_Startup_Kit.docx --pmo-lead "Sarah Connor" --delivery-lead "Alex Smith" --talent-pm "Taylor Brown" --all --non-interactive

# Offline mock run: workbook only:
python main.py --mock --non-interactive

# Offline mock run: readiness checklist only:
python main.py --mock --non-interactive --checklist
```

### Executive CLI Telemetry Output

Immediately after document creation or re-ingestion, the CLI displays an executive readiness summary:

```text
================================================================================
           TOPTAL PMO STARTUP READINESS GATEWAY (G-01) SUMMARY
================================================================================
 Project Name             : ACME Analytics & Cloud Modernization
 Client Sponsor           : ACME Corp
 Governance Tier          : Partnered | SLA: MET (Created within 1 business day)
--------------------------------------------------------------------------------
 COMPOSITE READINESS SCORE: 74.2% [CONDITIONAL / EXCEPTION REQUIRED - AMBER]
 GATE DECISION STATUS     : Approved with Exception
--------------------------------------------------------------------------------
 SCORE BREAKDOWN:
   • Mandatory Controls   (D1 - 40% Weight): 72.0%
   • Deliverables Rigor   (D2 - 25% Weight): 68.0%
   • Talent Staffing      (D3 - 20% Weight): 80.0%
   • Commercial & Risk    (D4 - 15% Weight): 78.0%
--------------------------------------------------------------------------------
 ACTION REQUIRED SUMMARY:
   • Open Exceptions      : 2 item(s) (G01-03, G01-08)
   • Open Clarifications  : 3 item(s) (G01-04, G01-07, G01-14)
   • Total Score Recovery : +18.5% -> Achievable Target: 92.7% (GREEN)
--------------------------------------------------------------------------------
 REPORT ARTIFACTS:
   • Startup Kit Doc      : C:\Users\...\output\ACME_Startup_Kit.docx
   • Readiness Checklist  : C:\Users\...\output\ACME_Startup_Readiness_Checklist.docx
================================================================================
```

---

## Startup Readiness Scoring & Governance Gates

The **Startup Readiness Score** is an objective, weighted metric designed to evaluate project onboarding health, governance maturity, deliverable clarity, team mobilization, and commercial safeguards prior to client kickoff. It quantifies readiness on a scale of **0.0% to 100.0%** and determines the G-01 Gate mobilization decision under governance rule **WR-03 (No-Mobilize / No-Kickoff Mandate)**.

### Composite Formula and Weight Distribution

The overall score aggregates four weighted dimensions calculated by `ReadinessScoringEngine`:

$$\text{Readiness Score} = (0.40 \times D_1 + 0.25 \times D_2 + 0.20 \times D_3 + 0.15 \times D_4) \times 100$$

| Dimension | Key Focus | Weight |
|---|---|---|
| **`mandatory_g01_controls`** ($D_1$) | Mandatory G-01 Checklist Criteria Completion & Exception Penalties | **40%** |
| **`deliverable_acceptance_rigor`** ($D_2$) | Scope Clarity, Acceptance Criteria & Sign-off Ownership | **25%** |
| **`talent_staffing_readiness`** ($D_3$) | Leadership Assignment & Delivery Roster Confirmation | **20%** |
| **`commercial_risk_mitigation`** ($D_4$) | RAID Log Ownership, Commercial Guardrails & Open Ambiguities | **15%** |

### Dimensional Breakdown Formulas

1. **Mandatory G-01 Controls ($D_1$ — 40% Weight)**:
   - Evaluates compliance across the 15 standard G-01 controls (`G01-01` through `G01-15`):
     $$D_1 = \max\left(0.0, \min\left(1.0, \frac{\sum_{k=1}^{15} \text{Score}(I_k)}{15} - (E \times 0.02)\right)\right)$$
   - Criteria statuses are weighted: `Complete`/`Approved` (1.00), `Approved with Exception` (0.85), `In Progress`/`Review Required` (0.50), `Confirmation Required` (0.30), `Exception Required` (0.20), `Rework Required`/`Not Started` (0.00).
   - $E$ is the count of active open exceptions (deducts **2% (`0.02`)** per exception).

2. **Deliverable & Acceptance Rigor ($D_2$ — 25% Weight)**:
   - Evaluates contractual precision and accountability across all deliverables:
     $$\text{Score}(d) = S_{\text{criteria}}(d) + S_{\text{owner}}(d) + S_{\text{approver}}(d)$$
   - Points awarded per deliverable ($1.00$ max):
     - $S_{\text{criteria}} = +0.40$ if explicit and contains no `[CONFIRMATION REQUIRED]` or `UNASSIGNED` (otherwise $0.00$).
     - $S_{\text{owner}} = +0.30$ if assigned named owner/role and contains no `[UNASSIGNED]` (otherwise $0.00$).
     - $S_{\text{approver}} = +0.30$ if designated client sign-off approver without `[CONFIRMATION REQUIRED]` or `UNASSIGNED` (otherwise $0.00$).
   - $D_2 = \frac{1}{|\text{Deliverables}|} \sum \text{Score}(d)$ (defaults to $0.50$ if no deliverables are defined).

3. **Talent & Staffing Readiness ($D_3$ — 20% Weight)**:
   - Evaluates key leadership roles and delivery team staffing:
     $$D_3 = \max(0.0, \min(1.0, S_{\text{leadership}} + S_{\text{roster}}))$$
   - $S_{\text{leadership}}$ (max 0.60): `+0.20` for confirmed PMO Lead, `+0.20` for confirmed Delivery Manager / Delivery Lead, `+0.20` for confirmed Talent PM (`0.00` if unassigned).
   - $S_{\text{roster}}$ (max 0.40): $0.40 \times \left(\frac{\text{Staffed Roles}}{\max(1, \text{Total Required Roles})}\right)$ for confirmed/ready candidates (defaults to $0.20$ baseline credit if no roster is provided).

4. **Commercial & Risk Mitigation ($D_4$ — 15% Weight)**:
   - Evaluates project safeguard maturity and ambiguity resolution:
     $$D_4 = \max(0.0, \min(1.0, S_{\text{raid}} + S_{\text{commercial}} - \min(0.40, Q \times 0.05)))$$
   - $S_{\text{raid}}$ (max 0.50): `+0.20` base identification credit for cataloged RAID items $+ 0.30 \times \left(\frac{\text{Assigned RAID Owners}}{\text{Total RAID Items}}\right)$ (defaults to $0.25$ if no RAID items exist).
   - $S_{\text{commercial}}$ (max 0.50): `+0.50` if confirmed budget baseline and commercial rules (contract implications, work-at-risk rules, exposure notes) are populated; `+0.40` if either is confirmed; `+0.30` for partial rules; `+0.25` default fallback.
   - $Q$ is the count of unresolved open questions / clarifications (deducts **5% (`0.05`)** per item, capped at **`0.40`** max deduction).

### Action Required Mapping & 1-to-1 In-Artifact Integration

The engine automatically synthesizes open exceptions and clarifications into discrete `ActionRequiredItem` objects mapped with strict **1-to-1 cell traceability** to specific artifact table cells (Deliverables, Milestones, RAID items, Roles, Governance controls). Remediation tags (e.g., `[ACT-XX: ... (+X.X% Recovery)]` or fallback `[ACT-REQ-XX: ...]`) are highlighted directly with yellow text runs (`WD_COLOR_INDEX.YELLOW`) while preserving standard table cell formatting.

| Gate ID | Section 4 Artifact Name | Layer | Primary Action Type | In-Cell Visual Integration | Target Scope |
| :--- | :--- | :---: | :--- | :--- | :---: |
| `G01-01` | **Project Startup Charter** | Layer 1 | Open Exception | Charter Authority Field Highlight `[ACT-XX]` | SLA / Charter |
| `G01-02` | **Project Startup Charter** | Layer 1 | Open Clarification | Delivery Model & Cadence Field `[ACT-XX]` | Governance Model |
| `G01-03` | **Deliverables Matrix** | Layer 2 | Open Exception / Clarification | In-Cell Text Highlight on Owner / Criteria `[ACT-XX]` | Deliverables |
| `G01-04` | **Milestone Delivery Plan** | Layer 1 | Open Exception | In-Cell Text Highlight on Target Date `[ACT-XX]` | Schedule / Buffer |
| `G01-05` | **RAID & Dependency Log** | Layer 2 | Open Clarification | In-Cell Mitigation / Status Column Marker `[ACT-XX]` | Risks & Dependencies |
| `G01-06` | **Talent Onboarding Record** | Layer 3 | Open Clarification | Leadership Briefing Status `[ACT-XX]` | KO Alignment |
| `G01-07` | **Scope & Baseline Interpretation** | Layer 1 | Open Clarification | Customer Obligations Cell Highlight `[ACT-XX]` | Access / Prerequisites |
| `G01-08` | **Talent Roster** | Layer 3 | Open Exception | Roster Row Highlight on `[UNASSIGNED]` `[ACT-XX]` | Delivery Roles |
| `G01-09` | **Stakeholder Model** | Layer 3 | Open Clarification | Decision Rights Column Marker `[ACT-XX]` | Sign-off Authority |
| `G01-10` | **RACI Matrix** | Layer 3 | Open Clarification | RACI Role Definition Callout `[ACT-XX]` | Governance RACI |
| `G01-11` | **Communications Plan** | Layer 2 | Open Clarification | Distribution Cadence Marker `[ACT-XX]` | Status Reporting |
| `G01-12` | **Scope & Baseline Rules** | Layer 3 | Open Clarification | Scope Boundaries & Authorization Marker | Scope Baseline |
| `G01-13` | **Change Control Procedure** | Layer 3 | Open Clarification | Change Control Route Marker `[ACT-XX]` | Scope Management |
| `G01-14` | **Scope Clarity & Alignment** | Layer 1 | Open Clarification | Baseline Alignment Marker | Scope Assurance |
| `G01-15` | **Startup Readiness Checklist** | Standalone Checklist Doc | Open Clarification | Executive Gate Decision Evidence Tag | Gate Governance |

### Action Item Resolution & Score Recovery Guide (From -> To Remediation Table)

When a Startup Kit report is initially generated, missing information, unassigned roles, and unconfirmed criteria trigger embedded action badges (e.g., `[ACT-01: ... (+X.X% Recovery)]` or fallback `[ACT-REQ-XX: ...]`) and reduce the Startup Readiness Score across the four scoring dimensions.

During **Re-evaluation (`main.py --reingest-docx <path>`)**, the user edits the generated Word (`.docx`) file (and optionally the companion `*_Startup_Readiness_Checklist.docx` file) to resolve these open action items. The re-ingestion parser reads the modified document, detects that placeholders and action badges have been replaced with valid project data, clears the action badges, and dynamically recomputes the Readiness Score.

The following **To and From Table** outlines how each action item is resolved in the Word document tables, the exact text transitions required, the affected scoring dimensions, and the mathematical score recovery impact:

#### Action Item Resolution Reference Table (From $\rightarrow$ To)

| Gate ID | Target Artifact & Location | Initial Unresolved State ("FROM") | Remediated Resolved State ("TO") | Affected Dimension | Score Recovery Impact | Operational Remediation Guidance |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Header** | **Document Metadata Header** (Table 1, Row 1–3 Col 3) | `[UNASSIGNED - TO BE CONFIRMED]` for PMO Lead, Delivery Lead, or Talent PM | Named leadership individuals (e.g., `Sarah Connor`, `Alex Mercer`, `Elena Rostova`) | $D_3$ (Talent & Staffing) | **+4.0% per role** (Up to **+12.0%** composite) | Replace unassigned placeholders in header table metadata with confirmed leadership personnel names or pass via CLI flags (`--pmo-lead`, `--delivery-lead`, `--talent-pm`). |
| `G01-01` | **Project Startup Charter** (Turnaround SLA & PMO Authorization) | `[CONFIRMATION REQUIRED]` / Delayed drafting SLA without waiver `[ACT-XX]` | `"Approved by PMO Lead with SLA turnaround validated / retroactive waiver recorded"` | $D_1$ (Mandatory Controls) | **+1.5% to +2.0%** | Enter explicit PMO authorization notes and confirm 1-business-day turnaround SLA compliance or log PMO approval waiver. |
| `G01-02` | **Project Startup Charter** (Delivery Model & Governance Tier) | `[CONFIRMATION REQUIRED]` / Unconfirmed governance cadence `[ACT-XX]` | Confirmed Governance Tier (`Partnered` / `Guided` / `Elevated`) and meeting cadence (e.g., `"Weekly Delivery Sync & Monthly SteerCo"`) | $D_1$ (Mandatory Controls) | **+2.0%** | Select and document the aligned governance tier and formal executive meeting cadence agreed with client stakeholders. |
| `G01-03` | **Deliverables Matrix** (Acceptance Criteria, Owner, Approver) | Criteria: `[CONFIRMATION REQUIRED]`, Owner: `Unassigned`, Approver: `[UNASSIGNED]` `[ACT-XX]` | Concrete test criteria (e.g., `"Approved upon passing automated CI/CD security test suite"`), named Owner (`"Alex Mercer"`), named Approver (`"Dr. Aris Thorne"`) | $D_2$ (Deliverable Rigor) + $D_1$ (Gate Control) | **+3.5% per deliverable** (Up to **+25.0%** total $D_2$) | Replace confirmation placeholders with objective, testable acceptance criteria, assign an internal delivery owner, and designate client sign-off approver. |
| `G01-04` | **Milestone Delivery Plan** (Target External Date & Internal Buffer) | External Date: `None` / `TBD` / `[CONFIRMATION REQUIRED]`, Buffer: empty `[ACT-XX]` | Valid external commitment date (e.g., `2026-11-15`) and 7-day internal buffer date (e.g., `2026-11-08`) | $D_1$ (Mandatory Controls) | **+3.0%** | Input agreed external milestone deadlines in `YYYY-MM-DD` format with proactive internal contingency buffer dates. |
| `G01-05` | **RAID & Dependency Log** (Owner & Mitigation Strategy) | Owner: `Unassigned` / `[UNASSIGNED]`, generic mitigation text `[ACT-XX]` | Assigned named risk/issue owner (e.g., `"Taylor Brown"`), documented mitigation steps and escalation trigger | $D_4$ (Commercial & Risk) + $D_1$ (Gate Control) | **+2.0%** | Assign named individuals to all RAID entries and articulate concrete mitigation actions and target resolution dates. |
| `G01-06` | **Talent Onboarding Record** (PMO Briefing & Kickoff Deck) | Briefing Status: `Pending` / `Unassigned` / `[CONFIRMATION REQUIRED]` `[ACT-XX]` | Briefing Status: `"Completed"`, kickoff deck confirmed and approved by PMO | $D_1$ (Mandatory Controls) + $D_3$ (Talent) | **+1.5%** | Mark PMO leadership briefings as completed and attach confirmation of project kickoff presentation readiness. |
| `G01-07` | **Scope & Baseline Interpretation** (Customer Obligations & Access) | `[CONFIRMATION REQUIRED]` / Undefined environment, or data prerequisites `[ACT-XX]` | Explicit customer obligations defined (e.g., `"Client to provision cloud tenant and access credentials by Day 3"`) | $D_1$ (Mandatory Controls) + $D_4$ (Clarifications) | **+2.5%** | Enumerate all mandatory client prerequisites, security access requirements, and dependency timelines. |
| `G01-08` | **Talent Roster** (Named Talent & Staffing Status) | Named Talent: `[UNASSIGNED - TO BE CONFIRMED]`, Status: `Pending` / `Open` `[ACT-XX]` | Named talent entered (e.g., `"Marcus Vance"`), Staffing Status: `"Confirmed"` / `"Ready"` / `"Active"` | $D_3$ (Talent & Staffing) + $D_1$ (Gate Control) | **+2.5% to +5.0%** | Replace placeholder text with vetted, contracted team members and update staffing status to Confirmed. |
| `G01-09` | **Stakeholder Model** (Decision Rights & Sign-off Authority) | Decision Rights: `[CONFIRMATION REQUIRED]` / Unconfirmed escalation authority `[ACT-XX]` | Specific authority defined (e.g., `"VP of Engineering - Sign-off on architecture blueprints and budget changes > $25k"`) | $D_1$ (Mandatory Controls) | **+2.0%** | Designate explicit decision rights, financial approval thresholds, and escalation pathways for each client stakeholder. |
| `G01-10` | **RACI / Decision Rights Matrix** (Activity Ownership) | Ambiguous role definitions or unassigned Accountable/Responsible designations `[ACT-XX]` | Complete RACI mapping with designated Accountable (`A`), Responsible (`R`), Consulted (`C`), and Informed (`I`) roles | $D_1$ (Mandatory Controls) | **+1.5%** | Verify each lifecycle governance activity has exactly one Accountable role and clearly identified Responsible delivery leads. |
| `G01-11` | **Communications Plan** (Distribution Cadence & Audience) | Distribution cadence undefined / missing stakeholder distribution list `[ACT-XX]` | Defined weekly status report recipient list, monthly steerco cadence, and sprint demo schedule | $D_1$ (Mandatory Controls) | **+1.5%** | Document report recipients, communication channels, meeting frequencies, and executive briefing schedules. |
| `G01-12` | **Scope & Baseline Rules** (Scope Boundaries & Rules) | Scope boundaries: `[CONFIRMATION REQUIRED]` / unconfirmed work rules `[ACT-XX]` | Confirmed scope boundaries, approved work authorization rules, and non-approved work handling | $D_4$ (Commercial & Risk) + $D_1$ (Gate Control) | **+3.0%** | Document approved scope boundaries, work-at-risk authorization policies, and baseline assumptions. |
| `G01-13` | **Scope Management** (Change Control Procedure) | Change route: `[CONFIRMATION REQUIRED]` / Undefined out-of-scope procedure `[ACT-XX]` | Documented formal Change Order request process, impact assessment workflow, and client sign-off route | $D_1$ (Mandatory Controls) | **+2.0%** | Outline the formal change request process, threshold for scope amendments, and commercial impact sign-off rules. |
| `G01-14` | **Scope Clarity & Alignment** (Baseline Ambiguity Resolution) | Ambiguity Status: `Open` / `Exception Required`, unresolved requirement gaps `[ACT-XX]` | Resolution notes or confirmed criteria clarifying project scope and deliverables | $D_4$ (Commercial & Risk) + $D_1$ (Gate Control) | **+3.5%** | Clarify scope requirements and resolve open clarification questions to clear gate exceptions. |
| `G01-15` | **Executive Startup Readiness Checklist** (G-01 Gateway & Governance Document) | Gate Criteria: `Exception Required` / `Review Required`, unresolved questions `[ACT-XX]` | Gate Criteria: `"Complete"` / `"Approved"`, with clear audit evidence documented in Evidence column and resolved ambiguities | $D_1$ (Mandatory Controls) + $D_4$ (Commercial) | **+2.5%** | Update G-01 checklist row statuses to Complete/Approved with supporting evidence summaries in the companion checklist document, and clear all open questions/ambiguities. |

#### Step-by-Step Re-evaluation Workflow

To execute a re-evaluation cycle and observe score recovery:

1. **Open the Generated Word Documents**: Open `output/<Project_Name>_Startup_Kit.docx` and its companion `output/<Project_Name>_Startup_Readiness_Checklist.docx` in Microsoft Word or any compatible DOCX editor.
2. **Locate Highlighted Action Badges**: Look for yellow-highlighted `[ACT-XX: ... (+X.X% Recovery)]` tags in the artifact tables (Deliverables, Milestones, Talent Roster, RAID) and open clarification questions in the checklist document.
3. **Apply Remediation Updates**:
   - Replace placeholder text (e.g., `[CONFIRMATION REQUIRED]`, `[UNASSIGNED]`, `TBD`) with confirmed project details as shown in the table above.
   - In the companion checklist document, update G-01 row statuses and evidence, resolve Actionable Questions, or add clarification notes to Contract Ambiguities.
   - For leadership, enter names directly in Table 1 (Metadata Header) or pass them via CLI flags (`--pmo-lead`, `--delivery-lead`, `--talent-pm`).
4. **Save the Modified Document(s)**: Save the documents in place or specify a new target path.
5. **Run Re-evaluation**:
   ```bash
   python main.py --reingest-docx output/Project_Startup_Kit_Updated.docx --non-interactive
   ```
6. **Verify Score Improvement**:
   - The CLI displays the updated composite score, showing recovery across $D_1$, $D_2$, $D_3$, and $D_4$.
   - The output Word documents are regenerated with resolved action badges automatically stripped and the updated G-01 Gate Decision status reflected in the executive gateway dashboard.

### Tri-directional Alignment Guarantees

The system guarantees mathematical and visual parity across all report sections:
1. **Exception Count Parity**: $\text{GateDecision.open\_exceptions\_count} \equiv \sum \text{Checklist Exceptions} \equiv \text{Count of Exception Action Tags}$.
2. **Clarification Parity**: $\text{len}(\text{Open Questions}) \equiv \text{Count of Open Clarification Action Tags}$.
3. **Score Recovery Invariant**: $\text{Current Readiness Score} + \sum \text{Score Recovery Deltas} \equiv \text{Achievable Target Score}$.

### Gate Review Thresholds and Decision Matrix

| Score Range | Status Classification | Gate Decision | Mobilization Action |
|---|---|---|---|
| **`≥ 85.0%`** (and 0 open exceptions) | **Green** (Optimal Health) | `Approved for Mobilize` | Full mobilization authorized; internal and client kickoffs cleared. |
| **`70.0% – 84.9%`** (or open exceptions when score $\ge 70.0\%$) | **Amber** (Conditional Risk) | `Approved with Exception` | Conditional mobilization permitted; bypass rationale and sponsor sign-off required. |
| **`< 70.0%`** | **Red** (High Vulnerability) | `Rework Required` | Mobilization blocked; critical defects and low baseline maturity mandate rework. |

---

## Running Tests

Run the test suite using `pytest`:

```bash
pytest
```

To run with verbose output and per-test status:

```bash
pytest -v
```

---

## Versioning & Releases

This project uses [bump-my-version](https://github.com/callowayproject/bump-my-version) for version management configured via `.bumpversion.toml`.

To bump the version (updating `src/version.py`, creating a Git commit and tag):

```bash
# Patch bump (0.4.0 -> 0.4.1)
bump-my-version bump patch

# Minor bump (0.4.0 -> 0.5.0)
bump-my-version bump minor

# Major bump (0.4.0 -> 1.0.0)
bump-my-version bump major
```

To preview version bumps without committing changes:

```bash
bump-my-version bump patch --dry-run --verbose
```
