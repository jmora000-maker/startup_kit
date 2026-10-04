# HTL-18 Audit: CLI-Coupled Logic in `main.py` and `src/orchestrator.py`

Date: 2026-10-03. Spec: `spec\PMO_Startup_Kit_Consolidated_Spec.md`, Revision 20 (commit `618d531`).
Pre-check: `git status` was clean at `618d531` before this audit started.

This is an audit only (section 17, step 2). No source file was changed; this report is the only new file.
HTL-16 (step 3) is the step that acts on these findings.

## 1. Spec text (raw `Select-String` output)

```
278: | HTL-16 | **One shared service layer.** All real logic -- ingestion, the 12-pass extraction, validation (`VAL-01` to `VAL-11`), document generation, and re-ingestion -- lives in one place (`src/orchestrator.py`, extended as needed), never duplicated in `main.py` or the Streamlit app. Every CLI flag and every Streamlit input both resolve to the same call into this layer, with the same return type (`RunResult` or equivalent); a capability added or changed here is immediately available to both front ends, with no second place to update. | New | `test_orchestrator.py` |
279: | HTL-17 | **Streamlit covers the full CLI surface.** The app's scope widens from "list and review runs" to a complete second front end: upload a SOW (or the other ingestible documents `main.py` accepts) in place of `inputs\`; set every option `main.py` exposes today (start date, governance tier, contract type, the three named roles, LLM provider and model, `--mock`, `--llm-cache` mode, `--reingest-docx` by uploading an existing Kit, and which outputs to produce); trigger a run; and, once generated, download every produced file. A `--review`-equivalent run (`HTL-01` onward) is one path through this same app, not a separate one. | New | `test_streamlit_app.py` (UI smoke test), Manual |
280: | HTL-18 | **Audit before building.** Before `HTL-16` and `HTL-17` are implemented, audit `main.py` and `orchestrator.py`, line by line, for logic coupled to the CLI specifically: argument parsing standing in for configuration, a `print` or log line standing in for a return value, and any assumption that input or output is a local file path rather than in-memory bytes or an uploaded-file object. Report every instance found, then move it into the shared layer, or behind a thin adapter, before any Streamlit code is written against it. | New | Manual audit report |
```

```
334: 2. **HTL-18, the audit:** in parallel with step 1, audit `main.py` and `orchestrator.py` for CLI-coupled logic and report every instance found. Nothing in steps 3 onward is implemented until this report exists, since both the pipeline split point (step 5) and the full Streamlit surface (step 6) modify or call exactly the code this audit is examining.
335: 3. **HTL-16, the shared service layer:** using the audit's findings, move CLI-coupled logic into `orchestrator.py` (or a thin adapter) so `main.py` and the future Streamlit app can call identical functions for identical results.
```

Citation note: the HTL-17 row above (line 279) names `test_streamlit_app.py`. That is the spec's *planned* test for a requirement whose Status is still New. It does not exist yet, and this report does not claim it passes. `check_report_citations` reports it as missing for this file, because the name appears inside a verbatim quote.

Note: HTL-18's last sentence ("then move it into the shared layer") is, per section 17, done in step 3 (HTL-16), not in this step.

## 2. Summary

| Bucket | Count |
|---|---|
| CORE LOGIC (correctly placed, no action) | 9 |
| CLI-COUPLED (needs moving or an adapter in HTL-16) | 20 (C-1 to C-17, plus prompts P-1 to P-3) |
| UNCLEAR / NEEDS A DECISION | 8 |

The two biggest problems:

1. **LLM client selection exists only in `main.py`.** Provider choice, API-key resolution, the cache mode, `--mock`, and a silent fall-back to the mock client when keys are missing (`main.py` 831–906) are all CLI-only. A Streamlit caller would have to duplicate about 75 lines, which HTL-16 forbids.
2. **Input and output are local directory paths end to end.** `run()` accepts only an inputs *directory* and writes into an output *directory*. Every extractor, the Kit parser and every writer takes a `Path` (`src/core/interfaces.py` lines 15, 20, 78). `RunResult` returns paths, not bytes. An upload/download front end (HTL-17) cannot call this without a temp-directory adapter or an interface change.

