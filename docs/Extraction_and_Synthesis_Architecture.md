# Extraction and Synthesis Architecture

This document specifies the end-to-end architecture of the PMO Startup Kit extraction pipeline, covering document ingestion precedence, multi-domain structured extraction, customer-outcome synthesis, 1:1 structural traceability, and companion audit-trail manifest generation.

---

## 1. Architectural Philosophy & Dual-Tier Pattern

The Startup Kit ingestion pipeline couples large language model (LLM) document parsing with strict deterministic validation and schema modeling:

1. **Extraction over Free-Form Text**: Document extraction operates against strongly-typed Pydantic schemas across 14 discrete extraction domains rather than unbounded text prompts.
2. **Dual-Tier Synthesis Architecture (`HTL-60`, `HTL-67`)**:
   - **Tier 1 (LLM Extraction-Time Synthesis)**: Synthesizes high-level narrative fields (`problem_statement`, `solution_overview`, `success_criteria_summary`) directly during extraction when the model has access to full source document context.
   - **Tier 2 (Deterministic Generation-Time Fallback)**: If an LLM synthesis field is absent or unpopulated, document builders apply deterministic fallback logic (e.g., combining `high_level_scope` items or extracting structured bullets) to guarantee that artifact generation never fails.
3. **Deterministic Verification Post-Extraction**: Extracted fields pass through rule-based invariant checks (structural counts, boundary checks, gate numbering repairs) before reaching the human review UI.

---

## 2. Ingestion Pipeline & Multi-Document Precedence (`HTL-57`, `HTL-59`)

The Generate page provides two dedicated file upload slots:
- **Required Primary Slot (SOW)**: Accepts a single primary Statement of Work (`.pdf`, `.docx`, `.pptx`, `.txt`).
- **Optional Supporting Slot (Kickoff & Discovery Materials)**: Accepts one or more supporting files, including kickoff presentations, technical architecture briefs, and Markdown meeting notes (`.md`).

### Precedence Hierarchy & Gap-Filling Rules
- **SOW as Definitive Authority**: The primary SOW establishes legal project name, client name, governance tier, contract classification, milestone dates, acceptance gates, deliverables, and commercial terms.
- **Supporting Materials for Operational Gap-Filling**: When the primary SOW is purely administrative or silent on background context (e.g., legacy technical debt, operational bottlenecks, or specific stakeholder pain points), the extractor uses supporting notes to fill missing narrative context.
- **Role Tagging**: Ingested files are labeled with `document_role="sow"` or `document_role="supporting"`. System prompts instruct extractors to prioritize facts from the SOW while drawing gap-filling background from supporting documents.

---

## 3. Customer-Outcome Problem Statement Extraction (`HTL-54`, `HTL-55`, `HTL-57`)

The `charter.problem_statement` field captures the client's current-state bottleneck or operational challenge in 1–2 concise sentences.

### Extraction Instructions & Honest Fallback
- **Customer Outcome & Pain Points**: Extracted statements must articulate concrete operational symptoms (e.g., manual workarounds, batch window overruns, compliance risks, or unmaintained legacy code).
- **Honest Null Fallback**: If neither the primary SOW nor supporting documents mention an existing problem or current-state limitation (e.g., greenfield product development or new capability builds), the extractor MUST set `problem_statement` to `null` (`None`). Inventing, inferring, or fabricating problems is strictly prohibited.
- **Single-Call Efficiency**: Extraction is performed in a single consolidated pass within `CharterDomainExtractor`, maximizing recall across multi-file evidence without requiring expensive multi-pass verification loops.

---

## 4. Outcome-Framed Solution Overview & Success Criteria (`HTL-60`, `HTL-67`)

Slide 5 ("What does success look like?") and Slide 6 ("Solution Overview") of the Client Kickoff Deck present executive summaries tailored for client kickoff audiences:

### Field Definitions & Extraction Rules
- **`charter.solution_overview`**: A cohesive 2–3 sentence narrative synthesizing the core technical approach, integrated workstreams, and delivery cadence. It explains how workstreams connect to deliver business value, using active verbs rather than listing deliverable titles or bullet points.
- **`charter.success_criteria_summary`**: A natural 2–3 sentence narrative framed entirely around customer outcomes and business value: what the client actually receives, can do, or can decide upon completion (e.g., operational visibility, confident modernization decisions, everyday usability, or trusted evidence).

### Explicit Metric Exclusions
To maintain client-centric executive clarity, `success_criteria_summary` strictly excludes raw internal delivery metrics:
- No percentage completion or test coverage thresholds (e.g., `"covers at least 95% of workloads"`).
- No contractual review SLAs (e.g., `"5-day milestone review signoff"`).
- No raw artifact or milestone counts.

---

## 5. 1:1 Structural Traceability Standard (`HTL-62`, `HTL-63`, `HTL-64`)

To ensure exact fidelity between contractual documents and generated delivery artifacts, deliverable acceptance criteria are modeled as native string lists:

- **Model Definition**: `Deliverable.acceptance_criteria: List[str]` represents distinct, countable criteria.
- **Count Invariance**: If an SOW defines $N$ acceptance criteria for a deliverable, the Kit (`.docx`), Delivery Workbook (`.xlsx`), and presentation decks (`.pptx`) must render exactly $N$ structural bullet points or list items.
- **Deterministic Cleaning**: Parsing strips leading bullet characters (`•`, `-`, `*`) and numeric prefixes during normalization, storing clean criterion strings while preserving exact count parity.

---

## 6. Companion Trace Manifests (`OUT-14`, `HTL-65`, `HTL-72`)

Every generated presentation deck is accompanied by a machine-readable JSON trace manifest (`{Project}_Client_Kickoff_Deck.trace.json` or `{Project}_Governance_Deck_trace.json`):

