"""HTL-107: Regression tests for Milestone Acceptance Period extraction, Fact Review propagation, and Slide 16 reconciliation."""

import pytest
from src.core.models import (
    StartupKitBaseline,
    Deliverable,
    Milestone,
    ProjectStartupCharter,
    SOWInterpretationSummary,
    GovernanceContext,
)
from src.llm.validation import validate_and_repair_baseline, validate_evidence_and_review_windows
from src.llm.aggregator import sanitize_report_text
from src.review_ui.facts import (
    build_fact_categories,
    compute_review,
    apply_corrections,
    contract_wide_review_window,
)
from src.generators.governance_deck.builder import (
    build_slide16_model,
    _extract_allowed_numeric_facts,
    _sanitize_acceptance_narrative,
)
from tests.test_htl_106 import load_baseline


def test_htl_107_pge_sow_real_extraction_pipeline_survives_into_deliverables_and_narrative():
    """HTL-107 Addition 1: Reproduce the ORIGINAL PGE extraction failure scenario.
    
    Verifies that PGE's real SOW clause:
    'Client will have five (5) business days from the date of notice of Supplier's completion of the Milestone (the 'Milestone Acceptance Period') to evaluate, review and/or test the Work Output'
    is captured by validate_evidence_and_review_windows, normalized across all deliverables,
    and reflected in Slide 16 Card 1 Review and Card 3 Deemed-accepted steps.
    """
    baseline = StartupKitBaseline(
        project_name="PGE Cloud Readiness",
        charter=ProjectStartupCharter(
            client_name="Pacific Gas & Electric",
            governance_tier="Guided",
        ),
        sow_interpretation=SOWInterpretationSummary(
            approval_expectations=(
                "Client will have five (5) business days from the date of notice of Supplier's completion "
                "of the Milestone (the 'Milestone Acceptance Period') to evaluate, review and/or test the Work Output. "
                "If Client does not provide written notice within the Milestone Acceptance Period, milestone is deemed accepted. "
                "Rejection is capped at three (3) repeated attempts."
            ),
            acceptance_process_narrative=(
                "**Inputs ready:** Confirm client environment read access, discovery tooling, spend data, and SME availability.\n"
                "**Execution:** Deliver six Milestone 1 work outputs by target date 2026-11-18, keeping Client Contact informed.\n"
                "**Submission:** Provide formal written completion notice, starting the 5-business-day acceptance period.\n"
                "**Review:** Client conducts 5-business-day evaluation and milestone review sessions against specifications and acceptance criteria.\n"
                "**Triage:** If Client identifies material non-conformance, provide specific written notice detailing deficiencies.\n"
                "**Remediation:** Toptal remediates identified non-conformances within commercially reasonable efforts, capped at 3 repeated attempts.\n"
                "**Deemed accepted:** Milestone is deemed accepted if Client provides no written notice of non-conformance within the 5-business-day window.\n"
                "**Sign-off:** Written certification authorizes Milestone 1 completion and billing gate progression."
            ),
        ),
        deliverables=[
            Deliverable(
                id="DEL-01",
                name="Portfolio Inventory & Application Disposition Register",
                description="Comprehensive inventory and disposition register.",
                review_window="",  # Initially empty prior to validation
            ),
            Deliverable(
                id="DEL-02",
                name="Target State Architecture Recommendation",
                description="Target architecture specification.",
                review_window="",
            ),
        ],
        milestones=[
            Milestone(
                id="M1",
                description="Discovery & Cloud Readiness Architecture",
                phase="P1",
            ),
        ],
    )

    # 1. Run validation layer (simulating extraction pipeline)
    validate_and_repair_baseline(baseline)

    # 2. Verify all deliverables carry the uniform contract-wide review window
    for d in baseline.deliverables:
        assert d.review_window == "5 business days from notice of milestone completion"

    assert contract_wide_review_window(baseline) == "5 business days from notice of milestone completion"

    # 3. Verify numeric fact extraction isolates the 5-day period
    facts = _extract_allowed_numeric_facts(baseline)
    assert facts["milestone_acceptance_period_days"] == {5}

    # 4. Verify Slide 16 model contains both Review: and Deemed accepted: steps with 5 days
    model = build_slide16_model(baseline)
    card1 = model.cards[0]
    card3 = model.cards[2]

    c1_labels = [lbl for lbl, _ in card1.steps if lbl]
    c1_text = " ".join([f"{lbl} {body}" for lbl, body in card1.steps])
    assert any("Review" in lbl for lbl in c1_labels)
    assert "5-business-day evaluation" in c1_text

    c3_labels = [lbl for lbl, _ in card3.steps if lbl]
    c3_text = " ".join([f"{lbl} {body}" for lbl, body in card3.steps])
    assert any("Deemed accepted" in lbl for lbl in c3_labels)
    assert "5-business-day window" in c3_text


