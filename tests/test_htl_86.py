"""HTL-86: Gate Fact Review Trace JSON Downloads and Startup Kit Deliverable Option Behind Admin Passphrase.

Requirements:
1. Fact Review page: Per-deck trace JSON download is completely absent when locked, and present when unlocked.
2. Generate page: Checkbox order is Client Kickoff Deck, PS Governance Kickoff, Delivery Workbook, then Startup Kit last.
   Startup Kit checkbox is completely absent when locked, and present as the last option when unlocked.
3. Re-ingest tab: Identical checkbox reordering and conditional presence/absence for Startup Kit.
"""

from pathlib import Path
import time
from unittest.mock import patch
import pytest
from streamlit.testing.v1 import AppTest

from src.config import config
from src.core.models import ProjectStartupCharter, StartupKitBaseline
from src.core.outputs import OutputSelection, RunResult
from src.review_storage.local import LocalReviewStorage

APP_FILE = str(Path(__file__).parent.parent / "src" / "review_ui" / "app.py")


def _create_sample_run_with_files(storage: LocalReviewStorage) -> str:
    baseline = StartupKitBaseline(
        project_name="Cloud Modernization Initiative",
        charter=ProjectStartupCharter(client_name="Acme Corp"),
    )
    run_id = storage.create_run(
        project_name=baseline.project_name,
        baseline=baseline.model_dump(mode="json"),
        validation_report={},
    )
    storage.update_status(run_id, "approved", if_state="pending_review")
    storage.update_status(run_id, "generated", if_state="approved")

    run_dir = storage._run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    # Regular generated files
    (run_dir / "Acme_Client_Kickoff_Deck.pptx").write_bytes(b"pptx-data")
    (run_dir / "Acme_Delivery_Workbook.xlsx").write_bytes(b"xlsx-data")
    (run_dir / "Acme_PS_Governance_Kickoff.pptx").write_bytes(b"gov-pptx-data")

    # Per-deck trace JSON files
    (run_dir / "Acme_Client_Kickoff_Deck.trace.json").write_bytes(b'{"trace": "client"}')
    (run_dir / "Acme_Governance_Deck_trace.json").write_bytes(b'{"trace": "gov"}')
    (run_dir / "Acme_Deck_Trace_Manifest.json").write_bytes(b'{"trace": "manifest"}')

    return run_id


# =========================================================================
# 1. Fact Review Page: Trace JSON Downloads Gating
# =========================================================================

def test_fact_review_locked_state_hides_trace_json_downloads(tmp_path, monkeypatch):
    """HTL-86: On Fact Review, trace JSON downloads are completely absent when admin is locked."""
    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    run_id = _create_sample_run_with_files(storage)

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.radio(key="app_page_selector").set_value("Fact Review").run()
    at.selectbox(key="fact_review_run_selector").set_value(run_id).run()
    assert not at.exception

    # Download buttons for regular artifacts exist
    download_labels = [db.label for db in at.download_button]
    assert any("Acme_Client_Kickoff_Deck.pptx" in lbl for lbl in download_labels)
    assert any("Acme_Delivery_Workbook.xlsx" in lbl for lbl in download_labels)
    assert any("Acme_PS_Governance_Kickoff.pptx" in lbl for lbl in download_labels)

    # Download buttons for trace JSON files MUST BE COMPLETELY ABSENT
    assert not any(".trace.json" in lbl for lbl in download_labels)
    assert not any("_trace.json" in lbl for lbl in download_labels)
    assert not any("_Deck_Trace_Manifest.json" in lbl for lbl in download_labels)


def test_fact_review_unlocked_state_renders_trace_json_downloads(tmp_path, monkeypatch):
    """HTL-86: On Fact Review, unlocking with admin passphrase renders trace JSON downloads."""
    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    run_id = _create_sample_run_with_files(storage)

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.radio(key="app_page_selector").set_value("Fact Review").run()
    at.selectbox(key="fact_review_run_selector").set_value(run_id).run()
    assert not at.exception

    # Unlock Fact Review's admin gate
    at.text_input(key="fact_review_admin_passphrase_input").input(config.admin_passphrase).run()
    at.button(key="fact_review_admin_unlock_button").click().run()
    assert not at.exception
    assert at.session_state["fact_review_admin_unlocked"] is True

    # Download buttons for both regular artifacts and trace JSON files MUST exist
    download_labels = [db.label for db in at.download_button]
    assert any("Acme_Client_Kickoff_Deck.pptx" in lbl for lbl in download_labels)
    assert any("Acme_Delivery_Workbook.xlsx" in lbl for lbl in download_labels)
    assert any("Acme_PS_Governance_Kickoff.pptx" in lbl for lbl in download_labels)

    assert any("Acme_Client_Kickoff_Deck.trace.json" in lbl for lbl in download_labels)
    assert any("Acme_Governance_Deck_trace.json" in lbl for lbl in download_labels)
    assert any("Acme_Deck_Trace_Manifest.json" in lbl for lbl in download_labels)


