"""Comprehensive test suite for in-table action embedding and closed-loop score remediation."""

import copy
from datetime import date
from pathlib import Path
import docx
import pytest

from src.core.models import (
    StartupKitBaseline,
    ProjectStartupCharter,
    Deliverable,
    Milestone,
    TalentMember,
    TalentOnboardingRecord,
    RiskAssumption,
    SourceReference,
    ReadinessChecklistItem,
    ActionRequiredItem,
    GateDecision,
    CommercialGuardrail,
    SOWInterpretationSummary,
    ContractAmbiguityItem,
    GovernanceContext,
    WorkPackageSeed,
    DependencyAssumptionItem,
)
from src.scoring.readiness_engine import ReadinessScoringEngine
from src.generators.docx_generator import DocxGenerator
from src.extractors.startup_kit_docx_parser import StartupKitDocxParser
from src.orchestrator import StartupKitController


@pytest.fixture
def mock_source_ref() -> SourceReference:
    return SourceReference(
        document_name="SOW_Enterprise_Modernization.pdf",
        clause_or_slide="Section 3.2",
        confidence_score=0.95
    )


@pytest.fixture
def baseline_with_all_action_types(mock_source_ref: SourceReference) -> StartupKitBaseline:
    """Creates a baseline with open deficiencies across all 4 scoring dimensions."""
    checklist = [
        ReadinessChecklistItem(
            item_id=f"G01-{i:02d}",
            gate_criterion=f"Control criterion {i}",
            related_section4_artifact="Section 4 Artifact",
            owner="PMO Lead",
            reviewer="Delivery Manager",
            approver="PMO Director",
            status="Complete" if i not in (3, 4, 5, 8, 12, 14) else "Exception Required",
            exception_required=(i in (3, 4, 5, 8, 12, 14)),
            evidence_summary="Initial baseline draft"
        )
        for i in range(1, 16)
    ]

    deliverables = [
        Deliverable(
            id="DEL-01",
            name="Architecture & API Blueprint",
            description="Complete microservices blueprint",
            source_reference=mock_source_ref,
            owner="Unassigned",
            acceptance_criteria="[CONFIRMATION REQUIRED]",
            client_approver="[UNASSIGNED - TO BE CONFIRMED]",
        ),
        Deliverable(
            id="DEL-02",
            name="Production CI/CD Automation",
            description="Automated deployment pipeline",
            source_reference=mock_source_ref,
            owner="Sarah Jenkins",
            acceptance_criteria="All automated tests pass with 90% coverage",
            client_approver="VP Engineering",
        )
    ]

    milestones = [
        Milestone(
            id="M01",
            description="Architecture Review Sign-off",
            external_date=None,  # Unconfirmed date
            internal_buffer_date=None,
            owner="Delivery Manager",
            source_reference=mock_source_ref
        ),
        Milestone(
            id="M02",
            description="Sprint 1 Mobilize",
            external_date=date(2026, 11, 1),
            internal_buffer_date=date(2026, 10, 25),
            owner="Delivery Manager",
            source_reference=mock_source_ref
        )
    ]

    roster = [
        TalentMember(
            role="Lead Cloud Architect",
            name="[UNASSIGNED - TO BE CONFIRMED]",
            required_skills="AWS, Terraform, Python",
            status="Pending"
        ),
        TalentMember(
            role="Senior DevOps Engineer",
            name="Marcus Vance",
            required_skills="Docker, Kubernetes, GitHub Actions",
            status="Confirmed"
        )
    ]

    raid = [
        RiskAssumption(
            id="RSK-01",
            type="Risk",
            description="Client API access delays",
            severity="High",
            impact="Schedule Slippage",
            mitigation_or_response="Active monitoring",
            owner="Unassigned",
            status="Open",
            source_reference=mock_source_ref
        )
    ]

    ambiguities = [
        ContractAmbiguityItem(
            anomaly_id="ANOM-01",
            category="Milestone Conflict",
            conflicting_clauses="Clause 3.1 vs Clause 9.4 date discrepancy",
            risk_impact="Late delivery penalty exposure",
            recommended_clarification="Execute formal clarification addendum",
            source_reference=mock_source_ref
        )
    ]

    commercial = CommercialGuardrail(
        contract_type_implication="Fixed Bid - Strict Scope Control",
        approved_work_rule="Only explicit SOW deliverables",
        non_approved_work_rule="Stop work on out-of-scope requests",
        work_at_risk_rule="Zero work-at-risk without written PMO authorization",
        change_control_trigger="Any deviation > 5 engineering days",
        change_order_route="Formal PCR sign-off by Client Sponsor",
        budget_baseline="[NOT STATED]",
        variance_indicator="[TBD]",
        margin_risk_indicator="High",
        escalation_threshold="Budget variance > 10%",
        source_reference=mock_source_ref
    )

    sow = SOWInterpretationSummary(
        contracted_deliverables=["Architecture & API Blueprint", "Production CI/CD Automation"],
        out_of_scope_items=["Legacy mainframe migration"],
        customer_obligations=["[CONFIRMATION REQUIRED]"],
        assumptions=["Client will provide cloud sandbox within 5 business days"],
        constraints=["All code must deploy in US-East region"],
        platform_environment_commitments=["AWS Enterprise Account"],
        dependencies=["Client IdP integration"],
        approval_expectations="5-day formal review window",
        ambiguity_notes=["Milestone date mismatch in SOW Clause 3.1"],
        source_reference=mock_source_ref
    )

    backlog = [
        WorkPackageSeed(
            id="WP-01",
            parent_deliverable_id="DEL-01",
            title="Core Architecture Modules",
            preliminary_sequence=1,
            owner="[UNASSIGNED - TO BE CONFIRMED]",
            status="Draft",
            source_reference=mock_source_ref
        )
    ]

    dependencies_assumptions = [
        DependencyAssumptionItem(
            id="DEP-01",
            type="Dependency",
            description="Client IAM and AWS Account Provisioning",
            owner="[UNASSIGNED - TO BE CONFIRMED]",
            status="Open",
            source_reference=mock_source_ref
        )
    ]

    baseline = StartupKitBaseline(
        project_name="Enterprise Cloud Migration",
        governance_tier="Partnered",
        contract_type="Fixed Bid",
        author_name="PMO Lead",
        reviewer_names=["Delivery Manager", "Talent PM"],
        concurring_approver_name="PMO Director",
        sla_met=True,
        readiness_checklist=checklist,
        deliverables=deliverables,
        milestones=milestones,
        backlog_seed=backlog,
        dependencies_assumptions=dependencies_assumptions,
        talent_onboarding=TalentOnboardingRecord(
            pmo_lead="PMO Lead",
            delivery_manager="Delivery Manager",
            talent_pm="Talent PM",
            delivery_talent_roster=roster,
            source_reference=mock_source_ref
        ),
        raid_items=raid,
        contract_ambiguities=ambiguities,
        commercial_guardrails=commercial,
        sow_interpretation=sow,
        open_questions=["Confirm client environment provisioning date", "Clarify SLA waiver scope"]
    )

    # Compute initial scores and actions
    return ReadinessScoringEngine.evaluate_and_rescore(baseline)


