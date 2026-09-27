# Toptal PMO Startup Kit Generator

Automated project onboarding and readiness toolkit. The PMO Startup Kit Generator ingests Statements of Work (SOWs), client contracts, and kickoff presentations to extract structured project management artifacts via LLMs and automatically generate standardized Word (`.docx`) Startup Kit reports and PMO Operating System seed data.

---

## Key Features

- **Multi-Format Ingestion & Pydantic v2 Validation**: Ingests project inputs across multiple file formats including PDF (`.pdf`), Word (`.docx`), PowerPoint (`.pptx`), and plain text (`.txt`). Enforces strict runtime validation at extraction boundaries, including PDF coordinate geometry and sequential page invariants.
- **Structured LLM Extraction**: Leverages LangChain and OpenAI models (e.g., `gpt-4o`) to extract critical project metadata:
  - Project Charter & Executive Summary
  - Scope Decomposition & Exclusions
  - Deliverables & Acceptance Criteria
  - Milestones & Delivery Roadmap
  - RAID Logs (Risks, Assumptions, Issues, Dependencies)
  - Stakeholder Matrix & Decision Rights
  - Governance Tiers (Guided, Partnered, Elevated) & Communications Plans
  - Commercial Guardrails & Contractual Ambiguity Analysis
  - Talent Onboarding Checklist & Resourcing Records
- **Authoritative Startup Readiness Scoring Engine**: Centralized, deterministic 4-dimension mathematical engine (`ReadinessScoringEngine`) calculating composite readiness scores, dimensional breakdowns, gate review statuses, and quantified score recovery potential.
- **Structured Action Required Mapping & 1-to-1 In-Artifact Integration**: Generates discrete, 1-to-1 mapped action items (`ACT-01`, `ACT-02`, etc.) for open exceptions and clarifications, embedding yellow-highlighted remediation badges directly inside Section 4 Layer 1, Layer 2, and Layer 3 artifact table cells without cell background shading alteration.
- **Standardized Word Report Generation**: Produces professionally styled Microsoft Word documents adhering to the executive review hierarchy: Header Metadata $\rightarrow$ `Startup Kit Readiness Score: [score]%` Heading $\rightarrow$ Section 4 Artifacts (Layer 1 $\rightarrow$ Layer 2 $\rightarrow$ Layer 3) $\rightarrow$ Executive Readiness Gateway (Gate Decision Dashboard $\rightarrow$ 15-Row G-01 Checklist Table).
- **Word Re-ingestion & Rescoring Engine**: Re-evaluates edited Word documents (`--reingest-docx`), dynamically recalculating scores across all 4 dimensions and clearing resolved action items without re-running LLM extraction.
- **Executive CLI Readiness Telemetry**: Outputs a formatted, color-coded summary dashboard in the terminal immediately following document generation and re-ingestion passes.
- **PMO Operating System Export**: Optional export of downstream CSV and JSON seed payloads for PMO workbooks and tracking toolkits.
- **Offline / Mock Mode**: Fully functional offline mock client for local testing and deterministic validation without requiring OpenAI API credentials.
- **Automated Versioning**: Configured with `bump-my-version` for semantic versioning.

---

## Project Structure

```text
Startup_Kit/
├── inputs/                 # Input directory for SOWs, decks, and contracts (.pdf, .docx, .pptx, .txt)
├── output/                 # Output directory for generated Word reports and toolkits
├── spec/                   # Technical and functional specifications
├── src/
│   ├── config.py           # Application settings and environment configuration
│   ├── orchestrator.py     # End-to-end pipeline execution controller
│   ├── version.py          # Current application version
│   ├── core/               # Domain interfaces, extraction models, and PDF metadata schemas
│   │   ├── interfaces.py   # Abstract extractor and LLM interfaces
│   │   ├── models.py       # Pydantic domain models, baselines, and action items
│   │   └── pdf_models.py   # PDF page and document coordinate validation models
│   ├── extractors/         # File parsers (PDF, DOCX, PPTX, TXT), Word parser, and ingestion service
│   ├── generators/         # Word document builder, formatting, G-01 checklist, and data exporters
│   ├── llm/                # LangChain LLM client, prompts, parsers, and aggregation logic
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

Create a `.env` file in the project root directory or set environment variables:

```ini
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.0

# Directory Paths (Optional overrides)
INPUTS_DIR=inputs
OUTPUT_DIR=output

# Governance & Contract Defaults (Optional)
DEFAULT_GOVERNANCE_TIER=Partnered
DEFAULT_CONTRACT_TYPE=Time and Materials
```

---

## Usage

Place your project documentation (SOWs, presentation decks, contracts) into the `inputs/` folder (or specify a custom path using `--inputs-dir`).

### Run with OpenAI LLM

```bash
python main.py
```

### Run in Offline Mock Mode (No API Key Required)

To verify the generation pipeline without connecting to OpenAI:

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
  Pressing `Enter` accepts the default value for directory and role prompts.

- **Non-Interactive Mode**:
  Pass `--non-interactive` to disable all terminal prompts and automatically use configured defaults for any unspecified directories or roles.

### Command-Line Arguments

| Flag | Type | Description | Default |
|---|---|---|---|
| `--reingest-docx` / `--docx-file` | Path | Path to existing `*_Startup_Kit.docx` to re-ingest and recalculate readiness score (bypasses raw ingestion in `inputs/`) | `None` |
| `--output-file` | Path | Explicit destination file path for regenerated Word report | In-place overwrite / parent dir |
| `--inputs-dir` | Path | Path to directory containing input documents | `inputs/` (interactive prompt if omitted) |
| `--output-dir` | Path | Directory where generated reports are saved | `output/` (interactive prompt if omitted) |
| `--model` | String | OpenAI model name | `gpt-4o` |
| `--tier` | Choice | Override Governance Tier (`Guided`, `Partnered`, `Elevated`) | Extracted / `Partnered` |
| `--contract-type` | String | Override Contract Type (e.g., `'Fixed Bid'`, `'Time and Materials'`) | Extracted |
| `--pmo-lead` | String | Set PMO Lead name | `[UNASSIGNED - TO BE CONFIRMED]` |
| `--delivery-lead` / `--delivery-manager` | String | Set Delivery Lead / Manager name | `[UNASSIGNED - TO BE CONFIRMED]` |
| `--talent-pm` | String | Set Talent PM name | `[UNASSIGNED - TO BE CONFIRMED]` |
| `--non-interactive` | Flag | Disable interactive directory and role prompts (uses defaults) | `False` |
| `--mock` | Flag | Run offline deterministic mock extraction | `False` |
| `--export-tools` | Flag | Export downstream PMO workbook toolkits (CSV/JSON) to output | `False` |
| `-v`, `--verbose` | Flag | Enable verbose debug logging | `False` |

### Example Commands

```bash
# Run interactively (prompts for mode, directories, and leadership roles):
python main.py