def test_fact_review_wrong_passphrase_shows_error_and_remains_locked(tmp_path, monkeypatch):
    """HTL-86: Incorrect passphrase on Fact Review shows error and keeps trace files hidden."""
    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    run_id = _create_sample_run_with_files(storage)

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.radio(key="app_page_selector").set_value("Fact Review").run()
    at.selectbox(key="fact_review_run_selector").set_value(run_id).run()
    assert not at.exception

    at.text_input(key="fact_review_admin_passphrase_input").input("wrong-passphrase").run()
    at.button(key="fact_review_admin_unlock_button").click().run()
    assert not at.exception

    # Error message rendered
    assert any("Incorrect passphrase." in err.value for err in at.error)
    assert at.session_state.get("fact_review_admin_unlocked", False) is False

    # Trace files remain completely absent
    download_labels = [db.label for db in at.download_button]
    assert not any(".trace.json" in lbl for lbl in download_labels)


# =========================================================================
# 2. Generate Page: Checkbox Order and Startup Kit Gating
# =========================================================================

def test_generate_page_locked_state_checkbox_order_and_startup_kit_hidden():
    """HTL-86: On Generate page when locked, checkboxes are [Client Deck, PS Governance, Workbook]
    and Startup Kit is completely absent (not rendered)."""
    at = AppTest.from_file(APP_FILE, default_timeout=10)
    at.session_state["generation_unlocked"] = True
    at.session_state["generation_unlocked_at"] = time.time()
    at.run()
    assert not at.exception

    checkbox_keys = [cb.key for cb in at.checkbox if cb.key.startswith("gen_out_")]
    expected_order_locked = [
        "gen_out_client_deck",
        "gen_out_slides",
        "gen_out_workbook",
    ]
    assert checkbox_keys == expected_order_locked

    # Startup Kit checkbox is completely absent
    assert not any(cb.key == "gen_out_kit" for cb in at.checkbox)


def test_generate_page_unlocked_state_startup_kit_rendered_as_last_option():
    """HTL-86: On Generate page when unlocked, Startup Kit appears as the LAST checkbox option."""
    at = AppTest.from_file(APP_FILE, default_timeout=10)
    at.session_state["generation_unlocked"] = True
    at.session_state["generation_unlocked_at"] = time.time()
    at.run()
    assert not at.exception

    # Unlock admin gate on Generate tab
    at.text_input(key="gen_admin_passphrase_input").input(config.admin_passphrase).run()
    at.button(key="gen_admin_unlock_button").click().run()
    assert not at.exception
    assert at.session_state["gen_admin_unlocked"] is True

    checkbox_keys = [cb.key for cb in at.checkbox if cb.key.startswith("gen_out_")]
    expected_order_unlocked = [
        "gen_out_client_deck",
        "gen_out_slides",
        "gen_out_workbook",
        "gen_out_kit",
    ]
    assert checkbox_keys == expected_order_unlocked

    # Check Startup Kit defaults to False
    kit_cb = next(cb for cb in at.checkbox if cb.key == "gen_out_kit")
    assert kit_cb.value is False
    assert kit_cb.label == "Startup Kit"


# =========================================================================
# 3. Re-ingest Tab: Checkbox Order and Startup Kit Gating
# =========================================================================

def test_reingest_tab_locked_state_checkbox_order_and_startup_kit_hidden():
    """HTL-86: On Re-ingest tab when locked, checkboxes are [Client Deck, PS Governance, Workbook]
    and Startup Kit is completely absent (not rendered)."""
    at = AppTest.from_file(APP_FILE, default_timeout=10)
    at.session_state["generation_unlocked"] = True
    at.session_state["generation_unlocked_at"] = time.time()
    at.run()
    assert not at.exception

    reingest_checkbox_keys = [cb.key for cb in at.checkbox if cb.key.startswith("reingest_out_")]
    expected_order_locked = [
        "reingest_out_client_deck",
        "reingest_out_slides",
        "reingest_out_workbook",
    ]
    assert reingest_checkbox_keys == expected_order_locked
    assert not any(cb.key == "reingest_out_kit" for cb in at.checkbox)


def test_reingest_tab_unlocked_state_startup_kit_rendered_as_last_option():
    """HTL-86: On Re-ingest tab when unlocked, Startup Kit appears as the LAST checkbox option."""
    at = AppTest.from_file(APP_FILE, default_timeout=10)
    at.session_state["generation_unlocked"] = True
    at.session_state["generation_unlocked_at"] = time.time()
    at.run()
    assert not at.exception

    # Unlock admin gate on Re-ingest tab
    at.text_input(key="reingest_admin_passphrase_input").input(config.admin_passphrase).run()
    at.button(key="reingest_admin_unlock_button").click().run()
    assert not at.exception
    assert at.session_state["reingest_admin_unlocked"] is True

    reingest_checkbox_keys = [cb.key for cb in at.checkbox if cb.key.startswith("reingest_out_")]
    expected_order_unlocked = [
        "reingest_out_client_deck",
        "reingest_out_slides",
        "reingest_out_workbook",
        "reingest_out_kit",
    ]
    assert reingest_checkbox_keys == expected_order_unlocked

    kit_r = next(cb for cb in at.checkbox if cb.key == "reingest_out_kit")
    assert kit_r.value is False
    assert kit_r.label == "Startup Kit"
