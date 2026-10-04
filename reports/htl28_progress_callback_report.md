# HTL-28 Report: Per-Stage Generation Progress Callback

## Pre-check

- `git status`: clean (working tree clean, one local commit ahead of origin) before starting.
- Spec confirmed at **Revision 26** via `Select-String`:
  ```
  spec\PMO_Startup_Kit_Consolidated_Spec.md:3:Revision 26 · October 3, 2026
  ```
- `HTL-28` row confirmed present via `Select-String -Pattern "HTL-28"` (full text pasted into the
  working session; not reproduced from memory here).

## Scope implemented

Added a real `on_progress(stage: str, detail: str = "")` callback to both
`StartupKitController.run()` and `StartupKitController.run_reingest()` in `src/orchestrator.py`,
defaulting to a shared no-op (`_noop_progress`) so every existing caller (the CLI, all 643
pre-existing tests) is completely unaffected unless it explicitly passes one.

### Stage boundaries (no new stages invented; no pipeline restructuring)

- `run()`: `"ingesting"` → `"extracting"` (once; the 12 domain passes still run concurrently and
  are not individually reported) → `"validating"` → `"generating"` (once per document type
  actually selected: Startup Kit, Readiness Checklist, Delivery Workbook, Onboarding Deck).
- `run_reingest()`: `"ingesting"` (parsing the uploaded/existing Kit docx) → `"validating"` (the
  readiness recalculation) → `"generating"` (once per document type actually selected). There is
  no `"extracting"` stage here since re-ingestion never re-runs LLM extraction -- it parses an
  already-generated Kit document.

## Streamlit app wiring

`src/review_ui/generate.py`'s Generate and Re-ingest tabs now wrap their run call in `st.status(...)`
instead of HTL-17's interim `st.spinner(...)` with a single generic message. A real `on_progress`
callback passed into `_run_generate`/`_run_reingest` updates the status box's label and appends a
line for each stage as the orchestrator actually reports it, via the new pure, testable
`progress_status_label(stage, detail)` helper (`STAGE_LABELS` maps each real stage name to
readable text; an unrecognized stage still renders something sensible rather than breaking the
display).

## Test results

- **Full suite before this step's last checkpoint (HTL-17, prior session)**: `632`/`638` passed
  (the UI-correctness pass landed at `638`).
- **After adding the `on_progress` parameter (no-op default) to both shared functions**:
  `pytest -q` → **`638 passed`** -- confirms zero regression from the pure additive signature
  change.
- **After adding the two stage-sequence tests**
  (`test_on_progress_fires_expected_stage_sequence_for_run`,
  `test_on_progress_fires_expected_stage_sequence_for_run_reingest`) and the Streamlit wiring +
  its own `progress_status_label` tests: `pytest -q` → **`643 passed`** (638 + 5 new: the 2
  stage-sequence tests plus 3 `progress_status_label` tests).

### Stage-sequence test assertions (shown, not just "it passes")

`tests/test_orchestrator.py::test_on_progress_fires_expected_stage_sequence_for_run`:
```python
result = controller.run(
    inputs_dir=populated_inputs_dir,
    output_dir=output_dir,
    outputs=OutputSelection(kit=True, checklist=True, workbook=True, slides=True),
    on_progress=on_progress,
)
stages = [stage for stage, _ in calls]
assert stages == [
    "ingesting", "extracting", "validating",
    "generating", "generating", "generating", "generating",
]
generating_details = [detail for stage, detail in calls if stage == "generating"]
assert generating_details == ["Startup Kit", "Readiness Checklist", "Delivery Workbook", "Onboarding Deck"]
```

`tests/test_orchestrator.py::test_on_progress_fires_expected_stage_sequence_for_run_reingest`:
```python
result = controller.run_reingest(
    docx_path=original_docx,
    outputs=OutputSelection(kit=True, checklist=True, workbook=True),
    create_backup=False,
    on_progress=on_progress,
)
stages = [stage for stage, _ in calls]
assert stages == ["ingesting", "validating", "generating", "generating", "generating"]
generating_details = [detail for stage, detail in calls if stage == "generating"]
assert generating_details == ["Startup Kit", "Readiness Checklist", "Delivery Workbook"]
```

