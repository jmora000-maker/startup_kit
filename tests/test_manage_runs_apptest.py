"""HTL-90: Streamlit AppTest regression test suite for Manage Runs UI.

Covers:
Group 1: Whole-Page Passphrase Gate Lifecycle (4 Tests)
- Locked state renders gate form and hides management dashboard
- Wrong passphrase displays error message and keeps dashboard locked
- Correct admin passphrase unlocks dashboard, metrics, and tab views
- Lock button relocks dashboard and restores passphrase gate

Group 2: HTL-81 Tab Navigation & State Persistence (3 Tests)
- Archiving an active run updates storage, flashes success, and preserves 'active' view tab
- Unarchiving an archived run updates storage, flashes success, and preserves 'archived' view tab
- Purging an archived run updates storage, flashes success, and preserves 'archived' view tab (HTL-81 core scenario)

Group 3: HTL-82 & HTL-83 Bulk-Selection & Two-Stage Confirmation Purge Flow (5 Tests)
- Select All and Deselect All toolbar buttons toggle all archived checkboxes and purge button state
- Purge Selected button initiates stage-2 confirmation warning banner and confirm/cancel controls
- Bulk purge cancellation dismisses confirmation panel and preserves runs and checkboxes
- Confirming purge of a single run deletes record/files and cleans up selection (HTL-83)
- Confirming purge of multiple runs deletes all selected runs and leaves unselected runs intact (HTL-82)

Group 4: Error Handling and Flash Messaging (2 Tests)
- Storage archive failure renders flash error message
- Bulk purge partial failure renders aggregate summary flash error message
"""

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

from src.config import config
from src.core.models import ProjectStartupCharter, StartupKitBaseline
from src.review_storage.local import LocalReviewStorage

APP_FILE = str(Path(__file__).parent.parent / "src" / "review_ui" / "app.py")


@pytest.fixture
def clean_storage(tmp_path, monkeypatch):
    """Ensure LocalReviewStorage points to an isolated temp review queue."""
    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)
    monkeypatch.setattr("src.review_ui.app.get_review_storage", lambda: storage)
    monkeypatch.setattr("src.review_ui.manage_runs.get_review_storage", lambda: storage)
    return storage


def _seed_sample_run(storage: LocalReviewStorage, project_name: str = "Project Phoenix") -> str:
    """Helper to seed a review run into isolated storage."""
    baseline = StartupKitBaseline(
        project_name=project_name,
        contract_type="Fixed Bid",
        governance_tier="Partnered",
        charter=ProjectStartupCharter(delivery_manager="Sarah Connor"),
    ).model_dump(mode="json")
    validation = {"findings": []}
    return storage.create_run(project_name, baseline, validation)


# ==============================================================================
# Group 1: Whole-Page Passphrase Gate Lifecycle (4 Tests)
# ==============================================================================

def test_manage_runs_apptest_locked_state_renders_gate_form(clean_storage):
    """Verify Manage Runs page in locked state renders only the gate form and hides dashboard."""
    _seed_sample_run(clean_storage, "Project Phoenix")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    assert not at.exception
    # Title and gate explanation are rendered
    assert any("Manage Runs" in str(t.value) for t in at.title)
    assert any("protected by an admin passphrase" in str(m.value) for m in at.markdown)

    # Password input and submit button exist
    assert at.text_input(key="manage_runs_passphrase_input")
    assert at.button(key="manage_runs_unlock_button")

    # Dashboard metrics, lock button, tabs, and action controls are hidden
    assert len(at.metric) == 0
    assert len([b for b in at.button if b.key == "manage_runs_lock_button"]) == 0
    assert len([r for r in at.radio if r.key == "manage_runs_view_tab"]) == 0


def test_manage_runs_apptest_wrong_passphrase_displays_error(clean_storage):
    """Verify submitting an incorrect passphrase displays error message and keeps dashboard locked."""
    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    at.text_input(key="manage_runs_passphrase_input").input("wrong_passphrase_value")
    at.button(key="manage_runs_unlock_button").click().run()

    assert not at.exception
    assert at.error
    assert any("Incorrect passphrase. Access denied." in str(e.value) for e in at.error)

    # Gate remains visible and locked
    assert at.text_input(key="manage_runs_passphrase_input")
    assert len(at.metric) == 0


