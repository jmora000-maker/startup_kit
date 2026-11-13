"""HTL-112: Streamlit AppTest regression test suite for button styling and theme standardization.

Verifies:
1. Theme configuration in .streamlit/config.toml sets primaryColor = "#0F256E".
2. Every button / form_submit_button call site across all 3 UI modules uses type="primary":
   - Fact Review (app.py): Save review (fixture & pending), Unlock generation (approved), Generate documents (approved), Approve (pending).
   - Generate / Re-ingest (generate.py): Unlock (admin gate), Unlock generation (generation gate), Generate (generate tab), Re-ingest and recalculate (reingest tab).
   - Manage Runs (manage_runs.py): Unlock Manage Runs, Lock page, Archive, Confirm & Delete, Cancel, Select All, Deselect All, Purge Selected, Unarchive.
3. Destructive actions ("Confirm & Delete {N} Runs" and "Purge Selected ({N})") are prefixed with warning emoji ⚠️ and no other button has the warning emoji.
"""

from pathlib import Path
import pytest
try:
    import tomllib
except ImportError:
    import tomli as tomllib
from streamlit.testing.v1 import AppTest

from src.config import config
from src.core.models import ProjectStartupCharter, StartupKitBaseline
from src.review_storage.local import LocalReviewStorage
from src.review_ui.app import DEMO_FIXTURE_LABEL

APP_FILE = str(Path(__file__).parent.parent / "src" / "review_ui" / "app.py")
CONFIG_TOML_PATH = Path(__file__).parent.parent / ".streamlit" / "config.toml"


@pytest.fixture
def clean_storage(tmp_path, monkeypatch):
    """Ensure LocalReviewStorage points to an isolated temp review queue."""
    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)
    monkeypatch.setattr("src.review_ui.app.get_review_storage", lambda: storage)
    monkeypatch.setattr("src.review_ui.manage_runs.get_review_storage", lambda: storage)
    return storage


def _seed_sample_run(
    storage: LocalReviewStorage,
    project_name: str = "Project Phoenix",
    state: str = "pending_review",
) -> str:
    """Helper to seed a review run with a specified state."""
    baseline = StartupKitBaseline(
        project_name=project_name,
        contract_type="Fixed Bid",
        governance_tier="Partnered",
        charter=ProjectStartupCharter(delivery_manager="Sarah Connor"),
    ).model_dump(mode="json")
    validation = {"findings": []}
    run_id = storage.create_run(project_name, baseline, validation)
    if state != "pending_review":
        storage.update_status(run_id, state)
    return run_id


# ==============================================================================
# Theme Configuration Tests
# ==============================================================================

def test_theme_primary_color_in_config_toml():
    """Verify .streamlit/config.toml exists and configures primaryColor = '#0F256E'."""
    assert CONFIG_TOML_PATH.exists(), f"Missing config file at {CONFIG_TOML_PATH}"
    content = CONFIG_TOML_PATH.read_text(encoding="utf-8")
    parsed = tomllib.loads(content)
    assert "theme" in parsed
    assert parsed["theme"].get("primaryColor") == "#0F256E"


# ==============================================================================
# Fact Review (app.py) Button Styling Tests
# ==============================================================================

def test_fact_review_fixture_mode_save_button_is_primary(clean_storage):
    """Verify 'Save review' button on Fact Review fixture mode has type='primary'."""
    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Fact Review").run()

    # Select demo fixture
    at.selectbox(key="fact_review_run_selector").set_value(DEMO_FIXTURE_LABEL).run()
    assert not at.exception

    save_btn = at.button(key="fact_review_save_button")
    assert save_btn is not None
    assert save_btn.proto.label == "Save review"
    assert save_btn.proto.type == "primary"
    assert "⚠️" not in save_btn.proto.label


def test_fact_review_pending_review_buttons_are_primary(clean_storage):
    """Verify 'Save review' and 'Approve' buttons for pending review runs have type='primary'."""
    run_id = _seed_sample_run(clean_storage, "Pending Run", state="pending_review")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Fact Review").run()

    run_option = [opt for opt in at.selectbox(key="fact_review_run_selector").options if run_id in opt][0]
    at.selectbox(key="fact_review_run_selector").set_value(run_option).run()
    assert not at.exception

    save_btn = at.button(key="fact_review_save_button")
    assert save_btn is not None
    assert save_btn.proto.label == "Save review"
    assert save_btn.proto.type == "primary"
    assert "⚠️" not in save_btn.proto.label

    approve_btn = at.button(key="fact_review_approve_button")
    assert approve_btn is not None
    assert approve_btn.proto.label == "Approve"
    assert approve_btn.proto.type == "primary"
    assert "⚠️" not in approve_btn.proto.label


