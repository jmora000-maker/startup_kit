"""Unit tests for the centralized ReadinessScoringEngine."""

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
)
from src.scoring.readiness_engine import ReadinessScoringEngine


@pytest.fixture
def base_source_ref():
    return SourceReference(document_name="SOW.pdf", clause_or_slide="Sec 1", confidence_score=1.0)


@pytest.fixture
def perfect_baseline(base_source_ref):
    """A fully satisfied baseline that should yield 100.0% readiness score."""
    checklist = [
        ReadinessChecklistItem(
            item_id=f"G01-{i:02d}",
            gate_criterion=f"Criterion {i}",
            related_section4_artifact="Artifact",
            owner="PMO Lead",
            status="Complete",
            evidence="Verified",
            approval_status="Approved",
            exception_required=False,
        )
        for i in range(1, 16)
    ]
    deliverables = [
        Deliverable(
            id="DEL-01",
            name="Architecture Design",
            description="Complete system design",
            source_reference=base_source_ref,
            owner="Senior Architect",
            acceptance_criteria="Sign-off by Enterprise Architecture Board",
            client_approver="VP Engineering",
        )
    ]
    talent = TalentOnboardingRecord(
        delivery_manager="Jane Doe",
        talent_pm="Taylor Brown",
        pmo_lead="Sarah Connor",
        delivery_talent_roster=[
            TalentMember(role="Architect", name="John Smith", status="Confirmed"),
            TalentMember(role="Senior Dev", name="Alice Wonderland", status="Confirmed"),
        ],
        required_roles=["Architect", "Senior Dev"],
    )
    raid = [
        RiskAssumption(
            type="Risk",
            description="API latency risk",
            owner="Tech Lead",
            source_reference=base_source_ref,
        )
    ]
    guardrail = CommercialGuardrail(
        contract_type_implication="Time & Materials standard guardrails",
        budget_baseline="$250,000 USD SOW Cap",
    )
    charter = ProjectStartupCharter(
        project_name="High Assurance System",
        client_name="FinTech Corp",
        governance_tier="Partnered",
        delivery_manager="Jane Doe",
        talent_pm="Taylor Brown",
        pmo_lead="Sarah Connor",
        source_reference=base_source_ref,
    )
    return StartupKitBaseline(
        project_name="High Assurance System",
        governance_tier="Partnered",
        charter=charter,
        readiness_checklist=checklist,
        deliverables=deliverables,
        talent_onboarding=talent,
        raid_items=raid,
        commercial_guardrails=guardrail,
        open_questions=[],
    )


def test_readiness_scoring_weights_sum_to_100():
    """Verify that dimension weights sum exactly to 1.00 (100%)."""
    engine = ReadinessScoringEngine
    total_weight = (
        engine.WEIGHT_MANDATORY_CONTROLS
        + engine.WEIGHT_DELIVERABLES_RIGOR
        + engine.WEIGHT_TALENT_STAFFING
        + engine.WEIGHT_COMMERCIAL_RISK
    )
    assert round(total_weight, 5) == 1.00


def test_readiness_scoring_engine_determinism(perfect_baseline):
    """Verify that running 1,000 iterations on identical input produces identical score and breakdown."""
    score_0, breakdown_0 = ReadinessScoringEngine.compute_scores(perfect_baseline)
    assert score_0 == 100.0
    assert breakdown_0["mandatory_g01_controls"] == 100.0
    assert breakdown_0["deliverable_acceptance_rigor"] == 100.0
    assert breakdown_0["talent_staffing_readiness"] == 100.0
    assert breakdown_0["commercial_risk_mitigation"] == 100.0

    for _ in range(1000):
        score, breakdown = ReadinessScoringEngine.compute_scores(perfect_baseline)
        assert score == score_0
        assert breakdown == breakdown_0


