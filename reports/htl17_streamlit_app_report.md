# HTL-17: Streamlit app covers the full CLI surface (with HTL-27's admin gate)

## 0. Pre-check

`git status` before this step showed clean except the user's own `instructions\` items (left untouched throughout, never committed). Spec header confirmed at Revision 25 before Group 1 work and again before the HTL-27 rework, via `Select-String`:

```
spec\PMO_Startup_Kit_Consolidated_Spec.md:3:Revision 25 · October 3, 2026
```

## 1. Scope actually built

The original Group 2 scope (every option visible to every user) was superseded mid-task by Revision 25's `HTL-27`, which requires splitting the form: upload, dates, governance tier, contract type, the three named roles, and output selection stay visible to everyone; LLM provider/model, the mock toggle, and the llm-cache mode move behind a collapsed, passphrase-locked "Advanced (admin)" section. Groups 1, 3, and the final verification proceeded exactly as originally scoped; only Group 2's field visibility changed.

## 2. Commits and what each addressed

| Commit | Addresses | Summary |
| --- | --- | --- |
| `5a42a7a` | C-2, C-3, C-4, C-10 | Group 1: `parse_start_date`, `resolve_execution_mode`, `resolve_mock_io_dirs` added to `src/orchestrator.py`; `main.py` and `StartupKitController.run()` both call the same three functions. |
| `4ed2c07` | HTL-17 scope (pre-`HTL-27`) | Groups 2+3: `src/review_ui/generate.py` built (upload/options form, trigger, structured-result rendering); `src/review_ui/app.py` rewired into a two-page router. |
| *(this commit)* | `HTL-27` | `config.admin_passphrase` added; `generate.py`'s form split into always-visible fields and a passphrase-gated "Advanced (admin)" expander (`is_admin_unlocked`, `resolve_llm_settings`, `_render_admin_gate`); six new tests proving the gate is genuinely inaccessible without the correct passphrase. |

## 3. Group 1 (C-2/C-3/C-4/C-10)

