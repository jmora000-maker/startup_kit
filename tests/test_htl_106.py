"""Regression tests for HTL-106: Validation-based fact verification for Slide 16 acceptance narrative.

Ensures that:
1. Day-counts and timeframes in synthesized acceptance narratives are strictly validated
   against real extracted baseline facts.
2. Fabricated timelines (e.g. PGE 'Decisions: Client answers review-item decision requests within 3 business days')
   are stripped/dropped.
3. Real contractual timelines (e.g. PGE 5-business-day review, ARC 10-business-day review, 30-day warranty)
   are preserved.
"""

import re
import pptx
import pytest
from src.core.models import StartupKitBaseline
from src.generators.governance_deck import export_governance_deck, build_governance_deck_model
from src.generators.governance_deck.builder import (
    _extract_allowed_numeric_facts,
    _sanitize_acceptance_narrative,
    build_slide16_model,
)
from tests.deck_bundle import load_baseline
from tests.test_htl_62 import _build_pge_baseline, PGE_ACCEPTANCE_PROCESS_NARRATIVE


def test_htl_106_numeric_fact_extraction():
    """HTL-106: Verifies _extract_allowed_numeric_facts compiles ground-truth numbers strictly from baseline data."""
    # 1. PGE baseline (5 business days review, 3 repeated remediation attempts)
    pge = _build_pge_baseline()
    pge.deliverables[0].rejection_rework_path = "Up to 3 repeated remediation attempts upon written notice."
    pge_facts = _extract_allowed_numeric_facts(pge)
    assert 5 in pge_facts["milestone_acceptance_period_days"]
    assert 5 in pge_facts["day_counts"]
    assert 3 not in pge_facts["day_counts"]  # 3 is an attempt count, not a review day count
    assert 3 in pge_facts["attempt_counts"]

    # 2. ARC baseline (10 business days Milestone Acceptance Period, 5 business days dispute escalation, 30-day warranty)
    arc = load_baseline("arc_application_implementation")
    arc_facts = _extract_allowed_numeric_facts(arc)
    assert arc_facts["milestone_acceptance_period_days"] == {10}
    assert arc_facts["dispute_escalation_days"] == {5}
    assert 30 in arc_facts["operational_warranty_days"]
    assert 10 in arc_facts["day_counts"]
    assert 5 in arc_facts["day_counts"]
    assert 30 in arc_facts["day_counts"]
    assert 7 not in arc_facts["day_counts"]


def test_htl_106_distinguish_milestone_acceptance_period_from_dispute_and_warranty():
    """HTL-106: Regression test ensuring Milestone Acceptance Period is specifically distinguished from
    dispute escalation sub-steps and operational warranty periods within the same baseline."""
    arc = load_baseline("arc_application_implementation")
    facts = _extract_allowed_numeric_facts(arc)

    # Core defined term: Milestone Acceptance Period must be 10 days, not 5 (dispute) or 30 (warranty)
    assert facts["milestone_acceptance_period_days"] == {10}, (
        f"Expected Milestone Acceptance Period to be exactly {{10}}, got {facts['milestone_acceptance_period_days']}"
    )
    assert facts["dispute_escalation_days"] == {5}, (
        f"Expected dispute escalation sub-step to be {{5}}, got {facts['dispute_escalation_days']}"
    )
    assert 30 in facts["operational_warranty_days"], (
        f"Expected 30-day operational warranty to be tracked, got {facts['operational_warranty_days']}"
    )

    # Verify ARC narrative retains 10-day review and 30-day warranty without stripping
    arc_narrative = (
        "**Review:** Client has 10 business days from the completion notice to evaluate, review, and test the Work Output.\n"
        "**Deliverable-specific rules:** Hypercare requires 30-day operational stability and warranty support.\n"
        "**Deemed accepted:** If Client provides no written notice of failure within the 10-business-day window, milestone is deemed accepted.\n"
        "**Exceptions:** Escalation follows Level 1 dispute protocols within 5 business days."
    )
    cleaned = _sanitize_acceptance_narrative(arc_narrative, baseline=arc)
    assert "10 business days" in cleaned
    assert "30-day operational stability" in cleaned
    assert "10-business-day window" in cleaned
    assert "5 business days" in cleaned


def test_htl_106_pge_fabricated_decisions_step_stripped():
    """HTL-106: Tests that fabricated 'Decisions: Client answers review-item decision requests within 3 business days'
    is stripped when checked against the real PGE baseline."""
    pge = _build_pge_baseline()

    fabricated_narrative = (
        "Inputs ready: Confirm that environment read access, discovery tooling access, spend data and SME availability are in place before Day 1.\n"
        "Execution: Deliver all six Work Output items as Milestone 1, targeting November 18, 2026.\n"
        "Submission: Give formal notice that Milestone 1 is complete. The 5-business-day Milestone Acceptance Period starts from notice date.\n"
        "Review: Client has 5 business days from the completion notice to evaluate the Work Output against specifications.\n"
        "Decisions: Client answers review-item decision requests within 3 business days.\n"
        "Deemed accepted: If Client gives no written notice of failure within 5 business days, Milestone 1 is deemed accepted.\n"
        "Rework limit: If Supplier cannot remedy after 3 repeated attempts, Client may terminate the SOW."
    )

    cleaned = _sanitize_acceptance_narrative(fabricated_narrative, baseline=pge)

    # Fabricated 3-day step must be completely removed
    assert "Decisions:" not in cleaned
    assert "within 3 business days" not in cleaned
    assert "review-item decision requests" not in cleaned

    # Real 5-day and 3-attempt steps must be fully preserved
    assert "Inputs ready: Confirm that environment read access" in cleaned
    assert "Submission: Give formal notice that Milestone 1 is complete" in cleaned
    assert "Review: Client has 5 business days from the completion notice" in cleaned
    assert "Deemed accepted: If Client gives no written notice of failure within 5 business days" in cleaned
    assert "Rework limit: If Supplier cannot remedy after 3 repeated attempts" in cleaned


