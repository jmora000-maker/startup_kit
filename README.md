# Toptal PMO Startup Kit Generator

Automated project onboarding and readiness toolkit. The PMO Startup Kit Generator ingests Statements of Work (SOWs), client contracts, and kickoff presentations to extract structured project management artifacts via LLMs and automatically generate standardized Word (`.docx`) Startup Kit reports and PMO Operating System seed data.

---

## Key Features

- **Multi-Format Ingestion**: Ingests project inputs across multiple file formats including PDF (`.pdf`), Word (`.docx`), PowerPoint (`.pptx`), and plain text (`.txt`).
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
- **Standardized Word Report Generation**: Produces styled, professional Microsoft Word documents containing structured tables, status callouts, and governance checklists.
- **PMO Operating System Export**: Optional export of downstream CSV and JSON seed payloads for PMO workbooks and tracking toolkits.
- **Offline / Mock Mode**: Fully functional offline mock client for local testing and deterministic validation without requiring OpenAI API credentials.
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
│   ├── core/               # Domain interfaces and Pydantic data models
│   ├── extractors/         # File parsers (PDF, DOCX, PPTX, TXT) and ingestion service
│   ├── generators/         # Word document builder, formatting, checklists, and data exporters
│   └── llm/                # LangChain LLM client, prompts, parsers, and aggregation logic
├── tests/                  # Unit and integration test suite
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

### Interactive vs Non-Interactive Execution

- **Interactive Mode (Default)**:
  When launched without specific directory or leadership flags, the CLI interactively prompts for:
  1. `inputs directory` (default: `inputs/`)
  2. `output directory` (default: `output/`)
  3. `PMO Lead` name (default: `[UNASSIGNED - TO BE CONFIRMED]`)
  4. `Delivery Lead` name (default: `[UNASSIGNED - TO BE CONFIRMED]`)
  5. `Talent PM` name (default: `[UNASSIGNED - TO BE CONFIRMED]`)
  Pressing `Enter` accepts the default value for each prompt.

- **Non-Interactive Mode**:
  Pass `--non-interactive` to disable all terminal prompts and automatically use configured defaults for any unspecified directories or roles.

### Command-Line Arguments

| Flag | Type | Description | Default |
|---|---|---|---|
| `--inputs-dir` | Path | Path to directory containing input documents | `inputs/` (interactive prompt if omitted) |
| `--output-dir` | Path | Directory where generated reports are saved | `output/` (interactive prompt if omitted) |
| `--model` | String | OpenAI model name | `gpt-4o` |
| `--tier` | Choice | Override Governance Tier (`Guided`, `Partnered`, `Elevated`) | Extracted / `Partnered` |
| `--contract-type` | String | Override Contract Type (e.g., `'Fixed Bid'`, `'Time and Materials'`) | Extracted |
| `--pmo-lead` | String | Set PMO Lead name | `[UNASSIGNED - TO BE CONFIRMED]` |
| `--delivery-lead` | String | Set Delivery Lead / Manager name (alias: `--delivery-manager`) | `[UNASSIGNED - TO BE CONFIRMED]` |
| `--talent-pm` | String | Set Talent PM name | `[UNASSIGNED - TO BE CONFIRMED]` |
| `--non-interactive` | Flag | Disable interactive directory and role prompts (uses defaults) | `False` |
| `--mock` | Flag | Run offline deterministic mock extraction | `False` |
| `--export-tools` | Flag | Export downstream PMO workbook toolkits (CSV/JSON) to output | `False` |
| `-v`, `--verbose` | Flag | Enable verbose debug logging | `False` |

### Example Commands

```bash
# Run interactively in offline mock mode (prompts for directories and leadership roles):
python main.py --mock

# Export downstream PMO tools with custom directories and leadership roles specified:
python main.py --mock --inputs-dir ./inputs --output-dir ./output --pmo-lead "Sarah Connor" --delivery-lead "Jane Doe" --talent-pm "John Smith" --export-tools

# Run non-interactively in automated CI/CD using defaults:
python main.py --mock --non-interactive

# Custom inputs and outputs with a tier override:
python main.py --inputs-dir ./client_docs --output-dir ./reports --tier Elevated --non-interactive
```

---

## Startup Readiness Scoring & Governance Gates

