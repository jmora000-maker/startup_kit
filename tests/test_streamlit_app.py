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

    at = AppTest.from_file(APP_FILE).run()
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

    at = AppTest.from_file(APP_FILE).run()
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

    at = AppTest.from_file(APP_FILE).run()
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

    at = AppTest.from_file(APP_FILE).run()
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
    assert format_fallback_message([]) == "Ran entirely on Anthropic."


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

    at = AppTest.from_file(APP_FILE).run()
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

    at = AppTest.from_file(APP_FILE).run()
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

    at = AppTest.from_file(APP_FILE).run()
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
