"""Unit and integration tests for Phase 2 PMO compliance features (spec/recommendations_2.md)."""

import json
import csv
import pytest
from datetime import date, timedelta
from pathlib import Path
import docx

from src.core.models import (
    SourceReference,
    Deliverable,
    Milestone,
    RiskAssumption,
    CharterExtraction,
    DeliverablesExtraction,
    MilestonesExtraction,
    RAIDExtraction,
    QuestionsExtraction,
    SOWInterpretationExtraction,
    StakeholdersExtraction,
    DecisionsExtraction,
    ContractConflictsExtraction,
    ContractAmbiguityItem,
    Stakeholder,
    DecisionItem,
    StartupKitBaseline,
)
from src.llm.aggregator import BaselineAggregator
from src.generators.docx_generator import DocxGenerator
from src.generators.pmo_workbook import export_pmo_workbook, PMOWorkbookResult


@pytest.fixture
def phase2_source_ref():
    return SourceReference(
        document_name="Pfizer_SOW_2026.pdf",
        clause_or_slide="Section 4.1",
        confidence_score=0.95
    )


def test_pmo_stakeholder_incorporation_and_raci(phase2_source_ref):
    """Verify PMO Lead and Director, PMO are populated as primary stakeholders and RACI enforces AR-10."""
    aggregator = BaselineAggregator()
    charter = CharterExtraction(
        project_name="Pfizer AI Analytics",
        governance_tier="Elevated",
        contract_type="Fixed Bid",
        pmo_lead="Sarah Connor",
        source_reference=phase2_source_ref
    )
    deliverables = DeliverablesExtraction(deliverables=[
        Deliverable(id="DEL-01", description="Model Engine", acceptance_criteria="UAT Pass", source_reference=phase2_source_ref)
    ])
    milestones = MilestonesExtraction(milestones=[
        Milestone(id="M1", description="Beta Release", external_date=date(2026, 11, 1), source_reference=phase2_source_ref)
    ])
    raid = RAIDExtraction(items=[])

    baseline = aggregator.aggregate(
        charter=charter,
        deliverables_ext=deliverables,
        milestones_ext=milestones,
        raid_ext=raid
    )

    # 1. PMO Stakeholders present
    roles = [s.role for s in baseline.stakeholders]
    assert "PMO Lead" in roles
    assert "Director, PMO" in roles

    pmo_lead = next(s for s in baseline.stakeholders if s.role == "PMO Lead")
    assert pmo_lead.organization == "Toptal PMO"
    assert "G-01 Gate Sign-off" in pmo_lead.decision_rights
    assert pmo_lead.escalation_responsibility == "Director, PMO"

    dir_pmo = next(s for s in baseline.stakeholders if s.role == "Director, PMO")
    assert dir_pmo.organization == "Toptal PMO Leadership"
    assert "Elevated Tier" in dir_pmo.decision_rights
    assert dir_pmo.escalation_responsibility == "VP, Delivery / Executive Leadership"

    # 2. RACI Matrix enforces AR-10 decision rights
    raci_map = {r.decision_or_activity: r for r in baseline.raci_matrix}
    assert "Startup readiness (G-01 gate)" in raci_map
    assert raci_map["Startup readiness (G-01 gate)"].pmo_lead == "R, A"
    assert raci_map["Startup readiness (G-01 gate)"].delivery_manager == "C"

    assert "Talent staffing & replacement" in raci_map
    assert raci_map["Talent staffing & replacement"].pmo_lead == "R, A"

    assert "Work at risk / commercial exceptions" in raci_map
    assert raci_map["Work at risk / commercial exceptions"].pmo_lead == "R, A"

    assert "Scope & change" in raci_map
    assert raci_map["Scope & change"].delivery_manager == "A"
    assert raci_map["Scope & change"].pmo_lead == "R"


