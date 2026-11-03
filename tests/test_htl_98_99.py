"""Regression tests for HTL-98 and HTL-99.

HTL-98: Removal of Purchase Order references from generated acceptance narratives and artifacts.
HTL-99: Removal of fabricated SLAs ('3 business days') and contradictory weekly status report acceptance loops.
"""

import re
import pptx
import pytest
from src.core.models import StartupKitBaseline
from src.generators.governance_deck import export_governance_deck, build_governance_deck_model
from src.generators.governance_deck.builder import (
    _sanitize_acceptance_narrative,
    build_slide16_model,
)
from tests.deck_bundle import load_baseline
from tests.test_htl_62 import _build_pge_baseline, PGE_ACCEPTANCE_PROCESS_NARRATIVE


def test_htl_98_no_purchase_order_references_in_governance_slide16_pge(tmp_path):
    """HTL-98: Asserts zero Purchase Order references in PGE Governance Deck Slide 16."""
    baseline = _build_pge_baseline()
    res = export_governance_deck(baseline, tmp_path / "pge_gov")
    prs = pptx.Presentation(str(res.file_path))

    slide16 = next(
        s for s in prs.slides
        if any(shape.has_text_frame and "How milestone acceptance works" in shape.text_frame.text for shape in s.shapes)
    )

    all_text = " ".join(s.text_frame.text for s in slide16.shapes if s.has_text_frame)

    # Must contain zero purchase order references
    assert not re.search(r'\b(?:purchase order|P\.O\.)\b', all_text, re.IGNORECASE), (
        f"Found Purchase Order reference in Slide 16 text: {all_text}"
    )

    # Verify Card 1 exact text alignment with approved correction
    card1_shapes = [s for s in slide16.shapes if s.has_text_frame and "Inputs ready:" in s.text_frame.text]
    assert len(card1_shapes) == 1
    c1_text = card1_shapes[0].text_frame.text

    assert "Confirm that environment read access, discovery tooling access, spend data and SME availability are in place before Day 1." in c1_text
    assert "Confirm Client has issued the Purchase Order" not in c1_text


def test_htl_99_no_contradictory_weekly_status_acceptance_and_no_3_day_fabrication(tmp_path):
    """HTL-99: Asserts absence of fabricated 3-day turnaround and contradictory weekly status acceptance loop."""
    baseline = _build_pge_baseline()
    res = export_governance_deck(baseline, tmp_path / "pge_gov_htl99")
    prs = pptx.Presentation(str(res.file_path))

    slide16 = next(
        s for s in prs.slides
        if any(shape.has_text_frame and "How milestone acceptance works" in shape.text_frame.text for shape in s.shapes)
    )

    all_text = " ".join(s.text_frame.text for s in slide16.shapes if s.has_text_frame)

    # 1. No fabricated 3 business days decision turnaround
    assert "within 3 business days" not in all_text
    assert "Client decision turnaround on review items is assumed to be within 3 business days" not in all_text

    # 2. No contradictory weekly status report acceptance loop
    assert "Send the weekly status report and ask Client Contact Alicia Cook to confirm acceptance" not in all_text
    assert "confirm acceptance or give feedback on each one" not in all_text

    # 3. Proper weekly status progress tracking & contractual 5-day acceptance period preserved
    assert "Weekly status reports track delivery progress and keep Client Contact informed." in all_text
    assert "Alicia Cook" not in all_text
    assert "The 5-business-day Milestone Acceptance Period starts from the date of that notice" in all_text
    assert "Client has 5 business days from the completion notice to evaluate the Work Output" in all_text


def test_htl_98_99_arc_governance_slide16_cleanliness(tmp_path):
    """HTL-98 / HTL-99: Verifies ARC baseline Slide 16 is free of PO references and fabricated SLAs."""
    baseline = load_baseline("arc_application_implementation")
    res = export_governance_deck(baseline, tmp_path / "arc_gov")
    prs = pptx.Presentation(str(res.file_path))

    slide16 = next(
        s for s in prs.slides
        if any(shape.has_text_frame and "How milestone acceptance works" in shape.text_frame.text for shape in s.shapes)
    )

    all_text = " ".join(s.text_frame.text for s in slide16.shapes if s.has_text_frame)

    assert not re.search(r'\b(?:purchase order|P\.O\.)\b', all_text, re.IGNORECASE)
    assert "Client decision turnaround on review items is assumed" not in all_text
    assert "10 business days" in all_text
    assert "Mike Magwire" not in all_text
    assert "Client Approver" in all_text


def test_htl_98_99_defensive_sanitizer_removes_po_and_slas_from_raw_llm_string():
    """HTL-98 / HTL-99: Tests that _sanitize_acceptance_narrative removes administrative boilerplate
    (Purchase Orders, NDAs, invoicing setup) and fabricated turnaround assumptions."""
    raw_dirty_narrative = (
        "Inputs ready: Confirm Client has issued the Purchase Order before work starts, and that environment read access is ready. "
        "Confirm NDA and invoicing setup are complete before kickoff. "
        "Client decision turnaround on review items is assumed to be within 3 business days.\n"
        "Execution: Deliver all work items. Send the weekly status report and ask Client Contact Alicia Cook to confirm acceptance or give feedback on each one.\n"
        "Submission: Work starts only after the client issues a Purchase Order. Give formal completion notice.\n"
        "Review: Review within 5 business days."
    )

    cleaned = _sanitize_acceptance_narrative(raw_dirty_narrative)

    assert "Purchase Order" not in cleaned
    assert "P.O." not in cleaned
    assert "NDA" not in cleaned
    assert "invoicing setup" not in cleaned
    assert "within 3 business days" not in cleaned
    assert "confirm acceptance or give feedback on each one" not in cleaned

    assert "Inputs ready: Confirm that environment read access is ready." in cleaned
    assert "Weekly status reports track delivery progress and keep Client Contact informed." in cleaned
    assert "Alicia Cook" not in cleaned
    assert "Submission: Give formal completion notice." in cleaned
    assert "Review: Review within 5 business days." in cleaned


def test_htl_98_99_tier2_fallback_cleanliness():
    """HTL-98 / HTL-99: Verifies Tier 2 fallback generates clean structured cards with zero PO or fabricated timelines."""
    baseline = _build_pge_baseline()
    baseline.sow_interpretation.acceptance_process_narrative = None

    model = build_slide16_model(baseline)
    assert model.tier == "Tier 2"

    for card in model.cards:
        for label, body in card.steps:
            full_step = f"{label or ''} {body}"
            assert not re.search(r'\b(?:purchase order|P\.O\.)\b', full_step, re.IGNORECASE)
            assert "within 3 business days" not in full_step
            assert "confirm acceptance or give feedback on each one" not in full_step