def test_fact_review_approved_run_buttons_are_primary(clean_storage):
    """Verify 'Unlock generation' and 'Generate documents' buttons for approved runs have type='primary'."""
    run_id = _seed_sample_run(clean_storage, "Approved Run", state="approved")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Fact Review").run()

    run_option = [opt for opt in at.selectbox(key="fact_review_run_selector").options if run_id in opt][0]
    at.selectbox(key="fact_review_run_selector").set_value(run_option).run()
    assert not at.exception

    # 1. Locked generation access gate
    unlock_gen_btn = at.button(key=f"fact_review_{run_id}_gen_unlock_button")
    assert unlock_gen_btn is not None
    assert unlock_gen_btn.proto.label == "Unlock generation"
    assert unlock_gen_btn.proto.type == "primary"
    assert "⚠️" not in unlock_gen_btn.proto.label

    # 2. Unlock generation
    at.text_input(key=f"fact_review_{run_id}_gen_passphrase_input").input(config.generation_passphrase)
    unlock_gen_btn.click().run()
    assert not at.exception

    # 3. Generate documents button
    gen_docs_btn = at.button(key="fact_review_generate_button")
    assert gen_docs_btn is not None
    assert gen_docs_btn.proto.label == "Generate documents"
    assert gen_docs_btn.proto.type == "primary"
    assert "⚠️" not in gen_docs_btn.proto.label


def test_fact_review_admin_gate_unlock_button_is_primary(clean_storage):
    """Verify 'Unlock' button on Admin gate in Fact Review has type='primary'."""
    _seed_sample_run(clean_storage, "Admin Gate Run", state="pending_review")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Fact Review").run()

    admin_unlock_btn = at.button(key="fact_review_admin_unlock_button")
    assert admin_unlock_btn is not None
    assert admin_unlock_btn.proto.label == "Unlock"
    assert admin_unlock_btn.proto.type == "primary"
    assert "⚠️" not in admin_unlock_btn.proto.label


# ==============================================================================
# Generate / Re-ingest (generate.py) Button Styling Tests
# ==============================================================================

def test_generate_page_gate_and_submit_buttons_are_primary(clean_storage):
    """Verify all buttons in Generate tab have type='primary'."""
    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Generate / Re-ingest").run()
    assert not at.exception

    # 1. Admin gate button in Generate tab
    admin_btn = at.button(key="gen_admin_unlock_button")
    assert admin_btn is not None
    assert admin_btn.proto.label == "Unlock"
    assert admin_btn.proto.type == "primary"
    assert "⚠️" not in admin_btn.proto.label

    # 2. Generation gate button in Generate tab
    gen_gate_btn = at.button(key="gen_gen_unlock_button")
    assert gen_gate_btn is not None
    assert gen_gate_btn.proto.label == "Unlock generation"
    assert gen_gate_btn.proto.type == "primary"
    assert "⚠️" not in gen_gate_btn.proto.label

    # 3. Unlock generation and check Generate execution button
    at.text_input(key="gen_gen_passphrase_input").input(config.generation_passphrase)
    gen_gate_btn.click().run()
    assert not at.exception

    gen_submit_btn = at.button(key="gen_submit_button")
    assert gen_submit_btn is not None
    assert gen_submit_btn.proto.label == "Generate"
    assert gen_submit_btn.proto.type == "primary"
    assert "⚠️" not in gen_submit_btn.proto.label


def test_reingest_tab_gate_and_submit_buttons_are_primary(clean_storage):
    """Verify all buttons in Re-ingest tab have type='primary'."""
    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Generate / Re-ingest").run()

    # Switch to Re-ingest tab (first unlock generation so form controls render)
    at.text_input(key="gen_gen_passphrase_input").input(config.generation_passphrase)
    at.button(key="gen_gen_unlock_button").click().run()
    assert not at.exception

    # Admin gate button in Re-ingest tab
    admin_btn_r = at.button(key="reingest_admin_unlock_button")
    assert admin_btn_r is not None
    assert admin_btn_r.proto.label == "Unlock"
    assert admin_btn_r.proto.type == "primary"
    assert "⚠️" not in admin_btn_r.proto.label

    # Re-ingest submit button
    reingest_btn = at.button(key="reingest_submit_button")
    assert reingest_btn is not None
    assert reingest_btn.proto.label == "Re-ingest and recalculate"
    assert reingest_btn.proto.type == "primary"
    assert "⚠️" not in reingest_btn.proto.label


