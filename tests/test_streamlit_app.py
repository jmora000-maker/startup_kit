"""HTL-17: tests for the pure, testable logic extracted from src/review_ui/generate.py's
Streamlit page -- form validation, role resolution, and result-rendering helpers. The Streamlit
widget code itself is not unit-tested here; it is covered by a manual smoke test
(streamlit run src/review_ui/app.py)."""

from pathlib import Path

import pytest

from src.config import config
from src.core.outputs import OutputSelection, RunResult
from src.generators.onboarding_deck import OnboardingDeckResult
from src.generators.pmo_workbook import PMOWorkbookResult
from src.review_ui.constants import (
    CONTRACT_TYPES,
    GOVERNANCE_TIERS,
    MODEL_OPTIONS_BY_PROVIDER,
    resolve_select_index,
)
from src.review_ui.generate import (
    DownloadTarget,
    LLM_CACHE_MODES_IN_APP,
    MIN_STAGE_DISPLAY_SECONDS,
    StageStatusUpdater,
    format_fallback_message,
    format_provider_name,
    format_run_error,
    collect_download_targets,
    is_admin_unlocked,
    progress_status_label,
    resolve_app_role,
    resolve_fallback_provider,
    resolve_llm_settings,
    validate_generate_inputs,
    validate_reingest_inputs,
    validate_start_date_text,
)


def test_validate_start_date_text_blank_is_valid():
    assert validate_start_date_text("") is None
    assert validate_start_date_text(None) is None


def test_validate_start_date_text_valid_iso_is_valid():
    assert validate_start_date_text("2026-10-07") is None


def test_validate_start_date_text_invalid_returns_error_message():
    error = validate_start_date_text("not-a-date")
    assert error is not None
    assert "not-a-date" in error


def test_validate_generate_inputs_requires_at_least_one_file():
    error = validate_generate_inputs([], "")
    assert error is not None
    assert "upload" in error.lower()


def test_validate_generate_inputs_valid_with_file_and_blank_date():
    assert validate_generate_inputs(["sow.pdf"], "") is None


def test_validate_generate_inputs_propagates_bad_date_error():
    error = validate_generate_inputs(["sow.pdf"], "garbage")
    assert error is not None


def test_validate_reingest_inputs_requires_a_file():
    error = validate_reingest_inputs(None, "")
    assert error is not None
    assert "docx" in error.lower()


def test_validate_reingest_inputs_valid_with_file():
    assert validate_reingest_inputs("Project_Startup_Kit.docx", "") is None


def test_resolve_app_role_blank_field_means_no_override():
    # HTL-25: a blank field on re-ingestion never overrides the existing baseline value.
    assert resolve_app_role("") is None
    assert resolve_app_role("   ") is None


def test_resolve_app_role_filled_field_is_applied():
    assert resolve_app_role("Sarah Connor") == "Sarah Connor"
    assert resolve_app_role("  John Connor  ") == "John Connor"


def test_llm_cache_modes_in_app_excludes_record():
    # HTL-22: the app exposes only off/replay -- never "record".
    assert "record" not in LLM_CACHE_MODES_IN_APP
    assert set(LLM_CACHE_MODES_IN_APP) == {"off", "replay"}


def test_is_admin_unlocked_correct_passphrase_unlocks():
    assert is_admin_unlocked("correct-horse-battery-staple", "correct-horse-battery-staple") is True


def test_is_admin_unlocked_wrong_passphrase_does_not_unlock():
    # HTL-27: a wrong passphrase must never unlock the Advanced (admin) section.
    assert is_admin_unlocked("wrong-guess", "correct-horse-battery-staple") is False


def test_is_admin_unlocked_empty_configured_passphrase_never_unlocks():
    assert is_admin_unlocked("", "") is False
    assert is_admin_unlocked("anything", "") is False


def test_is_admin_unlocked_against_real_configured_passphrase():
    # Exercises the real config.admin_passphrase (env var or its documented dev placeholder).
    assert is_admin_unlocked(config.admin_passphrase, config.admin_passphrase) is True
    assert is_admin_unlocked(config.admin_passphrase + "-wrong", config.admin_passphrase) is False


def test_resolve_llm_settings_locked_forces_fixed_safe_defaults():
    # HTL-27: the admin controls are genuinely inaccessible while locked -- whatever values an
    # (invisible) widget might otherwise hold are never used; the run always gets the server's
    # configured real provider, no model override, mock off, and cache off.
    provider, model, mock, cache_mode = resolve_llm_settings(
        admin_unlocked=False, provider="openai", model="gpt-4o", mock=True, cache_mode="replay"
    )
    assert provider == config.default_provider
    assert model == ""
    assert mock is False
    assert cache_mode == "off"


def test_resolve_llm_settings_unlocked_passes_through_admin_choices():
    provider, model, mock, cache_mode = resolve_llm_settings(
        admin_unlocked=True, provider="openai", model="gpt-4o", mock=True, cache_mode="replay"
    )
    assert provider == "openai"
    assert model == "gpt-4o"
    assert mock is True
    assert cache_mode == "replay"


def test_collect_download_targets_empty_result_has_no_targets():
    result = RunResult()
    assert collect_download_targets(result) == []


def test_collect_download_targets_includes_every_generated_path(tmp_path):
    kit_path = tmp_path / "Kit.docx"
    checklist_path = tmp_path / "Checklist.docx"
    workbook_path = tmp_path / "Workbook.xlsx"
    deck_path = tmp_path / "Deck.pptx"
    manifest_path = tmp_path / "Deck.trace.json"

    result = RunResult(
        kit_path=kit_path,
        checklist_path=checklist_path,
        workbook=PMOWorkbookResult(
            file_path=workbook_path,
            schedule_rows=0,
            wbs_rows=0,
            task_rows=0,
            raid_rows=0,
            unmapped_deliverables=0,
        ),
        slides=OnboardingDeckResult(
            file_path=deck_path,
            manifest_path=manifest_path,
            slides_count=7,
            trace_entries_count=0,
            project_name="Test Project",
        ),
    )

    targets = collect_download_targets(result)
    paths = {t.path for t in targets}
    assert kit_path in paths
    assert checklist_path in paths
    assert workbook_path in paths
    assert deck_path in paths
    assert manifest_path in paths
    assert len(targets) == 5


# Item 4: contract type is now one shared, closed-set list (src/review_ui/constants.py), imported
# identically by both the Generate tab (src/review_ui/generate.py) and the Fact Review screen
# (src/review_ui/app.py) -- these tests exercise that one shared definition and its helper.


def test_contract_types_is_the_closed_two_value_set():
    # Matches src/llm/prompts.py's extraction instructions and src/generators/checklist.py's
    # commercial-guardrail branching, which only ever distinguish these two values.
    assert CONTRACT_TYPES == ["Time and Materials", "Fixed Bid"]


def test_governance_tiers_matches_the_core_model_closed_set():
    assert GOVERNANCE_TIERS == ["Guided", "Partnered", "Elevated"]


def test_resolve_select_index_recognized_value_returns_its_own_index():
    assert resolve_select_index("Fixed Bid", CONTRACT_TYPES, "Time and Materials") == 1
    assert resolve_select_index("Time and Materials", CONTRACT_TYPES, "Fixed Bid") == 0


def test_resolve_select_index_unrecognized_value_falls_back_to_default_index():
    assert resolve_select_index("Cost Plus", CONTRACT_TYPES, "Fixed Bid") == 1
    assert resolve_select_index("", GOVERNANCE_TIERS, "Elevated") == 2


