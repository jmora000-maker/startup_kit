"""Unit tests for Pydantic v2 data models and validation constraints."""

import pytest
from datetime import date
from pydantic import ValidationError
from src.core.models import (
    SourceReference,
    Deliverable,
    Milestone,
    RiskAssumption,
    DependencyAssumptionItem,
    DecisionItem,
    WorkPackageSeed,
    ProjectStartupCharter,
    SOWInterpretationSummary,
    CommunicationsPlanItem,
    Stakeholder,
    RACIItem,
    CommercialGuardrail,
    TalentMember,
    TalentOnboardingRecord,
    ReadinessChecklistItem,
    GateDecision,
    GovernanceContext,
    StartupKitBaseline,
    CharterExtraction,
    DeliverablesExtraction,
    MilestonesExtraction,
    RAIDExtraction,
    QuestionsExtraction,
    SOWInterpretationExtraction,
    ScopeDecompositionExtraction,
    AcceptanceProcessExtraction,
    StakeholdersExtraction,
    CommunicationsExtraction,
    CommercialGuardrailsExtraction,
    TalentOnboardingExtraction,
    DecisionsExtraction,
    ContractConflictsExtraction,
    ContractAmbiguityItem,
)


def test_source_reference_valid():
    ref = SourceReference(
        document_name="SOW.pdf",
        clause_or_slide="Section 2.1",
        confidence_score=0.85
    )
    assert ref.document_name == "SOW.pdf"
    assert ref.clause_or_slide == "Section 2.1"
    assert ref.confidence_score == 0.85


def test_source_reference_bounds():
    # Confidence score must be between 0.0 and 1.0
    with pytest.raises(ValidationError):
        SourceReference(document_name="SOW.pdf", confidence_score=-0.1)

    with pytest.raises(ValidationError):
        SourceReference(document_name="SOW.pdf", confidence_score=1.05)


def test_deliverable_defaults(sample_source_ref):
    deliv = Deliverable(
        id="DEL-01",
        description="Architecture Blueprint",
        source_reference=sample_source_ref
    )
    assert deliv.owner == "Unassigned"
    assert deliv.acceptance_criteria is None


def test_milestone_dates(sample_source_ref):
    ms = Milestone(
        id="M-01",
        description="Project Kickoff",
        external_date=date(2026, 10, 1),
        internal_buffer_date=date(2026, 9, 28),
        source_reference=sample_source_ref
    )
    assert ms.external_date == date(2026, 10, 1)
    assert ms.internal_buffer_date == date(2026, 9, 28)

    # Test string parsing
    ms_parsed = Milestone(
        id="M-02",
        description="Delivery",
        external_date="2026-11-01",
        source_reference=sample_source_ref
    )
    assert ms_parsed.external_date == date(2026, 11, 1)


def test_risk_assumption_types(sample_source_ref):
    for valid_type in ["Risk", "Assumption", "Issue", "Dependency"]:
        item = RiskAssumption(
            type=valid_type,
            description="Test item",
            source_reference=sample_source_ref
        )
        assert item.type == valid_type
        assert item.owner == "Unassigned"
        assert item.status == "Open"

    with pytest.raises(ValidationError):
        RiskAssumption(
            type="InvalidType",
            description="Test invalid item",
            source_reference=sample_source_ref
        )


def test_governance_context_tiers():
    for tier in ["Guided", "Partnered", "Elevated"]:
        ctx = GovernanceContext(
            project_name="Test Project",
            governance_tier=tier
        )
        assert ctx.governance_tier == tier

    with pytest.raises(ValidationError):
        GovernanceContext(
            project_name="Test Project",
            governance_tier="InvalidTier"
        )


def test_startup_kit_baseline_serialization(sample_baseline):
    json_str = sample_baseline.model_dump_json()
    assert "Pfizer Cloud Migration" in json_str
    assert "DEL-01" in json_str

    deserialized = StartupKitBaseline.model_validate_json(json_str)
    assert deserialized.project_name == sample_baseline.project_name
    assert len(deserialized.deliverables) == len(sample_baseline.deliverables)
    assert len(deserialized.milestones) == len(sample_baseline.milestones)
    assert len(deserialized.raid_items) == len(sample_baseline.raid_items)
    assert len(deserialized.open_questions) == len(sample_baseline.open_questions)


def test_domain_extraction_models(sample_source_ref, sample_deliverables, sample_milestones, sample_raid_items):
    charter = CharterExtraction(
        project_name="Test",
        client_name="Client X",
        governance_tier="Elevated",
        contract_type="Fixed Bid",
        source_reference=sample_source_ref
    )
    assert charter.governance_tier == "Elevated"

    deliv_ext = DeliverablesExtraction(deliverables=sample_deliverables)
    assert len(deliv_ext.deliverables) == 2

    ms_ext = MilestonesExtraction(milestones=sample_milestones)
    assert len(ms_ext.milestones) == 2

    raid_ext = RAIDExtraction(items=sample_raid_items)
    assert len(raid_ext.items) == 3

    q_ext = QuestionsExtraction(open_questions=["What is the budget?", "Who is the sponsor?"])
    assert len(q_ext.open_questions) == 2


