"""HTL-46: Shared Generation Passphrase Gate Unit and Integration Tests."""

import os
from pathlib import Path
from src.config import AppConfig, config
from src.review_ui.generate import (
    DEFAULT_GENERATION_TTL_SECONDS,
    is_generation_session_unlocked,
    is_generation_unlocked,
    lock_generation_session,
    unlock_generation_session,
)

APP_FILE = str(Path(__file__).parent.parent / "src" / "review_ui" / "app.py")


def test_is_generation_unlocked_correct_passphrase():
    assert is_generation_unlocked("secret-passphrase", "secret-passphrase") is True


def test_is_generation_unlocked_wrong_passphrase():
    assert is_generation_unlocked("wrong-passphrase", "secret-passphrase") is False


def test_is_generation_unlocked_empty_entered_passphrase():
    assert is_generation_unlocked("", "secret-passphrase") is False


def test_is_generation_unlocked_empty_configured_passphrase():
    assert is_generation_unlocked("", "") is False
    assert is_generation_unlocked("secret-passphrase", "") is False


def test_is_generation_unlocked_exact_whitespace_matching():
    # Exact match semantics: no stripping
    assert is_generation_unlocked("secret ", "secret") is False
    assert is_generation_unlocked(" secret", "secret") is False


def test_fallback_passphrase_defaults_are_distinct():
    # Crucial security requirement: default fallback for GENERATION_PASSPHRASE must never
    # collide with ADMIN_PASSPHRASE's default fallback ("dev-only-change-me").
    default_config = AppConfig(
        admin_passphrase="dev-only-change-me",
        generation_passphrase="dev-generation-only-change-me",
    )
    assert default_config.generation_passphrase != default_config.admin_passphrase
    assert default_config.generation_passphrase == "dev-generation-only-change-me"
    assert default_config.admin_passphrase == "dev-only-change-me"


def test_is_generation_unlocked_against_real_configured_passphrase():
    assert is_generation_unlocked(config.generation_passphrase, config.generation_passphrase) is True
    assert is_generation_unlocked(config.generation_passphrase + "-wrong", config.generation_passphrase) is False


def test_generation_session_unlocked_lifecycle():
    from unittest.mock import patch

    mock_state = {}
    with patch("streamlit.session_state", mock_state):
        # Initial state: not unlocked
        assert is_generation_session_unlocked(now=1000.0) is False
        assert "generation_unlocked" not in mock_state

        # Unlock at t=1000
        unlock_generation_session(now=1000.0)
        assert mock_state["generation_unlocked"] is True
        assert mock_state["generation_unlocked_at"] == 1000.0

        # Check within TTL window (1000 + 1799 = 2799 <= 1800s)
        assert is_generation_session_unlocked(ttl_seconds=1800, now=2799.0) is True
        assert mock_state["generation_unlocked"] is True

        # Check at exact TTL limit (1000 + 1800 = 2800)
        assert is_generation_session_unlocked(ttl_seconds=1800, now=2800.0) is True

        # Check beyond TTL window (1000 + 1801 = 2801 > 1800s)
        assert is_generation_session_unlocked(ttl_seconds=1800, now=2801.0) is False
        assert "generation_unlocked" not in mock_state
        assert "generation_unlocked_at" not in mock_state


def test_generation_session_unlocked_invalid_or_future_timestamps():
    from unittest.mock import patch

    # 1. Invalid timestamp (non-numeric)
    mock_state = {"generation_unlocked": True, "generation_unlocked_at": "invalid"}
    with patch("streamlit.session_state", mock_state):
        assert is_generation_session_unlocked(now=1000.0) is False
        assert "generation_unlocked" not in mock_state
        assert "generation_unlocked_at" not in mock_state

    # 2. Missing timestamp but flag present
    mock_state = {"generation_unlocked": True}
    with patch("streamlit.session_state", mock_state):
        assert is_generation_session_unlocked(now=1000.0) is False
        assert "generation_unlocked" not in mock_state

    # 3. Future timestamp (clock skew)
    mock_state = {"generation_unlocked": True, "generation_unlocked_at": 2000.0}
    with patch("streamlit.session_state", mock_state):
        assert is_generation_session_unlocked(now=1000.0) is False
        assert "generation_unlocked" not in mock_state
        assert "generation_unlocked_at" not in mock_state