def test_manage_runs_apptest_correct_passphrase_unlocks_dashboard(clean_storage):
    """Verify submitting correct admin passphrase unlocks dashboard metrics and management tabs."""
    run_id = _seed_sample_run(clean_storage, "Project Phoenix")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()

    assert not at.exception
    # Gate form is gone
    assert len([t for t in at.text_input if t.key == "manage_runs_passphrase_input"]) == 0

    # Header caption and lock button render
    assert any("Administrative run lifecycle and storage management." in str(c.value) for c in at.caption)
    assert at.button(key="manage_runs_lock_button")

    # Metrics render accurately
    metrics = {m.label: m.value for m in at.metric}
    assert metrics.get("Total Runs") == "1"
    assert metrics.get("Active Runs") == "1"
    assert metrics.get("Archived Runs") == "0"

    # Action controls for active run exist
    assert at.button(key=f"btn_archive_{run_id}")


def test_manage_runs_apptest_lock_button_relocks_page(clean_storage):
    """Verify clicking 'Lock page' relocks the dashboard and restores the passphrase gate form."""
    _seed_sample_run(clean_storage, "Project Phoenix")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # Unlock
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()
    assert at.button(key="manage_runs_lock_button")

    # Click Lock page
    at.button(key="manage_runs_lock_button").click().run()
    assert not at.exception

    # Passphrase gate is restored
    assert at.text_input(key="manage_runs_passphrase_input")
    assert at.button(key="manage_runs_unlock_button")
    assert len(at.metric) == 0


# ==============================================================================
# Group 2: HTL-81 Tab Navigation & State Persistence (3 Tests)
# ==============================================================================

def test_manage_runs_apptest_active_tab_archive_preserves_active_view(clean_storage):
    """Verify archiving an active run updates storage, flashes success, and preserves 'active' view tab (HTL-81)."""
    run_id = _seed_sample_run(clean_storage, "Project Phoenix")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # Unlock
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()

    # Initial view is active
    assert at.radio(key="manage_runs_view_tab").value == "active"

    # Click Archive on active run
    at.button(key=f"btn_archive_{run_id}").click().run()
    assert not at.exception

    # Storage updated
    assert clean_storage.get_run(run_id).archived is True

    # Flash success message displayed
    assert at.success
    assert any(f"Run '{run_id}' has been archived." in str(s.value) for s in at.success)

    # Active view tab persists across rerun
    assert at.radio(key="manage_runs_view_tab").value == "active"

    # Metrics updated
    metrics = {m.label: m.value for m in at.metric}
    assert metrics.get("Active Runs") == "0"
    assert metrics.get("Archived Runs") == "1"


def test_manage_runs_apptest_archived_tab_unarchive_preserves_archived_view(clean_storage):
    """Verify unarchiving a run updates storage, flashes success, and preserves 'archived' view tab (HTL-81)."""
    run_id = _seed_sample_run(clean_storage, "Project Phoenix")
    clean_storage.archive_run(run_id)

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # Unlock
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()

    # Switch to Archived tab
    at.radio(key="manage_runs_view_tab").set_value("archived").run()
    assert at.radio(key="manage_runs_view_tab").value == "archived"

    # Click Unarchive on archived run
    at.button(key=f"btn_unarchive_{run_id}").click().run()
    assert not at.exception

    # Storage updated
    assert clean_storage.get_run(run_id).archived is False

    # Flash success message displayed
    assert at.success
    assert any(f"Run '{run_id}' restored to active." in str(s.value) for s in at.success)

    # Archived tab remains selected (does not snap back to active tab)
    assert at.radio(key="manage_runs_view_tab").value == "archived"


