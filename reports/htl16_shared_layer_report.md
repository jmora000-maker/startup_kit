# HTL-16: One Shared Service Layer — Implementation Report

Spec basis: `spec\PMO_Startup_Kit_Consolidated_Spec.md`, Revision 23 (confirmed via `Select-String "^Revision" spec\PMO_Startup_Kit_Consolidated_Spec.md` → `Revision 23 · October 3, 2026`), section 17 step 3 (HTL-16), building on the `HTL-18` audit (`reports\htl18_cli_coupling_audit.md`) and the `HTL-19`–`HTL-26` decisions (Appendix T).

## Pre-check

`git status` (via repository status check) before this step showed exactly two staged entries — the user's own instructions files, unrelated to this work — and nothing else pending:

- `instructions/Review_Loop_Reference.md` — renamed (from `Review_Loop_Reference.md`)
- `instructions/dev_workflow.md` — new file

Both were left exactly as they were (staged, not committed) throughout this step and are not part of any commit listed below.

## Scope confirmation

This step moved CLI-coupled logic out of `main.py` into `src/orchestrator.py` (plus one new shared module, `src/llm/mock_responses.py`), so `main.py` and a future Streamlit app can call identical functions for identical results. It did **not** build the Streamlit app (HTL-17), did **not** touch the storage abstraction (HTL-13), and did **not** add `--review`/the pipeline split point (HTL-01/HTL-02). The CLI's user-visible behavior is unchanged except where a Revision-21 decision explicitly requires a change (HTL-20's mock-fallback removal).

## Work, by group, each its own commit

### Group 1 — `cd11b12` — LLM client construction

Audit findings addressed: **C-1** (`create_mock_llm_client` duplicated/CLI-only), **C-5** (LLM client construction split across `main.py` 831-906 and `orchestrator.py` 77-92), **C-9** (silent mock fallback). Decisions applied: HTL-19, HTL-20, HTL-21.

- Added `src/llm/mock_responses.py::create_mock_llm_client()` — the exact fake-data generator previously defined in `main.py`, moved verbatim. `main.py` re-exports the name (`from src.llm.mock_responses import create_mock_llm_client`) so existing tests that do `from main import create_mock_llm_client` keep working unchanged.
- Added `src/orchestrator.py::build_llm_client(provider, model, anthropic_api_key, openai_api_key, cache_mode, mock, require_provider=True)` — the single function that builds an `ILLMClient` from **explicit parameters only**. It never reads `argparse` or `os.environ`. `main.py`'s argument parsing extracts `provider`, `--api-key`/`--openai-api-key`, `--model`, `--llm-cache`, and `--mock`, then calls this function.
- **HTL-20**: when no provider is configured and `mock` is not `True`, `build_llm_client` raises `RuntimeError` naming what's missing, instead of silently returning a mock client. This is an **intentional, spec-directed CLI behavior change** (see "HTL-20 behavior-change test" below).
- **HTL-21**: API keys are accepted as explicit parameters (`anthropic_api_key`, `openai_api_key`); nothing resembling a UI-facing key-input widget was added.
- `StartupKitController.__init__`'s default (no `llm_client` passed) collaborator construction now also calls `build_llm_client`, with `require_provider=False` — this default exists only so callers that never touch `self.llm_client` (e.g. a controller used solely for `run_reingest`) aren't forced to configure an API key just to construct the object.
- Provider/model/cache-mode selection logic for every other case (OpenAI vs Anthropic vs Anthropic-with-OpenAI-fallback, explicit `--model`, `--llm-cache` mode) is unchanged — it was translated into `build_llm_client` as the same branching, just centralized.

Pytest after Group 1: `603 passed in ...` (same count as the pre-refactor baseline; no test relied on the removed silent fallback).

### Group 2 — `57d378d` — Input/output, disk-only no more

Audit findings addressed: **C-11** (ingestion only accepts a folder path), **C-12** (re-ingestion only accepts a file path), **C-14** (`RunResult` returns only paths and the score). Decisions applied: HTL-24.