One latent defect was also found (C-17 below): `src/orchestrator.py` uses `date` in two signatures without importing it.

## 3. CORE LOGIC (no action needed)

| ID | Location | What it is | Why it is already correct |
|---|---|---|---|
| K-1 | `orchestrator.py` 54–111 | `StartupKitController.__init__` with every collaborator injectable | A Streamlit caller can inject the same objects. (The *defaults* are a concern, see C-9.) |
| K-2 | `orchestrator.py` 146–152 | Ingestion and the "no documents" `FileNotFoundError` | Raises, rather than printing and exiting. (Its input type is a concern, see C-11.) |
| K-3 | `orchestrator.py` 156–157 | VAL-11 stated award date extraction | Pure function over ingested documents. (The discarded warning is C-15.) |
| K-4 | `orchestrator.py` 161–220 | 12-pass concurrent extraction, then the backlog pass | Per-call `ThreadPoolExecutor`, no module state. |
| K-5 | `orchestrator.py` 222–245, 350–397 | Tier, contract-type and role overrides, with `normalize_person_name` | Parameters, not `args`. |
| K-6 | `orchestrator.py` 247–270 | Aggregation and `validate_and_repair_baseline` | Pure model transforms. |
| K-7 | `orchestrator.py` 399–401 | Re-ingest readiness recalculation | Pure. |
| K-8 | `src/core/outputs.py` 12–36 | `OutputSelection` and `OutputSelection.from_flags` | Already shared; the flag names are just keyword arguments, so a UI can call `from_flags` or construct `OutputSelection` directly. |
| K-9 | `src/scoring/cli_reporter.py` 12, 152, 255 | `format_readiness_cli_summary`, `format_workbook_export_summary`, `format_deck_export_summary` | They already *return* strings. Only the `print_*` wrappers (142–149, 246–252, 302–308) print. This makes C-6 a cheap fix. |

## 4. CLI-COUPLED

For each item: file and lines, what it does now, what it should become in the shared layer (HTL-16), and why it would break or be duplicated if called from Streamlit.

### 4.1 Argument parsing standing in for configuration

**C-1. `main.py` 438–596, `parse_args()`.**
- **Now:** defines the whole option surface as 25 argparse flags and calls `parser.parse_args()` against `sys.argv`. It reads `config.default_provider` at 473 as a flag default.
- **Should become:** a plain, typed request object in the shared layer (for example `RunRequest`: inputs, output target, tier, contract type, the three roles, provider, model, API keys, mock, cache mode, start date, `OutputSelection`, reingest Kit). `main.py` maps `args` to it; Streamlit maps widgets to it.
- **Why:** HTL-17 requires "every option `main.py` exposes today". Right now the only list of those options is argparse, which Streamlit can't use.

**C-2. `main.py` 727–733, start-date parsing.**
- **Now:** `date.fromisoformat(args.start_date.strip())`. On a bad value it logs an error and returns exit code 1.
- **Should become:** a shared parse/validate helper that raises `ValueError`, or a request object that accepts a `date`. The exit code stays in `main.py`.
- **Why:** an exit code means nothing to Streamlit. The UI needs the error message or a typed value.

**C-3. `main.py` 735–741 and 758, mode selection (`mode = "1"` or `"2"`).**
- **Now:** chooses generate or re-ingest from `args.reingest_docx`, an interactive prompt, or a default. The result is a magic string.
- **Should become:** determined by which shared entry point is called (`run` or `run_reingest`), or by an explicit field on the request. No string codes.
- **Why:** a UI just has two buttons or tabs.

**C-4. `main.py` 812–813, choosing default folders from `args.mock`.**
- **Now:** `config.mock_inputs_dir` / `config.mock_output_dir` are chosen in `main.py`. `orchestrator.py` 130–142 *also* chooses them, separately, with `isinstance(self.llm_client, MockLLMClient)`.
- **Should become:** one rule, in one place.
- **Why:** this is the duplication HTL-16 forbids. The two rules already disagree in kind: one keys off a flag, the other off the client's class. See also U-1.

