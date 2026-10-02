# PMO Startup Kit Generator

The PMO Startup Kit Generator ingests Statement of Work (SOW) documents and kickoff materials to extract structured project management baselines via LLMs. It produces four core project delivery documents:
- the **Startup Kit** (`.docx`), containing executive metadata, baseline governance tables, work packages, deliverables, milestones, and RAID items;
- the **Startup Readiness Checklist** (`.docx`), containing the G-01 executive gateway dashboard, 15-row readiness checklist, commercial guardrails, actionable clarification questions, and contract ambiguities;
- the **Project Delivery Workbook** (`.xlsx`), containing a Project Schedule of SOW acceptance gates by delivery phase, a Work Breakdown Structure (WBS) of deliverables and work items, and a consolidated RAID Log;
- the **Talent Team Onboarding Deck** (`.pptx`) and trace manifest (`.trace.json`), containing an executive 7-slide briefing deck for talent onboarding (cover, five content slides, and a closing Your Project Kit slide), built with strict traceability back to the Kit and Workbook.

For detailed specification rules and background, see [spec/PMO_Startup_Kit_Consolidated_Spec.md](spec/PMO_Startup_Kit_Consolidated_Spec.md) and [spec/Review_Loop_Reference.md](spec/Review_Loop_Reference.md).

---

## 1. Purpose

The tool reads a Statement of Work (SOW) and produces four standardized project management documents:
- the **Startup Kit** (`.docx`);
- the **Startup Readiness Checklist** (`.docx`);
- the **Project Delivery Workbook** (`.xlsx`), with a Project Schedule of SOW acceptance gates by phase, a WBS of deliverables and work items, and a RAID Log;
- the **Talent Team Onboarding Deck** (`.pptx`), with seven onboarding slides and a companion `{Project}_Talent_Onboarding_Deck.trace.json` manifest.

---

## 2. Setup

### Prerequisites & Python Environment
- Python 3.10+ (Python 3.11+ recommended)
- Virtual environment (`venv`)