def test_resolve_select_index_formatted_label_matches_embedded_option():
    # If a display label with parenthesized ID or state is passed, it resolves to that option's index
    options = ["Run_AAA_20261010", "Run_BBB_20261010", "Run_CCC_20261010"]
    assert resolve_select_index("Project AAA (Run_AAA_20261010)", options, "Run_BBB_20261010") == 0
    assert resolve_select_index("Project CCC (Run_CCC_20261010) [generated]", options, "Run_AAA_20261010") == 2


def test_resolve_select_index_neither_recognized_returns_zero():
    assert resolve_select_index("Cost Plus", CONTRACT_TYPES, "Also Not A Type") == 0


# Item 5: the admin-gated model field is a dropdown of known-valid model names per provider.


def test_model_options_by_provider_covers_both_providers():
    assert set(MODEL_OPTIONS_BY_PROVIDER) == {"anthropic", "openai"}
    assert config.anthropic_model in MODEL_OPTIONS_BY_PROVIDER["anthropic"]
    assert config.openai_model in MODEL_OPTIONS_BY_PROVIDER["openai"]


# HTL-28: progress_status_label(stage, detail) turns a real on_progress(stage, detail) call from
# orchestrator.run()/run_reingest() into the live status text the app displays -- these tests
# exercise that pure mapping directly (the Streamlit st.status widget itself is smoke-tested).


def test_progress_status_label_known_stages_without_detail():
    assert progress_status_label("ingesting") == "Ingesting documents..."
    assert progress_status_label("extracting") == "Running extraction..."
    assert progress_status_label("validating") == "Validating..."
    assert progress_status_label("generating") == "Generating documents..."


def test_progress_status_label_includes_detail_when_present():
    assert progress_status_label("generating", "Startup Kit") == "Generating documents... (Startup Kit)"
    assert progress_status_label("ingesting", "3 provided source(s)") == (
        "Ingesting documents... (3 provided source(s))"
    )


def test_progress_status_label_unrecognized_stage_falls_back_gracefully():
    assert progress_status_label("some_future_stage") == "Some_future_stage"
    assert progress_status_label("") == "Working"


def test_stage_status_updater_fast_stage_waits_for_minimum_duration():
    """HTL-28 (a): A stage that completes faster than the minimum duration (e.g. 0.15s < 1.0s)
    holds the display for at least min_display_seconds (sleeps the remaining 0.85s) before
    the next stage is displayed."""
    from unittest.mock import MagicMock

    mock_status_box = MagicMock()
    last_stage = [None]

    current_simulated_time = 100.0
    sleep_calls = []

    def mock_time():
        return current_simulated_time

    def mock_sleep(seconds):
        nonlocal current_simulated_time
        sleep_calls.append(seconds)
        current_simulated_time += seconds

    updater = StageStatusUpdater(
        status_box=mock_status_box,
        last_stage_ref=last_stage,
        min_display_seconds=1.0,
        time_fn=mock_time,
        sleep_fn=mock_sleep,
    )

    # Stage 1: ingesting at t=100.0
    updater.update("ingesting", "sow.pdf")
    assert last_stage[0] == "ingesting"
    assert sleep_calls == []
    mock_status_box.update.assert_called_with(label="Ingesting documents... (sow.pdf)")
    mock_status_box.write.assert_called_with("Ingesting documents... (sow.pdf)")

    # Underlying work completes fast: only 0.15s elapsed
    current_simulated_time += 0.15

    # Stage 2: extracting at t=100.15
    updater.update("extracting")
    assert last_stage[0] == "extracting"
    # Must sleep for remaining 1.0 - 0.15 = 0.85s
    assert len(sleep_calls) == 1
    assert pytest.approx(sleep_calls[0], 0.001) == 0.85
    assert pytest.approx(current_simulated_time, 0.001) == 101.0
    mock_status_box.update.assert_called_with(label="Running extraction...")


def test_stage_status_updater_long_stage_not_delayed():
    """HTL-28 (b): A stage that already takes longer than the minimum duration (e.g. 15.0s > 1.0s)
    is completely unaffected, adding zero extra delay."""
    from unittest.mock import MagicMock

    mock_status_box = MagicMock()
    last_stage = [None]

    current_simulated_time = 100.0
    sleep_calls = []

    def mock_time():
        return current_simulated_time

    def mock_sleep(seconds):
        nonlocal current_simulated_time
        sleep_calls.append(seconds)
        current_simulated_time += seconds

    updater = StageStatusUpdater(
        status_box=mock_status_box,
        last_stage_ref=last_stage,
        min_display_seconds=1.0,
        time_fn=mock_time,
        sleep_fn=mock_sleep,
    )

    updater.update("extracting")
    assert sleep_calls == []

    # Extraction takes 15 seconds
    current_simulated_time += 15.0

    # Stage 3: validating
    updater.update("validating")
    # No sleep should occur because 15.0s > 1.0s
    assert sleep_calls == []
    assert last_stage[0] == "validating"
    mock_status_box.update.assert_called_with(label="Validating...")


def test_stage_status_updater_pipeline_execution_decoupled_from_display():
    """HTL-28 (c): The real underlying pipeline work (ingestion, extraction, validation) runs
    at full execution speed and is not modified or throttled; only the inter-stage UI display
    transitions enforce the visual floor."""
    from unittest.mock import MagicMock

    mock_status_box = MagicMock()
    last_stage = [None]

    current_simulated_time = 0.0
    work_log = []
    sleep_calls = []

    def mock_time():
        return current_simulated_time

    def mock_sleep(seconds):
        nonlocal current_simulated_time
        sleep_calls.append(seconds)
        current_simulated_time += seconds

    updater = StageStatusUpdater(
        status_box=mock_status_box,
        last_stage_ref=last_stage,
        min_display_seconds=1.0,
        time_fn=mock_time,
        sleep_fn=mock_sleep,
    )

    # Simulated pipeline sequence
    # 1. Ingestion starts
    updater.update("ingesting", "sow.docx")
    work_log.append(("ingestion_start", current_simulated_time))
    # Ingestion real compute work takes 0.05s
    current_simulated_time += 0.05
    work_log.append(("ingestion_done", current_simulated_time))

    # 2. Extraction starts
    updater.update("extracting")
    work_log.append(("extraction_start", current_simulated_time))
    # Extraction real compute work takes 10.0s
    current_simulated_time += 10.0
    work_log.append(("extraction_done", current_simulated_time))

    # 3. Validation starts
    updater.update("validating")
    work_log.append(("validation_start", current_simulated_time))
    # Validation real compute work takes 0.02s
    current_simulated_time += 0.02
    work_log.append(("validation_done", current_simulated_time))

    # 4. Pipeline finishes and updates complete
    updater.complete("Awaiting review.")
    work_log.append(("completed", current_simulated_time))

    # Ingestion ran from 0.0 to 0.05
    assert work_log[0] == ("ingestion_start", 0.0)
    assert work_log[1] == ("ingestion_done", 0.05)

    # Sleep 0.95s to hold ingestion label for 1.0s, so extraction starts at 1.0
    assert work_log[2] == ("extraction_start", 1.0)
    # Extraction ran for 10.0s until 11.0
    assert work_log[3] == ("extraction_done", 11.0)

    # Extraction was already > 1.0s, so validation starts immediately at 11.0 with 0 sleep
    assert work_log[4] == ("validation_start", 11.0)
    # Validation ran for 0.02s until 11.02
    assert work_log[5] == ("validation_done", 11.02)

    # Sleep 0.98s to hold validation label for 1.0s, so completion happens at 12.0
    assert work_log[6] == ("completed", 12.0)

    # Total display floor sleeps: [0.95, 0.98]
    assert len(sleep_calls) == 2
    assert pytest.approx(sleep_calls[0], 0.001) == 0.95
    assert pytest.approx(sleep_calls[1], 0.001) == 0.98


