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

    at.text_input(key="manage_runs_passphrase_input").input("wrong_admin_password").run()
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

    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase).run()
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


def test_manage_runs_archive_and_unarchive_flow(clean_storage):
    """Verify clicking Archive moves run to archived and clicking Unarchive restores it."""
    run_id = _seed_sample_run(clean_storage, "Project Phoenix")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # Unlock
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase).run()
    at.button(key="manage_runs_unlock_button").click().run()

    # Click Archive
    at.button(key=f"btn_archive_{run_id}").click().run()
    assert not at.exception

    # Check storage state
    assert clean_storage.get_run(run_id).archived is True

    # Verify metrics update
    metrics = {m.label: m.value for m in at.metric}
    assert metrics.get("Active Runs") == "0"
    assert metrics.get("Archived Runs") == "1"

    # Click Unarchive
    at.button(key=f"btn_unarchive_{run_id}").click().run()
    assert not at.exception

    # Check storage state restored
    assert clean_storage.get_run(run_id).archived is False
    metrics_restored = {m.label: m.value for m in at.metric}
    assert metrics_restored.get("Active Runs") == "1"
    assert metrics_restored.get("Archived Runs") == "0"


def test_manage_runs_purge_flow_deletes_run(clean_storage, tmp_path):
    """Verify purging an archived run deletes files and record from storage."""
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
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase).run()
    at.button(key="manage_runs_unlock_button").click().run()

    # Check confirm purge checkbox and click Purge
    at.checkbox(key=f"chk_purge_{run_id}").check().run()
    at.button(key=f"btn_purge_{run_id}").click().run()

    assert not at.exception

    # Confirm run is completely gone from storage
    with pytest.raises(FileNotFoundError):
        clean_storage.get_run(run_id)
    assert clean_storage.list_runs(include_archived=True) == []


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