# Re-evaluate an updated Word report and recalculate readiness score (non-interactive):
python main.py --reingest-docx output/Project_Startup_Kit.docx --non-interactive

# Re-evaluate and re-export downstream PMO tools with leadership role overrides:
python main.py --reingest-docx output/Project_Startup_Kit.docx --pmo-lead "Sarah Connor" --delivery-lead "Alex Smith" --talent-pm "Taylor Brown" --export-tools --non-interactive

# Export downstream PMO tools with custom directories and leadership roles specified:
python main.py --mock --inputs-dir ./inputs --output-dir ./output --pmo-lead "Sarah Connor" --delivery-lead "Jane Doe" --talent-pm "John Smith" --export-tools

# Run non-interactively in automated CI/CD using defaults:
python main.py --mock --non-interactive
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
 REPORT ARTIFACT:
   • Output File Path     : C:\Users\...\output\ACME_Startup_Kit.docx
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

The engine automatically synthesizes open exceptions and clarifications into discrete `ActionRequiredItem` objects mapped with strict **1-to-1 cell traceability** to specific artifact table cells (Deliverables, Milestones, RAID items, Roles, Guardrails). Remediation tags (e.g., `[ACT-XX: ... (+X.X% Recovery)]` or fallback `[ACT-REQ-XX: ...]`) are highlighted directly with yellow text runs (`WD_COLOR_INDEX.YELLOW`) while preserving standard table cell zebra shading.

| Gate ID | Section 4 Artifact Name | Layer | Primary Action Type | In-Cell Visual Integration | Target Scope |
| :--- | :--- | :---: | :--- | :--- | :---: |
| `G01-01` | **Project Startup Charter** | Layer 1 | Open Exception | Charter Authority Field Highlight `[ACT-XX]` | SLA / Charter |
| `G01-02` | **Project Startup Charter** | Layer 1 | Open Clarification | Delivery Model & Cadence Field `[ACT-XX]` | Governance Model |
| `G01-03` | **Deliverables Matrix** | Layer 2 | Open Exception / Clarification | In-Cell Text Highlight on Owner / Criteria `[ACT-XX]` | Deliverables |
| `G01-04` | **Milestone Delivery Plan** | Layer 1 | Open Exception | In-Cell Text Highlight on Target Date `[ACT-XX]` | Schedule / Buffer |
| `G01-05` | **RAID & Dependency Log** | Layer 2 | Open Clarification | In-Cell Mitigation / Status Column Marker `[ACT-XX]` | Risks & Dependencies |
| `G01-06` | **Talent Onboarding Record** | Layer 3 | Open Clarification | Leadership Briefing Status `[ACT-XX]` | KO Alignment |
| `G01-07` | **SOW Interpretation Summary** | Layer 1 | Open Clarification | Customer Obligations Cell Highlight `[ACT-XX]` | Access / Obligations |
| `G01-08` | **Talent Roster** | Layer 3 | Open Exception | Roster Row Highlight on `[UNASSIGNED]` `[ACT-XX]` | Delivery Roles |
| `G01-09` | **Stakeholder Model** | Layer 3 | Open Clarification | Decision Rights Column Marker `[ACT-XX]` | Sign-off Authority |
| `G01-10` | **RACI Matrix** | Layer 3 | Open Clarification | RACI Role Definition Callout `[ACT-XX]` | Governance RACI |
| `G01-11` | **Communications Plan** | Layer 2 | Open Clarification | Distribution Cadence Marker `[ACT-XX]` | Status Reporting |
| `G01-12` | **Commercial Guardrails** | Layer 3 | Open Exception | SOW Budget Baseline / Cap Marker `[ACT-XX]` | Commercial Exposure |
| `G01-13` | **Change Control Procedure** | Layer 3 | Open Clarification | Change Control Route Marker `[ACT-XX]` | Scope Baseline |
| `G01-14` | **Contract Ambiguity Analysis**| Layer 1 | Open Exception | Ambiguity Resolution Marker `[ACT-XX]` | SOW Clauses |
| `G01-15` | **Startup Readiness Checklist** | Gateway | Open Clarification | Executive Gate Decision Evidence Tag | Gate Governance |

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
# Patch bump (0.0.1 -> 0.0.2)
bump-my-version bump patch

# Minor bump (0.0.2 -> 0.1.0)
bump-my-version bump minor

# Major bump (0.1.0 -> 1.0.0)
bump-my-version bump major
```

To preview version bumps without committing changes:

```bash
bump-my-version bump patch --dry-run --verbose
```