def test_manage_runs_apptest_archived_tab_purge_preserves_archived_view(clean_storage, tmp_path):
    """Verify purging an archived run maintains the 'archived' view tab across rerun without resetting to 'active' (HTL-81)."""
    run_id = _seed_sample_run(clean_storage, "Project Phoenix")
    doc_file = tmp_path / "doc.docx"
    doc_file.write_text("content", encoding="utf-8")
    clean_storage.put_generated_files(run_id, [doc_file])
    clean_storage.archive_run(run_id)

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # Unlock
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()

    # Switch to Archived tab
    at.radio(key="manage_runs_view_tab").set_value("archived").run()
    assert at.radio(key="manage_runs_view_tab").value == "archived"

    # Select and purge the run
    at.checkbox(key=f"chk_select_{run_id}").check().run()
    at.button(key="btn_bulk_purge_init").click().run()
    at.button(key="btn_bulk_purge_confirm").click().run()
    assert not at.exception

    # HTL-81 core assertion: after purge rerun, the tab remains 'archived'
    assert at.radio(key="manage_runs_view_tab").value == "archived"
    assert clean_storage.list_runs(include_archived=True) == []


# ==============================================================================
# Group 3: HTL-82 & HTL-83 Bulk-Selection & Two-Stage Confirmation Purge Flow (5 Tests)
# ==============================================================================

def test_manage_runs_apptest_select_all_and_deselect_all_toolbar(clean_storage):
    """Verify Select All and Deselect All toolbar buttons toggle all archived checkboxes and button state (HTL-82)."""
    run1 = _seed_sample_run(clean_storage, "Project Alpha")
    run2 = _seed_sample_run(clean_storage, "Project Beta")
    run3 = _seed_sample_run(clean_storage, "Project Gamma")

    clean_storage.archive_run(run1)
    clean_storage.archive_run(run2)
    clean_storage.archive_run(run3)

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # Unlock and navigate to Archived tab
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()
    at.radio(key="manage_runs_view_tab").set_value("archived").run()

    # Initial state: 0 selected, Purge button disabled
    purge_btn = at.button(key="btn_bulk_purge_init")
    assert purge_btn.disabled is True

    # Click Select All
    at.button(key="btn_select_all_archived").click().run()
    assert not at.exception
    assert at.checkbox(key=f"chk_select_{run1}").value is True
    assert at.checkbox(key=f"chk_select_{run2}").value is True
    assert at.checkbox(key=f"chk_select_{run3}").value is True
    assert at.button(key="btn_bulk_purge_init").disabled is False

    # Click Deselect All
    at.button(key="btn_deselect_all_archived").click().run()
    assert not at.exception
    assert at.checkbox(key=f"chk_select_{run1}").value is False
    assert at.checkbox(key=f"chk_select_{run2}").value is False
    assert at.checkbox(key=f"chk_select_{run3}").value is False
    assert at.button(key="btn_bulk_purge_init").disabled is True


def test_manage_runs_apptest_bulk_purge_init_opens_confirmation_panel(clean_storage):
    """Verify clicking Purge Selected opens stage-2 confirmation warning banner and action buttons."""
    run1 = _seed_sample_run(clean_storage, "Project Alpha")
    run2 = _seed_sample_run(clean_storage, "Project Beta")
    clean_storage.archive_run(run1)
    clean_storage.archive_run(run2)

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # Unlock and navigate to Archived tab
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()
    at.radio(key="manage_runs_view_tab").set_value("archived").run()

    # Select run1 and run2
    at.checkbox(key=f"chk_select_{run1}").check().run()
    at.checkbox(key=f"chk_select_{run2}").check().run()

    # Click Purge Selected (2)
    at.button(key="btn_bulk_purge_init").click().run()
    assert not at.exception

    # Warning confirmation container rendered
    assert at.warning
    assert any("Confirm Bulk Purge" in str(w.value) for w in at.warning)
    assert any("permanently delete **2**" in str(w.value) for w in at.warning)

    # Selected run titles listed in markdown
    assert any("Project Alpha" in str(m.value) for m in at.markdown)
    assert any("Project Beta" in str(m.value) for m in at.markdown)

    # Confirm & Cancel buttons exist
    assert at.button(key="btn_bulk_purge_confirm")
    assert at.button(key="btn_bulk_purge_cancel")