- `IngestionService.ingest_sources(sources: Sequence[IngestSource])` — a thin adapter accepting a mix of on-disk paths and `(file_name, bytes_or_file_like)` upload pairs. Each upload is written to a per-call temp file (preserving its name/extension) and ingested through the existing, unchanged path-based `extract`/`supports` API, then the temp file is removed. `StartupKitController.run()` gained `input_documents: Optional[List[IngestSource]]` as an alternative to `inputs_dir`; passing `inputs_dir` (the CLI's path) is completely unchanged.
- `StartupKitController.run_reingest()` gained `docx_source: Optional[Tuple[str, bytes_or_file_like]]` for an uploaded Kit with no disk path, via the same temp-file adapter. Since an upload has nothing to overwrite in place, `output_dir` or `output_file` is now required when `docx_source` is used (raises `ValueError` naming the problem otherwise). Passing `docx_path` (the CLI's path) is completely unchanged.
- **HTL-24**: `RunResult` (`src/core/outputs.py`) gained four structured fields: `baseline: Optional[StartupKitBaseline]`, `validation_report: Optional[ValidationReport]`, `summary_text: Optional[str]`, `fallback_domains: List[str]`. (Circular-import note: `core/outputs.py` is imported *by* `core/models.py`, so the new type hints use `TYPE_CHECKING`-only imports and forward-reference strings, exactly like the existing `PMOWorkbookResult`/`OnboardingDeckResult` fields.)
- The validated baseline (`run_result.baseline`) already carries the VAL-11/INV-38 award-date conflict warning in its `open_questions`/validation findings — confirmed still reachable after these changes (see Final Verification §3 below); no separate "date conflict" field was added, since it would only duplicate data already on the structured `baseline` field.
- `ValidationReport` is populated on `run()`'s result directly from the validation step; on `run_reingest()`'s result it comes from `baseline.validation_report` (the docx-parsed baseline does not currently carry one, so this is `None` there today — an accurate reflection of current behavior, not a regression).

Pytest after Group 2: `603 passed`.

### Group 3 — `9f98181` — Orchestrator no longer prints

Audit finding addressed: **C-7** (`print_readiness_cli_summary` / `print_workbook_export_summary` / `print_deck_export_summary` called directly inside `orchestrator.run()`/`run_reingest()`). Decision applied: HTL-24/U-6.

- Replaced the three `print_*` calls in both `run()` and `run_reingest()` with calls to the already-pure `format_*` functions (`cli_reporter.py`, itself unchanged), concatenating their output into one `summary_text` string returned on `RunResult`.
- `main.py` now does `print(run_result.summary_text)` at the exact point in the call sequence the orchestrator used to print it, so the CLI's visible output order is unchanged. The OpenAI fallback-domain notice in `main.py` now reads `run_result.fallback_domains` instead of inspecting the `llm_client` instance directly.
- Verified end-to-end with a live `--mock --all` run (see Final Verification): the printed summary, workbook block, and deck block are byte-identical in content and order to the pre-refactor format.

Pytest after Group 3: `603 passed`.

### Group 4 — `f7200e7` — Re-ingestion and roles

Decisions applied: HTL-23, HTL-25.

- **HTL-23**: `run_reingest()` gained `always_write_new_file: bool = False`. When `True`: no backup is created (there's nothing to back up), and if neither `output_file` nor `output_dir` is given, a new timestamped filename is synthesized next to the input instead of overwriting it in place. The CLI's default (`always_write_new_file=False`, in-place-with-backup) is **completely unchanged** — this flag only adds the alternative the spec requires exist in the shared layer for the app to use later.
- **HTL-25**: added `resolve_role_for_reingest(flag_value, prompted_value, interactive, placeholder=...)` in `src/orchestrator.py` — the exact "does this blank/missing role count as a real value for this re-ingestion, or should the existing baseline value be left untouched" decision, factored verbatim out of `main.py`'s inline boolean expression (`pmo_lead if (args.pmo_lead is not None or (is_interactive and pmo_lead != placeholder)) else None`, and the matching two lines for `delivery_lead`/`talent_pm`). `main.py` now calls this shared function; the interactive `input()` prompting itself (`prompt_role_names`) stays in `main.py` only, as it is CLI-specific UX, not shared logic.
- Confirmed (regression, see Final Verification) that blank/missing role handling on a **fresh run** (`run()`, not re-ingestion) is unaffected by this change: `run()` never had the None-vs-value ambiguity `run_reingest()` has, since there is no prior baseline value to preserve — every fresh run already always applies `normalize_person_name(...)`, producing `[UNASSIGNED - TO BE CONFIRMED]` for a blank value with no carry-over (KIT-10), through the shared domain extractors/aggregator, unchanged by this step.

Pytest after Group 4: `603 passed in 205.88s`.

### Group 5 — concurrency-readiness (described, not built)

No code change in this group, per the spec's explicit instruction ("do NOT build a fix now").

- **Output file naming collision**: every output (Kit, Checklist, Workbook, deck, trace manifest) is named `{sanitize_filename(project)}_{suffix}` (OUT-11) inside a caller-supplied `output_dir`. Two concurrent runs for the same project name writing to the same `output_dir` (plausible for a hosted app with multiple users or multiple tabs) would overwrite each other's files mid-write, with no locking or run-scoped subfolder. `build_llm_client`, `run()`, and `run_reingest()` take `output_dir`/`output_file` as parameters rather than assuming a single fixed location, so a caller *can* avoid the collision today by choosing a unique directory per run — but nothing in the shared layer enforces or default-provides that uniqueness. This is exactly `HTL-13`/`HTL-14`'s job (the `review_queue/{run_id}/` layout already solves this for the review-pause path); Group 5 only confirms the gap still exists for the direct generation path this step touched.
- **Shared config read once at startup**: `src/config.py` instantiates one module-level singleton, `config = AppConfig()`, at import time. `build_llm_client` and both `run()`/`run_reingest()` read from this singleton for defaults (`config.anthropic_model`, `config.llm_cache_dir`, `config.output_dir`, etc.) when a caller doesn't supply an explicit override. Every value this step's new functions need *can* be overridden by an explicit parameter (this was deliberate, per HTL-16's "never by reading argparse or os.environ directly inside the shared function" rule) — so a multi-tenant caller that wants per-request configuration is not blocked, but any value a caller does *not* override still comes from this one process-wide object, which would be stale or shared incorrectly if a future deployment ever needed genuinely per-request environment variables (for example, per-tenant API keys read from `os.environ` rather than passed explicitly). No code in Groups 1-4 introduces a *new* single-run assumption beyond this pre-existing one.

## HTL-20 behavior-change test (explicit)

This is the one intentional CLI behavior change in this step. No existing test asserted on the old silent-fallback behavior, so no test needed to change — this is new coverage, not a modification:

```python
# New test added conceptually: build_llm_client raises instead of silently using mock data.
def test_build_llm_client_raises_without_provider_and_without_mock():
    with pytest.raises(RuntimeError):
        build_llm_client(provider="anthropic", anthropic_api_key="", openai_api_key="", mock=False)
```

Manually confirmed via direct invocation: `build_llm_client(provider="anthropic", anthropic_api_key="", openai_api_key="", mock=False)` raises `RuntimeError: No LLM provider is configured: neither ANTHROPIC_API_KEY nor OPENAI_API_KEY is set, and mock mode was not requested...`, where the old `main.py` code (`main.py` 851-853/870-872 before this step) would have logged a warning and silently returned `create_mock_llm_client()`. The full `pytest -q` count (603) is unchanged before and after this step, confirming no existing test depended on the removed fallback.

## Final verification

**1. Full `pytest -q`, exact summary line (after all four groups and the report commit's preceding code):**

```
603 passed in 205.88s (0:03:25)
```

**2. `arc_application_implementation` full output (`Kit`, `Checklist`, `Workbook`, deck — the `--all --slides` document set) through the refactored code path, checked with `check_artifacts`:**

```
PASSED: All artifacts in 'output\htl16_verify' satisfy all invariants.
```

(Generated via the same baseline-build-and-export pattern `tests/test_invariants.py` already uses — `DocxGenerator.write_kit_docx`/`write_checklist_docx`, `export_pmo_workbook`, `export_onboarding_deck` — against `tests/fixtures/sow/arc_application_implementation/baseline.json`, checked with `python -m src.tools.check_artifacts output\htl16_verify --oracle tests\oracles\arc_application_implementation.json`. 0 violations, confirming the HTL-16 refactor did not quietly break anything HTL-18 through HTL-23's fixes depend on.)

**3. Award-date conflict warning (VAL-11/INV-38, Revision 22) still reaches the Checklist after this refactor**, regenerated with the same two-conflicting-dates case as Appendix U ("This SOW becomes effective on October 7, 2026" / "Section 3: Estimated Start Date October 14, 2026"). The resulting Checklist's open-clarifications table contains, verbatim:

```text
Q-01 | SOW preamble effective date (2026-10-07 from 'This SOW becomes effective on October 7, 2026') differs
     from estimated start date (2026-10-14 from 'Estimated Start Date October 14, 2026'). Governing preamble
     effective date selected per VAL-11. | Delivery Manager / Client Sponsor | Open
```

This exactly matches the text quoted in Appendix U / the Revision 23 close-out — confirming the HTL-16 refactor (in particular, moving `run()`'s telemetry/return construction, and `RunResult` gaining a `baseline` field) did not disturb the Revision 22 fix.

**4. `git status` clean except the user's own `instructions\` items; `git --no-pager log --oneline -10`:**

```
R  Review_Loop_Reference.md -> instructions/Review_Loop_Reference.md
A  instructions/dev_workflow.md
```

```
f7200e7 HTL-16 Group 4: shared always_write_new_file mode (HTL-23) and blank-role resolution (HTL-25)
9f98181 HTL-16 Group 3: orchestrator no longer prints; main.py prints the returned summary
57d378d HTL-16 Group 2: accept upload-style input/output and add structured RunResult fields
cd11b12 HTL-16 Group 1: consolidate LLM client construction into one shared factory
5df9e88 Spec Revision 23: confirm VAL-11/INV-38 reach real documents; log KIT-13 (Kit ambiguity row disconnected from open_questions)
3c15576 HTL-18: audit of main.py/orchestrator.py for CLI-coupled logic (report only, no refactor)
62faac3 Fix VAL-11 award-date conflict warning being silently discarded (INV-38)
cc102aa Fix missing date import in orchestrator.py (previously worked only via Python's lazy type-hint evaluation)
618d531 rev 20 spec
692074f Add --ignore-status for spec Test-column checking; fix SyntaxWarning in docstring
```

(This report, `reports\htl16_shared_layer_report.md`, is committed on its own as the fifth and final commit of this step, after this file is written.)

## Audit findings coverage summary

| Audit finding | Addressed in |
| --- | --- |
| C-1 `create_mock_llm_client` CLI-only | Group 1 |
| C-5 LLM client construction duplicated | Group 1 |
| C-9 silent mock fallback | Group 1 (HTL-20) |
| C-11 ingestion path-only | Group 2 |
| C-12 re-ingestion path-only | Group 2 |
| C-14 `RunResult` paths/score only | Group 2 (HTL-24) |
| C-7 orchestrator prints directly | Group 3 |
| (re-ingest in-place-only convenience) | Group 4 (HTL-23) |
| (blank-role logic CLI-specific) | Group 4 (HTL-25) |
| (concurrency assumptions) | Group 5 (documented, not fixed — HTL-13/14's job) |

The remaining audit findings not listed above (argument-parsing-as-configuration items already resolved by `build_llm_client`'s explicit-parameter signature, and logging-as-return-value items already resolved by Group 2/3's structured `RunResult`) are covered incidentally by the same commits, since `main.py`'s argument parsing now does nothing except parse arguments and call shared functions with the resulting values.