def test_stage_status_updater_handles_incrementing_extraction_progress():
    """HTL-28: As concurrent extractors complete and on_progress('extracting', 'N/14 complete')
    fires, StageStatusUpdater updates the label and write text to 'Running extraction... (N/14 complete)',
    enforcing min_display_seconds floor between consecutive updates."""
    from unittest.mock import MagicMock

    mock_status_box = MagicMock()
    last_stage = [None]

    current_simulated_time = 0.0
    sleep_calls = []

    def mock_time():
        return current_simulated_time

    def mock_sleep(seconds):
        nonlocal current_simulated_time
        sleep_calls.append(seconds)
        current_simulated_time += seconds

    updater = StageStatusUpdater(
        status_box=mock_status_box,
        last_stage_ref=last_stage,
        min_display_seconds=1.0,
        time_fn=mock_time,
        sleep_fn=mock_sleep,
    )

    # Initial extraction stage start
    updater.update("extracting")
    mock_status_box.update.assert_called_with(label="Running extraction...")

    # Fast completion 1: 0.2s elapsed
    current_simulated_time += 0.2
    updater.update("extracting", "1/14 complete")
    # Must sleep 0.8s
    assert len(sleep_calls) == 1
    assert pytest.approx(sleep_calls[0], 0.001) == 0.8
    mock_status_box.update.assert_called_with(label="Running extraction... (1/14 complete)")
    mock_status_box.write.assert_called_with("Running extraction... (1/14 complete)")

    # Slower completion 2: 2.5s elapsed
    current_simulated_time += 2.5
    updater.update("extracting", "2/14 complete")
    # No sleep needed
    assert len(sleep_calls) == 1
    mock_status_box.update.assert_called_with(label="Running extraction... (2/14 complete)")

    # Backlog decomposition start message
    current_simulated_time += 1.2
    updater.update("extracting", "13/14 complete -- decomposing backlog & SOW catalogue...")
    mock_status_box.update.assert_called_with(
        label="Running extraction... (13/14 complete -- decomposing backlog & SOW catalogue...)"
    )
    mock_status_box.write.assert_called_with(
        "Running extraction... (13/14 complete -- decomposing backlog & SOW catalogue...)"
    )


# HTL-26: on a failed run, the app must show a clear, specific error message -- "{stage or
# operation} failed: {concise reason}" -- never a bare generic message and never a raw
# traceback. format_run_error(exc, last_stage) is the pure logic behind the generic
# except-Exception branch in both the Generate and Re-ingest tabs.


def test_format_run_error_names_the_real_stage_reached():
    assert format_run_error(Exception("Anthropic API returned an error"), "extracting") == (
        "extraction failed: Anthropic API returned an error"
    )
    assert format_run_error(ValueError("bad schema"), "validating") == "validation failed: bad schema"
    assert format_run_error(OSError("disk full"), "generating") == "document generation failed: disk full"
    assert format_run_error(Exception("no source docs"), "ingesting") == "ingestion failed: no source docs"


def test_format_run_error_falls_back_to_run_when_no_stage_was_reached():
    # A failure before any on_progress call ever fired (e.g. client construction itself, before
    # run()/run_reingest() is even entered) has no stage to name.
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


# HTL-31: Generate and Re-ingest tabs retain uploaded files across page switches via state_persistence.


APP_FILE = str(Path(__file__).parent.parent / "src" / "review_ui" / "app.py")


def test_generate_retains_uploaded_sow_across_page_switches():
    """Upload a file, switch to Fact Review, switch back to Generate, confirm stored bytes are used for generate."""
    from unittest.mock import patch, MagicMock
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    # 1. Upload file
    at.file_uploader(key="gen_uploader").upload("project_sow.docx", b"binary-sow-content").run()
    assert not at.exception

    # 2. Switch away to Fact Review
    at.radio(key="app_page_selector").set_value("Fact Review (fixture)").run()
    assert not at.exception
    assert len(at.file_uploader) == 0

    # 3. Switch back to Generate
    at.radio(key="app_page_selector").set_value("Generate / Re-ingest").run()
    assert not at.exception
    # The uploader widget itself is empty due to Streamlit unmounting
    assert at.file_uploader(key="gen_uploader").value == []

    # 4. Trigger Generate and verify stored bytes are passed to _run_generate
    with patch("src.review_ui.generate._run_generate") as mock_run:
        mock_run.return_value = MagicMock(
            readiness_score=100.0,
            baseline=None,
            fallback_domains=[],
            validation_report=None,
            kit_path=None,
            checklist_path=None,
            workbook=None,
            slides=None,
        )
        at.button(key="gen_submit_button").click().run()
        assert not at.exception
        assert mock_run.called
        passed_files = mock_run.call_args.kwargs["uploaded_files"]
        assert len(passed_files) == 1
        assert passed_files[0].name == "project_sow.docx"
        assert passed_files[0].getvalue() == b"binary-sow-content"


def test_upload_replacement_replaces_stored_file_without_merging():
    """After an upload is stored, selecting a genuinely different file replaces the stored one, not merges."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    # Initial upload
    at.file_uploader(key="gen_uploader").upload("initial_sow.docx", b"initial-bytes").run()

    # Switch away and return
    at.radio(key="app_page_selector").set_value("Fact Review (fixture)").run()
    at.radio(key="app_page_selector").set_value("Generate / Re-ingest").run()

    # Select a genuinely different file
    at.file_uploader(key="gen_uploader").upload("replacement_sow.pdf", b"replacement-bytes").run()

    stored_files = at.session_state["generate_form_values"]["gen_uploaded_files"]
    assert len(stored_files) == 1
    assert stored_files[0].name == "replacement_sow.pdf"
    assert stored_files[0].getvalue() == b"replacement-bytes"


def test_using_previously_uploaded_message_rendering():
    """Verify 'Using previously uploaded: {filename}' renders when stored file exists and does not render when none uploaded."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    # 1. Initially nothing uploaded -> message does not render
    gen_info = [i.value for i in at.info if "Using previously uploaded:" in i.value]
    assert len(gen_info) == 0

    # 2. Upload file and switch away and back -> message renders
    at.file_uploader(key="gen_uploader").upload("statement_of_work.docx", b"sow-data").run()
    at.radio(key="app_page_selector").set_value("Fact Review (fixture)").run()
    at.radio(key="app_page_selector").set_value("Generate / Re-ingest").run()

    gen_info = [i.value for i in at.info if "Using previously uploaded:" in i.value]
    assert len(gen_info) == 1
    assert gen_info[0] == "Using previously uploaded: statement_of_work.docx -- choose a different file to replace it."