def test_expanded_models_defaults_and_validation(sample_source_ref):
    # 1. ProjectStartupCharter
    charter = ProjectStartupCharter(project_name="New Project")
    assert charter.project_purpose == "[CONFIRMATION REQUIRED]"
    assert charter.delivery_manager == "[UNASSIGNED - TO BE CONFIRMED]"
    assert charter.talent_pm == "[UNASSIGNED - TO BE CONFIRMED]"
    assert charter.pmo_lead == "[UNASSIGNED - TO BE CONFIRMED]"

    # 2. SOWInterpretationSummary
    sow = SOWInterpretationSummary(
        contracted_deliverables=["DEL-01", "DEL-02"],
        approval_expectations="5 business days"
    )
    assert len(sow.contracted_deliverables) == 2
    assert sow.approval_expectations == "5 business days"

    # 3. WorkPackageSeed
    wp = WorkPackageSeed(
        id="WP-01",
        parent_deliverable_id="DEL-01",
        title="Infrastructure Setup"
    )
    assert wp.status == "Draft"
    assert wp.preliminary_sequence == 1

    # 4. DependencyAssumptionItem
    da = DependencyAssumptionItem(
        id="DEP-01",
        type="Dependency",
        description="AWS account access",
        source_reference=sample_source_ref
    )
    assert da.type == "Dependency"
    assert da.status == "Open"

    # 5. DecisionItem
    dec = DecisionItem(
        id="DEC-01",
        decision_text="Use Terraform for IaC",
        decision_owner="PMO Lead"
    )
    assert dec.status == "Approved"

    # 6. CommunicationsPlanItem
    com = CommunicationsPlanItem(
        id="COM-01",
        name="Weekly Status Report",
        audience="Client Sponsor",
        content_owner="Talent PM",
        cadence="Weekly"
    )
    assert com.cadence == "Weekly"

    # 7. Stakeholder and RACI
    stk = Stakeholder(name="Jane Doe", role="Delivery Manager")
    assert stk.organization == "Toptal"

    raci = RACIItem(decision_or_activity="G-01 Readiness Gate", pmo_lead="R, A")
    assert raci.pmo_lead == "R, A"

    # 8. CommercialGuardrail
    cg = CommercialGuardrail(
        contract_type_implication="Fixed Bid constraints",
        budget_baseline="$100,000"
    )
    assert cg.variance_indicator == "Green (<5% variance)"

    # 9. TalentOnboardingRecord
    talent = TalentOnboardingRecord(
        talent_pm="John Smith",
        delivery_talent_roster=[
            TalentMember(role="Tech Lead", name="Alice", required_skills="Python, AWS")
        ]
    )
    assert talent.team_baseline_review_confirmation is True
    assert len(talent.delivery_talent_roster) == 1

    # 10. ReadinessChecklistItem & GateDecision
    chk = ReadinessChecklistItem(
        item_id="G01-01",
        gate_criterion="Startup Kit created within 1 day",
        related_section4_artifact="Project Startup Charter",
        owner="PMO Lead",
        status="Complete"
    )
    assert chk.status == "Complete"

    gate = GateDecision(gate_decision_status="Ready for G-01 Gate Review")
    assert gate.approved_with_exception is False


def test_expanded_baseline_defaults():
    baseline = StartupKitBaseline(project_name="Baseline Default Test")
    assert baseline.project_name == "Baseline Default Test"
    assert baseline.governance_tier == "Partnered"
    assert baseline.contract_type == "Time and Materials"
    assert baseline.deliverables == []
    assert baseline.milestones == []
    assert baseline.raid_items == []
    assert baseline.open_questions == []
    assert baseline.backlog_seed == []
    assert baseline.dependencies_assumptions == []
    assert baseline.decisions == []
    assert baseline.communications_plan == []
    assert baseline.stakeholders == []
    assert baseline.raci_matrix == []
    assert baseline.readiness_checklist == []


def test_additional_extraction_schemas(sample_source_ref):
    sow_ext = SOWInterpretationExtraction(
        contracted_deliverables=["D1"],
        out_of_scope_items=["E1"],
        customer_obligations=["O1"],
        source_reference=sample_source_ref
    )
    assert len(sow_ext.contracted_deliverables) == 1

    wp_ext = ScopeDecompositionExtraction(
        work_packages=[
            WorkPackageSeed(id="WP-01", parent_deliverable_id="D1", title="WP Title")
        ]
    )
    assert len(wp_ext.work_packages) == 1

    stk_ext = StakeholdersExtraction(
        stakeholders=[Stakeholder(name="Jane", role="DM")]
    )
    assert len(stk_ext.stakeholders) == 1

    dec_ext = DecisionsExtraction(
        decisions=[DecisionItem(id="DEC-01", decision_text="Decision 1")]
    )
    assert len(dec_ext.decisions) == 1

    conf_ext = ContractConflictsExtraction(
        ambiguities=[
            ContractAmbiguityItem(
                anomaly_id="AMB-01",
                category="Scope Contradiction",
                conflicting_clauses="Section 1 vs Section 2",
                risk_impact="High risk of scope creep",
                recommended_clarification="Align scope boundaries",
                status="Open",
                source_reference=sample_source_ref
            )
        ]
    )
    assert len(conf_ext.ambiguities) == 1
    assert conf_ext.ambiguities[0].anomaly_id == "AMB-01"


def test_contract_ambiguity_model(sample_source_ref):
    item = ContractAmbiguityItem(
        anomaly_id="CONF-01",
        category="Date Conflict",
        conflicting_clauses="Proposal has 2026-10-15; SOW has 2026-10-31",
        risk_impact="Schedule mismatch",
        recommended_clarification="Confirm 2026-10-31",
        status="Open",
        source_reference=sample_source_ref
    )
    assert item.anomaly_id == "CONF-01"
    assert item.category == "Date Conflict"
    assert item.status == "Open"
