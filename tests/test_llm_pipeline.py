"""Unit tests for multi-pass LLM pipeline, extractors, and aggregator."""

import pytest
from datetime import date
from pathlib import Path

from src.core.models import (
    DocumentSection,
    SourceReference,
    Deliverable,
    Milestone,
    RiskAssumption,
    DependencyAssumptionItem,
    DecisionItem,
    ExtractedDocument,
    CharterExtraction,
    DeliverablesExtraction,
    MilestonesExtraction,
    RAIDExtraction,
    QuestionsExtraction,
    SOWInterpretationExtraction,
    ScopeDecompositionExtraction,
    DecisionsExtraction,
)
from src.llm.client import MockLLMClient
from src.llm.parsers import (
    format_documents_for_prompt,
    CharterDomainExtractor,
    DeliverablesDomainExtractor,
    MilestonesDomainExtractor,
    RAIDDomainExtractor,
    QuestionsDomainExtractor,
    SOWInterpretationDomainExtractor,
    ScopeDecompositionDomainExtractor,
    DecisionsDomainExtractor,
)
from src.llm.aggregator import BaselineAggregator


@pytest.fixture
def mock_extracted_doc():
    return ExtractedDocument(
        file_name="pfizer_sow.pdf",
        file_type="pdf",
        file_path=Path("inputs/pfizer_sow.pdf"),
        text_content="Statement of Work for Pfizer Clinical Trial Analytics Platform.",
        sections=[
            DocumentSection(
                title="Page 1",
                content="Statement of Work for Pfizer Clinical Trial Analytics Platform.",
                metadata={"page_number": 1, "rect": [0.0, 0.0, 612.0, 792.0]}
            )
        ],
        metadata={"total_pages": 1, "title": "Pfizer SOW"}
    )


def test_format_documents_for_prompt(mock_extracted_doc):
    assert format_documents_for_prompt([]) == "No documents provided."
    res = format_documents_for_prompt([mock_extracted_doc])
    assert "=== DOCUMENT: pfizer_sow.pdf" in res
    assert "Pfizer Clinical Trial Analytics" in res


def test_domain_extractors_with_mock_client(mock_extracted_doc, sample_source_ref):
    mock_client = MockLLMClient()

    charter_res = CharterExtraction(
        project_name="Pfizer Analytics",
        client_name="Pfizer",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        source_reference=sample_source_ref
    )
    mock_client.set_response(CharterExtraction, charter_res)

    deliv_res = DeliverablesExtraction(deliverables=[
        Deliverable(
            id="DEL-01",
            description="Data pipeline",
            source_reference=sample_source_ref
        )
    ])
    mock_client.set_response(DeliverablesExtraction, deliv_res)

    ms_res = MilestonesExtraction(milestones=[
        Milestone(
            id="M1",
            description="Phase 1 Complete",
            external_date=date(2026, 11, 1),
            source_reference=sample_source_ref
        )
    ])
    mock_client.set_response(MilestonesExtraction, ms_res)

    raid_res = RAIDExtraction(items=[
        RiskAssumption(
            type="Risk",
            description="Access provisioning delay",
            source_reference=sample_source_ref
        )
    ])
    mock_client.set_response(RAIDExtraction, raid_res)

    q_res = QuestionsExtraction(open_questions=["Is VPN required?"])
    mock_client.set_response(QuestionsExtraction, q_res)

    docs = [mock_extracted_doc]

    charter = CharterDomainExtractor().extract(docs, mock_client)
    assert charter.project_name == "Pfizer Analytics"

    delivs = DeliverablesDomainExtractor().extract(docs, mock_client)
    assert len(delivs.deliverables) == 1

    milestones = MilestonesDomainExtractor().extract(docs, mock_client)
    assert len(milestones.milestones) == 1

    raid = RAIDDomainExtractor().extract(docs, mock_client)
    assert len(raid.items) == 1

    questions = QuestionsDomainExtractor().extract(docs, mock_client)
    assert questions.open_questions == ["Is VPN required?"]