def test_reingest_retains_uploaded_kit_across_page_switches():
    """Verify Re-ingest tab retains uploaded kit file and passes stored bytes to _run_reingest."""
    from unittest.mock import patch, MagicMock
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.file_uploader(key="reingest_file").upload("Existing_Startup_Kit.docx", b"existing-kit-docx").run()

    at.radio(key="app_page_selector").set_value("Fact Review (fixture)").run()
    at.radio(key="app_page_selector").set_value("Generate / Re-ingest").run()

    reingest_info = [i.value for i in at.info if "Using previously uploaded: Existing_Startup_Kit.docx" in i.value]
    assert len(reingest_info) == 1

    with patch("src.review_ui.generate._run_reingest") as mock_run:
        mock_run.return_value = MagicMock(
            readiness_score=95.0,
            baseline=None,
            fallback_domains=[],
            validation_report=None,
            kit_path=None,
            checklist_path=None,
            workbook=None,
            slides=None,
        )
        at.button(key="reingest_submit_button").click().run()
        assert not at.exception
        assert mock_run.called
        passed_file = mock_run.call_args.kwargs["uploaded_kit_file"]
        assert passed_file.name == "Existing_Startup_Kit.docx"
        assert passed_file.getvalue() == b"existing-kit-docx"


# HTL-32: Fallback domains and provider display on results screen


def test_format_fallback_message_empty_defaults_to_anthropic():
    expected_default = format_provider_name(None)
    assert format_fallback_message([]) == f"Ran entirely on {expected_default}."


def test_format_fallback_message_empty_anthropic_primary():
    assert format_fallback_message([], "anthropic") == "Ran entirely on Anthropic."
    assert format_fallback_message([], "Anthropic") == "Ran entirely on Anthropic."


def test_format_fallback_message_empty_openai_primary():
    assert format_fallback_message([], "openai") == "Ran entirely on OpenAI."
    assert format_fallback_message([], "OpenAI") == "Ran entirely on OpenAI."


def test_format_fallback_message_non_empty_anthropic_primary():
    msg = format_fallback_message(["Scope Decomposition", "Deliverables"], "anthropic")
    assert msg == "Fell back to OpenAI for: Scope Decomposition, Deliverables."


def test_format_fallback_message_non_empty_openai_primary():
    msg = format_fallback_message(["Scope Decomposition", "Deliverables"], "openai")
    assert msg == "Fell back to Anthropic for: Scope Decomposition, Deliverables."


def test_format_fallback_message_single_domain():
    msg = format_fallback_message(["Scope Decomposition"], "anthropic")
    assert msg == "Fell back to OpenAI for: Scope Decomposition."


def test_generate_results_renders_fallback_confirmation_empty():
    """When fallback_domains is empty, info widget renders 'Ran entirely on {provider}'."""
    from unittest.mock import patch, MagicMock
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.file_uploader(key="gen_uploader").upload("sow.docx", b"sow-bytes").run()

    mock_result = RunResult(
        readiness_score=90.0,
        baseline=None,
        fallback_domains=[],
        primary_provider="anthropic",
    )

    with patch("src.review_ui.generate._run_generate", return_value=mock_result):
        at.button(key="gen_submit_button").click().run()
        assert not at.exception
        info_msgs = [i.value for i in at.info]
        assert "Ran entirely on Anthropic." in info_msgs
        warning_msgs = [w.value for w in at.warning if "Fell back" in w.value]
        assert len(warning_msgs) == 0


def test_generate_results_renders_fallback_warning_non_empty():
    """When fallback_domains is non-empty, warning widget renders 'Fell back to {provider} for: ...'."""
    from unittest.mock import patch
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.file_uploader(key="gen_uploader").upload("sow.docx", b"sow-bytes").run()

    mock_result = RunResult(
        readiness_score=85.0,
        baseline=None,
        fallback_domains=["Scope Decomposition", "Deliverables"],
        primary_provider="anthropic",
    )

    with patch("src.review_ui.generate._run_generate", return_value=mock_result):
        at.button(key="gen_submit_button").click().run()
        assert not at.exception
        warning_msgs = [w.value for w in at.warning if "Fell back to OpenAI" in w.value]
        assert len(warning_msgs) == 1
        assert warning_msgs[0] == "Fell back to OpenAI for: Scope Decomposition, Deliverables."
        info_msgs = [i.value for i in at.info if "Ran entirely" in i.value]
        assert len(info_msgs) == 0


def test_reingest_results_renders_fallback_domains():
    """Re-ingest tab results also render the fallback/provider confirmation."""
    from unittest.mock import patch
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.file_uploader(key="reingest_file").upload("Kit.docx", b"kit-bytes").run()

    mock_result = RunResult(
        readiness_score=92.5,
        baseline=None,
        fallback_domains=["Risk Log"],
        primary_provider="anthropic",
    )

    with patch("src.review_ui.generate._run_reingest", return_value=mock_result):
        at.button(key="reingest_submit_button").click().run()
        assert not at.exception
        warning_msgs = [w.value for w in at.warning if "Fell back to OpenAI for: Risk Log." in w.value]
        assert len(warning_msgs) == 1


# HTL-29: Review before finalizing toggle and paused run UI behavior


def test_generate_tab_review_toggle_checked_by_default_pauses_and_shows_awaiting_review():
    """HTL-29: When 'Review before finalizing' is checked (the default), submitting passes
    pause_for_review=True, displays the 'awaiting review' message, and renders no download buttons."""
    from unittest.mock import patch
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    # Confirm default state of checkbox is checked (True)
    checkboxes = [cb for cb in at.checkbox if cb.label == "Review before finalizing"]
    assert len(checkboxes) == 1
    assert checkboxes[0].value is True

    at.file_uploader(key="gen_uploader").upload("sow.docx", b"sow-bytes").run()

    mock_paused_result = RunResult(
        readiness_score=88.0,
        baseline=None,
        paused=True,
        run_id="Acme_Project_20261008_120000",
    )

    with patch("src.review_ui.generate._run_generate", return_value=mock_paused_result) as mock_run:
        at.button(key="gen_submit_button").click().run()
        assert not at.exception
        assert mock_run.called
        assert mock_run.call_args.kwargs["pause_for_review"] is True

        info_msgs = [i.value for i in at.info]
        assert any(
            "Run Acme_Project_20261008_120000 created and awaiting review." in msg
            and "Final documents will be generated once approved." in msg
            for msg in info_msgs
        )
        assert len(at.download_button) == 0


def test_generate_tab_review_toggle_unchecked_generates_straight_through(tmp_path):
    """HTL-29: When 'Review before finalizing' is unchecked, submitting passes pause_for_review=False
    and displays the normal results screen with download buttons."""
    from unittest.mock import patch
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.file_uploader(key="gen_uploader").upload("sow.docx", b"sow-bytes").run()

    # Uncheck the review toggle
    for cb in at.checkbox:
        if cb.label == "Review before finalizing":
            cb.uncheck().run()
            break

    dummy_kit = tmp_path / "Acme_Startup_Kit.docx"
    dummy_kit.write_bytes(b"dummy docx bytes")
    mock_complete_result = RunResult(
        readiness_score=92.0,
        kit_path=dummy_kit,
        paused=False,
    )

    with patch("src.review_ui.generate._run_generate", return_value=mock_complete_result) as mock_run:
        at.button(key="gen_submit_button").click().run()
        assert not at.exception
        assert mock_run.called
        assert mock_run.call_args.kwargs["pause_for_review"] is False

        success_msgs = [s.value for s in at.success]
        assert "Run complete." in success_msgs
        assert len(at.download_button) >= 1


# HTL-06 / HTL-07 / HTL-29: Fact Review generalized to storage runs