def test_manage_runs_apptest_bulk_purge_cancel_dismisses_confirmation_panel(clean_storage):
    """Verify clicking Cancel in confirmation panel dismisses warning banner and preserves runs."""
    run1 = _seed_sample_run(clean_storage, "Project Alpha")
    run2 = _seed_sample_run(clean_storage, "Project Beta")
    clean_storage.archive_run(run1)
    clean_storage.archive_run(run2)

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # Unlock and navigate to Archived tab
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()
    at.radio(key="manage_runs_view_tab").set_value("archived").run()

    # Select run1 and open confirmation panel
    at.checkbox(key=f"chk_select_{run1}").check().run()
    at.button(key="btn_bulk_purge_init").click().run()
    assert at.button(key="btn_bulk_purge_confirm")

    # Click Cancel
    at.button(key="btn_bulk_purge_cancel").click().run()
    assert not at.exception

    # Confirmation panel dismissed
    assert len([b for b in at.button if b.key == "btn_bulk_purge_confirm"]) == 0
    assert len([b for b in at.button if b.key == "btn_bulk_purge_cancel"]) == 0

    # Runs remain preserved in storage
    assert clean_storage.get_run(run1).archived is True
    assert clean_storage.get_run(run2).archived is True


def test_manage_runs_apptest_confirm_purge_single_run_deletes_and_clears_selection(clean_storage, tmp_path):
    """Verify single-run purge via selection deletes record/files and clears checkbox state (HTL-83)."""
    run_id = _seed_sample_run(clean_storage, "Project Phoenix")

    # Create dummy output file
    doc_file = tmp_path / "Project_Phoenix_Startup_Kit.docx"
    doc_file.write_text("dummy artifact content", encoding="utf-8")
    clean_storage.put_generated_files(run_id, [doc_file])

    clean_storage.archive_run(run_id)

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # Unlock and navigate to Archived tab
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()
    at.radio(key="manage_runs_view_tab").set_value("archived").run()

    # Select run, open confirmation, and confirm purge
    at.checkbox(key=f"chk_select_{run_id}").check().run()
    at.button(key="btn_bulk_purge_init").click().run()
    at.button(key="btn_bulk_purge_confirm").click().run()
    assert not at.exception

    # Flash success rendered
    assert at.success
    assert any("Successfully purged 1 run(s) and all associated files." in str(s.value) for s in at.success)

    # View tab remains archived
    assert at.radio(key="manage_runs_view_tab").value == "archived"

    # Run record completely removed from storage
    with pytest.raises(FileNotFoundError):
        clean_storage.get_run(run_id)
    assert clean_storage.list_runs(include_archived=True) == []


def test_manage_runs_apptest_confirm_purge_multiple_runs_deletes_all_selected(clean_storage, tmp_path):
    """Verify bulk purge permanently deletes all selected runs and keeps unselected runs (HTL-82)."""
    run_active = _seed_sample_run(clean_storage, "Active Project")
    run_archived_1 = _seed_sample_run(clean_storage, "Archived Project 1")
    run_archived_2 = _seed_sample_run(clean_storage, "Archived Project 2")
    run_archived_3 = _seed_sample_run(clean_storage, "Archived Project 3")

    for rid in (run_archived_1, run_archived_2, run_archived_3):
        clean_storage.archive_run(rid)
        f = tmp_path / f"{rid}.docx"
        f.write_text("artifact", encoding="utf-8")
        clean_storage.put_generated_files(rid, [f])

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # Unlock and navigate to Archived tab
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()
    at.radio(key="manage_runs_view_tab").set_value("archived").run()

    # Select run 1 and run 3 (leave run 2 unselected)
    at.checkbox(key=f"chk_select_{run_archived_1}").check().run()
    at.checkbox(key=f"chk_select_{run_archived_3}").check().run()

    # Open confirmation and confirm
    at.button(key="btn_bulk_purge_init").click().run()
    at.button(key="btn_bulk_purge_confirm").click().run()
    assert not at.exception

    # Flash success rendered
    assert at.success
    assert any("Successfully purged 2 run(s) and all associated files." in str(s.value) for s in at.success)

    # Verify selected runs deleted, unselected and active runs intact
    with pytest.raises(FileNotFoundError):
        clean_storage.get_run(run_archived_1)
    with pytest.raises(FileNotFoundError):
        clean_storage.get_run(run_archived_3)

    assert clean_storage.get_run(run_archived_2).archived is True
    assert clean_storage.get_run(run_active).archived is False

    # Metrics updated
    metrics = {m.label: m.value for m in at.metric}
    assert metrics.get("Total Runs") == "2"
    assert metrics.get("Active Runs") == "1"
    assert metrics.get("Archived Runs") == "1"