def test_dimension_1_status_weights_and_exception_penalties(base_source_ref):
    """Verify status point values and 0.02 reduction per open exception in D1."""
    # 15 items with various statuses
    items = [
        ReadinessChecklistItem(
            item_id=f"G01-{i:02d}",
            gate_criterion=f"Criterion {i}",
            related_section4_artifact="Artifact",
            owner="PMO Lead",
            status="Complete",  # 1.00
            evidence="Done",
        )
        for i in range(1, 11)
    ] + [
        ReadinessChecklistItem(
            item_id=f"G01-{i:02d}",
            gate_criterion=f"Criterion {i}",
            related_section4_artifact="Artifact",
            owner="PMO Lead",
            status="Approved with Exception",  # 0.85
            evidence="Waiver",
        )
        for i in range(11, 13)
    ] + [
        ReadinessChecklistItem(
            item_id=f"G01-{i:02d}",
            gate_criterion=f"Criterion {i}",
            related_section4_artifact="Artifact",
            owner="PMO Lead",
            status="Review Required",  # 0.50
            evidence="Pending review",
        )
        for i in range(13, 16)
    ]
    # Raw total = 10 * 1.0 + 2 * 0.85 + 3 * 0.50 = 10 + 1.70 + 1.50 = 13.20 / 15 = 0.88
    dim1_clean, exc_0 = ReadinessScoringEngine.compute_dimension_1(items)
    assert round(dim1_clean, 4) == round(13.20 / 15.0, 4)
    assert len(exc_0) == 0

    # Add 2 open exceptions (deducts 2 * 0.02 = 0.04)
    items[0].exception_required = True
    items[1].status = "Exception Required"  # status point = 0.20 instead of 1.0, and exception count +1
    # Raw total = 9 * 1.0 + 1 * 0.20 + 2 * 0.85 + 3 * 0.50 = 9 + 0.20 + 1.70 + 1.50 = 12.40 / 15 = 0.82666...
    # Penalty: 2 * 0.02 = 0.04 -> dim1 = 0.82666... - 0.04 = 0.78666...
    dim1_penalized, exc_2 = ReadinessScoringEngine.compute_dimension_1(items)
    expected_dim1 = max(0.0, min(1.0, (12.40 / 15.0) - 0.04))
    assert round(dim1_penalized, 4) == round(expected_dim1, 4)
    assert len(exc_2) == 2


def test_dimension_2_deliverables_scoring(base_source_ref):
    """Verify Deliverable & Acceptance Rigor scoring rules."""
    # 1. Optimal deliverable: Criteria (0.4) + Owner (0.3) + Route (0.3) = 1.0
    d_optimal = Deliverable(
        id="D1",
        name="Design",
        source_reference=base_source_ref,
        owner="Named Architect",
        acceptance_criteria="Formal test sign-off",
        client_approver="VP Engineering",
    )
    assert ReadinessScoringEngine.compute_dimension_2([d_optimal]) == 1.0

    # 2. Missing criteria: Criteria (0.0) + Owner (0.3) + Route (0.3) = 0.6
    d_missing_crit = Deliverable(
        id="D2",
        name="Code",
        source_reference=base_source_ref,
        owner="Named Architect",
        acceptance_criteria="[CONFIRMATION REQUIRED]",
        client_approver="VP Engineering",
    )
    assert round(ReadinessScoringEngine.compute_dimension_2([d_missing_crit]), 2) == 0.60

    # 3. Unassigned owner: Criteria (0.4) + Owner (0.0) + Route (0.3) = 0.7
    d_unassigned_owner = Deliverable(
        id="D3",
        name="Infra",
        source_reference=base_source_ref,
        owner="[UNASSIGNED - TO BE CONFIRMED]",
        acceptance_criteria="Formal test sign-off",
        client_approver="VP Engineering",
    )
    assert round(ReadinessScoringEngine.compute_dimension_2([d_unassigned_owner]), 2) == 0.70

    # 4. Empty deliverables returns fallback 0.50
    assert ReadinessScoringEngine.compute_dimension_2([]) == 0.50


def test_dimension_3_leadership_and_roster(perfect_baseline):
    """Verify leadership assignments (+0.20 each) and talent roster completeness."""
    # Perfect baseline has all 3 leaders (0.60) + 100% staffed roster (0.40) = 1.0
    dim3_full = ReadinessScoringEngine.compute_dimension_3(perfect_baseline)
    assert dim3_full == 1.0

    # Unassign DM: drops by 0.20
    perfect_baseline.talent_onboarding.delivery_manager = "[UNASSIGNED - TO BE CONFIRMED]"
    perfect_baseline.charter.delivery_manager = "[UNASSIGNED - TO BE CONFIRMED]"
    dim3_no_dm = ReadinessScoringEngine.compute_dimension_3(perfect_baseline)
    assert round(dim3_no_dm, 2) == 0.80

    # Unassign Talent PM as well: drops by another 0.20 -> 0.60
    perfect_baseline.talent_onboarding.talent_pm = "[UNASSIGNED - TO BE CONFIRMED]"
    perfect_baseline.charter.talent_pm = "[UNASSIGNED - TO BE CONFIRMED]"
    dim3_no_leaders = ReadinessScoringEngine.compute_dimension_3(perfect_baseline)
    assert round(dim3_no_leaders, 2) == 0.60