**C-5. `main.py` 831–906, LLM client construction (provider, model, keys, cache mode, mock).**
- **Now:**
  - picks the provider from `--openai` / `--provider` (832–835);
  - resolves keys (837–843);
  - picks the cache mode (845);
  - then builds `MockLLMClient`, or `CachingLLMClient(LangChainLLMClient)` for OpenAI, Anthropic, or Anthropic-with-OpenAI-fallback (847–906).
- **Should become:** a shared factory, for example `build_llm_client(provider, model, anthropic_key, openai_key, cache_mode, mock) -> ILLMClient`, called identically by both front ends.
- **Why:**
  - It's the largest piece of real logic living only in the CLI.
  - It has rules a second copy would easily get wrong. For example, at 855 `--model` is ignored for OpenAI if it equals `config.anthropic_model`. And in the Anthropic-without-key-but-OpenAI-key branch (873–886), `--model` is silently ignored.
  - The silent mock fall-backs at 851–853 and 870–872 are a decision item: see U-2.

### 4.2 `print` or log lines standing in for a return value

**C-6. `orchestrator.py` 307–312 (in `run`) and 461–466 (in `run_reingest`).**
- **Now:** the shared layer itself calls `print_readiness_cli_summary`, `print_workbook_export_summary` and `print_deck_export_summary`, which `print()` to stdout (`cli_reporter.py` 149, 252, 308).
- **Should become:** the orchestrator returns the data (or the `format_*` strings, see K-9) on the result object. `main.py` prints them.
- **Why:** under Streamlit the summary would go to the server's stdout, not the user's browser. It's also printed from inside the "shared" layer, so a UI caller can't turn it off.

**C-7. `main.py` 799–807 and 930–938, success reporting.**
- **Now:** after a run, `main.py` logs each produced file's `.resolve()`d path, then returns exit code 0.
- **Should become:** this part is fine as CLI presentation, *provided* everything it shows is on `RunResult`. Today it is, except for the deck trace manifest, which is reachable only as `run_result.slides.manifest_path`.
- **Why:** listed so HTL-16 keeps `RunResult` complete enough for a download list. See C-14.

**C-8. `main.py` 927–928, OpenAI fallback notice.**
- **Now:** `hasattr(llm_client, "fallback_domains")` is read *after* the run and logged. It's per-instance state (`src/llm/client.py` 140, 234–235, 330–331).
- **Should become:** a `fallback_domains` (or `warnings`) field on the result, filled by the shared layer.
- **Why:** a UI user should see that some domains used the fallback model. Today that's only in a log line, and it depends on `main.py` keeping its own reference to the client.

### 4.3 Global/config state used as the source of configuration

**C-9. `orchestrator.py` 77–92, default LLM client in `__init__`.**
- **Now:** if no client is injected, the controller builds `CachingLLMClient(LangChainLLMClient(...))` from `config.anthropic_api_key`, `anthropic_model`, `openai_api_key`, `openai_model`, `temperature`, `llm_cache_dir` and `llm_cache_mode`. These are module-global values frozen when the program starts.
- **Should become:** the same factory as C-5, with explicit parameters.
- **Why:**
  - **Two diverging client builders.** This builder ignores provider and mock entirely, so it isn't the one `main.py` uses.
  - **The re-ingest path builds a pointless client.** `main.py` 781–784 doesn't inject a client, so re-ingest (which needs no LLM) still builds one from global config.
  - **Shared config would leak.** A Streamlit session that wants per-user keys can't use this default without mutating the shared global `config`, which would leak keys across sessions (see C-16).

**C-10. `orchestrator.py` 130–142, default inputs and outputs from `config` and the client's class.**
- **Now:** when `inputs_dir` or `output_dir` is `None`, falls back to `config.inputs_dir` / `config.output_dir`, or to the mock folders if the client is a `MockLLMClient`.
- **Should become:** explicit inputs and outputs required from the caller (or supplied by one documented resolver, see C-4).
- **Why:**
  - Server-relative folders like `inputs/` and `output/` have no meaning for a web upload.
  - Picking behaviour by `isinstance` on the client class is brittle. A caching wrapper around a mock, for example, would not count as mock.

### 4.4 Input assumed to be a file already on local disk