def test_baseline_aggregator_business_rules(sample_source_ref):
    aggregator = BaselineAggregator()

    charter = CharterExtraction(
        project_name="Pfizer Platform",
        client_name="Pfizer Inc.",
        governance_tier="Elevated",
        contract_type="Fixed Bid",
        source_reference=sample_source_ref
    )

    # Deliverable 1 has acceptance criteria, Deliverable 2 has none, Deliverable 3 has low confidence
    low_conf_ref = SourceReference(
        document_name="sow.pdf",
        clause_or_slide="Clause 3",
        confidence_score=0.5
    )
    deliverables = DeliverablesExtraction(deliverables=[
        Deliverable(
            id="DEL-01",
            description="Architecture Spec",
            source_reference=sample_source_ref,
            acceptance_criteria="Signed off by VP"
        ),
        Deliverable(
            id="DEL-02",
            description="DevOps Pipeline",
            source_reference=sample_source_ref,
            acceptance_criteria=None
        ),
        Deliverable(
            id="DEL-03",
            description="Security Review",
            source_reference=low_conf_ref,
            acceptance_criteria="SOC2 Passed"
        )
    ])

    # Milestone 1 has external date and no buffer date, Milestone 2 has no external date
    milestones = MilestonesExtraction(milestones=[
        Milestone(
            id="M1",
            description="Milestone 1",
            external_date=date(2026, 10, 20),
            internal_buffer_date=None,
            source_reference=sample_source_ref
        ),
        Milestone(
            id="M2",
            description="Milestone 2",
            external_date=None,
            source_reference=sample_source_ref
        )
    ])

    raid = RAIDExtraction(items=[
        RiskAssumption(
            type="Risk",
            description="API Throttling",
            source_reference=low_conf_ref
        )
    ])

    questions = QuestionsExtraction(open_questions=["Confirm billing contact."])

    baseline = aggregator.aggregate(
        charter=charter,
        deliverables_ext=deliverables,
        milestones_ext=milestones,
        raid_ext=raid,
        questions_ext=questions
    )

    assert baseline.project_name == "Pfizer Platform"
    assert baseline.governance_tier == "Elevated"
    assert baseline.contract_type == "Fixed Bid"

    # Check internal buffer calculation (Elevated tier has 10 day buffer)
    assert baseline.milestones[0].internal_buffer_date == date(2026, 10, 10)

    # Check open questions flagged
    questions_text = "\n".join(baseline.open_questions)
    assert "DEL-02" in questions_text
    assert "[CONFIRMATION REQUIRED]" in questions_text
    assert "Low Confidence" in questions_text
    assert "M2" in questions_text
    assert "Confirm billing contact." in questions_text