def test_fact_review_loads_selected_run_baseline(tmp_path, monkeypatch):
    """HTL-06: Fact Review screen displays facts from the selected stored run, not the hardcoded fixture."""
    from datetime import date
    from streamlit.testing.v1 import AppTest
    from src.core.models import ProjectStartupCharter, Stakeholder, StartupKitBaseline
    from src.review_storage.local import LocalReviewStorage

    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    baseline = StartupKitBaseline(
        project_name="Beta Health Analytics",
        contract_type="Time and Materials",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 12, 1),
        award_date_source="stated",
        charter=ProjectStartupCharter(
            project_name="Beta Health Analytics",
            client_name="Beta Health Inc",
            governance_tier="Elevated",
            contract_type="Time and Materials",
            delivery_manager="Jordan Hayes",
        ),
        stakeholders=[
            Stakeholder(name="Elena Rostova", role="Client Sponsor", organization="Beta Health Inc"),
            Stakeholder(name="Marcus Vance", role="Approver", organization="Beta Health Inc"),
            Stakeholder(name="Jordan Hayes", role="Delivery Manager", organization="Toptal"),
        ],
    )
    run_id = storage.create_run(
        project_name="Beta Health Analytics",
        baseline=baseline.model_dump(mode="json"),
        validation_report={},
    )

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.radio(key="app_page_selector").set_value("Fact Review (fixture)").run()
    assert not at.exception

    # Confirm run selector is present and defaults to the real pending run
    selector = at.selectbox(key="fact_review_run_selector")
    assert selector.value == run_id

    # Confirm subheader is the stored run's project name
    assert any(sh.value == "Beta Health Analytics" for sh in at.subheader)

    # Confirm caption references the stored run
    assert any(f"Reviewing run `{run_id}`" in cap.value for cap in at.caption)


def test_fact_review_edit_and_save_real_run_updates_storage(tmp_path, monkeypatch):
    """HTL-07 / HTL-06: Editing a fact and clicking Save updates the run in review storage."""
    from datetime import date
    from streamlit.testing.v1 import AppTest
    from src.core.models import ProjectStartupCharter, Stakeholder, StartupKitBaseline
    from src.review_storage.local import LocalReviewStorage

    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    baseline = StartupKitBaseline(
        project_name="Beta Health Analytics",
        contract_type="Time and Materials",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 12, 1),
        award_date_source="stated",
        charter=ProjectStartupCharter(
            project_name="Beta Health Analytics",
            client_name="Beta Health Inc",
            governance_tier="Elevated",
            contract_type="Time and Materials",
            delivery_manager="Jordan Hayes",
        ),
        stakeholders=[
            Stakeholder(name="Elena Rostova", role="Client Sponsor", organization="Beta Health Inc"),
            Stakeholder(name="Marcus Vance", role="Approver", organization="Beta Health Inc"),
            Stakeholder(name="Jordan Hayes", role="Delivery Manager", organization="Toptal"),
        ],
    )
    run_id = storage.create_run(
        project_name="Beta Health Analytics",
        baseline=baseline.model_dump(mode="json"),
        validation_report={},
    )

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.radio(key="app_page_selector").set_value("Fact Review (fixture)").run()
    assert not at.exception

    # Edit the Delivery Manager field
    dm_input_key = f"fact_review::{run_id}::edit::named_roles.delivery_manager"
    dm_inputs = [ti for ti in at.text_input if ti.key == dm_input_key]
    assert len(dm_inputs) == 1
    dm_inputs[0].input("Samira Khan").run()

    # Click Save review
    at.button(key="fact_review_save_button").click().run()
    assert not at.exception

    # Check success message
    assert any(f"Saved review for run {run_id} to review storage." in s.value for s in at.success)

    # Verify storage contains the updated baseline and audit file
    stored_run = storage.get_run(run_id)
    assert stored_run.baseline["charter"]["delivery_manager"] == "Samira Khan"
    audit_file = storage_dir / run_id / "review_audit.json"
    assert audit_file.exists()


def test_fact_review_demo_fixture_option_saves_to_scratch():
    """HTL-06 / HTL-07: Selecting Demo fixture retains standalone fixture review behavior."""
    from streamlit.testing.v1 import AppTest
    from src.review_ui import facts as review

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.radio(key="app_page_selector").set_value("Fact Review (fixture)").run()
    assert not at.exception

    # Select the Demo fixture option
    at.selectbox(key="fact_review_run_selector").select(review.DEMO_FIXTURE_OPTION).run()
    assert not at.exception

    # Confirm subheader is ARC Application Implementation
    assert any(sh.value == "ARC Application Implementation" for sh in at.subheader)

    # Confirm no Approve button is present
    approve_buttons = [b for b in at.button if b.key == "fact_review_approve_button" or b.label == "Approve"]
    assert len(approve_buttons) == 0

    # Click Save review
    at.button(key="fact_review_save_button").click().run()
    assert not at.exception

    # Confirm saved to scratch
    assert any("review_ui_scratch" in s.value or "Saved corrected_baseline.json" in s.value for s in at.success)
    scratch_file = review.SCRATCH_ROOT / review.FIXTURE_NAME / "corrected_baseline.json"
    assert scratch_file.exists()


# HTL-08 / HTL-09: Fact Review Approve action and error gating Streamlit UI tests


def test_fact_review_approve_blocked_by_error_severity_finding(tmp_path, monkeypatch):
    """HTL-08: When a run has an error-severity validation finding, the Approve button is disabled
    and a clear blocking error message is displayed naming the error."""
    from datetime import date
    from streamlit.testing.v1 import AppTest
    from src.core.models import ProjectStartupCharter, Stakeholder, StartupKitBaseline
    from src.review_storage.local import LocalReviewStorage

    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    baseline = StartupKitBaseline(
        project_name="Blocked Project",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 12, 1),
        award_date_source="stated",
        charter=ProjectStartupCharter(
            project_name="Blocked Project",
            client_name="Blocked Corp",
            governance_tier="Elevated",
            contract_type="Fixed Bid",
        ),
    )
    validation_report = {
        "findings": [
            {
                "invariant_id": "VAL-02",
                "severity": "error",
                "message": "Unmapped critical milestone gate missing required phase",
            },
            {
                "invariant_id": "VAL-05",
                "severity": "warning",
                "message": "Award date not explicitly stated",
            },
        ]
    }
    run_id = storage.create_run(
        project_name="Blocked Project",
        baseline=baseline.model_dump(mode="json"),
        validation_report=validation_report,
    )

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.radio(key="app_page_selector").set_value("Fact Review (fixture)").run()
    assert not at.exception

    # Confirm run selector is on the created run
    selector = at.selectbox(key="fact_review_run_selector")
    assert selector.value == run_id

    # Confirm error message is rendered and names the blocking error
    error_msgs = [e.value for e in at.error]
    assert any(
        "Approval blocked" in msg
        and "VAL-02" in msg
        and "Unmapped critical milestone gate missing required phase" in msg
        for msg in error_msgs
    )

    # Confirm Approve button is disabled
    approve_button = at.button(key="fact_review_approve_button")
    assert approve_button.disabled is True

    # Confirm run state on disk remains pending_review
    assert storage.get_run(run_id).state == "pending_review"