**C-11. `orchestrator.py` 147 to `src/extractors/service.py` 55–79; `src/core/interfaces.py` 15, 20.**
- **Now:**
  - `run()` accepts only a *directory*.
  - `ingest_directory` requires `dir_path.exists()` and `is_dir()`, lists the folder, and skips names starting with `~` or `.`.
  - Every extractor's `extract(file_path: Path)` and `supports(file_path: Path)` take paths.
- **Should become:** an ingestion entry point that accepts a list of named inputs (file name plus bytes or file-like object) as well as a directory. Alternatively, a thin adapter that writes uploads to a per-run temp folder and calls the existing path API.
- **Why:** HTL-17 says "upload a SOW ... in place of `inputs\`". `st.file_uploader` returns in-memory objects, not paths.

**C-12. `orchestrator.py` 343–348; `src/core/interfaces.py` 78; `startup_kit_docx_parser.py` 99–101.**
- **Now:** `run_reingest(docx_path)` checks `docx_file.exists()` and parses from a path.
- **Should become:** accept bytes or a file-like object for the Kit to re-ingest, or an adapter to a temp file.
- **Why:** HTL-17 asks for "`--reingest-docx` by uploading an existing Kit".

### 4.5 Output assumed to go to a local directory the caller knows

**C-13. `orchestrator.py` 282–305 and 404–456; `docx_generator.py` 274–298; `pmo_workbook/__init__.py` 36–41; `onboarding_deck/__init__.py` 39–45.**
- **Now:**
  - Every generator creates the folder with `mkdir`, saves to disk, and returns only a path.
  - File names come only from `sanitize_filename(project_name)`, with no run identifier.
  - `run_reingest` by default writes *back over the input file* (`target_path = docx_file`, 409–410), with a timestamped backup created alongside it (420–428).