def test_aggregator_artifact_splitting_and_defaults(sample_source_ref):
    aggregator = BaselineAggregator()

    charter = CharterExtraction(
        project_name="Cloud Modernization",
        client_name="Acme Corp",
        governance_tier="Partnered",
        contract_type="Fixed Bid",
        delivery_manager="Jane Doe",
        talent_pm="John Smith",
        pmo_lead="Sarah Connor",
        source_reference=sample_source_ref
    )

    deliverables = DeliverablesExtraction(deliverables=[
        Deliverable(
            id="DEL-01",
            description="Terraform IaC Modules",
            source_reference=sample_source_ref,
            owner="Talent PM",
            acceptance_criteria="Approved by Architecture Review Board"
        ),
        Deliverable(
            id="DEL-02",
            description="CI/CD Pipeline",
            source_reference=sample_source_ref,
            owner="Unassigned",
            acceptance_criteria=None
        )
    ])

    milestones = MilestonesExtraction(milestones=[
        Milestone(
            id="M1",
            description="Phase 1 Kickoff",
            external_date=date(2026, 10, 20),
            internal_buffer_date=None,
            source_reference=sample_source_ref
        )
    ])

    raid = RAIDExtraction(items=[
        RiskAssumption(
            type="Risk",
            description="Account provisioning delay",
            owner="Delivery Manager",
            status="Open",
            source_reference=sample_source_ref
        ),
        RiskAssumption(
            type="Assumption",
            description="Client provides test environment",
            owner="PMO Lead",
            status="Open",
            source_reference=sample_source_ref
        ),
        RiskAssumption(
            type="Dependency",
            description="Third-party vendor API access",
            owner="Client Lead",
            status="Open",
            source_reference=sample_source_ref
        )
    ])

    baseline = aggregator.aggregate(
        charter=charter,
        deliverables_ext=deliverables,
        milestones_ext=milestones,
        raid_ext=raid,
    )

    # 1. Verify Charter & SOW Interpretation
    assert baseline.charter is not None
    assert baseline.charter.project_name == "Cloud Modernization"
    assert baseline.sow_interpretation is not None
    assert len(baseline.sow_interpretation.contracted_deliverables) == 2

    # 2. Verify Deliverables and Backlog Seed derivation
    assert len(baseline.deliverables) == 2
    assert len(baseline.backlog_seed) == 2
    assert baseline.backlog_seed[0].parent_deliverable_id == "DEL-01"
    assert baseline.backlog_seed[1].parent_deliverable_id == "DEL-02"

    # 3. Verify RAID vs Dependency/Assumption splitting
    assert len(baseline.raid_items) == 1
    assert baseline.raid_items[0].type == "Risk"
    assert len(baseline.dependencies_assumptions) == 2
    types = {da.type for da in baseline.dependencies_assumptions}
    assert types == {"Assumption", "Dependency"}

    # 4. Verify Communications Plan defaults
    assert len(baseline.communications_plan) >= 2
    com_names = [c.name for c in baseline.communications_plan]
    assert any("Weekly Check-in" in name for name in com_names)
    assert any("Weekly Project Status Report" in name for name in com_names)

    # 5. Verify Commercial Guardrails for Fixed Bid
    assert baseline.commercial_guardrails is not None
    assert "Fixed Bid" in baseline.commercial_guardrails.contract_type_implication
    assert baseline.commercial_guardrails.approved_work_rule != ""

    # 6. Verify Talent Onboarding Record
    assert baseline.talent_onboarding is not None
    assert baseline.talent_onboarding.delivery_manager == "Jane Doe"
    assert baseline.talent_onboarding.talent_pm == "John Smith"
    assert len(baseline.talent_onboarding.artifacts_walked_through) >= 10

    # 7. Verify Readiness Checklist coverage
    assert len(baseline.readiness_checklist) >= 13
    chk_artifacts = {c.related_section4_artifact for c in baseline.readiness_checklist}
    assert "Project Startup Charter" in chk_artifacts
    assert "Milestone Delivery Plan" in chk_artifacts
    assert "Deliverables and Acceptance Matrix" in chk_artifacts
    assert "SOW Interpretation Summary" in chk_artifacts or "Dependency and Assumption Log" in chk_artifacts
    assert "RAID Log" in chk_artifacts
    assert "Communications and Reporting Plan" in chk_artifacts
    assert "Stakeholder and Responsibility Model" in chk_artifacts
    assert "RACI / Decision Rights Matrix" in chk_artifacts
    assert "Commercial and Margin Guardrails" in chk_artifacts
    assert "Talent Onboarding Record" in chk_artifacts
    assert "Startup Readiness Checklist" in chk_artifacts

    # 8. Verify Gate Decision
    assert baseline.gate_decision is not None
    assert baseline.gate_decision.approver_name != ""


def test_aggregator_tier_and_contract_tailoring(sample_source_ref):
    aggregator = BaselineAggregator()

    # Test Guided Tier + T&M
    charter_guided = CharterExtraction(
        project_name="Guided Project",
        governance_tier="Guided",
        contract_type="Time and Materials",
        source_reference=sample_source_ref
    )
    milestones = MilestonesExtraction(milestones=[
        Milestone(id="M1", description="M1", external_date=date(2026, 10, 20), source_reference=sample_source_ref)
    ])
    delivs = DeliverablesExtraction(deliverables=[
        Deliverable(id="D1", description="D1", source_reference=sample_source_ref, acceptance_criteria="OK")
    ])
    raid = RAIDExtraction(items=[])

    baseline_guided = aggregator.aggregate(
        charter=charter_guided,
        deliverables_ext=delivs,
        milestones_ext=milestones,
        raid_ext=raid
    )

    # Guided buffer is 3 days: 2026-10-20 - 3 days = 2026-10-17
    assert baseline_guided.milestones[0].internal_buffer_date == date(2026, 10, 17)
    assert "Time and Materials" in baseline_guided.commercial_guardrails.contract_type_implication

    # Test Elevated Tier + Fixed Bid
    charter_elevated = CharterExtraction(
        project_name="Elevated Project",
        governance_tier="Elevated",
        contract_type="Fixed Bid",
        source_reference=sample_source_ref
    )
    baseline_elevated = aggregator.aggregate(
        charter=charter_elevated,
        deliverables_ext=delivs,
        milestones_ext=milestones,
        raid_ext=raid
    )

    # Elevated buffer is 10 days: 2026-10-20 - 10 days = 2026-10-10
    assert baseline_elevated.milestones[0].internal_buffer_date == date(2026, 10, 10)
    assert "Fixed Bid" in baseline_elevated.commercial_guardrails.contract_type_implication
    assert len(baseline_elevated.communications_plan) >= 3  # Daily standup or MBR added for Elevated