The **Startup Readiness Score** is an objective, weighted metric designed to evaluate project onboarding health, governance maturity, deliverable clarity, team mobilization, and commercial safeguards prior to client kickoff. It quantifies readiness on a scale of **0.0% to 100.0%** and determines the G-01 Gate mobilization decision.

### Composite Formula and Weight Distribution

The overall score aggregates four weighted dimensions:

$$\text{Readiness Score} = (0.40 \times \text{Dim}_1 + 0.25 \times \text{Dim}_2 + 0.20 \times \text{Dim}_3 + 0.15 \times \text{Dim}_4) \times 100$$

| Dimension | Key Focus | Weight |
|---|---|---|
| **`mandatory_g01_controls`** | Mandatory G-01 Checklist Criteria Completion & Exception Penalties | **40%** |
| **`deliverable_acceptance_rigor`** | Scope Clarity, Acceptance Criteria & Sign-off Ownership | **25%** |
| **`talent_staffing_readiness`** | Leadership Assignment & Delivery Roster Confirmation | **20%** |
| **`commercial_risk_mitigation`** | RAID Log Ownership, Commercial Guardrails & Open Ambiguities | **15%** |

### Dimensional Breakdown

1. **Mandatory G-01 Controls (`mandatory_g01_controls` — 40% Weight)**:
   - Evaluates compliance across the 15 standard G-01 controls (`G01-01` through `G01-15`).
   - Criteria statuses are weighted: `Complete`/`Approved` (1.0), `Approved with Exception` (0.85), `In Progress`/`Review Required` (0.50), `Confirmation Required` (0.30), `Exception Required` (0.20), `Rework Required`/`Not Started` (0.0).
   - Base score is the average point value across all 15 items minus an **exception penalty of 3% (`0.03`)** for each open exception.

2. **Deliverable & Acceptance Rigor (`deliverable_acceptance_rigor` — 25% Weight)**:
   - Evaluates clarity and accountability for contracted deliverables.
   - Points awarded per deliverable: `+0.40` for confirmed acceptance criteria, `+0.30` for assigned internal owner, `+0.30` for designated client approver role.

3. **Talent & Staffing Readiness (`talent_staffing_readiness` — 20% Weight)**:
   - Evaluates key leadership and delivery team staffing:
     - `+0.35` for assigned and confirmed `delivery_manager`.
     - `+0.35` for assigned and confirmed `talent_pm`.
     - `+0.30` proportional to confirmed talent roster members (or `0.15` default credit if no roster is provided).

4. **Commercial & Risk Mitigation (`commercial_risk_mitigation` — 15% Weight)**:
   - Evaluates project safeguard maturity:
     - `+0.40` proportional to assigned owners on RAID log items.
     - `+0.30` for contract-type guardrails (e.g., T&M caps, work-at-risk rules).
     - `+0.30` baseline with a **5% penalty (`-0.05`)** per unresolved ambiguity or open question.

### Open Exceptions

An **Open Exception** represents a critical readiness gap or uncommitted baseline item flagged on the checklist (`exception_required == True` or `status == "Exception Required"`).

- **Common Triggers**:
  - `G01-01`: Startup Kit drafted $>1$ business day after SOW award date.
  - `G01-03`: Unresolved scope clarification questions pending.
  - `G01-04`: Missing external milestone commitment dates.
  - `G01-06`: Missing or unconfirmed deliverable acceptance criteria.
  - `G01-13`: Key leadership roles unassigned (`delivery_manager` or `talent_pm`).
  - `G01-14`: Contractual ambiguities or clause conflicts identified.
- **Impact**: Each open exception applies a 3% deduction to Dimension 1 and prevents unconditional Green Gate authorization.

### Gate Review Thresholds and Decision Matrix

| Score Range | Status Classification | Gate Decision | Mobilization Action |
|---|---|---|---|
| **`≥ 85.0%`** (and 0 open exceptions) | **Green** (Optimal Health) | `Approved for Mobilize` | Full mobilization authorized; baseline locked. |
| **`70.0% – 84.9%`** (or open exceptions) | **Amber** (Conditional Risk) | `Approved with Exception` | Mobilization permitted with formal PMO exception log and scheduled review. |
| **`< 70.0%`** | **Red** (High Vulnerability) | `Rework Required` | Mobilization blocked; SOW realignment and team onboarding rework mandated. |

---

## Running Tests

Run the test suite using `pytest`:

```bash
pytest
```

To run with verbose output and coverage:

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