def test_in_table_annotations_and_shading_rendering(baseline_with_all_action_types: StartupKitBaseline, tmp_path: Path):
    """Verify that generated Word document contains in-table action tags and warning shading across all tables."""
    generator = DocxGenerator()
    doc_path = generator.write_docx(baseline_with_all_action_types, tmp_path)

    doc = docx.Document(str(doc_path))
    tables = doc.tables

    # 1. Deliverables table verification
    deliv_table = next(
        t for t in tables
        if any("acceptance criteria" in c.text.lower() for c in t.rows[0].cells)
    )
    # Row 1 (DEL-01) must have [ACT- in acceptance criteria and owner
    row_deliv = deliv_table.rows[1]
    assert "[ACT-" in row_deliv.cells[2].text
    assert "[ACT-" in row_deliv.cells[5].text

    # 2. Milestones table verification
    ms_table = next(
        t for t in tables
        if any("milestone id" in c.text.lower() for c in t.rows[0].cells)
    )
    row_ms = ms_table.rows[1]
    assert "[ACT-" in row_ms.cells[2].text

    # 3. Talent roster table verification
    roster_table = next(
        t for t in tables
        if any("named talent" in c.text.lower() for c in t.rows[0].cells)
    )
    row_roster = roster_table.rows[1]
    assert "[ACT-" in row_roster.cells[1].text

    # 4. RAID log table verification
    raid_table = next(
        t for t in tables
        if any("mitigation / response" in c.text.lower() for c in t.rows[0].cells)
    )
    row_raid = raid_table.rows[1]
    assert "[ACT-" in row_raid.cells[3].text

    # 5. SOW interpretation summary table verification
    sow_table = next(
        t for t in tables
        if any("sow interpretation dimension" in c.text.lower() for c in t.rows[0].cells)
    )
    sow_text = " ".join(c.text for r in sow_table.rows for c in r.cells)
    assert "[ACT-" in sow_text

    # 7. Scope decomposition table verification
    wp_table = next(
        t for t in tables
        if any("wp id" in c.text.lower() for c in t.rows[0].cells)
    )
    row_wp = wp_table.rows[1]
    assert "[ACT-" in row_wp.cells[4].text

    # 8. Dependency and assumption log verification
    da_table = next(
        t for t in tables
        if any("item id" in c.text.lower() for c in t.rows[0].cells)
    )
    row_da = da_table.rows[1]
    assert "[ACT-" in row_da.cells[4].text or "[ACT-" in row_da.cells[5].text

    # 9. Commercial guardrails table verification (removed from report)
    assert not any(
        any("commercial guardrail area" in c.text.lower() for c in t.rows[0].cells)
        for t in tables
    )


