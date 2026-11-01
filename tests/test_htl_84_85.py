"""Regression tests for HTL-84 and HTL-85.

HTL-84: Fact Review title-length warning renders via Streamlit AppTest for real PGE baseline (>60 characters).
HTL-85: Client Kickoff Deck Slide 1 renders unconditionally at flat 24pt for real PGE baseline without dynamic font-stepping.
"""

from pathlib import Path
import pptx
import pytest
from streamlit.testing.v1 import AppTest

from src.core.models import ProjectStartupCharter, StartupKitBaseline
from src.generators.client_deck import build_client_deck_model, export_client_deck, write_client_deck
from src.generators.governance_deck import export_governance_deck
from src.review_storage.local import LocalReviewStorage
from tests.deck_bundle import load_baseline
from tests.test_htl_62 import _build_pge_baseline

APP_FILE = str(Path(__file__).parent.parent / "src" / "review_ui" / "app.py")


def test_htl_84_fact_review_warning_renders_for_real_pge_apptest(tmp_path, monkeypatch):
    """HTL-84: Fact Review title-length warning actually renders for real PGE baseline (98 combined chars > 60 chars)."""
    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    pge_baseline = _build_pge_baseline()
    client_name = pge_baseline.charter.client_name  # "Portland General Electric Company" (33 chars)
    project_name = pge_baseline.project_name        # "Cloud Migration Assessment – Operational Compliance Program (OCP)" (65 chars)
    combined_len = len(client_name.strip()) + len(project_name.strip())
    assert combined_len == 98
    assert combined_len > 60

    run_id = storage.create_run(
        project_name=pge_baseline.project_name,
        baseline=pge_baseline.model_dump(mode="json"),
        validation_report={},
    )

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.radio(key="app_page_selector").set_value("Fact Review").run()
    assert not at.exception

    # Select the PGE run
    selector = at.selectbox(key="fact_review_run_selector")
    if selector.value != run_id:
        at.selectbox(key="fact_review_run_selector").set_value(run_id).run()
    assert not at.exception

    # Confirm the category-level warning renders
    warning_texts = [w.value for w in at.warning]
    expected_notice = (
        f"Slide 1 title length notice: Combined Client Name and Project Name length ({combined_len} chars) "
        "exceeds 60 characters and risks Slide 1 title wrapping or overflow in kickoff presentations. "
        "Consider shortening the Project Name or Client Name using the fields below."
    )
    assert any(expected_notice in w for w in warning_texts), f"Expected warning not found in at.warning: {warning_texts}"

    # Confirm the field-level caption warning renders
    caption_texts = [c.value for c in at.caption]
    expected_caption = (
        f"⚠️ Combined Client & Project Name length ({combined_len} chars) exceeds 60 characters and risks Slide 1 title overflow. "
        "Consider shortening one or both names."
    )
    assert any(expected_caption in c for c in caption_texts), f"Expected caption not found in at.caption: {caption_texts}"


def test_htl_84_fact_review_warning_dynamic_edit_lifecycle(tmp_path, monkeypatch):
    """HTL-84: Fact Review warning dynamically responds to field edits in session state."""
    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    pge_baseline = _build_pge_baseline()
    run_id = storage.create_run(
        project_name=pge_baseline.project_name,
        baseline=pge_baseline.model_dump(mode="json"),
        validation_report={},
    )

    at = AppTest.from_file(APP_FILE, default_timeout=10).run()
    at.radio(key="app_page_selector").set_value("Fact Review").run()
    at.selectbox(key="fact_review_run_selector").set_value(run_id).run()
    assert not at.exception

    # Initially warning is displayed
    assert any("Slide 1 title length notice: Combined Client Name and Project Name length (98 chars)" in w.value for w in at.warning)

    # Edit project name to a short name: "OCP Cloud Assessment" (20 chars) -> combined = 33 + 20 = 53 <= 60
    proj_input_key = f"fact_review::{run_id}::edit::project_identity.project_name"
    proj_input = next(ti for ti in at.text_input if ti.key == proj_input_key)
    proj_input.input("OCP Cloud Assessment").run()
    assert not at.exception

    # Warning should now disappear
    assert not any("Slide 1 title length notice:" in w.value for w in at.warning)
    assert not any("⚠️ Combined Client & Project Name length" in c.value for c in at.caption)

    # Edit back to long name: "Cloud Migration Assessment – Operational Compliance Program (OCP) - Full Scope" (78 chars) -> combined = 111 > 60
    proj_input = next(ti for ti in at.text_input if ti.key == proj_input_key)
    proj_input.input("Cloud Migration Assessment – Operational Compliance Program (OCP) - Full Scope").run()
    assert not at.exception

    # Warning should reappear with updated length (111 chars)
    assert any("Combined Client Name and Project Name length (111 chars) exceeds 60 characters" in w.value for w in at.warning)


def test_htl_85_client_kickoff_deck_slide1_renders_flat_24pt_for_pge(tmp_path):
    """HTL-85: Client Kickoff Deck Slide 1 renders unconditionally at flat 24pt for real long PGE name, matching Governance Deck."""
    pge_baseline = _build_pge_baseline()

    # 1. Export Client Kickoff Deck
    client_res = export_client_deck(pge_baseline, tmp_path / "client_deck")
    assert client_res.file_path.exists()

    prs_client = pptx.Presentation(str(client_res.file_path))
    slide1_client = prs_client.slides[0]

    # Find Slide 1 Title shape
    title_shape = next(
        s for s in slide1_client.shapes
        if s.has_text_frame and ("Portland General Electric Company" in s.text_frame.text or s.shape_id == 92)
    )

    # Verify font size is flat 24pt (304800 EMUs), NOT stepped down to 14pt
    for p in title_shape.text_frame.paragraphs:
        for r in p.runs:
            assert r.font.size.pt == 24.0, f"Expected 24.0pt font size, got {r.font.size.pt}"
            assert r.font.size == 304800, f"Expected 304800 EMUs, got {r.font.size}"

    # 2. Export Governance Deck and confirm exact 24pt match
    gov_res = export_governance_deck(pge_baseline, tmp_path / "gov_deck")
    prs_gov = pptx.Presentation(str(gov_res.file_path))
    slide1_gov = prs_gov.slides[0]
    gov_title_shape = next(
        s for s in slide1_gov.shapes
        if s.has_text_frame and ("Portland General Electric Company" in s.text_frame.text or s.shape_id == 93)
    )
    for p in gov_title_shape.text_frame.paragraphs:
        for r in p.runs:
            assert r.font.size.pt == 24.0
            assert r.font.size == 304800


def test_htl_85_client_kickoff_deck_slide1_renders_flat_24pt_for_arc_genomics(tmp_path):
    """HTL-85: Client Kickoff Deck Slide 1 renders at flat 24pt across diverse baselines."""
    arc_baseline = load_baseline("arc_application_implementation")

    client_res = export_client_deck(arc_baseline, tmp_path / "arc_client_deck")
    prs_client = pptx.Presentation(str(client_res.file_path))
    slide1_client = prs_client.slides[0]

    title_shape = next(
        s for s in slide1_client.shapes
        if s.has_text_frame and ("Syngenta" in s.text_frame.text or s.shape_id == 92)
    )

    for p in title_shape.text_frame.paragraphs:
        for r in p.runs:
            assert r.font.size.pt == 24.0
            assert r.font.size == 304800
