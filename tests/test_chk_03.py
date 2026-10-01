"""Tests for CHK-03: G01-03 client approver confirmation."""

import pytest
from src.core.models import (
    StartupKitBaseline,
    CharterExtraction,
    DeliverablesExtraction,
    MilestonesExtraction,
    RAIDExtraction,
    QuestionsExtraction,
    Deliverable,
    Milestone,
    TalentOnboardingExtraction,
    SourceReference,
)
from src.llm.aggregator import BaselineAggregator
from src.scoring.readiness_engine import ReadinessScoringEngine


def test_chk_03_generic_approver_with_open_question_requires_review():
    """CHK-03: Deliverables with generic approvers when an open question asks for names gives G01-03 Review Required."""
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="Sec 1", confidence_score=1.0)
    delivs = [
        Deliverable(
            id="DEL-01",
            name="Micro-frontend Shell",
            description="Shell",
            acceptance_criteria="Shell hosts remotes",
            evidence_required="Test logs",
            owner="Talent PM",
            client_approver="Client's designated approvers",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-02",
            name="Authentication Gateway",
            description="Auth",
            acceptance_criteria="Token exchange passes",
            evidence_required="Auth test reports",
            owner="Talent PM",
            client_approver="Client's designated approvers",
            source_reference=ref,
        ),
    ]
    questions = [
        "Who are the named Client approvers authorized to provide Milestone Sign-Off for each of the four milestones?"
    ]

    agg = BaselineAggregator()
    baseline = agg.aggregate(
        charter=CharterExtraction(
            project_name="Test",
            client_name="Client",
            contract_type="Time and Materials",
            governance_tier="Partnered",
            pmo_lead="Sarah Connor",
            delivery_manager="Jane Doe",
            talent_pm="John Smith",
            source_reference=ref,
        ),
        deliverables_ext=DeliverablesExtraction(deliverables=delivs, source_reference=ref),
        milestones_ext=MilestonesExtraction(milestones=[Milestone(id="M1", description="M1", external_date=None, source_reference=ref)], source_reference=ref),
        raid_ext=RAIDExtraction(source_reference=ref),
        talent_ext=TalentOnboardingExtraction(delivery_talent_roster=[], source_reference=ref),
        questions_ext=QuestionsExtraction(open_questions=questions, source_reference=ref),
    )

    # Initial G01-03 from aggregator
    g01_03 = next(i for i in baseline.readiness_checklist if i.item_id == "G01-03")
    assert g01_03.status == "Review Required"
    assert g01_03.exception_required is True

    # Evaluated through ReadinessScoringEngine
    rescored = ReadinessScoringEngine.evaluate_and_rescore(baseline)
    rescored_g01_03 = next(i for i in rescored.readiness_checklist if i.item_id == "G01-03")
    assert rescored_g01_03.status == "Review Required"
    assert rescored_g01_03.exception_required is True

    # Same baseline with named approvers gives Complete
    for d in delivs:
        d.client_approver = "Dr. Alice Morgan, Chief Scientist"

    baseline_named = agg.aggregate(
        charter=CharterExtraction(
            project_name="Test",
            client_name="Client",
            contract_type="Time and Materials",
            governance_tier="Partnered",
            pmo_lead="Sarah Connor",
            delivery_manager="Jane Doe",
            talent_pm="John Smith",
            source_reference=ref,
        ),
        deliverables_ext=DeliverablesExtraction(deliverables=delivs, source_reference=ref),
        milestones_ext=MilestonesExtraction(milestones=[Milestone(id="M1", description="M1", external_date=None, source_reference=ref)], source_reference=ref),
        raid_ext=RAIDExtraction(source_reference=ref),
        talent_ext=TalentOnboardingExtraction(delivery_talent_roster=[], source_reference=ref),
        questions_ext=QuestionsExtraction(open_questions=questions, source_reference=ref),
    )

    named_g01_03 = next(i for i in baseline_named.readiness_checklist if i.item_id == "G01-03")
    assert named_g01_03.status == "Complete"
    assert named_g01_03.exception_required is False

    rescored_named = ReadinessScoringEngine.evaluate_and_rescore(baseline_named)
    rescored_named_g01_03 = next(i for i in rescored_named.readiness_checklist if i.item_id == "G01-03")
    assert rescored_named_g01_03.status == "Complete"
    assert rescored_named_g01_03.exception_required is False