```bash
# Create virtual environment
python -m venv .venv

# Activate on Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Activate on Linux / macOS
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Configuration (`.env`)
Create a `.env` file in the project root to configure application paths and API keys:

- `INPUTS_DIR`: Path to the default inputs directory containing SOWs and input documents.
- `MOCK_INPUTS_DIR`: Path to the mock inputs directory used during offline `--mock` runs.
- `OUTPUT_DIR`: Path to the default output directory for generated reports.
- `MOCK_OUTPUT_DIR`: Path to the mock output directory used during offline `--mock` runs.
- `LLM_PROVIDER`: Default LLM provider service (`anthropic` or `openai`).
- `ANTHROPIC_API_KEY`: Authentication API key for Anthropic Claude models.
- `ANTHROPIC_MODEL`: Model identifier for Anthropic Claude (e.g. `claude-sonnet-5-5`).
- `OPENAI_API_KEY`: Authentication API key for OpenAI models (used directly or as fallback).
- `OPENAI_MODEL`: Model identifier for OpenAI (e.g. `gpt-4o`).
- `TEMPERATURE` / `OPENAI_TEMPERATURE`: Sampling temperature for LLM generation requests.
- `DEFAULT_GOVERNANCE_TIER`: Default governance tier (`Guided`, `Partnered`, or `Elevated`).
- `DEFAULT_CONTRACT_TYPE`: Default contract classification (e.g. `Time and Materials`, `Fixed Bid`).
- `MAX_TOKENS`: Maximum output tokens allowed per LLM response.
- `LLM_CACHE_MODE`: Default LLM caching mode (`off`, `record`, or `replay`).
- `LLM_CACHE_DIR`: Directory path where LLM request/response cache fixtures are stored.
- `DECK_TEMPLATE_PATH`: Path to PowerPoint presentation template (default: `templates/Toptal_Presentation_Template.pptx`).

---

## 3. Usage

### Output Selection Flags
By default, when no output flag is provided, only the Project Delivery Workbook (`.xlsx`) is generated.
- `--export-tools`: Write the Project Delivery Workbook Excel workbook (`.xlsx`) (default when no output flag is given).
- `--kit`: Write the Startup Kit Word document (`.docx`).
- `--checklist`: Write the Startup Readiness Checklist Word document (`.docx`).
- `--slides`: Write the Talent Team Onboarding Deck (`.pptx`) and its trace manifest (`.trace.json`). Writing the deck automatically generates its source Kit and Workbook.
- `--all`: Write all four outputs: the Startup Kit, the Readiness Checklist, the Project Delivery Workbook, and the Talent Onboarding Deck.

### Re-ingestion Workflow
When updating an existing project, re-ingesting an approved `*_Startup_Kit.docx` via `--reingest-docx <path>` is recommended over regenerating from the raw SOW. The input Kit serves as the source of truth; it is not rewritten unless `--kit` or `--all` is explicitly passed.

### CLI Options Reference
All options as provided by `python main.py --help`:

- `-h, --help`: Show help message and exit.
- `--inputs-dir INPUTS_DIR`: Path to inputs directory containing SOWs and decks (default: `inputs/`, or `inputs/SOWs/Test` when `--mock` is used).
- `--output-dir OUTPUT_DIR`: Path to output directory for generated Word reports (default: `output/`, or `output/Reports/Test` when `--mock` is used).
- `--output-file OUTPUT_FILE`: Explicit destination file path for regenerated Word report.
- `--reingest-docx, --docx-file REINGEST_DOCX`: Path to existing `*_Startup_Kit.docx` to re-ingest and recalculate readiness score.
- `--provider, --llm-provider {anthropic,openai,claude,gpt}`: LLM provider to use: `'anthropic'` (Claude, default) or `'openai'` (GPT).
- `--openai, --open-ai`: Use OpenAI as the LLM provider.
- `--anthropic, --claude`: Use Anthropic Claude as the LLM provider (default).
- `--model MODEL`: LLM model name (defaults to `'claude-sonnet-5-5'` for Anthropic or `'gpt-4o'` for OpenAI).
- `--tier {Guided,Partnered,Elevated}`: Override Governance Tier (`Guided`, `Partnered`, `Elevated`).
- `--contract-type CONTRACT_TYPE`: Override Contract Type (e.g. `'Time and Materials'`, `'Fixed Bid'`).
- `--pmo-lead PMO_LEAD`: PMO Lead name (defaults to `'[UNASSIGNED - TO BE CONFIRMED]'` if not provided).
- `--delivery-lead, --delivery-manager DELIVERY_LEAD`: Delivery Lead / Manager name (defaults to `'[UNASSIGNED - TO BE CONFIRMED]'` if not provided).
- `--talent-pm TALENT_PM`: Talent PM name (defaults to `'[UNASSIGNED - TO BE CONFIRMED]'` if not provided).
- `--non-interactive`: Disable interactive directory and role prompts (uses default paths and unassigned roles).
- `--api-key, --anthropic-api-key API_KEY`: Anthropic API Key (overrides `ANTHROPIC_API_KEY` environment variable and `.env`).
- `--openai-api-key OPENAI_API_KEY`: OpenAI API Key for fallback or direct execution (overrides `OPENAI_API_KEY` environment variable and `.env`).
- `--mock`: Run using offline deterministic Mock LLM client (no API keys required).
- `--llm-cache {off,record,replay}`: LLM cache mode (`off`, `record`, `replay`; default from `LLM_CACHE_MODE` or `off`).
- `--start-date START_DATE`: Project Start Date in ISO format (`YYYY-MM-DD`); planned dates are derived from this date.
- `--export-tools`: Write the Project Delivery Workbook Excel workbook (default when no output flag is given).
- `--kit`: Write the Startup Kit Word document.
- `--checklist`: Write the Startup Readiness Checklist Word document.
- `--slides`: Write the Talent Team Onboarding Deck PowerPoint presentation.
- `--all`: Write the Startup Kit, the Readiness Checklist, the Project Delivery Workbook, and the Talent Onboarding Deck.
- `-v, --verbose`: Enable verbose debug logging.

### Input and Output Paths
- **Inputs**: Read from `inputs/` by default. Only files located directly in `inputs/` are read; subfolders are not scanned.
- **PowerShell Note**: Input filenames containing square brackets (e.g. `[V1] <SOW file name>.pdf`) must be copied using `Copy-Item -LiteralPath` in PowerShell to avoid wildcard expansion:
  ```powershell
  Copy-Item -LiteralPath "tests\fixtures\sow\arc_genomics\inputs\[V1] Exhibit A - Arc Genomics Platform.pdf" -Destination "inputs\"
  ```
- **Outputs**: Written to `output/` by default.

### Example Commands

#### 1. Offline Mock Run
Run extraction using the built-in deterministic mock client and generate all documents:
```bash
python main.py --mock --non-interactive --all
```

#### 2. Live SOW Ingestion
Place your SOW file in `inputs/` and run with your configured LLM provider and project start date:
```bash
python main.py --start-date 2026-10-05 --all --non-interactive
```

#### 3. Re-evaluating an Approved Kit (`--reingest-docx`)
When a Startup Kit has been reviewed and edited, regenerate the documents and recalculate readiness scores directly from the `.docx` file without invoking LLM extraction:
```bash
python main.py --reingest-docx output/<Project_Name>_Startup_Kit.docx --all --non-interactive
```
*Recommendation*: Always use the `--reingest-docx` route for approved Kits when generating the Project Delivery Workbook, because running a fresh LLM extraction from the raw SOW can renumber deliverables and work packages.

---

## 4. LLM Recording and Replay

The tool includes a caching client wrapper (`--llm-cache`) that caches structured LLM extractions by a SHA-256 hash of the model ID, system prompt, user prompt, and target schema:

- `--llm-cache off`: Disables caching. All calls are sent live to the active LLM provider.
- `--llm-cache record`: Sends calls live to the LLM and writes the prompt and response payload to `.json` files in the cache directory (`tests/fixtures/llm_cache/` by default, or configured via `LLM_CACHE_DIR`).
- `--llm-cache replay`: Executes extractions entirely offline using recorded cache files. Replay mode never makes live network calls; if a required prompt or schema is missing from the cache, an `LLMCacheMiss` error is raised immediately.

---

## 5. Testing and Quality Checks

The testing framework employs a multi-tiered validation architecture:

1. **Recorded Fixtures**: Offline end-to-end extraction fixtures located in `tests/fixtures/sow/` (such as `arc_genomics`, `arc_overextracted`, `mock_sow`, `no_story_ids`, `numbered_deliverables`). They can be replayed deterministically without live API calls.
2. **Oracles (`tests\oracles\`)**: Human-curated ground truth facts per SOW (e.g. gate counts, milestone delivery phases, story titles). Tested against baseline models and generated artifacts.
3. **Invariants (`check_artifacts`)**: Strict programmatic invariant validation across generated Word reports and Excel workbooks (e.g. non-empty checkpoint phases, valid parent deliverable references, WBS structure). Run against any output directory with:
   ```bash
   python -m src.tools.check_artifacts output
   ```
   The deck checks read the written files back: INV-26 resolves every trace key in the Kit and Workbook and applies the boundary rules (no ellipsis, no comma cuts, no unbalanced brackets, names whole); INV-30 compares the Workbook RAID rows with the Kit RAID Log; INV-31 checks text quality; INV-32 checks bounds, overlaps, the fit estimate, and minimum fonts.
4. **Snapshots (`tests\snapshots\` and `tests\snapshots_proposed\`)**: Regression tests compare newly generated workbook models and document contents against approved snapshot files in `tests/snapshots/<fixture>/snapshot.json`. Any differences are written to `tests/snapshots_proposed/` for human review.
5. **Full Test Suite Execution**:
   ```bash
   pytest -q
   ```

---

## 6. Review and Promotion Workflow

Snapshot updates and oracle modifications follow a controlled human-in-the-loop review process:

1. **Collect Review Bundle**: Run the PowerShell script to stage approved and proposed snapshots into `review_uploads/`:
   ```powershell
   .\make_review_copies.ps1
   ```
2. **Human Inspection**: A human reviewer inspects the diffs between approved snapshots (`tests/snapshots/`) and proposed snapshots (`tests/snapshots_proposed/`).
3. **Safe Promotion**: The human promotes the approved changes using the promotion script:
   ```powershell
   .\promote_snapshots.ps1 -Message "Promote snapshots for <feature or revision>"
   ```
   Add `-Push` to push the resulting commit to `origin`.

*Note*: Only a human may promote snapshots or edit files in `tests/oracles/`. For complete details on the find-check-fix diagnostic loop, see [spec/Review_Loop_Reference.md](spec/Review_Loop_Reference.md).

---

## 7. Rules for Contributors and Coding Agents

- **Never edit `spec\` or `tests\oracles\`**: Specifications and oracle truths are strictly human-owned.
- **Never run `--update-snapshots` or edit `tests\snapshots\` directly**: Snapshot updates are performed solely by humans via `promote_snapshots.ps1`.
- **No project-specific data in `src\`**: In accordance with rule P-08, never hardcode SOW-specific IDs, client names, or deliverables into application source code (enforced by `tests/test_no_sow_literals.py`).
- **Re-recordings go in their own commit**: Any update to LLM recordings or fixture baselines must be isolated in a dedicated Git commit.
- **Commit all work and maintain a clean working tree**: Always ensure `git status` is clean before and after completing a task.

---

## Talent Team Onboarding Deck

`--slides` writes `{Project}_Talent_Onboarding_Deck.pptx` and `{Project}_Talent_Onboarding_Deck.trace.json` beside the Kit and Workbook; because every fact in the deck traces to those two documents, `--slides` also writes them in the same run (the log says `Deck sources: Startup Kit and Project Delivery Workbook also written`).

- **Slides:** Cover, Project Charter, Workstreams / Milestones / Deliverables / Dates, Acceptance Criteria, High-Risk Items, Client Collaboration, and Your Project Kit. Each slide carries talking points and a `SOURCES` line in its speaker notes.
- **Template:** `templates/Toptal_Presentation_Template.pptx`, or the path in `DECK_TEMPLATE_PATH`. The generator removes the template's slides and slide parts and builds on the `CUSTOM_1` (cover) and `CUSTOM_16` (content) layouts.
- **Trace manifest:** lists every element (slide, shape, displayed text, and its `Kit` / `Workbook` TraceRefs) and every talking point on slides 2 to 6. `check_artifacts` uses it.
- **Text:** shown whole or cut only at a sentence or clause boundary; never an ellipsis, a comma cut, an unbalanced bracket, or a shortened name. Text that does not fit gets a smaller font (within the minimums), then a `+N more` row or line.
- **Review aids:** `python -m src.tools.render_deck <deck.pptx>` renders each slide to a PNG beside the deck when LibreOffice is installed (set `SOFFICE_PATH` if it is not on `PATH`). `python -m src.tools.dump_deck <deck.pptx>` prints every slide's text, tables, notes, and the slide-part count.

---

## 8. Project Structure

```text
startup_kit/
├── inputs/                 # Input directory for SOWs and project documentation (.pdf, .docx, .pptx, .txt)
├── output/                 # Output directory for generated Word reports and Excel workbooks
├── reports/                # Specification revision and verification reports
├── review_uploads/         # Staging directory for review bundles collected by make_review_copies.ps1
├── spec/                   # Authoritative specification documents and revision history
├── src/
│   ├── core/               # Pydantic data models, interfaces, and baseline definitions
│   ├── extractors/         # Multi-format document parsers and ingestion coordinator
│   ├── generators/         # Document writers for Word reports (.docx) and Project Delivery Workbook (.xlsx)
│   ├── llm/                # LLM clients, prompt templates, structured domain extractors, and caching
│   ├── scoring/            # 4-dimension readiness scoring engine and CLI telemetry reporting
│   └── tools/              # Utility scripts for artifact checking, normalization, and fixture recording
├── tests/
│   ├── fixtures/           # SOW inputs and recorded LLM cache payloads
│   ├── oracles/            # Human-curated ground truth facts per SOW
│   ├── snapshots/          # Approved golden snapshots for regression testing
│   └── snapshots_proposed/ # Proposed snapshot updates generated during test runs
├── main.py                 # CLI entry point
├── make_review_copies.ps1  # Helper script to assemble snapshot review bundles
├── promote_snapshots.ps1   # Safe snapshot promotion and verification script
├── requirements.txt        # Python package dependencies
└── README.md               # Tool documentation and user guide
```
