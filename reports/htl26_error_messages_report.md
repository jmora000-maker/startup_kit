# HTL-26 -- Clear, Specific Error Messages on a Failed Run

## Scope (from the spec)

```
spec\PMO_Startup_Kit_Consolidated_Spec.md:289:| HTL-26 | **Verbosity and error detail.** Log verbosity (`-v`) is a
server/deployment setting, never an app-facing option; it is not exposed in the app's UI at all. On a failed run, the
app shows a clear, specific error message (for example "extraction failed: Anthropic API returned an error"), neither
a bare generic message nor a raw traceback, so a colleague can usefully report the problem without being shown
implementation detail. | New (decision recorded in Appendix T) | Manual |
```

Pre-check: `git status` was clean before this step started (no pending `instructions\` items even -- confirmed via
`git status --porcelain=v1 -uall` returning nothing).

## Investigation (before any fix)

`src/review_ui/generate.py`'s Generate and Re-ingest tabs each already had a two-branch exception handler, added
proactively during HTL-17/HTL-28 (referencing "HTL-26" in a comment even before this step formally began):

```python
except RuntimeError as exc:
    st.error(str(exc))
except Exception as exc:  # noqa: BLE001
    st.error(f"Run failed: {exc}")
```

No `-v`/verbosity option exists anywhere in `src/review_ui/` (confirmed via a regex search for `verbos|-v\b|log_level|
--verbose` across that directory -- no matches), so that half of HTL-26 was already satisfied and required no change.

Three failure cases were reproduced directly (not guessed), by calling the real shared functions
(`build_llm_client`, `StartupKitController.run`) with inputs engineered to fail at a known point:

### 1. No LLM provider configured, mock not requested (HTL-20's `RuntimeError`)

```python
build_llm_client(provider="anthropic", anthropic_api_key="", openai_api_key="", mock=False)
```

**Before (and after -- unchanged):**
```
No LLM provider is configured: neither ANTHROPIC_API_KEY nor OPENAI_API_KEY is set, and mock mode was not requested. Set an API key, choose a different provider, or pass mock=True.
```
This was already clear and specific (names the exact missing config and the exact remedies), so it needed no change.

### 2. A real extraction failure (a fake client raising `Exception("Anthropic API returned an error")`)

**Before:**
```
Run failed: Anthropic API returned an error
```
**After:**
```
extraction failed: Anthropic API returned an error
```

### 3. An unexpected/unhandled exception (a fake client triggering `None.some_attribute`, an `AttributeError`
unrelated to any LLM/API error)

**Before:**
```
Run failed: 'NoneType' object has no attribute 'some_attribute'
```
**After:**
```
extraction failed: 'NoneType' object has no attribute 'some_attribute'
```

In both cases 2 and 3, the "before" text used a flat, un-specific "Run failed: ..." prefix that doesn't identify which
stage broke -- not matching the spec's own example shape ("extraction failed: ..."). Neither case exposed a raw
Python traceback (only `str(exc)`), so the "no traceback" half of HTL-26 was already satisfied; the gap was purely
the missing stage-specific naming.

## Fix

`src/review_ui/generate.py` gained:

- `STAGE_FAILURE_LABELS`: maps each real `on_progress` stage name (`ingesting`, `extracting`, `validating`,
  `generating`) to its failure wording (`ingestion`, `extraction`, `validation`, `document generation`).
- `format_run_error(exc, last_stage=None)`: a pure function building `"{stage label} failed: {reason}"`, falling
  back to `"run failed: ..."` when no stage was ever reached (e.g. a failure in client construction itself, before
  `run()`/`run_reingest()` is even entered) or when the reported stage isn't recognized. `str(exc)` alone is used as
  the reason: for every exception type this app actually raises or catches (HTL-20's `RuntimeError`, LLM/API client
  errors, validation errors, unexpected bugs), `str(exc)` is a short, human-readable description -- never a
  multi-line traceback -- so surfacing it directly is both safe (no file paths, line numbers, or stack frames) and
  specific enough to usefully report. A full traceback is deliberately never surfaced.
- Both tabs' `try`/`with st.status(...)` blocks now track the last stage reported by their existing `on_progress`
  callback (`last_stage`/`last_stage_r`, a one-element list so the inner closure can write to it) and pass it to
  `format_run_error` in the generic `except Exception` branch. The specific `except RuntimeError` branch (HTL-20) is
  unchanged -- it was already a complete, specific message on its own.

## Verification

### Pytest, full suite

```
648 passed in 135.77s (0:02:15)
```
(642 before this step's 6 new tests: 5 naming the real stage reached for each stage, the no-stage-reached fallback,
the unrecognized-stage fallback, the "never includes a literal traceback marker" check, and the blank-message
fallback to the exception's class name.)

### `format_run_error`'s actual test assertions (`tests/test_streamlit_app.py`)

```python
def test_format_run_error_names_the_real_stage_reached():
    assert format_run_error(Exception("Anthropic API returned an error"), "extracting") == (
        "extraction failed: Anthropic API returned an error"
    )
    assert format_run_error(ValueError("bad schema"), "validating") == "validation failed: bad schema"
    assert format_run_error(OSError("disk full"), "generating") == "document generation failed: disk full"
    assert format_run_error(Exception("no source docs"), "ingesting") == "ingestion failed: no source docs"


def test_format_run_error_falls_back_to_run_when_no_stage_was_reached():
    assert format_run_error(Exception("boom"), None) == "run failed: boom"


def test_format_run_error_unrecognized_stage_falls_back_to_run():
    assert format_run_error(Exception("boom"), "some_future_stage") == "run failed: boom"


def test_format_run_error_never_includes_a_traceback():
    try:
        raise AttributeError("'NoneType' object has no attribute 'some_attribute'")
    except AttributeError as exc:
        message = format_run_error(exc, "extracting")
    assert message == "extraction failed: 'NoneType' object has no attribute 'some_attribute'"
    assert "Traceback" not in message
    assert "File \"" not in message


def test_format_run_error_blank_exception_message_falls_back_to_class_name():
    assert format_run_error(ValueError(), "validating") == "validation failed: ValueError"
```

### Re-reproduced the same three cases against the fixed code

| Case | Before | After |
|---|---|---|
| 1. No provider configured | `No LLM provider is configured: neither ANTHROPIC_API_KEY nor OPENAI_API_KEY is set, and mock mode was not requested. Set an API key, choose a different provider, or pass mock=True.` | *(unchanged -- already specific)* |
| 2. Real extraction failure | `Run failed: Anthropic API returned an error` | `extraction failed: Anthropic API returned an error` |
| 3. Unexpected exception | `Run failed: 'NoneType' object has no attribute 'some_attribute'` | `extraction failed: 'NoneType' object has no attribute 'some_attribute'` |

Cases 2 and 3 now match the spec's own example shape exactly, naming the stage that actually failed.

### `git status` / `git log`

```
nothing to commit, working tree clean
```
```
fe6dfc6 HTL-26: stage-specific error messages on a failed run ("{stage} failed: {reason}"), replacing the generic "Run failed: ..." in the Generate/Re-ingest tabs' catch-all exception handler
2241319 HTL-28 report: append correction note clarifying 638/643 pytest counts were not separated by a real commit boundary
345d1f2 HTL-28: add reports/htl28_progress_callback_report.md documenting the progress-callback implementation and verification
041075a HTL-28: wire Generate/Re-ingest tabs to a live st.status display driven by the real on_progress callback, replacing HTL-17's interim generic spinner
41f9b26 HTL-28: add on_progress(stage, detail) callback to orchestrator.run()/run_reingest(), firing at real ingesting/extracting/validating/generating stage boundaries (default no-op; CLI unaffected)
```

## Notes

- `-v`/log verbosity was already absent from the app's UI before this step; nothing needed to change for that half
  of HTL-26.
- HTL-20's `RuntimeError` message was already specific and was deliberately left untouched -- only the broader
  catch-all branch needed the stage-specific reformatting.
- Two scratch investigation/verification scripts (`temp_htl26_investigate.py`, `temp_htl26_verify_after.py`) were
  used to reproduce all three cases directly and were deleted before committing; nothing from them was committed.