def test_htl_106_conservative_sentence_level_stripping():
    """HTL-106: Tests that ungrounded clauses are stripped while preserving grounded sentences in the same step."""
    pge = _build_pge_baseline()

    # Step has one grounded sentence (5 business days) and one fabricated sentence (4 business days)
    mixed_step = (
        "Review: Client conducts formal review within 5 business days of submission. "
        "Interim feedback turnaround is required within 4 business days."
    )

    cleaned = _sanitize_acceptance_narrative(mixed_step, baseline=pge)

    assert "Review: Client conducts formal review within 5 business days of submission." in cleaned
    assert "4 business days" not in cleaned
    assert "Interim feedback" not in cleaned


def test_htl_106_governance_deck_slide16_pge_full_export(tmp_path):
    """HTL-106: Verifies exported PPTX presentation has zero fabricated timelines on Slide 16."""
    pge = _build_pge_baseline()
    pge.sow_interpretation.acceptance_process_narrative = (
        PGE_ACCEPTANCE_PROCESS_NARRATIVE + "\nDecisions: Client answers review-item decision requests within 3 business days."
    )

    res = export_governance_deck(pge, tmp_path / "pge_htl106")
    prs = pptx.Presentation(str(res.file_path))

    slide16 = next(
        s for s in prs.slides
        if any(shape.has_text_frame and "How milestone acceptance works" in shape.text_frame.text for shape in s.shapes)
    )

    all_text = " ".join(s.text_frame.text for s in slide16.shapes if s.has_text_frame)

    assert "within 3 business days" not in all_text
    assert "Decisions:" not in all_text
    assert "5 business days" in all_text
    assert "3 repeated attempts" in all_text


def test_htl_106_category_aware_validation_catches_cross_category_conflation():
    """HTL-106: Regression test proving category-aware validation catches cross-category number conflation.
    
    In ARC, dispute escalation is 5 business days and Milestone Acceptance Period is 10 business days.
    Under the old flattened union ({5, 10, 30}), an erroneous 'Review: Client has 5 business days...'
    would pass because 5 is in the union.
    Under category-aware validation, 'Review' and 'Deemed accepted' validate specifically against
    milestone_acceptance_period_days ({10}), so 5-day claims in those steps are stripped, while the
    genuine 5-day dispute escalation step in 'Exceptions' is preserved.
    """
    arc = load_baseline("arc_application_implementation")
    facts = _extract_allowed_numeric_facts(arc)

    # Confirm baseline facts are segregated
    assert facts["milestone_acceptance_period_days"] == {10}
    assert facts["dispute_escalation_days"] == {5}
    assert 5 in facts["day_counts"]  # 5 is in the union!

    conflated_narrative = (
        "**Inputs ready:** Client provisions environment and SME availability.\n"
        "**Execution:** Track delivery phases against milestone acceptance criteria.\n"
        "**Submission:** Submit formal milestone package to Client Approver with written notice.\n"
        "**Review:** Client has 5 business days from the completion notice to evaluate, review, and test the Work Output.\n"
        "**Deemed accepted:** If Client provides no written notice of failure within the 5-business-day window, milestone is deemed accepted.\n"
        "**Exceptions:** Escalation follows Level 1 dispute protocols within 5 business days."
    )

    cleaned = _sanitize_acceptance_narrative(conflated_narrative, baseline=arc)

    # 1. Erroneous 5-day review and deemed-accepted steps must be stripped
    assert "Review:" not in cleaned
    assert "5 business days from the completion notice" not in cleaned
    assert "Deemed accepted:" not in cleaned
    assert "5-business-day window" not in cleaned

    # 2. Genuine 5-day dispute escalation step must be preserved
    assert "Exceptions: Escalation follows Level 1 dispute protocols within 5 business days." in cleaned

    # 3. Grounded non-day steps must be preserved
    assert "Inputs ready:" in cleaned
    assert "Execution:" in cleaned
    assert "Submission:" in cleaned

    # 4. When correct 10-day review timeline is used, it passes validation and is preserved
    correct_narrative = (
        "**Review:** Client has 10 business days from the completion notice to evaluate, review, and test the Work Output.\n"
        "**Deemed accepted:** If Client provides no written notice of failure within the 10-business-day window, milestone is deemed accepted.\n"
        "**Exceptions:** Escalation follows Level 1 dispute protocols within 5 business days."
    )
    cleaned_correct = _sanitize_acceptance_narrative(correct_narrative, baseline=arc)
    assert "Review: Client has 10 business days from the completion notice to evaluate, review, and test the Work Output." in cleaned_correct
    assert "Deemed accepted: If Client provides no written notice of failure within the 10-business-day window, milestone is deemed accepted." in cleaned_correct
    assert "Exceptions: Escalation follows Level 1 dispute protocols within 5 business days." in cleaned_correct
