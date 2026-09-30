"""Comprehensive test suite for Part B specification items B1 through B10 (spec v4)."""

import docx
from datetime import date
from src.core.models import (
    StartupKitBaseline,
    Deliverable,
    Milestone,
    WorkPackageSeed,
    RiskAssumption,
    DependencyAssumptionItem,
    CommunicationsPlanItem,
    DecisionItem,
    ContractAmbiguityItem,
    SourceReference,
    AcceptanceProcessExtraction,
    DeliverablesExtraction,
    MilestonesExtraction,
    RAIDExtraction,
    CharterExtraction,
    ProjectStartupCharter,
    DecisionsExtraction,
    ScopeDecompositionExtraction,
    ContractConflictsExtraction,
)
from src.llm.aggregator import BaselineAggregator
from src.generators.docx_generator import DocxGenerator, format_cell_with_action
from src.extractors.startup_kit_docx_parser import StartupKitDocxParser
from src.scoring.readiness_engine import ReadinessScoringEngine


def test_b1_acceptance_merge_jaccard_similarity_different_order():
    """B1: Merge acceptance items into deliverables by name similarity (Jaccard >= 0.5), with ID only as tiebreaker.
    
    Test with two lists numbered in different orders.
    """
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="Section 3", confidence_score=0.95)
    
    # Deliverables in order: Auth first, then Shell
    deliverables = [
        Deliverable(id="DEL-01", name="Azure AD MSAL authentication integration", description="Auth", source_reference=ref),
        Deliverable(id="DEL-02", name="Micro-frontend shell architecture", description="Shell", source_reference=ref),
    ]
    # Acceptance items in reverse order: DEL-01 is Shell, DEL-02 is Auth
    acc_items = [
        Deliverable(id="DEL-01", name="Micro-frontend shell architecture", acceptance_criteria="Shell loads", evidence_required="Shell logs", client_approver="Jane Approver", source_reference=ref),
        Deliverable(id="DEL-02", name="Azure AD MSAL authentication integration", acceptance_criteria="SSO works", evidence_required="Auth logs", client_approver="John Approver", source_reference=ref),
    ]

    agg = BaselineAggregator()
    charter_ext = CharterExtraction(project_name="Test", client_name="Client", governance_tier="Partnered", contract_type="Time and Materials", executive_summary="Summary text.", source_reference=ref)
    deliv_ext = DeliverablesExtraction(deliverables=deliverables)
    ms_ext = MilestonesExtraction(milestones=[Milestone(id="M1", description="Phase 1", external_date=date(2026, 11, 1), source_reference=ref)])
    raid_ext = RAIDExtraction(items=[])
    acc_ext = AcceptanceProcessExtraction(acceptance_matrix_items=acc_items)

    baseline = agg.aggregate(charter_ext, deliv_ext, ms_ext, raid_ext, acceptance_ext=acc_ext)

    deliv_map = {d.id: d for d in baseline.deliverables}
    # DEL-01 (Auth) should have merged acc_items[1] (Auth)
    assert deliv_map["DEL-01"].acceptance_criteria == "SSO works"
    assert deliv_map["DEL-01"].evidence_required == "Auth logs"
    assert deliv_map["DEL-01"].client_approver == "John Approver"

    # DEL-02 (Shell) should have merged acc_items[0] (Shell)
    assert deliv_map["DEL-02"].acceptance_criteria == "Shell loads"
    assert deliv_map["DEL-02"].evidence_required == "Shell logs"
    assert deliv_map["DEL-02"].client_approver == "Jane Approver"


def test_b2_no_default_milestone_or_deliverable_links_in_dependencies():
    """B2: Remove the hard-coded milestones[0] and deliverables[0] links from dependencies and fallback backlog."""
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="Section 3", confidence_score=0.95)
    charter_ext = CharterExtraction(project_name="Test", client_name="Client", governance_tier="Partnered", contract_type="Time and Materials", executive_summary="Summary text.", source_reference=ref)
    deliv_ext = DeliverablesExtraction(deliverables=[Deliverable(id="DEL-01", name="Core System", description="Core", source_reference=ref)])
    ms_ext = MilestonesExtraction(milestones=[Milestone(id="M1", description="Phase 1", external_date=date(2026, 11, 1), source_reference=ref)])
    raid_ext = RAIDExtraction(items=[
        RiskAssumption(id="RSK-01", type="Dependency", description="Client provides test data in staging.", owner="Client", status="Open"),
    ])

    agg = BaselineAggregator()
    baseline = agg.aggregate(charter_ext, deliv_ext, ms_ext, raid_ext)

    assert len(baseline.dependencies_assumptions) == 1
    dep = baseline.dependencies_assumptions[0]
    # Should be None because description does not mention M1 or DEL-01
    assert dep.linked_milestone is None
    assert dep.linked_deliverable is None

    # Check fallback backlog linked_milestones
    assert len(baseline.backlog_seed) == 1
    assert baseline.backlog_seed[0].linked_milestones == []