def test_dimension_4_raid_commercial_question_penalties(perfect_baseline):
    """Verify RAID, commercial guardrails, and 0.05 deduction per open question in D4 (capped at 0.40)."""
    # Perfect baseline has assigned RAID (0.50) + commercial (0.50) - 0 questions = 1.0
    dim4_full = ReadinessScoringEngine.compute_dimension_4(perfect_baseline)
    assert dim4_full == 1.0

    # Add 3 open questions: deducts 3 * 0.05 = 0.15 -> 0.85
    perfect_baseline.open_questions = ["Q1", "Q2", "Q3"]
    dim4_3q = ReadinessScoringEngine.compute_dimension_4(perfect_baseline)
    assert round(dim4_3q, 2) == 0.85

    # 20 open questions: deducts capped 0.40 -> 0.60
    perfect_baseline.open_questions = [f"Q{i}" for i in range(25)]
    dim4_capped = ReadinessScoringEngine.compute_dimension_4(perfect_baseline)
    assert dim4_capped == 0.60


def test_dimension_4_commercial_guardrails_edge_cases(perfect_baseline):
    """Verify Commercial & Risk mitigation scoring under missing/partial guardrails and unassigned RAID."""
    # 1. Commercial Guardrails is None -> fallback 0.25 (s_raid=0.50, s_comm=0.25, q=0) -> 0.75
    perfect_baseline.open_questions = []
    perfect_baseline.commercial_guardrails = None
    dim4_no_cg = ReadinessScoringEngine.compute_dimension_4(perfect_baseline)
    assert round(dim4_no_cg, 2) == 0.75

    # 2. Commercial Guardrails with unconfirmed budget baseline but standard rules -> 0.40
    perfect_baseline.commercial_guardrails = CommercialGuardrail(
        contract_type_implication="Time & Materials standard guardrails",
        budget_baseline="[CONFIRMATION REQUIRED - T&M BUDGET CAP]"
    )
    dim4_unconfirmed_budget = ReadinessScoringEngine.compute_dimension_4(perfect_baseline)
    assert round(dim4_unconfirmed_budget, 2) == 0.90  # 0.50 raid + 0.40 comm

    # 3. Empty RAID items fallback 0.25 + confirmed commercial guardrails 0.50 -> 0.75
    perfect_baseline.raid_items = []
    perfect_baseline.commercial_guardrails = CommercialGuardrail(
        contract_type_implication="Time & Materials standard guardrails",
        budget_baseline="$250,000 USD SOW Cap"
    )
    dim4_empty_raid = ReadinessScoringEngine.compute_dimension_4(perfect_baseline)
    assert round(dim4_empty_raid, 2) == 0.75


def test_gate_decision_thresholds():
    """Verify Gate Decision categories: Green (>=85% + 0 exc), Amber (70-84.9% or >0 exc), Red (<70%)."""
    # 1. 90% score with 0 exceptions -> Approved for Mobilize (Green)
    dec_green, state_green = ReadinessScoringEngine.determine_gate_decision(
        composite_score=90.0, open_exceptions_count=0
    )
    assert dec_green.gate_decision_status == "Approved for Mobilize"
    assert dec_green.approved_with_exception is False
    assert dec_green.rework_required is False

    # 2. 90% score with 1 exception -> Approved with Exception (Amber)
    dec_amber_exc, state_amber_exc = ReadinessScoringEngine.determine_gate_decision(
        composite_score=90.0, open_exceptions_count=1
    )
    assert dec_amber_exc.gate_decision_status == "Approved with Exception"
    assert dec_amber_exc.approved_with_exception is True
    assert dec_amber_exc.rework_required is False

    # 3. 75% score with 0 exceptions -> Approved with Exception (Amber)
    dec_amber_score, state_amber_score = ReadinessScoringEngine.determine_gate_decision(
        composite_score=75.0, open_exceptions_count=0
    )
    assert dec_amber_score.gate_decision_status == "Approved with Exception"

    # 4. 65% score with 0 exceptions -> Rework Required (Red)
    dec_red, state_red = ReadinessScoringEngine.determine_gate_decision(
        composite_score=65.0, open_exceptions_count=0
    )
    assert dec_red.gate_decision_status == "Rework Required"
    assert dec_red.rework_required is True

    # 5. 52.2% score with 2 exceptions -> Rework Required (Red)
    dec_red_exc, state_red_exc = ReadinessScoringEngine.determine_gate_decision(
        composite_score=52.2, open_exceptions_count=2
    )
    assert dec_red_exc.gate_decision_status == "Rework Required"
    assert dec_red_exc.rework_required is True
    assert state_red_exc == "Clarification Pending"