def test_lock_generation_session():
    from unittest.mock import patch

    mock_state = {"generation_unlocked": True, "generation_unlocked_at": 1000.0}
    with patch("streamlit.session_state", mock_state):
        lock_generation_session()
        assert "generation_unlocked" not in mock_state
        assert "generation_unlocked_at" not in mock_state


def test_generate_page_locked_state_hides_widgets():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    assert not at.exception
    # When generation is locked:
    # 1. File uploader is completely hidden
    assert len(at.file_uploader) == 0
    # 2. Submit button is completely hidden
    assert len([b for b in at.button if b.key == "gen_submit_button"]) == 0
    # 3. Generation gate is wrapped in a collapsed expander labeled "Generation access"
    gen_expanders = [e for e in at.expander if e.label == "Generation access"]
    assert len(gen_expanders) >= 1
    assert not gen_expanders[0].proto.expanded
    # 4. Generation gate input and unlock button are rendered inside the expander
    assert at.text_input(key="gen_gen_passphrase_input") is not None
    assert at.button(key="gen_gen_unlock_button") is not None


def test_generate_page_wrong_passphrase_displays_error():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.text_input(key="gen_gen_passphrase_input").input("wrong-guess").run()
    at.button(key="gen_gen_unlock_button").click().run()

    assert not at.exception
    assert any("Incorrect generation passphrase." in err.value for err in at.error)
    assert len(at.file_uploader) == 0
    assert at.session_state.get("generation_unlocked") is not True


def test_generate_page_correct_passphrase_unlocks_widgets():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.text_input(key="gen_gen_passphrase_input").input(config.generation_passphrase).run()
    at.button(key="gen_gen_unlock_button").click().run()

    assert not at.exception
    assert at.session_state["generation_unlocked"] is True
    assert at.file_uploader(key="gen_uploader") is not None
    assert at.button(key="gen_submit_button") is not None
    assert any("Generation unlocked for this session." in c.value for c in at.caption)


def test_reingest_tab_locked_and_unlocked_states():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    # When generation is locked:
    # 1. Re-ingest uploader is completely hidden
    assert len([u for u in at.file_uploader if u.key == "reingest_file"]) == 0
    # 2. Re-ingest tab has collapsed "Generation access" expander
    reingest_expanders = [e for e in at.expander if e.label == "Generation access"]
    assert len(reingest_expanders) >= 1
    assert not reingest_expanders[0].proto.expanded
    assert at.text_input(key="reingest_gen_passphrase_input") is not None
    assert at.button(key="reingest_gen_unlock_button") is not None

    # Unlock via reingest tab gate
    at.text_input(key="reingest_gen_passphrase_input").input(config.generation_passphrase).run()
    at.button(key="reingest_gen_unlock_button").click().run()

    assert not at.exception
    assert at.session_state["generation_unlocked"] is True
    assert at.file_uploader(key="reingest_file") is not None
    assert at.button(key="reingest_submit_button") is not None


def test_admin_and_generation_gates_are_independent():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()

    # Unlock admin gate
    at.text_input(key="gen_admin_passphrase_input").input(config.admin_passphrase).run()
    at.button(key="gen_admin_unlock_button").click().run()

    assert at.session_state["gen_admin_unlocked"] is True
    # Generation gate is still locked
    assert at.session_state.get("generation_unlocked") is not True
    assert len(at.file_uploader) == 0

    # Now unlock generation gate
    at.text_input(key="gen_gen_passphrase_input").input(config.generation_passphrase).run()
    at.button(key="gen_gen_unlock_button").click().run()

    assert at.session_state["generation_unlocked"] is True
    assert at.file_uploader(key="gen_uploader") is not None


def test_fact_review_pending_run_workflows_are_ungated(tmp_path, monkeypatch):
    """HTL-46: Fact Review browsing, fact inspection, field corrections, and run approvals
    remain ungated even when generation is locked."""
    from datetime import date
    from streamlit.testing.v1 import AppTest
    from src.core.models import ProjectStartupCharter, StartupKitBaseline
    from src.review_storage.local import LocalReviewStorage

    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    baseline = StartupKitBaseline(
        project_name="Pending Ungated Project",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 11, 1),
        charter=ProjectStartupCharter(client_name="Test Corp"),
    )
    run_id = storage.create_run(
        project_name="Pending Ungated Project",
        baseline=baseline.model_dump(mode="json"),
        validation_report={"findings": []},
    )

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.radio(key="app_page_selector").set_value("Fact Review").run()

    # Select the run
    at.selectbox(key="fact_review_run_selector").set_value(run_id).run()
    assert not at.exception

    # Fact review workflows are completely accessible while generation is locked
    assert at.session_state.get("generation_unlocked") is not True
    assert at.button(key="fact_review_save_button") is not None
    assert at.button(key="fact_review_approve_button") is not None