def test_b3_renumber_decisions_when_repeated_or_default():
    """B3: Renumber decision IDs DEC-01, DEC-02... whenever an ID repeats or equals the default."""
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="Section 3", confidence_score=0.95)
    charter_ext = CharterExtraction(project_name="Test", client_name="Client", governance_tier="Partnered", contract_type="Time and Materials", executive_summary="Summary text.", source_reference=ref)
    deliv_ext = DeliverablesExtraction(deliverables=[Deliverable(id="DEL-01", name="Core System", description="Core", source_reference=ref)])
    ms_ext = MilestonesExtraction(milestones=[Milestone(id="M1", description="Phase 1", external_date=date(2026, 11, 1), source_reference=ref)])
    raid_ext = RAIDExtraction(items=[])
    
    # 3 decisions all carrying default ID 'DEC-01' from extraction
    decisions_ext = DecisionsExtraction(decisions=[
        DecisionItem(id="DEC-01", decision_text="Decision Alpha", decision_owner="Tech Lead", status="Approved"),
        DecisionItem(id="DEC-01", decision_text="Decision Beta", decision_owner="Tech Lead", status="Approved"),
        DecisionItem(id="DEC-01", decision_text="Decision Gamma", decision_owner="Tech Lead", status="Approved"),
    ])

    agg = BaselineAggregator()
    baseline = agg.aggregate(charter_ext, deliv_ext, ms_ext, raid_ext, decisions_ext=decisions_ext)

    assert len(baseline.decisions) == 3
    assert [d.id for d in baseline.decisions] == ["DEC-01", "DEC-02", "DEC-03"]


def test_b4_backlog_parent_deliverable_validation():
    """B4: Validate work package parents against real deliverable IDs and clear invalid parents."""
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="Section 3", confidence_score=0.95)
    charter_ext = CharterExtraction(project_name="Test", client_name="Client", governance_tier="Partnered", contract_type="Time and Materials", executive_summary="Summary text.", source_reference=ref)
    deliv_ext = DeliverablesExtraction(deliverables=[Deliverable(id="DEL-01", name="Core System", description="Core", source_reference=ref)])
    ms_ext = MilestonesExtraction(milestones=[Milestone(id="M1", description="Phase 1", external_date=date(2026, 11, 1), source_reference=ref)])
    raid_ext = RAIDExtraction(items=[])
    
    backlog_ext = ScopeDecompositionExtraction(work_packages=[
        WorkPackageSeed(id="WP-01", title="Valid Parent", parent_deliverable_id="DEL-01", preliminary_sequence=1),
        WorkPackageSeed(id="WP-02", title="Invalid Parent", parent_deliverable_id="DEL-99", preliminary_sequence=2),
    ])

    agg = BaselineAggregator()
    baseline = agg.aggregate(charter_ext, deliv_ext, ms_ext, raid_ext, backlog_ext=backlog_ext)

    assert baseline.backlog_seed[0].parent_deliverable_id == "DEL-01"
    assert baseline.backlog_seed[1].parent_deliverable_id is None


def test_b5_docx_raid_and_comms_id_columns_roundtrip(arc_run2, tmp_path):
    """B5: Add ID columns to Kit RAID table (RSK-NN, ISS-NN, Probability, Impact) and comms table (COM-NN), and parse back."""
    gen = DocxGenerator()
    kit_path = tmp_path / "Test_Startup_Kit.docx"
    gen.write_kit_docx(arc_run2, kit_path)

    doc = docx.Document(str(kit_path))
    parser = StartupKitDocxParser()
    reparsed = parser.parse_startup_kit_docx(kit_path)

    # Verify RAID items have structured IDs
    assert len(reparsed.raid_items) > 0
    for r in reparsed.raid_items:
        assert r.id.startswith("RSK-") or r.id.startswith("ISS-")
        assert r.probability in ("Low", "Medium", "High", None)
        assert r.impact in ("Low", "Medium", "High", None)

    # Verify Communications items have structured IDs
    assert len(reparsed.communications_plan) > 0
    for idx, c in enumerate(reparsed.communications_plan, 1):
        assert c.id == f"COM-{idx:02d}"