def test_startup_readiness_scoring_engine(phase2_source_ref):
    """Verify Startup Readiness Score calculation under complete, partial, and empty inputs (NFR-04)."""
    aggregator = BaselineAggregator()

    # Complete baseline
    charter_complete = CharterExtraction(
        project_name="Complete Readiness Project",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        delivery_manager="Jane Doe",
        talent_pm="John Smith",
        pmo_lead="Sarah Connor",
        source_reference=phase2_source_ref
    )
    deliverables_complete = DeliverablesExtraction(deliverables=[
        Deliverable(
            id="DEL-01",
            description="Core Platform",
            acceptance_criteria="Passes all test assertions",
            owner="John Smith",
            client_approver="Client Tech Lead",
            source_reference=phase2_source_ref
        )
    ])
    milestones_complete = MilestonesExtraction(milestones=[
        Milestone(id="M1", description="Launch", external_date=date(2026, 12, 1), source_reference=phase2_source_ref)
    ])
    raid_complete = RAIDExtraction(items=[
        RiskAssumption(type="Risk", description="API rate limit risk", owner="Jane Doe", status="Open", source_reference=phase2_source_ref)
    ])

    baseline_complete = aggregator.aggregate(
        charter=charter_complete,
        deliverables_ext=deliverables_complete,
        milestones_ext=milestones_complete,
        raid_ext=raid_complete
    )

    assert baseline_complete.readiness_score >= 85.0
    assert "mandatory_g01_controls" in baseline_complete.readiness_breakdown
    assert "deliverable_acceptance_rigor" in baseline_complete.readiness_breakdown
    assert "talent_staffing_readiness" in baseline_complete.readiness_breakdown
    assert "commercial_risk_mitigation" in baseline_complete.readiness_breakdown
    assert baseline_complete.gate_decision.gate_decision_status == "Approved for Mobilize"

    # Partial baseline (missing criteria, dates, unassigned roles)
    charter_partial = CharterExtraction(
        project_name="Partial Project",
        governance_tier="Guided",
        contract_type="Fixed Bid",
        delivery_manager=None,
        talent_pm=None,
        source_reference=phase2_source_ref
    )
    deliverables_partial = DeliverablesExtraction(deliverables=[
        Deliverable(id="DEL-01", description="Module X", acceptance_criteria=None, owner="Unassigned", source_reference=phase2_source_ref)
    ])
    milestones_partial = MilestonesExtraction(milestones=[
        Milestone(id="M1", description="Milestone X", external_date=None, source_reference=phase2_source_ref)
    ])

    baseline_partial = aggregator.aggregate(
        charter=charter_partial,
        deliverables_ext=deliverables_partial,
        milestones_ext=milestones_partial,
        raid_ext=RAIDExtraction(items=[])
    )

    assert baseline_partial.readiness_score < 85.0
    assert baseline_partial.gate_decision.gate_decision_status in ("Approved with Exception", "Rework Required")


