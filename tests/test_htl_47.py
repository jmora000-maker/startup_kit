"""HTL-47: Tests confirming that submitting with zero output deliverables selected
is blocked with a clear validation error on both Generate and Re-ingest tabs,
and that expensive LLM extraction work is never initiated.
"""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from streamlit.testing.v1 import AppTest

from src.core.outputs import OutputSelection, RunResult
from src.review_ui.generate import (
    validate_generate_inputs,
    validate_output_selection,
    validate_reingest_inputs,
)

APP_FILE = str(Path(__file__).parent.parent / "src" / "review_ui" / "app.py")


def _make_unlocked_app_test():
    at = AppTest.from_file(APP_FILE, default_timeout=15)
    at.session_state["generation_unlocked"] = True
    at.session_state["generation_unlocked_at"] = time.time()
    at.session_state["gen_admin_unlocked"] = True
    at.session_state["reingest_admin_unlocked"] = True
    return at


# =========================================================================
# 1. Pure Unit Validation Tests (HTL-47)
# =========================================================================


def test_validate_output_selection_all_false_returns_error():
    """OutputSelection with all False returns the specific error message."""
    outputs = OutputSelection(kit=False, checklist=False, workbook=False, slides=False)
    error = validate_output_selection(outputs=outputs)
    assert error is not None
    assert "Select at least one output deliverable" in error
    assert "Startup Kit, Delivery Workbook, or Onboarding Deck" in error


def test_validate_output_selection_booleans_all_false_returns_error():
    """Boolean kwargs all False returns the specific error message."""
    error = validate_output_selection(kit=False, workbook=False, slides=False)
    assert error is not None
    assert "Select at least one output deliverable" in error


@pytest.mark.parametrize(
    "kit,workbook,slides",
    [
        (True, False, False),
        (False, True, False),
        (False, False, True),
        (True, True, True),
    ],
)
def test_validate_output_selection_at_least_one_true_is_valid(kit, workbook, slides):
    """OutputSelection with at least one deliverable selected returns None (valid)."""
    outputs = OutputSelection(kit=kit, checklist=False, workbook=workbook, slides=slides)
    assert validate_output_selection(outputs=outputs) is None
    assert validate_output_selection(kit=kit, workbook=workbook, slides=slides) is None


def test_validate_generate_inputs_blocks_zero_outputs():
    """validate_generate_inputs fails when outputs has zero deliverables selected."""
    outputs = OutputSelection(kit=False, checklist=False, workbook=False, slides=False)
    error = validate_generate_inputs(["sow.docx"], "2026-11-01", outputs=outputs)
    assert error is not None
    assert "Select at least one output deliverable" in error


def test_validate_generate_inputs_succeeds_with_outputs():
    """validate_generate_inputs succeeds when at least one output deliverable is selected."""
    outputs = OutputSelection(kit=True, checklist=False, workbook=False, slides=False)
    assert validate_generate_inputs(["sow.docx"], "2026-11-01", outputs=outputs) is None


def test_validate_reingest_inputs_blocks_zero_outputs():
    """validate_reingest_inputs fails when outputs has zero deliverables selected."""
    outputs = OutputSelection(kit=False, checklist=False, workbook=False, slides=False)
    error = validate_reingest_inputs("Acme_Startup_Kit.docx", "2026-11-01", outputs=outputs)
    assert error is not None
    assert "Select at least one output deliverable" in error


def test_validate_reingest_inputs_succeeds_with_outputs():
    """validate_reingest_inputs succeeds when at least one output deliverable is selected."""
    outputs = OutputSelection(kit=False, checklist=False, workbook=True, slides=False)
    assert validate_reingest_inputs("Acme_Startup_Kit.docx", "2026-11-01", outputs=outputs) is None


# =========================================================================
# 2. AppTest Integration Tests: Generate Tab Submission Blocking
# =========================================================================


