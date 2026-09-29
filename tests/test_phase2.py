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
from src.generators.export_payloads import (
    export_all_pmo_tools,
    export_raid_csv,
    export_decision_log_csv,
    export_milestone_plan_json,
    export_psa_seed_json,
    export_budget_burndown_seed_json,
)


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
    """Verify Contract Ambiguity & Conflict Detection creation and reporting are removed."""
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

    # 1. Ambiguities creation removed from baseline
    assert len(baseline.contract_ambiguities) == 0

    # 2. Ambiguities do not feed into open questions or RAID risks or action items
    q_text = "\n".join(baseline.open_questions)
    assert "[AMB-01]" not in q_text
    assert "[CONF-01]" not in q_text

    raid_text = "\n".join(r.description for r in baseline.raid_items)
    assert "AMB-01" not in raid_text
    assert "CONF-01" not in raid_text

    assert not any("Contract Ambiguity" in a.related_artifact for a in baseline.action_required_items)

    # 3. Render in Word document and check that ambiguities table is not present
    generator = DocxGenerator()
    out_file = generator.write_docx(baseline, tmp_path / "out")
    doc = docx.Document(str(out_file))

    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Contractual Ambiguities & Conflict Analysis" not in full_text

    all_table_cells = []
    for t in doc.tables:
        for r in t.rows:
            all_table_cells.extend(c.text.strip() for c in r.cells)

    assert "AMB-01" not in all_table_cells
    assert "CONF-01" not in all_table_cells


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
        kit_drafted_date=drafted_late
    )

    assert baseline_breached.sla_met is False
    g01_sla_breached_item = next(i for i in baseline_breached.readiness_checklist if i.item_id == "G01-01")
    assert g01_sla_breached_item.status == "Exception Required"
    assert g01_sla_breached_item.exception_required is True


def test_downstream_pmo_toolkit_export_payloads(sample_baseline, tmp_path):
    """Verify downstream PMO Operating System workbook toolkit export utilities (NFR-09)."""
    export_dir = tmp_path / "pmo_exports"
    results = export_all_pmo_tools(sample_baseline, export_dir)

    assert "raid_csv" in results
    assert "decision_log_csv" in results
    assert "milestone_plan_json" in results
    assert "psa_seed_json" in results
    assert "budget_burndown_seed_json" in results

    # 1. Verify RAID CSV
    raid_file = results["raid_csv"]
    assert raid_file.exists()
    assert raid_file.suffix == ".csv"
    with open(raid_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) >= len(sample_baseline.raid_items)
        assert "ID" in reader.fieldnames
        assert "Type" in reader.fieldnames
        assert "Mitigation_Response" in reader.fieldnames

    # 2. Verify Decision Log CSV
    dec_file = results["decision_log_csv"]
    assert dec_file.exists()
    with open(dec_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert "Decision_Text" in reader.fieldnames
        assert "Decision_Owner" in reader.fieldnames

    # 3. Verify Milestone Plan JSON
    ms_file = results["milestone_plan_json"]
    assert ms_file.exists()
    with open(ms_file, "r", encoding="utf-8") as f:
        ms_data = json.load(f)
        assert ms_data["project_name"] == sample_baseline.project_name
        assert "milestones" in ms_data
        assert len(ms_data["milestones"]) == len(sample_baseline.milestones)
        assert "internal_buffer_date" in ms_data["milestones"][0]

    # 4. Verify PSA Seed JSON
    psa_file = results["psa_seed_json"]
    assert psa_file.exists()
    with open(psa_file, "r", encoding="utf-8") as f:
        psa_data = json.load(f)
        assert psa_data["project_name"] == sample_baseline.project_name
        assert "readiness_score" in psa_data
        assert "leadership_roles" in psa_data
        assert "pmo_lead" in psa_data["leadership_roles"]

    # 5. Verify Budget Burndown Seed JSON
    bb_file = results["budget_burndown_seed_json"]
    assert bb_file.exists()
    with open(bb_file, "r", encoding="utf-8") as f:
        bb_data = json.load(f)
        assert bb_data["project_name"] == sample_baseline.project_name
        assert "commercial_guardrails" in bb_data
        assert "contract_type_implication" in bb_data["commercial_guardrails"]