- `parse_start_date(value)`: the one shared ISO-date parse/validate helper; raises `ValueError` on a bad value, letting each caller decide how to present the failure. `main.py` keeps its existing log-and-exit-1 behavior on that exception, so CLI behavior on a bad date is unchanged (same message, same exit code).
- `resolve_execution_mode(reingest_docx, is_interactive, prompted_mode)`: the one shared mode-selection rule (`--reingest-docx` always wins; otherwise the CLI's own interactive prompt result; otherwise Initial Generation). `main.py`'s interactive `input()` prompting itself stays CLI-only.
- `resolve_mock_io_dirs(mock, inputs_dir, output_dir)`: the one shared mock-folder-selection rule, replacing both `main.py`'s own `args.mock`-based defaulting and `StartupKitController.run()`'s `isinstance(self.llm_client, MockLLMClient)` branch.
- Full suite after Group 1: **603 passed** (plus the 10 new direct unit tests for these three functions, included in later totals) -- no regression; every consolidation is a pure refactor.

## 4. Groups 2 and 3 (built together; the form and its trigger/render logic share state)

- `src/review_ui/generate.py`: a complete second front end -- `render()` with two tabs (Generate from SOW upload, Re-ingest an existing Kit), each a `st.form` whose submit calls `StartupKitController.run()` / `run_reingest()` through `_run_generate`/`_run_reingest` (never duplicating orchestrator logic).
- HTL-24: results render as real widgets (`st.metric` for readiness score, `st.table` for the breakdown, gate decision, open questions in an expander, fallback-model warning, validation findings in an expander) plus one `st.download_button` per generated file (`collect_download_targets`), built from `RunResult`'s structured fields, never from `cli_reporter`'s formatted text.
- HTL-20/HTL-26: `build_llm_client`'s `RuntimeError` (no provider configured, mock not requested) is caught and shown via `st.error` with its exact message; any other exception shows `f"Run failed: {exc}"`, never a raw traceback.
- HTL-23: `_run_reingest` always passes `always_write_new_file=True`; there is no in-place-overwrite control anywhere in the UI.
- HTL-25: `resolve_app_role` always calls the shared `resolve_role_for_reingest(..., interactive=False)`; a blank field never overrides an existing baseline value, and there is no interactive/non-interactive toggle in the UI.
- `src/review_ui/app.py`: rewired into a two-page router (sidebar radio) so the pre-existing, HTL-06/07 fact-review screen keeps working unchanged at the same `streamlit run src/review_ui/app.py` entry point.
- Full suite after Groups 2+3: **626 passed**. Streamlit smoke test: `streamlit run src/review_ui/app.py --server.headless true` started cleanly with no errors and served HTTP 200.

## 5. `HTL-27`: the admin-gated Advanced section (the Group 2 rework)

- `src/config.py` gained `admin_passphrase: str = os.getenv("ADMIN_PASSPHRASE", "dev-only-change-me")` -- the same `os.getenv(VAR, default)` convention every other secret/setting in `AppConfig` already uses. In production this environment variable is populated from a Secret Manager value (per `HTL-15`'s existing deployment design); for local development, when it is unset, the code falls back to a clearly-named, documented, non-secret placeholder (`"dev-only-change-me"`) -- never a hardcoded real secret.
- `is_admin_unlocked(entered_passphrase, configured_passphrase)`: unlocks only on an exact, non-empty match. An empty configured passphrase never unlocks (a defensive refusal, not a usable bypass).
- `resolve_llm_settings(admin_unlocked, provider, model, mock, cache_mode)`: when the section was never unlocked, every run uses fixed, safe defaults -- `config.default_provider`, no model override, mock off, cache off -- regardless of whatever an invisible, inert widget might otherwise hold. Only an unlocked admin's actual selections are ever passed through.
- `_render_admin_gate(key_prefix)`: a collapsed `st.expander("Advanced (admin)", expanded=False)` rendered outside each tab's `st.form` (a passphrase check must take effect immediately; a form only reacts on its own submit button). Locked, it shows only a passphrase input and an Unlock button. Unlocked (tracked per-tab in `st.session_state`), the form then renders the LLM provider/model/mock/cache-mode widgets.
- `render()`'s two tabs each call `_render_admin_gate` before their `st.form`, conditionally render the four admin widgets only when unlocked, and call `resolve_llm_settings` right before triggering the run -- so a locked section's (non-rendered, default-valued) widgets can never influence the actual run even if someone tried to force a value into them.
- No API key field exists anywhere, locked or unlocked (`HTL-21` unchanged) -- `build_app_llm_client` reads `config.anthropic_api_key`/`config.openai_api_key` only. `LLM_CACHE_MODES_IN_APP = ["off", "replay"]` is unchanged by `HTL-27`: `record` stays excluded even for an unlocked admin.
- New tests in `tests/test_streamlit_app.py` (6 added): correct passphrase unlocks; a wrong passphrase does not unlock; an empty configured passphrase never unlocks (including against an empty entry); the real `config.admin_passphrase` value round-trips correctly; `resolve_llm_settings` forces the fixed safe defaults when locked (confirming the admin controls are genuinely inaccessible in substance, not just hidden in the widget tree); and `resolve_llm_settings` passes an unlocked admin's actual choices through unchanged.
- Full suite after this rework: **632 passed**. Streamlit smoke test re-run after the rework: started cleanly, no errors, HTTP 200.

## 6. Final verification

### 6.1 Full pytest -q, exact summary line

```
632 passed in 218.56s (0:03:38)
```

### 6.2 A full, real run through the app's own code path (not `main.py`) against `arc_application_implementation`

**Scope limitation found and handled honestly.** This fixture's original input corpus (per spec Appendix N: the SOW PDF plus two internal Toptal planning/briefing documents) is only partially present in this environment -- only the SOW PDF itself survives on disk, at `inputs\SOW\Syngenta\Syngenta Crop Protection, LLC - ARC Application Implementation SOW + Exhibit A.pdf` (confirmed present; not tracked in git, consistent with `.gitignore`). The fixture's recorded `llm_cache` entries key on the exact prompt text built from the *full* original multi-document corpus, so driving the Generate tab's real extraction path (`_run_generate`) against only the surviving PDF in `--llm-cache replay` produced a genuine `LLMCacheMiss` (not a silent fallback) -- expected, since a different document set builds a different prompt and therefore a different cache key.

Given that constraint, two real, non-mock-logic-bypassing checks were run through the app's own code instead of one:

1. **Generate tab, real uploaded document, HTL-19 in-scope app-mock mode** (needs no cache match and no live key): `_run_generate` with the real SOW PDF above, `resolve_llm_settings(admin_unlocked=True, mock=True, ...)`, all four outputs selected. Produced a real Kit, Checklist, Workbook, and Deck. `check_artifacts` (no oracle, since mock data does not correspond to any recorded SOW's oracle) on the result:

   ```
   PASSED: All artifacts in '...\startup_kit_app_run_17a2zjr8' satisfy all invariants.
   ```

2. **Re-ingest tab, the fixture's own recorded (real) baseline, non-mock settings**: a Kit `.docx` was first written straight from `tests/fixtures/sow/arc_application_implementation/baseline.json` (the fixture's own real, validated extraction result), then uploaded through `_run_reingest` with `resolve_llm_settings(admin_unlocked=True, mock=False, cache_mode="replay", ...)` (re-ingestion makes no LLM call at all, so this exercises the real settings-resolution path without needing a cache hit). Produced all four outputs; readiness score 75.0%. `check_artifacts --oracle arc_application_implementation` on this result showed `INV-19`/`INV-33` keyword-taxonomy workstream-mapping violations (milestone phase labels not surviving the Kit-`.docx` round trip) and one `INV-09` violation.

   **This is confirmed pre-existing and unrelated to this step's work, not a regression introduced by `HTL-17`.** The identical seed Kit, re-ingested through `main.py --reingest-docx` (the CLI's own, unmodified-by-this-session code path) with `--mock`, reproduces the exact same `INV-19`/`INV-33`/`INV-02`/`INV-30`/`INV-34` violation set under `check_artifacts --oracle arc_application_implementation`. Since both front ends call the identical shared `run_reingest()` and the same violations appear either way, this is a property of `StartupKitDocxParser`'s existing Kit-`.docx` round-trip (the same family of gap already tracked as `KIT-12`), not something this session's `generate.py` or `HTL-27` work caused. No code change was made to chase this, per the issue's scope (this step is a refactor/app-build step, not a new round-trip-fidelity fix); it is logged here for visibility.

### 6.3 No API key field, no record cache option, no in-place-overwrite option anywhere in the UI

`grep`-equivalent search (`api[_-]?key|API key|record|in.place|overwrite|passphrase`) across `src/review_ui/*.py` confirms:

- Every `api_key` occurrence reads from `config.anthropic_api_key`/`config.openai_api_key` (server-side config); none is a Streamlit input widget.
- The only `record` occurrence is the comment explaining `LLM_CACHE_MODES_IN_APP = ["off", "replay"]` deliberately excludes it.
- The only `overwrite`/`in-place` occurrence is the comment on `always_write_new_file=True`, confirming no in-place-overwrite option exists.
- `passphrase` occurrences are all `is_admin_unlocked`/`_render_admin_gate`/`config.admin_passphrase` -- no literal passphrase string anywhere in committed code; the only default value is the documented dev-only placeholder `"dev-only-change-me"` in `src/config.py`, and this project's own `.env` (gitignored, confirmed via `Select-String .gitignore -Pattern "\.env"`) already supplies a real, non-committed `ADMIN_PASSPHRASE`.

### 6.4 git status / git log

`git status` clean except the user's own untouched `instructions\` items throughout this step. `git --no-pager log --oneline -10` (after this report's commit) shows, newest first: this report's commit, the `HTL-27` rework commit, `25cd856 add spec 25`, `4ed2c07` (Groups 2+3), `5a42a7a` (Group 1), `9c03eec spec 24`, and the five `HTL-16` commits below that.

## 7. Notes carried forward

- The deferred, pre-existing Kit-`.docx` round-trip phase-label gap found in 6.2 is not fixed here, consistent with this step's scope (build the app, don't chase unrelated existing gaps); it behaves identically through `main.py` and the app, so neither front end is worse off than the other.
- Section 17's own build order lists the queue/state-machine steps (`HTL-13`, `HTL-04`, `HTL-01/02`) as *before* the full app in the originally-planned sequence; this step followed the issue's explicit instruction that this is a straight-through app only, with no `pending_review` pause/resume flow, consistent with how the app behaves today.