def test_htl_47_generate_tab_blocks_submission_with_zero_outputs_and_skips_llm():
    """On Generate tab, submitting with all 3 output checkboxes unchecked (default)
    displays an error and strictly prevents calling _run_generate or any LLM workflow."""
    at = _make_unlocked_app_test().run()
    assert not at.exception

    # Upload valid document
    at.file_uploader(key="gen_sow_uploader").upload("statement_of_work.pdf", b"pdf-bytes").run()

    # Confirm all three output checkboxes are in their default unchecked state
    kit_cb = next(cb for cb in at.checkbox if cb.key == "gen_out_kit")
    wb_cb = next(cb for cb in at.checkbox if cb.key == "gen_out_workbook")
    slides_cb = next(cb for cb in at.checkbox if cb.key == "gen_out_slides")
    assert kit_cb.value is False
    assert wb_cb.value is False
    assert slides_cb.value is False

    with patch("src.review_ui.generate._run_generate") as mock_run_generate, patch(
        "src.review_ui.generate.build_app_llm_client"
    ) as mock_build_client, patch("src.orchestrator.StartupKitController.run") as mock_controller_run:

        # Click Generate
        at.button(key="gen_submit_button").click().run()

        assert not at.exception
        # Confirm error is shown to the user
        error_msgs = [e.value for e in at.error]
        assert any("Select at least one output deliverable" in msg for msg in error_msgs)

        # Confirm NO LLM extraction or generation function was called
        assert not mock_run_generate.called
        assert not mock_build_client.called
        assert not mock_controller_run.called

        # Confirm run state was not set to running or completed
        assert at.session_state.get("gen_is_running", False) is False
        assert at.session_state.get("generate_run_result") is None


def test_htl_47_generate_tab_proceeds_when_output_selected():
    """On Generate tab, checking at least one output deliverable allows submission to proceed."""
    at = _make_unlocked_app_test().run()
    at.file_uploader(key="gen_sow_uploader").upload("statement_of_work.pdf", b"pdf-bytes").run()

    # Check Startup Kit
    at.checkbox(key="gen_out_kit").check().run()

    mock_result = RunResult(
        readiness_score=85.0,
        paused=True,
        run_id="Run_With_Output_20261025",
    )

    with patch("src.review_ui.generate._run_generate", return_value=mock_result) as mock_run:
        at.button(key="gen_submit_button").click().run()
        assert not at.exception
        assert mock_run.called
        assert mock_run.call_args.kwargs["outputs"].kit is True
        error_msgs = [e.value for e in at.error]
        assert not any("Select at least one output deliverable" in msg for msg in error_msgs)


# =========================================================================
# 3. AppTest Integration Tests: Re-ingest Tab Submission Blocking
# =========================================================================


def test_htl_47_reingest_tab_blocks_submission_with_zero_outputs_and_skips_llm():
    """On Re-ingest tab, submitting with all 3 output checkboxes unchecked (default)
    displays an error and strictly prevents calling _run_reingest or any LLM workflow."""
    at = _make_unlocked_app_test().run()
    assert not at.exception

    # Upload valid kit document for re-ingestion
    at.file_uploader(key="reingest_file").upload("Acme_Startup_Kit.docx", b"kit-bytes").run()

    # Confirm all three reingest output checkboxes are unchecked
    kit_r = next(cb for cb in at.checkbox if cb.key == "reingest_out_kit")
    wb_r = next(cb for cb in at.checkbox if cb.key == "reingest_out_workbook")
    slides_r = next(cb for cb in at.checkbox if cb.key == "reingest_out_slides")
    assert kit_r.value is False
    assert wb_r.value is False
    assert slides_r.value is False

    with patch("src.review_ui.generate._run_reingest") as mock_run_reingest, patch(
        "src.review_ui.generate.build_app_llm_client"
    ) as mock_build_client:

        # Click Re-ingest and recalculate
        at.button(key="reingest_submit_button").click().run()

        assert not at.exception
        # Confirm error is shown to the user
        error_msgs = [e.value for e in at.error]
        assert any("Select at least one output deliverable" in msg for msg in error_msgs)

        # Confirm NO reingest LLM or generation function was called
        assert not mock_run_reingest.called
        assert not mock_build_client.called

        # Confirm run state was not set to running or completed
        assert at.session_state.get("reingest_is_running", False) is False
        assert at.session_state.get("reingest_run_result") is None


def test_htl_47_reingest_tab_proceeds_when_output_selected():
    """On Re-ingest tab, checking at least one output deliverable allows submission to proceed."""
    at = _make_unlocked_app_test().run()
    at.file_uploader(key="reingest_file").upload("Acme_Startup_Kit.docx", b"kit-bytes").run()

    # Check Delivery Workbook
    at.checkbox(key="reingest_out_workbook").check().run()

    mock_result = RunResult(
        readiness_score=92.0,
        paused=False,
        run_id="Reingest_Run_20261025",
    )

    with patch("src.review_ui.generate._run_reingest", return_value=mock_result) as mock_run:
        at.button(key="reingest_submit_button").click().run()
        assert not at.exception
        assert mock_run.called
        assert mock_run.call_args.kwargs["outputs"].workbook is True
        error_msgs = [e.value for e in at.error]
        assert not any("Select at least one output deliverable" in msg for msg in error_msgs)