def test_fact_review_approve_succeeds_with_only_warning_findings(tmp_path, monkeypatch):
    """HTL-08 / HTL-09: When a run has only warning/repaired findings, the Approve button is enabled,
    and clicking Approve transitions the run to 'approved' in storage."""
    from datetime import date
    from streamlit.testing.v1 import AppTest
    from src.core.models import ProjectStartupCharter, Stakeholder, StartupKitBaseline
    from src.review_storage.local import LocalReviewStorage

    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    baseline = StartupKitBaseline(
        project_name="Ready Project",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 12, 1),
        award_date_source="stated",
        charter=ProjectStartupCharter(
            project_name="Ready Project",
            client_name="Ready Corp",
            governance_tier="Elevated",
            contract_type="Fixed Bid",
        ),
    )
    validation_report = {
        "findings": [
            {
                "invariant_id": "VAL-05",
                "severity": "warning",
                "message": "Award date not explicitly stated",
            },
            {
                "invariant_id": "VAL-09",
                "severity": "repaired",
                "message": "Rebuilt schedule from work items",
            },
        ]
    }
    run_id = storage.create_run(
        project_name="Ready Project",
        baseline=baseline.model_dump(mode="json"),
        validation_report=validation_report,
    )

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.radio(key="app_page_selector").set_value("Fact Review (fixture)").run()
    assert not at.exception

    # Confirm run selector is on the created run
    selector = at.selectbox(key="fact_review_run_selector")
    assert selector.value == run_id

    # Confirm Approve button is NOT disabled
    approve_button = at.button(key="fact_review_approve_button")
    assert approve_button.disabled is False

    # Click Approve
    approve_button.click().run()
    assert not at.exception

    # Check success message
    assert any(f"Run {run_id} approved successfully." in s.value for s in at.success)

    # Verify state in storage is 'approved'
    assert storage.get_run(run_id).state == "approved"
    fresh_storage = LocalReviewStorage(base_dir=storage_dir)
    assert fresh_storage.get_run(run_id).state == "approved"


# HTL-10: Resume generation from approved review run Streamlit UI tests


def test_fact_review_approved_run_shows_generate_button_and_renders_downloads(tmp_path, monkeypatch):
    """HTL-10: When an approved run is selected on the Fact Review page, a 'Generate documents'
    button is shown in place of Save/Approve, clicking it generates documents and renders download buttons."""
    from datetime import date
    from streamlit.testing.v1 import AppTest
    from src.core.models import ProjectStartupCharter, Stakeholder, StartupKitBaseline
    from src.review_storage.local import LocalReviewStorage

    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    baseline = StartupKitBaseline(
        project_name="Approved Project",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 12, 1),
        award_date_source="stated",
        charter=ProjectStartupCharter(
            project_name="Approved Project",
            client_name="Approved Corp",
            governance_tier="Elevated",
            contract_type="Fixed Bid",
            delivery_manager="Jordan Hayes",
        ),
        stakeholders=[
            Stakeholder(name="Jordan Hayes", role="Delivery Manager", organization="Toptal"),
        ],
    )
    run_id = storage.create_run(
        project_name="Approved Project",
        baseline=baseline.model_dump(mode="json"),
        validation_report={"findings": []},
    )
    storage.update_status(run_id, "approved", if_state="pending_review")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.radio(key="app_page_selector").set_value("Fact Review (fixture)").run()
    assert not at.exception

    # Confirm run selector is on the approved run
    selector = at.selectbox(key="fact_review_run_selector")
    assert selector.value == run_id

    # Confirm Save and Approve buttons are absent
    save_buttons = [b for b in at.button if b.key == "fact_review_save_button"]
    approve_buttons = [b for b in at.button if b.key == "fact_review_approve_button"]
    assert len(save_buttons) == 0
    assert len(approve_buttons) == 0

    # Confirm Generate documents button is present
    gen_buttons = [b for b in at.button if b.key == "fact_review_generate_button"]
    assert len(gen_buttons) == 1
    assert gen_buttons[0].label == "Generate documents"

    # Click Generate documents
    gen_buttons[0].click().run()
    assert not at.exception

    # Check success message
    assert any(f"Run {run_id} documents generated successfully." in s.value for s in at.success)

    # Confirm download buttons are rendered
    assert len(at.download_button) >= 4

    # Verify state in storage is now 'generated'
    assert storage.get_run(run_id).state == "generated"
    fresh_storage = LocalReviewStorage(base_dir=storage_dir)
    assert fresh_storage.get_run(run_id).state == "generated"


def test_fact_review_pending_run_does_not_show_generate_documents_button(tmp_path, monkeypatch):
    """HTL-10: A pending_review run shows Save/Approve and does NOT show 'Generate documents'."""
    from datetime import date
    from streamlit.testing.v1 import AppTest
    from src.core.models import ProjectStartupCharter, Stakeholder, StartupKitBaseline
    from src.review_storage.local import LocalReviewStorage

    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    baseline = StartupKitBaseline(
        project_name="Pending Project",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 12, 1),
        award_date_source="stated",
        charter=ProjectStartupCharter(
            project_name="Pending Project",
            client_name="Pending Corp",
            governance_tier="Elevated",
            contract_type="Fixed Bid",
        ),
    )
    run_id = storage.create_run(
        project_name="Pending Project",
        baseline=baseline.model_dump(mode="json"),
        validation_report={"findings": []},
    )

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.radio(key="app_page_selector").set_value("Fact Review (fixture)").run()
    assert not at.exception

    # Confirm Generate documents button is absent
    gen_buttons = [b for b in at.button if b.key == "fact_review_generate_button"]
    assert len(gen_buttons) == 0

    # Confirm Save and Approve buttons are present
    save_buttons = [b for b in at.button if b.key == "fact_review_save_button"]
    approve_buttons = [b for b in at.button if b.key == "fact_review_approve_button"]
    assert len(save_buttons) == 1
    assert len(approve_buttons) == 1


# HTL-33: Run selection persistence and download buttons survival across page switch / remount


def test_htl33_fact_review_run_selection_persists_and_downloads_survive(tmp_path, monkeypatch):
    """HTL-33: In a multi-run queue, approving and generating a run transitions the UI immediately
    via st.rerun(), and navigating away to Generate / Re-ingest and back retains the generated run's
    selection and download buttons rather than reverting to pending_review options[0]."""
    from datetime import date
    from streamlit.testing.v1 import AppTest
    from src.core.models import ProjectStartupCharter, Stakeholder, StartupKitBaseline
    from src.review_storage.local import LocalReviewStorage

    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    # 1. Seed existing pending and generated runs so options[0] will be a pending run
    pending_baseline = StartupKitBaseline(
        project_name="Existing Pending Run",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 12, 1),
        award_date_source="stated",
        charter=ProjectStartupCharter(
            project_name="Existing Pending Run",
            client_name="Pending Corp",
            governance_tier="Elevated",
            contract_type="Fixed Bid",
        ),
    )
    pending_run_id = storage.create_run(
        project_name="Existing Pending Run",
        baseline=pending_baseline.model_dump(mode="json"),
        validation_report={"findings": []},
    )

    # 2. Create target run
    target_baseline = StartupKitBaseline(
        project_name="Target Generation Run",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 12, 2),
        award_date_source="stated",
        charter=ProjectStartupCharter(
            project_name="Target Generation Run",
            client_name="Target Corp",
            governance_tier="Elevated",
            contract_type="Fixed Bid",
        ),
    )
    target_run_id = storage.create_run(
        project_name="Target Generation Run",
        baseline=target_baseline.model_dump(mode="json"),
        validation_report={"findings": []},
    )

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.radio(key="app_page_selector").set_value("Fact Review (fixture)").run()
    assert not at.exception

    # Select target run
    at.selectbox(key="fact_review_run_selector").set_value(target_run_id).run()
    assert at.selectbox(key="fact_review_run_selector").value == target_run_id

    # Click Approve -> next-state button ('Generate documents') appears immediately
    at.button(key="fact_review_approve_button").click().run()
    assert not at.exception
    assert at.selectbox(key="fact_review_run_selector").value == target_run_id
    gen_buttons = [b for b in at.button if b.key == "fact_review_generate_button"]
    assert len(gen_buttons) == 1

    # Click Generate documents -> download buttons appear immediately
    gen_buttons[0].click().run()
    assert not at.exception
    assert at.selectbox(key="fact_review_run_selector").value == target_run_id
    assert len(at.download_button) >= 4

    # Navigate away to Generate / Re-ingest page
    at.radio(key="app_page_selector").set_value("Generate / Re-ingest").run()
    assert not at.exception

    # Navigate back to Fact Review
    at.radio(key="app_page_selector").set_value("Fact Review (fixture)").run()
    assert not at.exception

    # Confirm selected run did NOT revert to options[0] (pending_run_id)
    assert at.selectbox(key="fact_review_run_selector").value == target_run_id

    # Confirm download buttons survived and no Save/Approve buttons are shown
    assert len(at.download_button) >= 4
    save_buttons = [b for b in at.button if b.key == "fact_review_save_button"]
    approve_buttons = [b for b in at.button if b.key == "fact_review_approve_button"]
    assert len(save_buttons) == 0
    assert len(approve_buttons) == 0

    # Click first download button and confirm buttons remain intact
    at.download_button[0].click().run()
    assert not at.exception
    assert at.selectbox(key="fact_review_run_selector").value == target_run_id
    assert len(at.download_button) >= 4