def test_artifact_banners_rendered_for_active_actions(baseline_with_all_action_types: StartupKitBaseline, tmp_path: Path):
    """Verify that in-table action annotations are rendered with action details and score recovery deltas."""
    generator = DocxGenerator()
    doc_path = generator.write_docx(baseline_with_all_action_types, tmp_path)

    doc = docx.Document(str(doc_path))
    doc_text = " ".join(p.text for p in doc.paragraphs) + " " + " ".join(
        c.text for tbl in doc.tables for r in tbl.rows for c in r.cells
    )

    # Deliverables in-table action annotations
    assert "Deliverables and Acceptance Matrix" in doc_text
    assert "ACT-" in doc_text
    assert "Score Recovery" in doc_text or "Recovery" in doc_text


def test_table_cell_remediation_rescores_to_green(baseline_with_all_action_types: StartupKitBaseline, tmp_path: Path):
    """Verify that directly editing table cells in the Word document recalculates scores and elevates gate to Green."""
    generator = DocxGenerator()
    initial_doc_path = generator.write_docx(baseline_with_all_action_types, tmp_path)

    initial_score = baseline_with_all_action_types.readiness_score
    assert initial_score < 70.0
    assert baseline_with_all_action_types.gate_decision.gate_decision_status == "Rework Required"

    # Simulate stakeholder editing the generated Word document directly
    doc = docx.Document(str(initial_doc_path))

    # 1. Edit Deliverables table: assign owner and confirm criteria
    deliv_table = next(
        t for t in doc.tables
        if any("acceptance criteria" in c.text.lower() for c in t.rows[0].cells)
    )
    deliv_table.rows[1].cells[2].text = "Architecture blueprint reviewed and signed off by Enterprise Architecture Board"
    deliv_table.rows[1].cells[4].text = "VP Engineering"
    deliv_table.rows[1].cells[5].text = "Sarah Jenkins"

    # 2. Edit Milestone table: set confirmed external date
    ms_table = next(
        t for t in doc.tables
        if any("milestone id" in c.text.lower() for c in t.rows[0].cells)
    )
    ms_table.rows[1].cells[2].text = "2026-10-15"
    ms_table.rows[1].cells[3].text = "2026-10-08"

    # 3. Edit Talent Roster: assign named talent and mark Staffed
    roster_table = next(
        t for t in doc.tables
        if any("named talent" in c.text.lower() for c in t.rows[0].cells)
    )
    roster_table.rows[1].cells[1].text = "Alex Chen"
    roster_table.rows[1].cells[3].text = "Confirmed"

    # 4. Edit RAID Log: assign owner and concrete mitigation
    raid_table = next(
        t for t in doc.tables
        if any("mitigation / response" in c.text.lower() for c in t.rows[0].cells)
    )
    raid_table.rows[1].cells[3].text = "Marcus Vance"
    raid_table.rows[1].cells[4].text = "Pre-provisioned local mock container environment"

    # 5. Edit G-01 Checklist Table: mark items Complete
    checklist_file = tmp_path / "Enterprise_Cloud_Migration_Startup_Readiness_Checklist.docx"
    if checklist_file.exists():
        cl_doc = docx.Document(str(checklist_file))
        checklist_table = next(
            (t for t in cl_doc.tables if any("gate criterion" in c.text.lower() for c in t.rows[0].cells)),
            None
        )
        if checklist_table:
            for row in checklist_table.rows[1:]:
                row.cells[3].text = "Complete"
                row.cells[7].text = "Fully remediated and aligned with stakeholders"
            cl_doc.save(str(tmp_path / "Edited_Startup_Kit_Startup_Readiness_Checklist.docx"))

    # Save edited Word document
    edited_doc_path = tmp_path / "Edited_Startup_Kit.docx"
    doc.save(str(edited_doc_path))

    # Re-ingest and rescore
    parser = StartupKitDocxParser()
    rescored_baseline = parser.parse_startup_kit_docx(edited_doc_path)
    rescored_baseline = ReadinessScoringEngine.evaluate_and_rescore(rescored_baseline)

    # Assert elevated readiness score
    assert rescored_baseline.readiness_score > initial_score
    assert rescored_baseline.readiness_score >= 85.0
    assert rescored_baseline.gate_decision.gate_decision_status == "Approved for Mobilize"

    # Assert resolved actions are cleared
    assert len(rescored_baseline.action_required_items) < len(baseline_with_all_action_types.action_required_items)

    # Verify that clean extracted data has no lingering action tags
    assert "[ACT-" not in rescored_baseline.deliverables[0].acceptance_criteria
    assert "[ACT-" not in rescored_baseline.deliverables[0].owner
    assert rescored_baseline.deliverables[0].owner == "Sarah Jenkins"
    assert rescored_baseline.milestones[0].external_date == date(2026, 10, 15)
    assert rescored_baseline.talent_onboarding.delivery_talent_roster[0].name == "Alex Chen"
    assert rescored_baseline.talent_onboarding.delivery_talent_roster[0].status == "Confirmed"