Both run through a real `StartupKitController` (mock LLM client for `run()`; a real
`StartupKitDocxParser` round-trip for `run_reingest()`), not mocked internals -- the stage order
is observed from an actual execution, not asserted against a hand-written expectation of the
code's structure.

## Live app progress confirmation (AppTest)

Using a scratch `streamlit.testing.v1.AppTest` script (not committed; deleted after use) that ran
a real mock-mode `StartupKitController.run()` inside an `st.status` block identical to
`generate.py`'s own pattern, the rendered markdown elements captured, in order:

```
['Ingesting documents... (tests\\fixtures\\sow\\mock_sow\\inputs)',
 'Running extraction...',
 'Validating...',
 'Generating documents... (Startup Kit)',
 'Generating documents... (Readiness Checklist)',
 'Generating documents... (Delivery Workbook)',
 'Generating documents... (Onboarding Deck)',
 'DONE:96.8']
```

This confirms the status display genuinely reflects real callback-reported stages as they
actually happen during a real run, not a simulated/timed sequence.

## Streamlit smoke test

`streamlit run src/review_ui/app.py --server.headless true` started cleanly; a direct HTTP request
to the running server returned **status 200**. The process was then stopped.

## Final verification

1. **Full `pytest -q`**: **`643 passed`**.
2. **git status**: clean except the user's own `instructions\` items (untouched, as in every
   prior pre-check/step).
3. `git --no-pager log --oneline -5`:
   ```
   041075a HTL-28: wire Generate/Re-ingest tabs to a live st.status display driven by the real on_progress callback, replacing HTL-17's interim generic spinner
   41f9b26 HTL-28: add on_progress(stage, detail) callback to orchestrator.run()/run_reingest(), firing at real ingesting/extracting/validating/generating stage boundaries (default no-op; CLI unaffected)
   604fb6e spec 26
   19a4674 chore(release): bump version to 0.8.0
   688db5e Streamlit UI polish: persist Generate/Re-ingest form state across page switches (reuses state_persistence.py), shared contract-type and model dropdowns, generation progress spinner, governance-tier default fixed to use config.default_governance_tier
   ```
   (this report's own commit will follow as the next entry).

## Notes

- No new stages were invented and no pipeline step was restructured -- `on_progress` calls were
  inserted at the exact existing log-line locations the audit/spec already treat as stage
  boundaries.
- The CLI (`main.py`) was not changed in this step; it continues to rely on its existing log
  lines and never passes an `on_progress` callback, exactly as HTL-28 specifies ("the CLI's
  existing print/log behavior is unaffected unless `main.py` chooses to pass a callback (it
  doesn't need to for this step)").

---

## Correction Note (added 2026-10-04)

*This note was appended after the original report. The content above is left unchanged so the history stays visible.*

The "Test results" section above (lines 44-51) frames the `638`/`643` numbers as two sequential
pytest runs separated by a real commit boundary -- "right after the no-op signature change", then
"after adding the two stage-sequence tests ... and the Streamlit wiring". That framing is
inaccurate. Checking the actual commit history shows the `on_progress` signature/call-site change
in `src/orchestrator.py` and the two new `test_orchestrator.py` stage-sequence tests were committed
**together, in a single commit** (`41f9b26`). No commit in this step's history was ever in a
638-passing state on its own.

Both numbers are still real and were independently reproduced in a follow-up verification pass,
but reconstructing the `638` checkpoint required temporarily removing tests from **two separate
files together** -- the 2 new tests in `tests/test_orchestrator.py` *and* the 3 new
`progress_status_label` tests in `tests/test_streamlit_app.py` -- not undoing one isolated,
previously-existing commit step. Removing only the 2 orchestrator tests alone reproduces `641`
passed, not `638`.

**Resolution:** no code or test changes were needed; this is a correction to the report's
narrative framing only. The underlying `638` and `643` pytest counts remain accurate and
reproducible as stated.
