"""HTL-75 / HTL-76: Automated Streamlit AppTest suite for Manage Runs UI and Fact Review filtering.

Covers:
1. Whole-page admin passphrase gate: locked by default, hides run lists/metrics/actions.
2. Invalid passphrase entry: displays error and remains locked.
3. Valid passphrase entry: unlocks dashboard, renders metrics, tabs, and action controls.
4. Active run archiving: clicking Archive moves run to archived state and shows flash message.
5. Archived run unarchiving: clicking Unarchive restores run to active state and Fact Review selector.
6. Archived run purge: clicking Purge with confirmation permanently removes the run and its files.
7. Fact Review selector filtering: strictly excludes archived runs and updates immediately upon archive/unarchive.
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
    baseline = StartupKitBaseline(
        project_name=project_name,
        contract_type="Fixed Bid",
        governance_tier="Partnered",
        charter=ProjectStartupCharter(delivery_manager="Sarah Connor"),
    ).model_dump(mode="json")
    validation = {"findings": []}
    return storage.create_run(project_name, baseline, validation)


def test_manage_runs_page_locked_by_default(clean_storage):
    """Verify Manage Runs page renders only the passphrase gate when locked."""
    _seed_sample_run(clean_storage, "Project Phoenix")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    assert not at.exception
    # Passphrase gate is visible
    assert at.text_input(key="manage_runs_passphrase_input")
    assert at.button(key="manage_runs_unlock_button")
    # Dashboard elements are hidden
    assert not any("Total Runs" in str(m.label) for m in at.metric)
    assert not any("btn_archive_" in str(b.key) for b in at.button)
    assert not any("btn_unarchive_" in str(b.key) for b in at.button)


def test_manage_runs_wrong_passphrase_displays_error(clean_storage):
    """Verify entering an incorrect passphrase displays error message and stays locked."""
    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    at.text_input(key="manage_runs_passphrase_input").input("wrong_admin_password")
    at.button(key="manage_runs_unlock_button").click().run()

    assert not at.exception
    assert at.error
    assert "Incorrect passphrase" in at.error[0].value
    # Still locked
    assert at.text_input(key="manage_runs_passphrase_input")


def test_manage_runs_correct_passphrase_unlocks_dashboard(clean_storage):
    """Verify entering correct ADMIN_PASSPHRASE unlocks dashboard metrics and tabs."""
    run_id = _seed_sample_run(clean_storage, "Project Phoenix")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()

    assert not at.exception
    # Passphrase input is now gone
    assert len([t for t in at.text_input if t.key == "manage_runs_passphrase_input"]) == 0

    # Metrics render
    metrics = {m.label: m.value for m in at.metric}
    assert metrics.get("Total Runs") == "1"
    assert metrics.get("Active Runs") == "1"
    assert metrics.get("Archived Runs") == "0"

    # Archive button for the run exists
    assert at.button(key=f"btn_archive_{run_id}")


def test_manage_runs_passphrase_with_whitespace_unlocks_dashboard(clean_storage):
    """Verify entering ADMIN_PASSPHRASE with surrounding whitespace cleanly unlocks."""
    run_id = _seed_sample_run(clean_storage, "Project Phoenix")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    at.text_input(key="manage_runs_passphrase_input").input(f"  {config.admin_passphrase} \n")
    at.button(key="manage_runs_unlock_button").click().run()

    assert not at.exception
    assert len([t for t in at.text_input if t.key == "manage_runs_passphrase_input"]) == 0
    assert at.button(key=f"btn_archive_{run_id}")


def test_manage_runs_archive_and_unarchive_flow(clean_storage):
    """Verify clicking Archive moves run to archived and clicking Unarchive restores it, maintaining tab persistence."""
    run_id = _seed_sample_run(clean_storage, "Project Phoenix")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # Unlock
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()

    # Verify initial tab is 'active'
    assert at.radio(key="manage_runs_view_tab").value == "active"

    # Click Archive on Active tab
    at.button(key=f"btn_archive_{run_id}").click().run()
    assert not at.exception

    # Check storage state and verify active tab remained active
    assert clean_storage.get_run(run_id).archived is True
    assert at.radio(key="manage_runs_view_tab").value == "active"

    # Verify metrics update
    metrics = {m.label: m.value for m in at.metric}
    assert metrics.get("Active Runs") == "0"
    assert metrics.get("Archived Runs") == "1"

    # Switch to Archived tab
    at.radio(key="manage_runs_view_tab").set_value("archived").run()
    assert not at.exception
    assert at.radio(key="manage_runs_view_tab").value == "archived"

    # Click Unarchive on Archived tab
    at.button(key=f"btn_unarchive_{run_id}").click().run()
    assert not at.exception

    # Verify tab remained 'archived' across rerun (HTL-81)
    assert at.radio(key="manage_runs_view_tab").value == "archived"

    # Check storage state restored
    assert clean_storage.get_run(run_id).archived is False
    metrics_restored = {m.label: m.value for m in at.metric}
    assert metrics_restored.get("Active Runs") == "1"
    assert metrics_restored.get("Archived Runs") == "0"


def test_manage_runs_single_purge_flow_deletes_run_and_preserves_tab(clean_storage, tmp_path):
    """Verify purging an archived run deletes files and record, preserving Archived tab across rerun."""
    run_id = _seed_sample_run(clean_storage, "Project Phoenix")

    # Put a generated file
    test_file = tmp_path / "Project_Phoenix_Startup_Kit.docx"
    test_file.write_text("sample content", encoding="utf-8")
    clean_storage.put_generated_files(run_id, [test_file])

    # Archive the run
    clean_storage.archive_run(run_id)

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # Unlock
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()

    # Switch to Archived tab
    at.radio(key="manage_runs_view_tab").set_value("archived").run()
    assert at.radio(key="manage_runs_view_tab").value == "archived"

    # Check confirm purge checkbox and click Purge
    at.checkbox(key=f"chk_purge_{run_id}").check().run()
    at.button(key=f"btn_purge_{run_id}").click().run()

    assert not at.exception

    # Verify tab remained 'archived' across rerun (HTL-81)
    assert at.radio(key="manage_runs_view_tab").value == "archived"

    # Confirm run is completely gone from storage
    with pytest.raises(FileNotFoundError):
        clean_storage.get_run(run_id)
    assert clean_storage.list_runs(include_archived=True) == []


def test_manage_runs_bulk_selection_and_select_all_deselect_all_toggles(clean_storage):
    """Verify Select All and Deselect All controls toggle all archived checkboxes (HTL-82)."""
    run1 = _seed_sample_run(clean_storage, "Project Alpha")
    run2 = _seed_sample_run(clean_storage, "Project Beta")
    run3 = _seed_sample_run(clean_storage, "Project Gamma")

    clean_storage.archive_run(run1)
    clean_storage.archive_run(run2)
    clean_storage.archive_run(run3)

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # Unlock
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()

    # Switch to Archived tab
    at.radio(key="manage_runs_view_tab").set_value("archived").run()

    # Initial state: none selected, Purge Selected (0) is disabled
    assert at.button(key="btn_bulk_purge_init").disabled is True

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


def test_manage_runs_bulk_purge_cancellation_preserves_runs_and_selection(clean_storage):
    """Verify clicking Cancel in bulk purge confirmation leaves runs and selection intact (HTL-82)."""
    run1 = _seed_sample_run(clean_storage, "Project Alpha")
    run2 = _seed_sample_run(clean_storage, "Project Beta")
    clean_storage.archive_run(run1)
    clean_storage.archive_run(run2)

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # Unlock
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()

    # Switch to Archived tab
    at.radio(key="manage_runs_view_tab").set_value("archived").run()

    # Select run1
    at.checkbox(key=f"chk_select_{run1}").check().run()
    assert at.button(key="btn_bulk_purge_init").disabled is False

    # Click Purge Selected (1) -> opens confirmation
    at.button(key="btn_bulk_purge_init").click().run()
    assert not at.exception
    assert at.button(key="btn_bulk_purge_confirm")
    assert at.button(key="btn_bulk_purge_cancel")

    # Click Cancel
    at.button(key="btn_bulk_purge_cancel").click().run()
    assert not at.exception

    # Confirmation panel dismissed, runs intact in storage
    assert len([b for b in at.button if b.key == "btn_bulk_purge_confirm"]) == 0
    assert clean_storage.get_run(run1).archived is True
    assert clean_storage.get_run(run2).archived is True


def test_manage_runs_selective_bulk_purge_execution(clean_storage, tmp_path):
    """Verify bulk purge permanently deletes only selected runs and keeps unselected/active runs (HTL-82)."""
    run_active = _seed_sample_run(clean_storage, "Active Project")
    run_archived_1 = _seed_sample_run(clean_storage, "Archived Project 1")
    run_archived_2 = _seed_sample_run(clean_storage, "Archived Project 2")
    run_archived_3 = _seed_sample_run(clean_storage, "Archived Project 3")
    run_archived_4 = _seed_sample_run(clean_storage, "Archived Project 4")

    # Create dummy output files
    for rid in (run_archived_1, run_archived_2, run_archived_3, run_archived_4):
        clean_storage.archive_run(rid)
        f = tmp_path / f"{rid}_doc.docx"
        f.write_text("sample content", encoding="utf-8")
        clean_storage.put_generated_files(rid, [f])

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # Unlock
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()

    # Switch to Archived tab
    at.radio(key="manage_runs_view_tab").set_value("archived").run()

    # Select run_archived_1 and run_archived_3 (leave 2 and 4 unchecked)
    at.checkbox(key=f"chk_select_{run_archived_1}").check().run()
    at.checkbox(key=f"chk_select_{run_archived_3}").check().run()

    # Click Purge Selected
    at.button(key="btn_bulk_purge_init").click().run()
    assert not at.exception

    # Verify confirmation shows the 2 runs
    assert at.button(key="btn_bulk_purge_confirm")
    assert any("Archived Project 1" in str(m.value) for m in at.markdown)
    assert any("Archived Project 3" in str(m.value) for m in at.markdown)

    # Confirm Deletion
    at.button(key="btn_bulk_purge_confirm").click().run()
    assert not at.exception

    # Verify tab remained 'archived' across bulk purge rerun
    assert at.radio(key="manage_runs_view_tab").value == "archived"

    # Verify selected runs are deleted from storage
    with pytest.raises(FileNotFoundError):
        clean_storage.get_run(run_archived_1)
    with pytest.raises(FileNotFoundError):
        clean_storage.get_run(run_archived_3)

    # Verify unselected archived runs and active run remain intact
    assert clean_storage.get_run(run_active).archived is False
    assert clean_storage.get_run(run_archived_2).archived is True
    assert clean_storage.get_run(run_archived_4).archived is True

    # Verify metrics
    metrics = {m.label: m.value for m in at.metric}
    assert metrics.get("Total Runs") == "3"
    assert metrics.get("Active Runs") == "1"
    assert metrics.get("Archived Runs") == "2"


def test_manage_runs_bulk_purge_partial_failure_reporting(clean_storage, monkeypatch):
    """Verify bulk purge handles individual run failure without aborting remaining deletions (HTL-82)."""
    run1 = _seed_sample_run(clean_storage, "Project Alpha")
    run2 = _seed_sample_run(clean_storage, "Project Beta")
    run3 = _seed_sample_run(clean_storage, "Project Gamma")

    clean_storage.archive_run(run1)
    clean_storage.archive_run(run2)
    clean_storage.archive_run(run3)

    # Monkeypatch storage.purge_run to fail on run2 only
    original_purge = clean_storage.purge_run

    def mock_purge(rid: str):
        if rid == run2:
            raise RuntimeError("Disk I/O error on test run2")
        return original_purge(rid)

    monkeypatch.setattr(clean_storage, "purge_run", mock_purge)

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # Unlock
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()

    # Switch to Archived tab
    at.radio(key="manage_runs_view_tab").set_value("archived").run()

    # Select all 3 runs
    at.button(key="btn_select_all_archived").click().run()

    # Click Purge Selected -> Confirm
    at.button(key="btn_bulk_purge_init").click().run()
    at.button(key="btn_bulk_purge_confirm").click().run()

    assert not at.exception

    # Verify run1 and run3 were successfully deleted, run2 remains
    with pytest.raises(FileNotFoundError):
        clean_storage.get_run(run1)
    with pytest.raises(FileNotFoundError):
        clean_storage.get_run(run3)
    assert clean_storage.get_run(run2).archived is True

    # Verify error flash message is rendered
    assert at.error
    assert any("Purged 2 run(s). 1 failed" in str(e.value) for e in at.error)
    assert any("Disk I/O error on test run2" in str(e.value) for e in at.error)


def test_fact_review_excludes_archived_runs_and_updates_on_toggle(clean_storage):
    """Verify Fact Review selector lists ONLY active runs, excluding archived ones."""
    run_active = _seed_sample_run(clean_storage, "Active Project")
    run_archived = _seed_sample_run(clean_storage, "Archived Project")
    clean_storage.archive_run(run_archived)

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Fact Review").run()

    assert not at.exception
    # Check selector options
    selector = at.selectbox(key="fact_review_run_selector")
    assert selector is not None
    options = list(selector.options)

    # run_active is present, run_archived is strictly excluded
    assert any(run_active in opt for opt in options)
    assert not any(run_archived in opt for opt in options)

    # Unarchive the run and verify Fact Review updates
    clean_storage.unarchive_run(run_archived)
    at.sidebar.radio(key="app_page_selector").set_value("Fact Review").run()
    updated_options = list(at.selectbox(key="fact_review_run_selector").options)
    assert any(run_active in opt for opt in updated_options)
    assert any(run_archived in opt for opt in updated_options)