def test_reingestion_tag_sanitization_robustness(tmp_path: Path):
    """Verify that various forms of [ACT-XX] badges are completely sanitized during docx parsing."""
    src_ref = SourceReference(document_name="SOW.pdf", clause_or_slide="C1", confidence_score=1.0)
    baseline = StartupKitBaseline(
        project_name="Sanitization Test Project",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        deliverables=[
            Deliverable(
                id="DEL-01",
                name="Deliverable 1",
                description="Deliverable 1",
                source_reference=src_ref,
                owner="John Doe [ACT-03]",
                acceptance_criteria="Standard acceptance criteria [ACT-03: Assign Owner]",
                client_approver="Approver [ACT-XX]",
            )
        ],
        milestones=[
            Milestone(
                id="M01",
                description="Milestone 1",
                external_date=date(2026, 12, 1),
                owner="Delivery Manager [ACT-04]",
                source_reference=src_ref
            )
        ]
    )

    generator = DocxGenerator()
    doc_path = generator.write_docx(baseline, tmp_path)

    parser = StartupKitDocxParser()
    parsed = parser.parse_startup_kit_docx(doc_path)

    d = parsed.deliverables[0]
    assert "[ACT-" not in d.owner
    assert "[ACT-" not in d.acceptance_criteria
    assert "[ACT-" not in d.client_approver
    assert d.owner == "John Doe"
    assert "Standard acceptance criteria" in d.acceptance_criteria


def test_reingestion_idempotence_on_unedited_document(baseline_with_all_action_types: StartupKitBaseline, tmp_path: Path):
    """Verify that re-ingesting an unedited document yields mathematically identical scores down to 0.1%."""
    generator = DocxGenerator()
    doc_path = generator.write_docx(baseline_with_all_action_types, tmp_path)

    parser = StartupKitDocxParser()
    parsed = parser.parse_startup_kit_docx(doc_path)
    rescored = ReadinessScoringEngine.evaluate_and_rescore(parsed)

    assert abs(rescored.readiness_score - baseline_with_all_action_types.readiness_score) < 0.2
    assert rescored.gate_decision.gate_decision_status == baseline_with_all_action_types.gate_decision.gate_decision_status