def test_fact_review_persisted_formatted_label_resolves_to_run_id(tmp_path, monkeypatch):
    """If state_persistence store contains a formatted display label string, Fact Review
    normalizes it to the raw run_id rather than falling back to options[0]."""
    from datetime import date
    from streamlit.testing.v1 import AppTest
    from src.core.models import ProjectStartupCharter, StartupKitBaseline
    from src.review_storage.local import LocalReviewStorage
    from src.review_ui import state_persistence

    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    baseline_1 = StartupKitBaseline(
        project_name="Run Alpha",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 12, 1),
        award_date_source="stated",
        charter=ProjectStartupCharter(
            project_name="Run Alpha",
            client_name="Alpha Corp",
            governance_tier="Elevated",
            contract_type="Fixed Bid",
        ),
    )
    run_1 = storage.create_run("Run Alpha", baseline_1.model_dump(mode="json"), {"findings": []})

    baseline_2 = StartupKitBaseline(
        project_name="Run Beta",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 12, 2),
        award_date_source="stated",
        charter=ProjectStartupCharter(
            project_name="Run Beta",
            client_name="Beta Corp",
            governance_tier="Elevated",
            contract_type="Fixed Bid",
        ),
    )
    run_2 = storage.create_run("Run Beta", baseline_2.model_dump(mode="json"), {"findings": []})

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()

    # Pre-populate session state store with the formatted display label of run_2
    formatted_label = f"Run Beta ({run_2})"
    at.session_state["fact_review_page"] = {"selected_run_id": formatted_label}

    at.radio(key="app_page_selector").set_value("Fact Review (fixture)").run()
    assert not at.exception

    # Confirm it selected run_2 (raw run ID), not run_1 (options[0])
    assert at.selectbox(key="fact_review_run_selector").value == run_2
    assert at.session_state["fact_review_page"]["selected_run_id"] == run_2


# HTL-35: Generate/Re-ingest page fixes (checkbox defaults, button disabling during and after run)


def test_htl_35_document_type_checkboxes_all_default_to_true():
    """HTL-35 (1): Every document-type checkbox (Startup Kit, Readiness Checklist,
    Delivery Workbook, and Onboarding Deck) on both Generate and Re-ingest tabs
    defaults to checked (True)."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()

    # Generate tab checkboxes
    gen_deck_cb = [cb for cb in at.checkbox if cb.label == "Onboarding Deck" and cb.key == "gen_out_slides"]
    assert len(gen_deck_cb) == 1
    assert gen_deck_cb[0].value is True

    gen_labels = {
        "Startup Kit": "gen_out_kit",
        "Readiness Checklist": "gen_out_checklist",
        "Delivery Workbook": "gen_out_workbook",
        "Onboarding Deck": "gen_out_slides",
    }
    for label, key in gen_labels.items():
        cbs = [cb for cb in at.checkbox if cb.key == key]
        assert len(cbs) == 1, f"Missing checkbox {key}"
        assert cbs[0].value is True, f"Checkbox {label} ({key}) did not default to True"

    # Re-ingest tab checkboxes
    reingest_labels = {
        "Startup Kit": "reingest_out_kit",
        "Readiness Checklist": "reingest_out_checklist",
        "Delivery Workbook": "reingest_out_workbook",
        "Onboarding Deck": "reingest_out_slides",
    }
    for label, key in reingest_labels.items():
        cbs = [cb for cb in at.checkbox if cb.key == key]
        assert len(cbs) == 1, f"Missing checkbox {key}"
        assert cbs[0].value is True, f"Checkbox {label} ({key}) did not default to True"


def test_htl_35_generate_button_in_progress_state_during_long_running_call():
    """HTL-35 (2): The Generate button tracks in-progress execution via session state
    flag (gen_is_running) during a mocked long-running generation pipeline call."""
    from unittest.mock import patch
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.file_uploader(key="gen_uploader").upload("sow.docx", b"sow-bytes").run()

    in_progress_flag_captured = []

    def mock_long_running_generate(*args, **kwargs):
        # Verify that gen_is_running is True while generation is executing
        in_progress_flag_captured.append(at.session_state.get("gen_is_running"))
        # Execute progress callback
        on_progress = kwargs.get("on_progress")
        if on_progress:
            on_progress("ingesting", "sow.docx")
            on_progress("extracting")
            on_progress("validating")
        return RunResult(
            readiness_score=90.0,
            paused=True,
            run_id="Long_Run_20261010_120000",
        )

    with patch("src.review_ui.generate.time.sleep", return_value=None), patch(
        "src.review_ui.generate._run_generate", side_effect=mock_long_running_generate
    ) as mock_gen:
        at.button(key="gen_submit_button").click().run()
        assert not at.exception
        assert mock_gen.called
        assert in_progress_flag_captured == [True]
        # After run returns, gen_is_running is cleared to False
        assert at.session_state.get("gen_is_running") is False


def test_htl_35_generate_button_disabled_after_successful_run_completes():
    """HTL-35 (3): Once a run completes and the 'Run {run_id} created and awaiting review...'
    message appears, the Generate button becomes disabled (disabled=True). Uploading a new file
    resets the result state and re-enables the Generate button."""
    from unittest.mock import patch
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.file_uploader(key="gen_uploader").upload("sow.docx", b"sow-bytes").run()

    # Initial state: button is enabled
    assert at.button(key="gen_submit_button").disabled is False

    mock_paused_result = RunResult(
        readiness_score=85.0,
        paused=True,
        run_id="Pilot_Ready_Product_20261010_103601",
    )

    with patch("src.review_ui.generate._run_generate", return_value=mock_paused_result):
        at.button(key="gen_submit_button").click().run()
        assert not at.exception

        # Message is displayed
        info_msgs = [i.value for i in at.info]
        assert any("Run Pilot_Ready_Product_20261010_103601 created and awaiting review." in msg for msg in info_msgs)

        # On rerun / subsequent state inspection, the Generate button is disabled
        at.run()
        assert at.button(key="gen_submit_button").disabled is True

    # Uploading a new file resets the completed run result and re-enables the button
    at.file_uploader(key="gen_uploader").upload("new_sow.docx", b"new-sow-bytes").run()
    assert at.button(key="gen_submit_button").disabled is False


def test_htl_35_safeguard_clears_stuck_running_flags_without_inputs():
    """HTL-35 safeguard: If gen_is_running or reingest_is_running is somehow set to True
    in session_state when no files are uploaded, render() clears them to False."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.session_state["gen_is_running"] = True
    at.session_state["reingest_is_running"] = True

    at.run()
    assert at.session_state.get("gen_is_running") is False
    assert at.session_state.get("reingest_is_running") is False


