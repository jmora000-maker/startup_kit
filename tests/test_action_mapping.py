"""Unit and integration tests for Action Required mapping and Tri-directional Alignment."""

import pytest
from datetime import date
from src.core.models import (
    StartupKitBaseline,
    ProjectStartupCharter,
    Deliverable,
    Milestone,
    RiskAssumption,
    ReadinessChecklistItem,
    CommercialGuardrail,
    TalentOnboardingRecord,
    TalentMember,
    SourceReference,
    GovernanceContext,
    ActionRequiredItem,
)
from src.scoring.readiness_engine import ReadinessScoringEngine
from src.llm.aggregator import BaselineAggregator


@pytest.fixture
def base_source_ref():
    return SourceReference(document_name="SOW.pdf", clause_or_slide="Sec 1", confidence_score=1.0)


@pytest.fixture
def sample_baseline_with_issues(base_source_ref):
    """Baseline with unassigned deliverable owner (G01-03), unconfirmed milestone (G01-04), and 2 questions."""
    checklist = [
        ReadinessChecklistItem(
            item_id=f"G01-{i:02d}",
            gate_criterion=f"Criterion {i}",
            related_section4_artifact="Section 4 Artifact",
            owner="PMO Lead" if i not in (3, 4, 8) else ("Talent PM" if i in (3, 8) else "Delivery Manager"),
            status="Complete" if i not in (3, 4) else ("Review Required" if i == 3 else "Confirmation Required"),
            evidence="Evidence",
            approval_status="Approved" if i not in (3, 4) else "Pending Review",
            exception_required=(i in (3, 4)),
            exception_details=(
                "Deliverable missing owner" if i == 3 else ("Milestone external date unconfirmed" if i == 4 else None)
            ),
        )
        for i in range(1, 16)
    ]
    deliverables = [
        Deliverable(
            id="DEL-01",
            name="Architecture Design",
            description="Complete system design",
            source_reference=base_source_ref,
            owner="[UNASSIGNED - TO BE CONFIRMED]",
            acceptance_criteria="Sign-off required",
            client_approver="VP Engineering",
        )
    ]
    milestones = [
        Milestone(
            id="M1",
            description="Go-Live",
            external_date=None,
            source_reference=base_source_ref,
        )
    ]
    talent = TalentOnboardingRecord(
        delivery_manager="Jane Doe",
        talent_pm="Taylor Brown",
        pmo_lead="Sarah Connor",
        delivery_talent_roster=[
            TalentMember(role="Architect", name="John Smith", status="Confirmed"),
        ],
    )
    charter = ProjectStartupCharter(
        project_name="FinTech Modernization",
        client_name="FinTech Corp",
        governance_tier="Partnered",
        delivery_manager="Jane Doe",
        talent_pm="Taylor Brown",
        pmo_lead="Sarah Connor",
        source_reference=base_source_ref,
    )
    open_questions = [
        "Confirm deliverable DEL-01 named owner and acceptance test criteria.",
        "Verify third-party API dependencies and access credentials.",
    ]
    baseline = StartupKitBaseline(
        project_name="FinTech Modernization",
        governance_tier="Partnered",
        charter=charter,
        readiness_checklist=checklist,
        deliverables=deliverables,
        milestones=milestones,
        talent_onboarding=talent,
        open_questions=open_questions,
    )
    # Compute scores and generate action items
    score, breakdown = ReadinessScoringEngine.compute_scores(baseline)
    baseline.readiness_score = score
    baseline.readiness_breakdown = breakdown
    actions = ReadinessScoringEngine.generate_action_required_items(baseline)
    baseline.action_required_items = actions
    return baseline


def test_action_items_generated_from_exceptions(sample_baseline_with_issues):
    """Verify that exceptions in the checklist produce mapped 'Open Exception' action items."""
    actions = sample_baseline_with_issues.action_required_items
    exceptions = [a for a in actions if a.item_type == "Open Exception"]

    assert len(exceptions) == 2
    g01_03_action = next((a for a in exceptions if a.checklist_id == "G01-03"), None)
    assert g01_03_action is not None
    assert g01_03_action.owner == "Talent PM"
    assert g01_03_action.score_recovery_delta > 0.0
    assert "G01-03" in g01_03_action.target_gate_impact

    g01_04_action = next((a for a in exceptions if a.checklist_id == "G01-04"), None)
    assert g01_04_action is not None
    assert g01_04_action.owner == "Delivery Manager"
    assert g01_04_action.score_recovery_delta > 0.0


def test_action_items_generated_from_questions(sample_baseline_with_issues):
    """Verify that open questions produce mapped 'Open Clarification' action items."""
    actions = sample_baseline_with_issues.action_required_items
    clarifications = [a for a in actions if a.item_type == "Open Clarification"]

    assert len(clarifications) == len(sample_baseline_with_issues.open_questions)
    for c in clarifications:
        assert c.score_recovery_delta > 0.0
        assert c.checklist_id.startswith("G01-")
        assert c.resolution_deadline == "Prior to Mobilize Kickoff"


def test_tri_directional_count_parity(sample_baseline_with_issues):
    """Verify Count & State Parity: open_exceptions_count == sum(checklist exceptions) == sum(action exceptions)."""
    aggregator = BaselineAggregator()
    recalculated = aggregator.recalculate_readiness(sample_baseline_with_issues)

    checklist_exc_count = sum(
        1 for i in recalculated.readiness_checklist if i.exception_required or i.status == "Exception Required"
    )
    action_exc_count = sum(
        1 for a in recalculated.action_required_items if a.item_type == "Open Exception"
    )
    decision_exc_count = recalculated.gate_decision.open_exceptions_count

    assert checklist_exc_count == action_exc_count == decision_exc_count


def test_tri_directional_clarification_parity(sample_baseline_with_issues):
    """Verify Clarification Parity: len(open_questions) == sum(action clarifications)."""
    aggregator = BaselineAggregator()
    recalculated = aggregator.recalculate_readiness(sample_baseline_with_issues)

    questions_count = len(recalculated.open_questions)
    action_clarif_count = sum(
        1 for a in recalculated.action_required_items if a.item_type == "Open Clarification"
    )

    assert questions_count == action_clarif_count


def test_score_recovery_sum_invariant(sample_baseline_with_issues):
    """Verify that composite_score + sum(deltas) <= 100.0."""
    actions = sample_baseline_with_issues.action_required_items
    total_delta = sum(a.score_recovery_delta for a in actions)
    target_score = round(sample_baseline_with_issues.readiness_score + total_delta, 1)

    assert target_score <= 100.0


def test_score_recovery_potential_reaches_green(sample_baseline_with_issues):
    """Verify that resolving all action items on an Amber baseline raises achievable score >= 85.0% Green."""
    assert sample_baseline_with_issues.readiness_score >= 70.0
    total_delta = sum(a.score_recovery_delta for a in sample_baseline_with_issues.action_required_items)
    achievable_score = sample_baseline_with_issues.readiness_score + total_delta

    assert achievable_score >= 85.0, f"Achievable score {achievable_score} must be >= 85.0% Green"


def test_owner_and_artifact_traceability(sample_baseline_with_issues):
    """Verify that every ActionRequiredItem's owner matches the mapped checklist item owner."""
    checklist_map = {item.item_id: item for item in sample_baseline_with_issues.readiness_checklist}

    for action in sample_baseline_with_issues.action_required_items:
        chk_item = checklist_map.get(action.checklist_id)
        assert chk_item is not None, f"Checklist item {action.checklist_id} must exist"
        assert action.owner == chk_item.owner, (
            f"Action owner {action.owner} must match checklist owner {chk_item.owner}"
        )