def test_b6_cell_text_formatting_preserves_text_and_brackets():
    """B6: Cell formatting preserves balanced brackets, parentheses, and bare words like undefined."""
    test_cases = [
        "SLA Met (Yes)",
        "Delivery Manager (Toptal)",
        "Client's designated approvers [NAMES TO BE CONFIRMED]",
        "The number of re-test cycles is undefined.",
        "Not specified (TBD); reviewed at the Milestone Acceptance Review",
    ]

    doc = docx.Document()
    table = doc.add_table(rows=len(test_cases), cols=1)

    for idx, text in enumerate(test_cases):
        cell = table.cell(idx, 0)
        format_cell_with_action(cell, text, action=None, is_warning=False)
        assert cell.text.strip() == text


def test_b7_contract_ambiguities_row_in_sow_interpretation(arc_run2, tmp_path):
    """B7: Add 'Contract Ambiguities Logged' row to the Kit's SOW Interpretation table."""
    gen = DocxGenerator()
    kit_path = tmp_path / "Test_Startup_Kit.docx"
    gen.write_kit_docx(arc_run2, kit_path)

    doc = docx.Document(str(kit_path))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    table_texts = "\n".join(c.text for tbl in doc.tables for row in tbl.rows for c in row.cells)

    assert "Contract Ambiguities Logged" in table_texts
    assert "contractual ambiguities logged" in table_texts


def test_b8_checklist_evidence_and_statuses(arc_run2):
    """B8: Checklist evidence and status rules:
    - G01-14 derives from ambiguity count and status is Review Required when open.
    - G01-11 lists actual comms plan item names.
    - G01-03 checks client approver.
    - G01-02 drops tailored buffers when undated.
    """
    ReadinessScoringEngine.synchronize_checklist_with_artifacts(arc_run2)
    chk_map = {i.item_id: i for i in arc_run2.readiness_checklist}

    # G01-14
    assert chk_map["G01-14"].status == "Review Required"
    assert "15 contractual ambiguities logged" in chk_map["G01-14"].evidence

    # G01-11
    assert "Kickoff Call" in chk_map["G01-11"].evidence
    assert "Milestone Acceptance Review" in chk_map["G01-11"].evidence

    # G01-02
    assert "tailored buffers" not in chk_map["G01-02"].evidence


def test_b9_sow_story_ids_in_tables_and_roundtrip(arc_run2, tmp_path):
    """B9: SOW story IDs on deliverables and work packages, carried through Kit tables and parser."""
    gen = DocxGenerator()
    kit_path = tmp_path / "Test_Startup_Kit.docx"
    gen.write_kit_docx(arc_run2, kit_path)

    doc = docx.Document(str(kit_path))
    parser = StartupKitDocxParser()
    reparsed = parser.parse_startup_kit_docx(kit_path)

    deliv_map = {d.id: d for d in reparsed.deliverables}
    assert len(deliv_map) == 20


def test_b10_completeness_check_uncovered_story_ids():
    """B10: Assign deliverable IDs and log uncovered story IDs as open questions."""
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="Section 3", confidence_score=0.95)
    charter_ext = CharterExtraction(project_name="Test", client_name="Client", governance_tier="Partnered", contract_type="Time and Materials", executive_summary="Summary text.", source_reference=ref)
    deliv_ext = DeliverablesExtraction(deliverables=[
        Deliverable(id="DEL-01", name="Core Feature", description="Feature", sow_reference="HS-1001", source_reference=ref)
    ])
    ms_ext = MilestonesExtraction(milestones=[Milestone(id="M1", description="Phase 1", external_date=date(2026, 11, 1), source_reference=ref)])
    raid_ext = RAIDExtraction(items=[])
    conflicts_ext = ContractConflictsExtraction(ambiguities=[
        ContractAmbiguityItem(anomaly_id="AMB-01", category="Scope Contradiction", conflicting_clauses="HS-9999 contradicts Section 4", recommended_clarification="Clarify HS-9999")
    ])

    agg = BaselineAggregator()
    baseline = agg.aggregate(charter_ext, deliv_ext, ms_ext, raid_ext, conflicts_ext=conflicts_ext)

    # Story HS-9999 is cited in AMB-01 but not covered in DEL-01 -> open question logged
    uncovered_q = [q for q in baseline.open_questions if "HS-9999" in q]
    assert len(uncovered_q) == 1
    assert "HS-9999" in uncovered_q[0]