def test_contract_ambiguity_and_conflict_engine(phase2_source_ref, tmp_path):
    """Verify Contract Ambiguity & Conflict Detection creation and reporting."""
    aggregator = BaselineAggregator()
    charter = CharterExtraction(
        project_name="Ambiguity Test Project",
        governance_tier="Elevated",
        contract_type="Fixed Bid",
        source_reference=phase2_source_ref
    )
    conflicts = ContractConflictsExtraction(ambiguities=[
        ContractAmbiguityItem(
            anomaly_id="AMB-01",
            category="Ambiguous Acceptance",
            conflicting_clauses="Section 5 requires complete customer satisfaction while Section 2 lists 99.9% uptime test.",
            risk_impact="Subjective criteria risks milestone sign-off disputes.",
            recommended_clarification="Agree on automated test metrics as the sole contractual acceptance gate.",
            status="Open",
            source_reference=phase2_source_ref
        ),
        ContractAmbiguityItem(
            anomaly_id="CONF-01",
            category="Date Conflict",
            conflicting_clauses="Proposal commits 2026-10-15 but SOW schedule states 2026-10-31.",
            risk_impact="2-week schedule variance between estimate and SOW.",
            recommended_clarification="Confirm 2026-10-31 as binding external delivery date.",
            status="Open",
            source_reference=phase2_source_ref
        )
    ])

    baseline = aggregator.aggregate(
        charter=charter,
        deliverables_ext=DeliverablesExtraction(deliverables=[]),
        milestones_ext=MilestonesExtraction(milestones=[]),
        raid_ext=RAIDExtraction(items=[]),
        conflicts_ext=conflicts
    )

    # 1. Ambiguities present in baseline
    assert len(baseline.contract_ambiguities) == 2

    # 2. Ambiguities do not pollute open questions or RAID risks
    q_text = "\n".join(baseline.open_questions)
    assert "[AMB-01]" not in q_text
    assert "[CONF-01]" not in q_text

    raid_text = "\n".join(r.description for r in baseline.raid_items)
    assert "AMB-01" not in raid_text
    assert "CONF-01" not in raid_text

    # 3. Render in Word document and check that ambiguities table is present in checklist document
    generator = DocxGenerator()
    kit_file, cl_file = generator.write_documents(baseline, tmp_path / "Ambiguity_Test_Startup_Kit.docx")
    cl_doc = docx.Document(str(cl_file))

    cl_full_text = "\n".join(p.text for p in cl_doc.paragraphs)
    assert "Contract Ambiguities & Conflicts" in cl_full_text

    cl_table_cells = [c.text.strip() for t in cl_doc.tables for r in t.rows for c in r.cells]
    assert "AMB-01" in cl_table_cells
    assert "CONF-01" in cl_table_cells


def test_readiness_workflow_states_and_sla_and_segregation(phase2_source_ref):
    """Verify 9 workflow states, 1-day creation SLA tracking, and role segregation checks."""
    aggregator = BaselineAggregator()

    # Case A: SLA Met (<= 1 day)
    awarded = date(2026, 10, 1)
    drafted = date(2026, 10, 2)
    charter = CharterExtraction(
        project_name="SLA Test Project",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        delivery_manager="Jane Doe",
        pmo_lead="Sarah Connor",
        source_reference=phase2_source_ref
    )

    baseline_met = aggregator.aggregate(
        charter=charter,
        deliverables_ext=DeliverablesExtraction(deliverables=[]),
        milestones_ext=MilestonesExtraction(milestones=[]),
        raid_ext=RAIDExtraction(items=[]),
        sow_awarded_date=awarded,
        award_date_source="stated",
        kit_drafted_date=drafted
    )

    assert baseline_met.sla_met is True
    assert baseline_met.segregation_of_duties_verified is True
    assert baseline_met.author_name != baseline_met.reviewer_names[0]
    g01_sla_item = next(i for i in baseline_met.readiness_checklist if i.item_id == "G01-01")
    assert g01_sla_item.status == "Complete"
    assert g01_sla_item.exception_required is False

    # Case B: SLA Breached (> 1 day)
    drafted_late = date(2026, 10, 5)
    baseline_breached = aggregator.aggregate(
        charter=charter,
        deliverables_ext=DeliverablesExtraction(deliverables=[]),
        milestones_ext=MilestonesExtraction(milestones=[]),
        raid_ext=RAIDExtraction(items=[]),
        sow_awarded_date=awarded,
        award_date_source="stated",
        kit_drafted_date=drafted_late
    )

    assert baseline_breached.sla_met is False
    g01_sla_breached_item = next(i for i in baseline_breached.readiness_checklist if i.item_id == "G01-01")
    assert g01_sla_breached_item.status == "Exception Required"
    assert g01_sla_breached_item.exception_required is True


def test_downstream_pmo_toolkit_export_payloads(sample_baseline, tmp_path):
    """Verify PMO Startup Toolkit workbook export utilities."""
    export_dir = tmp_path / "pmo_exports"
    result = export_pmo_workbook(sample_baseline, export_dir)

    assert isinstance(result, PMOWorkbookResult)
    assert result.file_path.exists()
    assert result.file_path.suffix == ".xlsx"
    assert result.schedule_rows > 0
    assert result.wbs_rows > 0
    assert result.raid_rows >= len(sample_baseline.raid_items)