# ==============================================================================
# Group 4: Error Handling and Flash Messaging (2 Tests)
# ==============================================================================

def test_manage_runs_apptest_archive_failure_displays_flash_error(clean_storage, monkeypatch):
    """Verify storage archive exception renders a descriptive flash error banner."""
    run_id = _seed_sample_run(clean_storage, "Project Phoenix")

    def mock_archive_fail(rid: str):
        raise PermissionError("Disk write protected")

    monkeypatch.setattr(clean_storage, "archive_run", mock_archive_fail)

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # Unlock
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()

    # Attempt archive
    at.button(key=f"btn_archive_{run_id}").click().run()
    assert not at.exception

    # Error message rendered
    assert at.error
    assert any(f"Failed to archive run '{run_id}': Disk write protected" in str(e.value) for e in at.error)


def test_manage_runs_apptest_partial_purge_failure_displays_summary_error(clean_storage, monkeypatch):
    """Verify bulk purge partial failure purges valid items and renders an aggregate error message."""
    run1 = _seed_sample_run(clean_storage, "Project Alpha")
    run2 = _seed_sample_run(clean_storage, "Project Beta")
    clean_storage.archive_run(run1)
    clean_storage.archive_run(run2)

    original_purge = clean_storage.purge_run

    def mock_purge_partial(rid: str):
        if rid == run2:
            raise RuntimeError("Cloud Storage timeout on run2")
        return original_purge(rid)

    monkeypatch.setattr(clean_storage, "purge_run", mock_purge_partial)

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # Unlock and navigate to Archived tab
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()
    at.radio(key="manage_runs_view_tab").set_value("archived").run()

    # Select all and confirm purge
    at.button(key="btn_select_all_archived").click().run()
    at.button(key="btn_bulk_purge_init").click().run()
    at.button(key="btn_bulk_purge_confirm").click().run()
    assert not at.exception

    # Run 1 deleted, Run 2 retained
    with pytest.raises(FileNotFoundError):
        clean_storage.get_run(run1)
    assert clean_storage.get_run(run2).archived is True

    # Error summary rendered
    assert at.error
    assert any("Purged 1 run(s). 1 failed: " in str(e.value) for e in at.error)
    assert any("Cloud Storage timeout on run2" in str(e.value) for e in at.error)


# ==============================================================================
# Group 5: HTL-111 Sequential Archive & Unarchive Actions (Multi-Step Regression)
# ==============================================================================

def test_manage_runs_apptest_sequential_archive_actions_survive_consecutive_reruns(clean_storage):
    """Verify consecutive Archive actions in sequence do not clear radio selection or hide active list (HTL-111)."""
    run1 = _seed_sample_run(clean_storage, "Alpha Project")
    run2 = _seed_sample_run(clean_storage, "Beta Project")
    run3 = _seed_sample_run(clean_storage, "Gamma Project")
    run4 = _seed_sample_run(clean_storage, "Delta Project")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # Unlock
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()

    # Initial state: 4 active runs rendered
    assert at.radio(key="manage_runs_view_tab").value == "active"
    archive_buttons_initial = [b for b in at.button if b.key.startswith("btn_archive_")]
    assert len(archive_buttons_initial) == 4

    # Action 1: Archive Run 1 (1st consecutive action)
    at.button(key=f"btn_archive_{run1}").click().run()
    assert not at.exception
    assert clean_storage.get_run(run1).archived is True
    assert at.radio(key="manage_runs_view_tab").value == "active"
    archive_buttons_after_1 = [b for b in at.button if b.key.startswith("btn_archive_")]
    assert len(archive_buttons_after_1) == 3

    # Action 2: Archive Run 2 (2nd consecutive action - triggers HTL-111 bug if dynamic label serde fails)
    at.button(key=f"btn_archive_{run2}").click().run()
    assert not at.exception
    assert clean_storage.get_run(run2).archived is True
    # The active tab must remain selected and the active run list must not disappear
    assert at.radio(key="manage_runs_view_tab").value == "active"
    archive_buttons_after_2 = [b for b in at.button if b.key.startswith("btn_archive_")]
    assert len(archive_buttons_after_2) == 2
    assert any(f"btn_archive_{run3}" == b.key for b in archive_buttons_after_2)
    assert any(f"btn_archive_{run4}" == b.key for b in archive_buttons_after_2)

    # Action 3: Archive Run 3 (3rd consecutive action)
    at.button(key=f"btn_archive_{run3}").click().run()
    assert not at.exception
    assert clean_storage.get_run(run3).archived is True
    assert at.radio(key="manage_runs_view_tab").value == "active"
    archive_buttons_after_3 = [b for b in at.button if b.key.startswith("btn_archive_")]
    assert len(archive_buttons_after_3) == 1
    assert archive_buttons_after_3[0].key == f"btn_archive_{run4}"

    # Verify metrics update accurately
    metrics = {m.label: m.value for m in at.metric}
    assert metrics.get("Total Runs") == "4"
    assert metrics.get("Active Runs") == "1"
    assert metrics.get("Archived Runs") == "3"


