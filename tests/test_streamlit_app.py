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
    collect_download_targets,
    is_admin_unlocked,
    progress_status_label,
    resolve_app_role,
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
