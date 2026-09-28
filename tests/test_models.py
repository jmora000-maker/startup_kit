"""Unit tests for Pydantic v2 data models and validation constraints."""

import pytest
from datetime import date
from pathlib import Path
from pydantic import ValidationError
from src.core.models import (
    DocumentSection,
    ExtractedDocument,
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


# ==========================================
# Extraction Models & PDF Invariants Tests
# ==========================================

def test_document_section_valid():
    """DocumentSection instantiates cleanly and matches model_dump."""
    sec = DocumentSection(title="Section 1", content="Hello world", metadata={"custom": 123})
    assert sec.title == "Section 1"
    assert sec.content == "Hello world"
    assert sec.metadata == {"custom": 123}
    assert sec.model_dump() == {
        "title": "Section 1",
        "content": "Hello world",
        "metadata": {"custom": 123}
    }


def test_document_section_extra_forbid():
    """Unknown top-level fields on DocumentSection raise ValidationError."""
    with pytest.raises(ValidationError):
        DocumentSection(title="A", content="B", unknown_field=123)


def test_extracted_document_path_coercion():
    """String file_path is automatically coerced to pathlib.Path."""
    doc = ExtractedDocument(
        file_name="test.txt",
        file_type="txt",
        file_path="C:/docs/test.txt",
        text_content="content"
    )
    assert isinstance(doc.file_path, Path)
    assert str(doc.file_path).replace("\\", "/") == "C:/docs/test.txt"


def test_model_default_isolation():
    """Independent instances have isolated default list and dict references."""
    sec1 = DocumentSection()
    sec2 = DocumentSection()
    sec1.metadata["key"] = "val"
    assert "key" not in sec2.metadata

    doc1 = ExtractedDocument(file_name="d1.txt", file_type="txt", file_path=Path("d1.txt"))
    doc2 = ExtractedDocument(file_name="d2.txt", file_type="txt", file_path=Path("d2.txt"))
    doc1.sections.append(sec1)
    doc1.metadata["key"] = "val"
    assert len(doc2.sections) == 0
    assert "key" not in doc2.metadata


def test_pdf_invariant_total_pages_mismatch():
    """PDF metadata total_pages mismatch with section count raises ValidationError mentioning file_name."""
    with pytest.raises(ValidationError, match="total_pages \\(2\\) does not match section count \\(1\\)"):
        ExtractedDocument(
            file_name="mismatch.pdf",
            file_type="pdf",
            file_path=Path("mismatch.pdf"),
            sections=[
                DocumentSection(
                    title="Page 1",
                    content="Text 1",
                    metadata={"page_number": 1, "rect": [0.0, 0.0, 100.0, 100.0]}
                )
            ],
            metadata={"total_pages": 2}
        )


def test_pdf_invariant_page_sequence_gap():
    """Gaps in page_number sequence raise ValidationError."""
    with pytest.raises(ValidationError, match="page_number 3, expected 2"):
        ExtractedDocument(
            file_name="gap.pdf",
            file_type="pdf",
            file_path=Path("gap.pdf"),
            sections=[
                DocumentSection(
                    title="Page 1",
                    content="Text 1",
                    metadata={"page_number": 1, "rect": [0.0, 0.0, 100.0, 100.0]}
                ),
                DocumentSection(
                    title="Page 3",
                    content="Text 3",
                    metadata={"page_number": 3, "rect": [0.0, 0.0, 100.0, 100.0]}
                ),
            ],
            metadata={"total_pages": 2}
        )


def test_pdf_invariant_page_sequence_dup():
    """Duplicate page numbers in sequence raise ValidationError."""
    with pytest.raises(ValidationError, match="page_number 1, expected 2"):
        ExtractedDocument(
            file_name="dup.pdf",
            file_type="pdf",
            file_path=Path("dup.pdf"),
            sections=[
                DocumentSection(
                    title="Page 1",
                    content="Text 1",
                    metadata={"page_number": 1, "rect": [0.0, 0.0, 100.0, 100.0]}
                ),
                DocumentSection(
                    title="Page 1",
                    content="Text 1 dup",
                    metadata={"page_number": 1, "rect": [0.0, 0.0, 100.0, 100.0]}
                ),
            ],
            metadata={"total_pages": 2}
        )


def test_pdf_invariant_page_sequence_swap():
    """Out-of-order page numbers raise ValidationError."""
    with pytest.raises(ValidationError, match="page_number 2, expected 1"):
        ExtractedDocument(
            file_name="swap.pdf",
            file_type="pdf",
            file_path=Path("swap.pdf"),
            sections=[
                DocumentSection(
                    title="Page 2",
                    content="Text 2",
                    metadata={"page_number": 2, "rect": [0.0, 0.0, 100.0, 100.0]}
                ),
                DocumentSection(
                    title="Page 1",
                    content="Text 1",
                    metadata={"page_number": 1, "rect": [0.0, 0.0, 100.0, 100.0]}
                ),
            ],
            metadata={"total_pages": 2}
        )


def test_pdf_invariant_zero_indexed_pages():
    """0-indexed page numbers raise ValidationError."""
    with pytest.raises(ValidationError):
        ExtractedDocument(
            file_name="zero_idx.pdf",
            file_type="pdf",
            file_path=Path("zero_idx.pdf"),
            sections=[
                DocumentSection(
                    title="Page 0",
                    content="Text 0",
                    metadata={"page_number": 0, "rect": [0.0, 0.0, 100.0, 100.0]}
                )
            ],
            metadata={"total_pages": 1}
        )


def test_pdf_validation_mutation_isolation():
    """Failed validation leaves caller's original DocumentSection unmutated."""
    orig_meta = {"page_number": 1, "rect": [0, 0, 100, 100], "unnormalized_key": 42}
    sec = DocumentSection(title="Page 1", content="Text", metadata=orig_meta)

    # Attempt to construct invalid document (total_pages=2 with 1 section)
    with pytest.raises(ValidationError):
        ExtractedDocument(
            file_name="isolation.pdf",
            file_type="pdf",
            file_path=Path("isolation.pdf"),
            sections=[sec],
            metadata={"total_pages": 2}
        )

    # Verify original section metadata is untouched
    assert sec.metadata == orig_meta
    assert sec.metadata["rect"] == [0, 0, 100, 100]  # Not mutated into floats in caller object


def test_flexible_date_and_schema_resilience():
    """Verify that descriptive dates, variations, and missing optional fields are parsed resiliently."""
    # 1. Descriptive non-ISO date string resolves to None without raising ValidationError
    ms = Milestone(id="MS-01", description="Beta Release", external_date="Mid-November 2026")
    assert ms.external_date is None

    # 2. ISO date string parses correctly
    ms2 = Milestone(id="MS-02", description="Launch", external_date="2026-11-30")
    assert ms2.external_date == date(2026, 11, 30)

    # 3. Empty string / None / TBD date resolves to None
    d = Deliverable(id="DEL-01", description="Architecture Doc", submission_target_date="")
    assert d.submission_target_date is None

    d_tbd = Deliverable(id="DEL-02", description="Test Doc", submission_target_date="TBD")
    assert d_tbd.submission_target_date is None

    # 4. Governance tier case tolerance
    charter = CharterExtraction(project_name="Test", governance_tier="guided")
    assert charter.governance_tier == "Guided"

    charter_partnered = CharterExtraction(project_name="Test", governance_tier="partnered tier")
    assert charter_partnered.governance_tier == "Partnered"

    # 5. RAID type normalization
    raid_item = RiskAssumption(type="risk", description="Security issue")
    assert raid_item.type == "Risk"

    dep_item = DependencyAssumptionItem(id="DEP-01", type="dependency", description="Network setup")
    assert dep_item.type == "Dependency"