def test_htl_35_reingest_two_phase_rerun_and_disabled_button():
    """HTL-35: Re-ingest tab uses the two-phase pattern and disables the Re-ingest button
    during execution and after completion."""
    from unittest.mock import patch
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.file_uploader(key="reingest_file").upload("Project_Startup_Kit.docx", b"docx-bytes").run()

    # Initial state: button enabled
    assert at.button(key="reingest_submit_button").disabled is False

    reingest_flag_captured = []

    def mock_run_reingest(*args, **kwargs):
        reingest_flag_captured.append(at.session_state.get("reingest_is_running"))
        return RunResult(
            readiness_score=88.0,
            paused=False,
            run_id="Reingest_Run_20261010_130000",
        )

    with patch("src.review_ui.generate._run_reingest", side_effect=mock_run_reingest) as mock_reingest:
        at.button(key="reingest_submit_button").click().run()
        assert not at.exception
        assert mock_reingest.called
        assert reingest_flag_captured == [True]
        assert at.session_state.get("reingest_is_running") is False

        # Button is disabled after run completion
        at.run()
        assert at.button(key="reingest_submit_button").disabled is True

    # Uploading a new file re-enables the reingest button
    at.file_uploader(key="reingest_file").upload("New_Startup_Kit.docx", b"new-docx-bytes").run()
    assert at.button(key="reingest_submit_button").disabled is False


def test_fact_review_generate_button_in_progress_state_during_long_running_call(tmp_path, monkeypatch):
    """Fact Review 'Generate documents' button uses two-phase pattern and sets
    fact_review::{run_id}::is_generating during execution, with disabled=True on the rerun pass."""
    from datetime import date
    from unittest.mock import patch
    from streamlit.testing.v1 import AppTest
    from src.core.models import ProjectStartupCharter, Stakeholder, StartupKitBaseline
    from src.review_storage.local import LocalReviewStorage

    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    baseline = StartupKitBaseline(
        project_name="Approved Project For Gen",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 12, 1),
        award_date_source="stated",
        charter=ProjectStartupCharter(
            project_name="Approved Project For Gen",
            client_name="Approved Corp",
            governance_tier="Elevated",
            contract_type="Fixed Bid",
            delivery_manager="Jordan Hayes",
        ),
        stakeholders=[
            Stakeholder(name="Jordan Hayes", role="Delivery Manager", organization="Toptal"),
        ],
    )
    run_id = storage.create_run(
        project_name="Approved Project For Gen",
        baseline=baseline.model_dump(mode="json"),
        validation_report={"findings": []},
    )
    storage.update_status(run_id, "approved", if_state="pending_review")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.radio(key="app_page_selector").set_value("Fact Review (fixture)").run()
    assert not at.exception

    # Initially enabled
    gen_btn = at.button(key="fact_review_generate_button")
    assert gen_btn.disabled is False

    is_generating_captured = []

    def mock_long_running_generate_approved(r_id, **kwargs):
        # Capture the is_generating flag state during generation
        is_generating_captured.append(at.session_state.get(f"fact_review::{r_id}::is_generating"))
        # Call the real generate_approved_run or return dummy references
        storage.update_status(r_id, "generated", if_state="approved")
        return {"Startup_Kit.docx": str(storage_dir / r_id / "Startup_Kit.docx")}, None

    with patch("src.review_ui.facts.generate_approved_run", side_effect=mock_long_running_generate_approved) as mock_gen:
        gen_btn.click().run()
        assert not at.exception
        assert mock_gen.called
        assert is_generating_captured == [True]
        # Flag cleared after completion
        assert at.session_state.get(f"fact_review::{run_id}::is_generating") is False
        # State transitioned to generated
        assert any(f"Run {run_id} documents generated successfully." in s.value for s in at.success)


def test_fact_review_generate_button_per_run_scoping_and_safeguard(tmp_path, monkeypatch):
    """Fact Review is_generating flag is scoped per run_id and safeguard clears stuck flags for non-approved runs."""
    from datetime import date
    from unittest.mock import patch
    from streamlit.testing.v1 import AppTest
    from src.core.models import ProjectStartupCharter, Stakeholder, StartupKitBaseline
    from src.review_storage.local import LocalReviewStorage

    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    baseline_1 = StartupKitBaseline(
        project_name="Approved Run 1",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 12, 1),
        award_date_source="stated",
        charter=ProjectStartupCharter(
            project_name="Approved Run 1",
            client_name="Corp 1",
            governance_tier="Elevated",
            contract_type="Fixed Bid",
        ),
    )
    run_1 = storage.create_run("Approved Run 1", baseline_1.model_dump(mode="json"), {"findings": []})
    storage.update_status(run_1, "approved", if_state="pending_review")

    baseline_2 = StartupKitBaseline(
        project_name="Approved Run 2",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 12, 1),
        award_date_source="stated",
        charter=ProjectStartupCharter(
            project_name="Approved Run 2",
            client_name="Corp 2",
            governance_tier="Elevated",
            contract_type="Fixed Bid",
        ),
    )
    run_2 = storage.create_run("Approved Run 2", baseline_2.model_dump(mode="json"), {"findings": []})
    storage.update_status(run_2, "approved", if_state="pending_review")

    # Seed an already-generated run to verify safeguard clears its stuck flag
    run_gen = storage.create_run("Generated Run", baseline_2.model_dump(mode="json"), {"findings": []})
    storage.update_status(run_gen, "generated", if_state="pending_review")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    # Set non-approved runs as generating to test safeguard
    at.session_state[f"fact_review::{run_gen}::is_generating"] = True
    at.session_state["fact_review::stuck_nonexistent_run::is_generating"] = True

    # Navigate to Fact Review
    at.radio(key="app_page_selector").set_value("Fact Review (fixture)").run()
    assert not at.exception

    # Safeguard cleared stuck flags for non-approved runs
    assert at.session_state.get(f"fact_review::{run_gen}::is_generating") is False
    assert at.session_state.get("fact_review::stuck_nonexistent_run::is_generating") is False

    # Verify per-run scoping: when run_1 is generating, run_2's flag is unaffected
    run_1_flag_captured = []
    run_2_flag_captured = []

    def mock_generate_scoped(r_id, **kwargs):
        run_1_flag_captured.append(at.session_state.get(f"fact_review::{run_1}::is_generating", False))
        run_2_flag_captured.append(at.session_state.get(f"fact_review::{run_2}::is_generating", False))
        storage.update_status(r_id, "generated", if_state="approved")
        return {"Startup_Kit.docx": str(storage_dir / r_id / "Startup_Kit.docx")}, None

    at.selectbox(key="fact_review_run_selector").set_value(run_1).run()
    with patch("src.review_ui.facts.generate_approved_run", side_effect=mock_generate_scoped):
        at.button(key="fact_review_generate_button").click().run()

    assert run_1_flag_captured == [True]
    assert run_2_flag_captured == [False]