def test_fact_review_approved_run_is_gated(tmp_path, monkeypatch):
    """HTL-46: On an approved run, 'Generate documents' is hidden behind the generation gate until unlocked."""
    from datetime import date
    from streamlit.testing.v1 import AppTest
    from src.core.models import ProjectStartupCharter, StartupKitBaseline
    from src.review_storage.local import LocalReviewStorage

    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    baseline = StartupKitBaseline(
        project_name="Approved Gated Project",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 11, 1),
        charter=ProjectStartupCharter(client_name="Test Corp"),
    )
    run_id = storage.create_run(
        project_name="Approved Gated Project",
        baseline=baseline.model_dump(mode="json"),
        validation_report={"findings": []},
    )
    storage.update_status(run_id, "approved", if_state="pending_review")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.radio(key="app_page_selector").set_value("Fact Review").run()
    at.selectbox(key="fact_review_run_selector").set_value(run_id).run()
    assert not at.exception

    # 1. Locked state: "Generate documents" button is hidden, generation gate is rendered in collapsed expander
    assert len([b for b in at.button if b.key == "fact_review_generate_button"]) == 0
    fr_expanders = [e for e in at.expander if e.label == "Generation access"]
    assert len(fr_expanders) == 1
    assert not fr_expanders[0].proto.expanded
    gate_input_key = f"fact_review_{run_id}_gen_passphrase_input"
    gate_unlock_key = f"fact_review_{run_id}_gen_unlock_button"
    assert at.text_input(key=gate_input_key) is not None
    assert at.button(key=gate_unlock_key) is not None

    # 2. Wrong passphrase: error displayed, remains locked
    at.text_input(key=gate_input_key).input("wrong-passphrase").run()
    at.button(key=gate_unlock_key).click().run()
    assert any("Incorrect generation passphrase." in err.value for err in at.error)
    assert len([b for b in at.button if b.key == "fact_review_generate_button"]) == 0

    # 3. Correct passphrase: unlocks generation and reveals "Generate documents" button
    at.text_input(key=gate_input_key).input(config.generation_passphrase).run()
    at.button(key=gate_unlock_key).click().run()
    assert at.session_state["generation_unlocked"] is True
    assert at.button(key="fact_review_generate_button") is not None


def test_cross_page_session_state_persistence_generate_to_review(tmp_path, monkeypatch):
    """HTL-46: Unlocking generation on Generate immediately unlocks Fact Review for approved runs."""
    from datetime import date
    from streamlit.testing.v1 import AppTest
    from src.core.models import ProjectStartupCharter, StartupKitBaseline
    from src.review_storage.local import LocalReviewStorage

    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    baseline = StartupKitBaseline(
        project_name="Cross Page Project",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 11, 1),
        charter=ProjectStartupCharter(client_name="Test Corp"),
    )
    run_id = storage.create_run(
        project_name="Cross Page Project",
        baseline=baseline.model_dump(mode="json"),
        validation_report={"findings": []},
    )
    storage.update_status(run_id, "approved", if_state="pending_review")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()

    # Unlock on Generate tab
    at.text_input(key="gen_gen_passphrase_input").input(config.generation_passphrase).run()
    at.button(key="gen_gen_unlock_button").click().run()
    assert at.session_state["generation_unlocked"] is True

    # Navigate to Fact Review
    at.radio(key="app_page_selector").set_value("Fact Review").run()
    at.selectbox(key="fact_review_run_selector").set_value(run_id).run()
    assert not at.exception

    # Immediately unlocked without re-prompting
    assert at.button(key="fact_review_generate_button") is not None
    assert len([b for b in at.button if b.key == f"fact_review_{run_id}_gen_unlock_button"]) == 0