def test_htl_107_fact_review_correction_propagates_to_slide16_and_approval_expectations():
    """HTL-107 Part B: Verify manual Fact Review correction propagates end-to-end.
    
    If an initial extraction was missing the review window (e.g. deliverable review_window is generic
    and narrative omitted Review step), a human correction on Fact Review entering '5 business days'
    must update:
      1. baseline.deliverables[*].review_window
      2. baseline.sow_interpretation.approval_expectations
      3. Slide 16 generated model narrative (reconciling Review: and Deemed accepted: steps)
    """
    baseline = StartupKitBaseline(
        project_name="PGE Cloud Readiness",
        charter=ProjectStartupCharter(
            client_name="Pacific Gas & Electric",
            governance_tier="Guided",
        ),
        sow_interpretation=SOWInterpretationSummary(
            approval_expectations="Client accepts deliverables upon completion.",
            acceptance_process_narrative=(
                "**Inputs ready:** Confirm client environment read access and SME availability.\n"
                "**Execution:** Deliver Milestone 1 work outputs.\n"
                "**Submission:** Provide formal written completion notice to initiate acceptance.\n"
                "**Triage:** Client provides written notice detailing non-conformance.\n"
                "**Remediation:** Remediate deficiencies capped at 3 repeated attempts.\n"
                "**Sign-off:** Written certification authorizes billing gate progression."
            ),
        ),
        deliverables=[
            Deliverable(
                id="DEL-01",
                name="Portfolio Inventory",
                description="Application inventory.",
                review_window="Not specified; reviewed at the Milestone Acceptance Review at the end of Phase P1",
            ),
        ],
        milestones=[
            Milestone(id="M1", description="Cloud Readiness", phase="P1"),
        ],
    )

    # 1. Build fact categories and simulate Fact Review edit
    categories = build_fact_categories(baseline)
    submitted = {"contract_wide_review_window": "5 business days from notice of milestone completion"}

    facts_map, corrections = compute_review(categories, submitted)
    assert len(corrections) == 1
    assert corrections[0]["field"] == "contract_wide_review_window"
    assert corrections[0]["corrected_to"] == "5 business days from notice of milestone completion"

    # 2. Apply corrections to baseline
    corrected = apply_corrections(baseline, corrections)

    # 3. Assert deliverable review_window and approval_expectations are updated
    assert corrected.deliverables[0].review_window == "5 business days from notice of milestone completion"
    assert "5 business days from notice of milestone completion" in corrected.sow_interpretation.approval_expectations

    # 4. Assert allowed numeric facts captures 5 days
    facts = _extract_allowed_numeric_facts(corrected)
    assert 5 in facts["milestone_acceptance_period_days"]

    # 5. Assert Slide 16 generated model reconciles Review: and Deemed accepted: steps
    slide16 = build_slide16_model(corrected)
    c1_text = " ".join([f"{lbl} {body}" for lbl, body in slide16.cards[0].steps])
    c3_text = " ".join([f"{lbl} {body}" for lbl, body in slide16.cards[2].steps])

    assert "Review: Client conducts 5-business-day evaluation against specifications and acceptance criteria." in c1_text
    assert "Deemed accepted: If Client provides no written notice of failure within the 5-business-day window, milestone is deemed accepted." in c3_text


def test_htl_107_arc_10_day_milestone_acceptance_period_unaffected():
    """HTL-107: Verify ARC's real 10-business-day Milestone Acceptance Period is completely unaffected."""
    arc = load_baseline("arc_application_implementation")
    validate_and_repair_baseline(arc)

    facts = _extract_allowed_numeric_facts(arc)
    assert facts["milestone_acceptance_period_days"] == {10}
    assert facts["dispute_escalation_days"] == {5}

    slide16 = build_slide16_model(arc)
    c1_text = " ".join([f"{lbl} {body}" for lbl, body in slide16.cards[0].steps])
    c3_text = " ".join([f"{lbl} {body}" for lbl, body in slide16.cards[2].steps])

    assert "10 business days" in c1_text
    assert "10-business-day" in c3_text or "10 business days" in c3_text
    # 5 business days in dispute escalation remains isolated and not conflated
    assert "5 business days" not in c1_text


def test_htl_107_deliverable_model_default_is_empty_string():
    """HTL-107: Ensure Deliverable.review_window defaults to empty string to prevent anti-pattern collisions."""
    d = Deliverable(id="DEL-99", name="Test Deliverable")
    assert d.review_window == ""