- **Should become:** the shared layer writes into a caller-owned destination, for example a per-run folder or a storage object (which lines up with HTL-13's `ReviewStorage`). It returns enough information for the caller to offer downloads.
- **Why:**
  - In a web app the "output dir" is on the server, so the user can't open it.
  - Overwriting an uploaded file in place, with a backup next to it, has no web meaning.
  - Without a run ID in the folder or file name, two runs of the same SOW clobber each other (see C-16).

**C-14. `src/core/outputs.py` 39–46, `RunResult`.**
- **Now:** holds `kit_path`, `checklist_path`, `workbook` (`PMOWorkbookResult`), `slides`, `slides_path` and `readiness_score`. It does *not* hold:
  - the validated `StartupKitBaseline`;
  - the `validation_report` (computed at `orchestrator.py` 270, then discarded except where it's attached to the baseline);
  - the gate decision;
  - the summary text;
  - `fallback_domains`;
  - the VAL-11 date-conflict warning.
- **Should become:** HTL-16 says "same return type (`RunResult` or equivalent)". It needs those fields for a UI to show what the CLI currently prints. The HTL-02 split point will need the baseline anyway.
- **Why:** today the only way to see the readiness summary or warnings is to read stdout or the logs.

**C-15. `orchestrator.py` 157, discarded `date_warning`.**
- **Now:** `stated_award_date, date_warning = extract_stated_award_date(documents)`. `date_warning` is never used, logged or returned.
- **Should become:** carried to the result (and arguably into the validation report). This was already noted as an open finding in the HTL-06 standalone report.
- **Why:** listed here because "nothing reaches the caller" is exactly the return-value gap HTL-18 asks about. It's invisible to *both* front ends today, not just Streamlit.

### 4.6 Interactive prompts with no web equivalent

**P-1. `main.py` 599–623, `prompt_directories`.**
- **Now:** `input()` asks for the inputs and output folders. Its defaults are bound when Python defines the function: `default_inputs_dir: Path = config.inputs_dir`, `default_output_dir: Path = config.output_dir` (603–604).
- **Should become:** CLI-only. It stays in `main.py`; uploads replace it in the UI.
- **Why it is listed:** it's correctly CLI-only, but HTL-16 must not move it into the shared layer.

**P-2. `main.py` 626–657 and 660–673, `prompt_reingest_file` and `prompt_execution_mode`.**
- **Now:** `input()` and `print()` loops.
- **Should become:** CLI-only, as above.

**P-3. `main.py` 676–699 and 774–792, role prompts and re-ingest role forwarding.**
- **Now:** `prompt_role_names` uses `input()`, defaulting to `"[UNASSIGNED - TO BE CONFIRMED]"`. For re-ingest, `main.py` 790–792 then decides whether each role is forwarded or passed as `None`, by comparing against that placeholder string *and* checking `is_interactive`.
- **Should become:** the rule "a role is applied only if a person actually supplied it" belongs in the shared layer, keyed on `None` vs. a value. It shouldn't depend on string sentinels or on whether a terminal is attached.
- **Why:**
  - **Behaviour would differ.** KIT-10 behaviour (`tests/test_cli_roles.py`) currently depends on CLI interactivity. A Streamlit form with blank role fields must reach the same result. Today it could only do that by copying lines 790–792.
  - **Inconsistent `None` handling.** `run()` (236) uses `delivery_lead if delivery_lead is not None else delivery_manager`. `run_reingest` (351) uses `delivery_lead or delivery_manager`, so an empty string behaves differently in the two paths.

### 4.7 Global / module-level state under concurrent requests (Cloud Run, HTL-14/15)

**C-16. Concurrency hazards (several locations).**

| Hazard | Location | Effect with two concurrent runs |
|---|---|---|
| Output file names depend only on the project name | `docx_generator.py` 295–297; `pmo_workbook/__init__.py` 37–38; `onboarding_deck/__init__.py` 40–45 | Two runs of the same SOW into the same output folder overwrite each other's files, including the `.trace.json` manifest. |
| LLM cache files written non-atomically, with no lock | `src/llm/caching_client.py` 96, 109, 132, 141 (`open(cache_file, "w")`) | Two runs recording the same prompt race on one file; a concurrent reader can read half-written JSON. The default cache folder is `tests/fixtures/llm_cache` (`config.py` 116), which a server should never write to. |
| Global `config` singleton, evaluated once at import; `.env` loaded with `override=True` | `src/config.py` 11–15, 100–117, 232 | Read-only use is safe. Any per-request change (keys, model, folders) would leak across sessions, and C-9 / C-10 invite exactly that. |
| `logging.basicConfig` in `main.py` 48–54; module loggers everywhere | `main.py`, `orchestrator.py` | Log lines from concurrent runs interleave with no run ID, so a UI can't show one run's log. |
| Relative paths resolved against the process working folder | `config.py` 102–117 (`inputs`, `output`, `templates/...`, `tests/fixtures/...`) | Depends on the server's start folder. This is the same fragility found earlier with `mock_inputs_dir`. |

Already safe: the `ThreadPoolExecutor` is per call (`orchestrator.py` 163); `fallback_domains` is per client instance; `MockLLMClient` and `DocxGenerator` are built per call in `main.py`.

### 4.8 Latent defect found during the audit

**C-17. `orchestrator.py` 6, 124, 336: `date` is never imported.**
- **Now:** the module imports only `from datetime import datetime` (line 6), but annotates `start_date: Optional[date] = None` in both `run` (124) and `run_reingest` (336).
- **Why it hasn't broken yet:** on the project's Python 3.14, annotations are evaluated lazily, so the code runs.
- **Evidence it is a real bug:**
  ```
  .venv\Scripts\python.exe -c "import src.orchestrator as o, inspect; print(inspect.signature(o.StartupKitController.run).parameters['start_date'])"
  ...
    File "...\src\orchestrator.py", line 124, in __annotate__
      start_date: Optional[date] = None,
  NameError: name 'date' is not defined
  ```
- **Why it matters for HTL-16/17:** any code that introspects these signatures will crash, for example a form generated from the request type, `typing.get_type_hints`, or pydantic validation of the call. On an older Python it would fail at import.
- **Status:** not fixed here, per this step's scope. The fix is a one-line import, to be applied in HTL-16 or as its own small commit.

## 5. UNCLEAR / NEEDS A DECISION

Each of these needs your answer before HTL-16 moves the code.

**U-1. Is "mock" a CLI-only concept, or a first-class run option?**
HTL-17 lists `--mock` among the options the app must expose, which suggests first-class. But two related things are coupled to it today:
- the *folders* (`config.mock_inputs_dir` = the tracked `tests/fixtures/sow/mock_sow/inputs`, `config.mock_output_dir` = `output/Reports/Test`);
- the *fake data*, `create_mock_llm_client()` (`main.py` 57–435, about 380 lines of hard-coded responses living in the CLI module).

**Question:** In the app, should "mock" mean only "use the offline client on whatever the user uploaded"? Or should it also mean "ignore uploads and use the tracked mock fixture"? And should `create_mock_llm_client` move out of `main.py` into a shared module (for example `src/llm/mock_responses.py`) so both front ends can use it?

**U-2. Silent fall-back to mock when API keys are missing (`main.py` 851–853, 870–872).**
The CLI logs a warning and generates documents from the Pfizer mock data, not the uploaded SOW, when no keys are configured.

**Question:** Should the shared layer keep this behaviour, or should it raise an error? In a web app it would quietly produce a plausible-looking Kit for the wrong project. Should the CLI keep it as a CLI-only convenience?

**U-3. API keys as user input.**
`--api-key` / `--openai-api-key` (`main.py` 533–547) let a CLI user pass keys. HTL-15 says keys move to Secret Manager.

**Question:** Should the Streamlit app accept keys from the user at all, or only use server-side secrets? HTL-17's list ("every option `main.py` exposes today") doesn't mention keys explicitly, so it is unclear whether they count as an "option".

**U-4. `--llm-cache` mode in a web app.**
`record` writes into `tests/fixtures/llm_cache` by default (`config.py` 116), which is test data.

**Question:** Should the app expose `record` (and if so, write to which storage?), only `off` / `replay`, or nothing? HTL-17 lists "`--llm-cache` mode" as an option to expose.

**U-5. Re-ingest output destination.**
The CLI default overwrites the input Kit in place, with a timestamped backup (`orchestrator.py` 409–410, 420–428). `--output-file` (`main.py` 455–460) and `--output-dir` exist only for this path.

**Question:** For an uploaded Kit, should the shared layer always write a new file (no in-place / backup concept), keeping in-place-with-backup as CLI-only behaviour?

**U-6. Where the readiness and summary text should live.**
The `format_*` functions are in `src/scoring/cli_reporter.py`, a "CLI" module.

**Question:** Should the summary *data* go on `RunResult` and each front end render it itself? Or should the formatted text (CLI-flavoured, as currently produced) be shared? This decides whether `cli_reporter` stays CLI-only or becomes shared presentation logic.

**U-7. Role-name defaults and KIT-10.**

**Question:** Should a blank role in the UI be treated exactly like "flag not supplied, non-interactive"? That is, `[UNASSIGNED - TO BE CONFIRMED]` on generate, and *don't override* on re-ingest. It's the closest match, but it bakes the CLI's interactive-vs-non-interactive distinction (P-3) into a decision for a UI that has no such distinction.

**U-8. Verbose logging and error detail.**
`-v` (`main.py` 591–595) only changes the log level and whether tracebacks are logged (942).

**Question:** Is log verbosity an app option at all, or a server setting? Should the app show the exception message to the user (the CLI shows it via `logger.error`)?

## 6. Coverage note

- **`main.py`:** read in full (lines 1–948). Lines 57–435 are the mock response data inside `create_mock_llm_client()`. They're covered by U-1 rather than line by line, since they contain no control flow.
- **`src/orchestrator.py`:** read in full (lines 1–481).
- **Collaborators** read only to confirm a finding: `src/config.py`, `src/core/outputs.py`, `src/core/interfaces.py`, `src/extractors/service.py`, `src/scoring/cli_reporter.py` (function list), `src/llm/client.py` (`fallback_domains`), `src/llm/caching_client.py` (file I/O), and the three generators' save entry points.
- **Not audited:** the collaborators' own internals beyond those points. HTL-18 scopes the audit to `main.py` and `orchestrator.py`.
- **No code was changed.** `main.py`, `src/orchestrator.py` and every other source file are untouched.