def test_manage_runs_apptest_sequential_unarchive_actions_survive_consecutive_reruns(clean_storage):
    """Verify consecutive Unarchive actions in sequence do not clear radio selection or hide archived list (HTL-111)."""
    run1 = _seed_sample_run(clean_storage, "Alpha Project")
    run2 = _seed_sample_run(clean_storage, "Beta Project")
    run3 = _seed_sample_run(clean_storage, "Gamma Project")
    run4 = _seed_sample_run(clean_storage, "Delta Project")

    clean_storage.archive_run(run1)
    clean_storage.archive_run(run2)
    clean_storage.archive_run(run3)
    clean_storage.archive_run(run4)

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # Unlock and switch to Archived tab
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()
    at.radio(key="manage_runs_view_tab").set_value("archived").run()

    # Initial state: 4 archived runs rendered
    assert at.radio(key="manage_runs_view_tab").value == "archived"
    unarchive_buttons_initial = [b for b in at.button if b.key.startswith("btn_unarchive_")]
    assert len(unarchive_buttons_initial) == 4

    # Action 1: Unarchive Run 1 (1st consecutive action)
    at.button(key=f"btn_unarchive_{run1}").click().run()
    assert not at.exception
    assert clean_storage.get_run(run1).archived is False
    assert at.radio(key="manage_runs_view_tab").value == "archived"
    unarchive_buttons_after_1 = [b for b in at.button if b.key.startswith("btn_unarchive_")]
    assert len(unarchive_buttons_after_1) == 3

    # Action 2: Unarchive Run 2 (2nd consecutive action - triggers HTL-111 bug if dynamic label serde fails)
    at.button(key=f"btn_unarchive_{run2}").click().run()
    assert not at.exception
    assert clean_storage.get_run(run2).archived is False
    # The archived tab must remain selected and the archived run list must not disappear
    assert at.radio(key="manage_runs_view_tab").value == "archived"
    unarchive_buttons_after_2 = [b for b in at.button if b.key.startswith("btn_unarchive_")]
    assert len(unarchive_buttons_after_2) == 2
    assert any(f"btn_unarchive_{run3}" == b.key for b in unarchive_buttons_after_2)
    assert any(f"btn_unarchive_{run4}" == b.key for b in unarchive_buttons_after_2)

    # Action 3: Unarchive Run 3 (3rd consecutive action)
    at.button(key=f"btn_unarchive_{run3}").click().run()
    assert not at.exception
    assert clean_storage.get_run(run3).archived is False
    assert at.radio(key="manage_runs_view_tab").value == "archived"
    unarchive_buttons_after_3 = [b for b in at.button if b.key.startswith("btn_unarchive_")]
    assert len(unarchive_buttons_after_3) == 1
    assert unarchive_buttons_after_3[0].key == f"btn_unarchive_{run4}"

    # Verify metrics update accurately
    metrics = {m.label: m.value for m in at.metric}
    assert metrics.get("Total Runs") == "4"
    assert metrics.get("Active Runs") == "3"
    assert metrics.get("Archived Runs") == "1"