### Manifest Structure
Each entry in `entries[]` defines:
- `slide`: Integer slide number (1-indexed).
- `shape`: PowerPoint shape identifier or logical container label.
- `element`: Human-readable UI element name (e.g., `"What problem are we solving?"`, `"Solution Overview"`).
- `displayed_value`: Exact text rendered on the slide.
- `traces`: List of `TraceRef` objects containing `artifact`, `locator`, `key`, and `field`.
- `derived`: Optional classification tag indicating provenance mode (`null` for direct field usage, `"Deterministic Fallback"` for rule-based synthesis, or `"Fallback"` for default values).

### Dynamic Trace Mapping
Trace generators evaluate the baseline's actual data state at export time:
- When `charter.problem_statement` is present, it traces directly to `artifact="Charter", field="problem_statement"`.
- When `charter.success_criteria_summary` is populated, it traces directly to `artifact="Charter", field="success_criteria_summary"`. If synthesized via fallback, `traces` references `success_criteria` with `derived="Deterministic Fallback"`.
- Slide 6 workstreams and out-of-scope panels dynamically bind to `Milestones` and `Charter.exclusions` / `SOWInterpretation.out_of_scope_items`.

---

## 7. Slide 1 Title Sizing & Review Warnings (`HTL-72`, `HTL-84`, `HTL-85`)

To ensure clean visual hierarchy across presentation decks without dynamic font shrinkage regressions:
- **Flat 24pt Standard**: Title text on Slide 1 of both the PS Governance Kickoff Deck and Client Kickoff Deck is rendered at a fixed 24pt font.
- **Fact Review Warning**: In `src/review_ui/app.py`, if the combined length of Client Name and Project Name (`len(project_name.strip()) + len(client_name.strip())`) exceeds 60 characters, the Fact Review interface displays a contextual warning advising reviewers that the combined title risks wrapping or overflow on Slide 1.

---

## 8. Financial Scrubbing in Delivery Workbook (`HTL-77`)

To prevent billing figures, milestone fees, and commercial pricing terms from appearing in operational schedules:
- **Downstream Generation Pipeline**: Financial scrubbing operates downstream specifically within the Project Delivery Workbook (`.xlsx`) generation pipeline (`src/generators/pmo_workbook/builder.py`), where `clean_text_v2` and `clean_contract_text` process Milestone descriptions, WBS tasks, and `critical_path_assumptions`.
- **Regex Smoothing vs. Redaction Placeholders**: `sanitize_financial_text` (`src/config.py`) uses targeted regular expressions to strip raw dollar amounts (`$26,808`), milestone fees, and hourly rates (`150/hr`) while naturally smoothing sentences (e.g., transforming `"Fee of $26,808 is invoiced on acceptance"` to `"Fee is invoiced on acceptance"`). It never inserts `[REDACTED]` placeholder tokens.
- **Preservation of Legitimate Numerics**: The sanitizer preserves formulas (cells starting with `=`), dates, percentages, SLA windows, durations, deliverable IDs, and WBS codes.
- **Pipeline Scope**: Financial sanitization is scoped specifically to Workbook output generation and does not modify source text prior to LLM extraction or alter other baseline data.

---

## 9. Security Gates & Admin Controls (`HTL-46`, `HTL-53`, `HTL-75`, `HTL-86`)

The application enforces role-appropriate security and diagnostic boundaries across three distinct surfaces:
- **Billed LLM Action Protection (`GENERATION_PASSPHRASE`)**: Unauthenticated users may inspect public runs and review baseline facts, but SOW uploads and document generation require validation against `GENERATION_PASSPHRASE`.
- **Administrative Settings & Deliverable Gating (`ADMIN_PASSPHRASE`, `HTL-27`, `HTL-86`)**:
  - The "Advanced (admin)" configuration section exposes:
    - **LLM Provider**: `LLM_PROVIDERS = ["anthropic", "openai"]` (default `config.default_provider`).
    - **Model Override**: `PROVIDER_DEFAULT_MODEL_LABEL = "(provider default)"`, mapping to `MODEL_OPTIONS_BY_PROVIDER` (`claude-sonnet-5-5`, `claude-haiku-4-5-20251001` for Anthropic; `gpt-4o`, `gpt-6.1-sol` for OpenAI).
    - **Mock Mode**: `gen_mock` / `reingest_mock` (default `False`), executing offline deterministic extraction via `MockLLMClient` (`create_mock_llm_client()`).
    - **LLM Cache Mode**: `LLM_CACHE_MODES_IN_APP = ["off", "replay"]` (default `"off"`).
  - The legacy "Startup Kit" deliverable checkbox is positioned as the final option in column 4 (`[Client Kickoff Deck, PS Governance Kickoff, Delivery Workbook, Startup Kit]`) and completely omitted when locked so other controls do not shift.
- **Diagnostic Trace Download Gating (`ADMIN_PASSPHRASE`, `HTL-86`)**: On Fact Review, diagnostic per-deck trace JSON files (`.trace.json`, `_trace.json`, `_Deck_Trace_Manifest.json`) are completely absent when locked, and become available for download only when the Fact Review admin gate is unlocked.
- **Manage Runs Lifecycle Dashboard (`ADMIN_PASSPHRASE`, `HTL-75`, `HTL-81`, `HTL-82`, `HTL-83`)**: Provides administrative status filtering, run archive/unarchive toggles, and bulk run purge capabilities.
- **Collapsed Fact Review Ergonomics (`HTL-53`)**: All 14 Fact Review expandable category containers default to collapsed (`expanded=False`), allowing reviewers to focus on targeted validation without excessive scrolling.
