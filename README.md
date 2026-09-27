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

### Command-Line Arguments

| Flag | Type | Description | Default |
|---|---|---|---|
| `--inputs-dir` | Path | Path to directory containing input documents | `inputs/` |
| `--output-dir` | Path | Directory where generated reports are saved | `output/` |
| `--model` | String | OpenAI model name | `gpt-4o` |
| `--tier` | Choice | Override Governance Tier (`Guided`, `Partnered`, `Elevated`) | Extracted / `Partnered` |
| `--contract-type` | String | Override Contract Type (e.g., `'Fixed Bid'`, `'Time and Materials'`) | Extracted |
| `--pmo-lead` | String | Set PMO Lead name | `[UNASSIGNED - TO BE CONFIRMED]` |
| `--delivery-lead` | String | Set Delivery Lead / Manager name (alias: `--delivery-manager`) | `[UNASSIGNED - TO BE CONFIRMED]` |
| `--talent-pm` | String | Set Talent PM name | `[UNASSIGNED - TO BE CONFIRMED]` |
| `--non-interactive` | Flag | Disable interactive role prompts and use default unassigned | `False` |
| `--mock` | Flag | Run offline deterministic mock extraction | `False` |
| `--export-tools` | Flag | Export downstream PMO workbook toolkits (CSV/JSON) to output | `False` |
| `-v`, `--verbose` | Flag | Enable verbose debug logging | `False` |

### Example Commands

```bash
# Export downstream PMO tools with leadership roles specified:
python main.py --mock --pmo-lead "Sarah Connor" --delivery-lead "Jane Doe" --talent-pm "John Smith" --export-tools

# Run non-interactively using unassigned defaults:
python main.py --mock --non-interactive

# Custom inputs and outputs with a tier override:
python main.py --inputs-dir ./client_docs --output-dir ./reports --tier Elevated
```

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