# ==============================================================================
# Manage Runs (manage_runs.py) Button Styling & Emoji Tests
# ==============================================================================

def test_manage_runs_passphrase_gate_and_lock_buttons_are_primary(clean_storage):
    """Verify 'Unlock Manage Runs' and 'Lock page' buttons have type='primary'."""
    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()

    # 1. Whole-page gate submit button
    unlock_gate_btn = at.button(key="manage_runs_unlock_button")
    assert unlock_gate_btn is not None
    assert unlock_gate_btn.proto.label == "Unlock Manage Runs"
    assert unlock_gate_btn.proto.type == "primary"
    assert "⚠️" not in unlock_gate_btn.proto.label

    # 2. Unlock page
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    unlock_gate_btn.click().run()
    assert not at.exception

    # 3. Lock page button
    lock_btn = at.button(key="manage_runs_lock_button")
    assert lock_btn is not None
    assert lock_btn.proto.label == "Lock page"
    assert lock_btn.proto.type == "primary"
    assert "⚠️" not in lock_btn.proto.label


def test_manage_runs_active_tab_archive_button_is_primary(clean_storage):
    """Verify 'Archive' button in Active Runs view has type='primary'."""
    run_id = _seed_sample_run(clean_storage, "Active Project")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()

    archive_btn = at.button(key=f"btn_archive_{run_id}")
    assert archive_btn is not None
    assert archive_btn.proto.label == "Archive"
    assert archive_btn.proto.type == "primary"
    assert "⚠️" not in archive_btn.proto.label


def test_manage_runs_archived_tab_buttons_styling_and_warning_emojis(clean_storage):
    """Verify all buttons in Archived Runs view have type='primary' and destructive buttons have ⚠️ emoji."""
    run_id = _seed_sample_run(clean_storage, "Archived Project")
    clean_storage.archive_run(run_id)

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.sidebar.radio(key="app_page_selector").set_value("Manage Runs").run()
    at.text_input(key="manage_runs_passphrase_input").input(config.admin_passphrase)
    at.button(key="manage_runs_unlock_button").click().run()

    # Switch to Archived view
    at.radio(key="manage_runs_view_tab").set_value("archived").run()

    # 1. Select All and Deselect All
    sel_all_btn = at.button(key="btn_select_all_archived")
    assert sel_all_btn is not None
    assert sel_all_btn.proto.label == "Select All"
    assert sel_all_btn.proto.type == "primary"
    assert "⚠️" not in sel_all_btn.proto.label

    desel_all_btn = at.button(key="btn_deselect_all_archived")
    assert desel_all_btn is not None
    assert desel_all_btn.proto.label == "Deselect All"
    assert desel_all_btn.proto.type == "primary"
    assert "⚠️" not in desel_all_btn.proto.label

    # 2. Unarchive button
    unarchive_btn = at.button(key=f"btn_unarchive_{run_id}")
    assert unarchive_btn is not None
    assert unarchive_btn.proto.label == "Unarchive"
    assert unarchive_btn.proto.type == "primary"
    assert "⚠️" not in unarchive_btn.proto.label

    # 3. Purge Selected button (destructive - must have warning emoji ⚠️ and type='primary')
    purge_btn = at.button(key="btn_bulk_purge_init")
    assert purge_btn is not None
    assert purge_btn.proto.label == "⚠️ Purge Selected (0)"
    assert purge_btn.proto.type == "primary"
    assert "⚠️" in purge_btn.proto.label

    # Select the run
    at.checkbox(key=f"chk_select_{run_id}").check().run()
    purge_btn_selected = at.button(key="btn_bulk_purge_init")
    assert purge_btn_selected.proto.label == "⚠️ Purge Selected (1)"
    assert purge_btn_selected.proto.type == "primary"

    # 4. Open 2-stage confirmation panel
    purge_btn_selected.click().run()
    assert not at.exception

    # 5. Confirm & Delete button (destructive - must have warning emoji ⚠️ and type='primary')
    confirm_btn = at.button(key="btn_bulk_purge_confirm")
    assert confirm_btn is not None
    assert confirm_btn.proto.label == "⚠️ Confirm & Delete 1 Runs"
    assert confirm_btn.proto.type == "primary"
    assert "⚠️" in confirm_btn.proto.label

    # 6. Cancel button (neutral - type='primary', no emoji)
    cancel_btn = at.button(key="btn_bulk_purge_cancel")
    assert cancel_btn is not None
    assert cancel_btn.proto.label == "Cancel"
    assert cancel_btn.proto.type == "primary"
    assert "⚠️" not in cancel_btn.proto.label