def test_cross_page_session_state_persistence_review_to_generate(tmp_path, monkeypatch):
    """HTL-46: Unlocking generation on Fact Review immediately unlocks Generate tab without re-prompting."""
    from datetime import date
    from streamlit.testing.v1 import AppTest
    from src.core.models import ProjectStartupCharter, StartupKitBaseline
    from src.review_storage.local import LocalReviewStorage

    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    baseline = StartupKitBaseline(
        project_name="Review To Gen Project",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 11, 1),
        charter=ProjectStartupCharter(client_name="Test Corp"),
    )
    run_id = storage.create_run(
        project_name="Review To Gen Project",
        baseline=baseline.model_dump(mode="json"),
        validation_report={"findings": []},
    )
    storage.update_status(run_id, "approved", if_state="pending_review")

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()

    # Navigate to Fact Review and unlock
    at.radio(key="app_page_selector").set_value("Fact Review").run()
    at.selectbox(key="fact_review_run_selector").set_value(run_id).run()

    gate_input_key = f"fact_review_{run_id}_gen_passphrase_input"
    gate_unlock_key = f"fact_review_{run_id}_gen_unlock_button"
    at.text_input(key=gate_input_key).input(config.generation_passphrase).run()
    at.button(key=gate_unlock_key).click().run()
    assert at.session_state["generation_unlocked"] is True

    # Navigate back to Generate
    at.radio(key="app_page_selector").set_value("Generate / Re-ingest").run()
    assert not at.exception

    # Immediately unlocked without re-prompting
    assert at.file_uploader(key="gen_uploader") is not None
    assert at.button(key="gen_submit_button") is not None
    assert len([b for b in at.button if b.key == "gen_gen_unlock_button"]) == 0


def test_direct_fact_review_landing_fresh_session_is_gated(tmp_path, monkeypatch):
    """HTL-46: A fresh session navigating directly to Fact Review on an approved run
    without visiting Generate is strictly gated."""
    from datetime import date
    from streamlit.testing.v1 import AppTest
    from src.core.models import ProjectStartupCharter, StartupKitBaseline
    from src.review_storage.local import LocalReviewStorage

    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    baseline = StartupKitBaseline(
        project_name="Direct Landing Gated Project",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 11, 1),
        charter=ProjectStartupCharter(client_name="Direct Corp"),
    )
    run_id = storage.create_run(
        project_name="Direct Landing Gated Project",
        baseline=baseline.model_dump(mode="json"),
        validation_report={"findings": []},
    )
    storage.update_status(run_id, "approved", if_state="pending_review")

    # Brand new AppTest instance without any prior state
    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.radio(key="app_page_selector").set_value("Fact Review").run()
    at.selectbox(key="fact_review_run_selector").set_value(run_id).run()
    assert not at.exception

    # Confirm strictly locked and gate rendered inside collapsed expander
    assert at.session_state.get("generation_unlocked") is not True
    assert len([b for b in at.button if b.key == "fact_review_generate_button"]) == 0
    fr_expanders = [e for e in at.expander if e.label == "Generation access"]
    assert len(fr_expanders) == 1
    assert not fr_expanders[0].proto.expanded
    assert at.text_input(key=f"fact_review_{run_id}_gen_passphrase_input") is not None
    assert at.button(key=f"fact_review_{run_id}_gen_unlock_button") is not None


def test_generation_gate_expander_collapsed_by_default_across_all_surfaces(tmp_path, monkeypatch):
    """HTL-46: Generation gate locked-state content is wrapped in st.expander('Generation access', expanded=False)
    across the Generate tab, Re-ingest tab, and Fact Review page for approved runs."""
    from datetime import date
    from streamlit.testing.v1 import AppTest
    from src.core.models import ProjectStartupCharter, StartupKitBaseline
    from src.review_storage.local import LocalReviewStorage

    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    baseline = StartupKitBaseline(
        project_name="Expander Test Project",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 11, 1),
        charter=ProjectStartupCharter(client_name="Expander Corp"),
    )
    run_id = storage.create_run(
        project_name="Expander Test Project",
        baseline=baseline.model_dump(mode="json"),
        validation_report={"findings": []},
    )
    storage.update_status(run_id, "approved", if_state="pending_review")

    # 1. Generate tab & Re-ingest tab
    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    gen_expanders = [e for e in at.expander if e.label == "Generation access"]
    # Two generation access expanders rendered on Generate/Re-ingest page (one per tab)
    assert len(gen_expanders) == 2
    for exp in gen_expanders:
        assert not exp.proto.expanded

    # 2. Fact Review page (approved run)
    at.radio(key="app_page_selector").set_value("Fact Review").run()
    at.selectbox(key="fact_review_run_selector").set_value(run_id).run()
    fr_expanders = [e for e in at.expander if e.label == "Generation access"]
    assert len(fr_expanders) == 1
    assert not fr_expanders[0].proto.expanded
