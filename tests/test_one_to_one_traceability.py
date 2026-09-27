"""Comprehensive Unit & Integration Test Suite for 1-to-1 Traceability.

Validates the 4 core recommendations:
1. Defect-Driven Action Generation (Cell-level discrete defect identification)
2. Unique Cell-to-Action Binding without Broadcasting (Zero duplicate [ACT-XX] badges across cells/tables)
3. Exact Marginal Score Attribution (score recovery deltas and composite score boost)
4. Automated Status Synchronization During Re-ingestion (Cell resolution clears action and gate exception)
"""

import re
import pytest
import docx
from datetime import date
from pathlib import Path

from src.core.models import (
    SourceReference,
    ProjectStartupCharter,
    GovernanceContext,
    Deliverable,
    Milestone,
    RiskAssumption,
    TalentOnboardingRecord,
    TalentMember,
    ReadinessChecklistItem,
    StartupKitBaseline,
    ContractAmbiguityItem,
    CommercialGuardrail,
    SOWInterpretationExtraction,
    SOWInterpretationSummary,
)
from src.generators.docx_generator import DocxGenerator
from src.extractors.startup_kit_docx_parser import StartupKitDocxParser
from src.scoring.readiness_engine import ReadinessScoringEngine
from src.llm.aggregator import BaselineAggregator


@pytest.fixture
def multi_defect_baseline() -> StartupKitBaseline:
    """Create a baseline with multiple distinct cell defects across different tables."""
    ref = SourceReference(document_name="SOW_Enterprise.pdf", clause_or_slide="Sec 3.2", confidence_score=0.95)
    charter = ProjectStartupCharter(
        project_name="Multi-Cloud Analytics",
        client_name="Global Health",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        delivery_manager="Jane Doe",
        talent_pm="John Smith",
        pmo_lead="Sarah Connor",
        project_purpose="Clinical data modern analytics pipeline migration.",
        delivery_model="Toptal Partnered Delivery",
        governance_model="PMO Weekly PSR",
        escalation_path="TPM -> DM -> PMO Lead",
        unresolved_assumptions_status="Logged in RAID",
        delivery_objectives=["Deploy AWS infrastructure", "Automate clinical pipelines"],
        success_criteria=["Zero data loss", "Full compliance sign-off"],
        high_level_scope=["Data pipeline", "Cloud infra"],
        exclusions=["Decommissioning on-prem"],
        source_reference=ref
    )
    gov_ctx = GovernanceContext(
        project_name="Multi-Cloud Analytics",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        client_name="Global Health",
        delivery_manager="Jane Doe",
        talent_pm="John Smith",
        pmo_lead="Sarah Connor",
        workflow_state="Ready for G-01 Gate Review",
        sla_met=True
    )
    deliverables = [
        Deliverable(
            id="DEL-01",
            name="Cloud Security Architecture",
            description="Cloud Security Architecture",
            source_reference=ref,
            owner="Talent PM",
            acceptance_criteria="Approved by Architecture Board",
            client_approver="Chief Security Officer"
        ),
        Deliverable(
            id="DEL-02",
            name="Automated Ingestion Pipeline",
            description="Automated Ingestion Pipeline",
            source_reference=ref,
            owner="Unassigned",  # Defect 1: Unassigned deliverable owner
            acceptance_criteria="[CONFIRMATION REQUIRED]",  # Defect 2: Missing acceptance criteria
            client_approver="Chief Data Officer"
        ),
        Deliverable(
            id="DEL-03",
            name="Regulatory Validation Matrix",
            description="Regulatory Validation Matrix",
            source_reference=ref,
            owner="Talent PM",
            acceptance_criteria="[CONFIRMATION REQUIRED]",  # Defect 3: Missing acceptance criteria
            client_approver="Compliance Officer"
        )
    ]
    milestones = [
        Milestone(
            id="M1",
            description="Kickoff Baseline",
            external_date=date(2026, 10, 15),
            internal_buffer_date=date(2026, 10, 8),
            owner="Delivery Manager",
            source_reference=ref
        ),
        Milestone(
            id="M2",
            description="Production Deployment",
            external_date=None,  # Defect 4: Missing external date
            internal_buffer_date=None,
            owner="Delivery Manager",
            source_reference=ref
        )
    ]
    raid_items = [
        RiskAssumption(
            id="R-01",
            type="Risk",
            description="IAM provisioning delays by client",
            category="Cloud Security",
            owner="Unassigned",  # Defect 5: Unassigned risk owner
            probability="High",
            impact="High",
            severity="High",
            mitigation_or_response="[TBD]",  # Defect 6: Missing mitigation
            status="Open",
            source_reference=ref
        ),
        RiskAssumption(
            id="R-02",
            type="Risk",
            description="Third-party vendor API throttle limits",
            category="External API",
            owner="Unassigned",  # Defect 7: Second unassigned risk owner
            probability="Medium",
            impact="High",
            severity="Medium",
            mitigation_or_response="Implement rate limiting and caching",
            status="Open",
            source_reference=ref
        )
    ]
    talent_onboarding = TalentOnboardingRecord(
        pmo_lead="Sarah Connor",
        delivery_manager="Jane Doe",
        talent_pm="John Smith",
        delivery_talent_roster=[
            TalentMember(role="Lead Data Engineer", name="Jane Specialist", required_skills="Python, Spark", status="Confirmed"),
            TalentMember(role="Cloud Architect", name="[UNASSIGNED - TO BE CONFIRMED]", required_skills="AWS, Terraform", status="Pending")  # Defect 8: Unstaffed role
        ],
        source_reference=ref
    )
    contract_ambiguities = [
        ContractAmbiguityItem(
            anomaly_id="AMB-01",
            category="Ambiguous Acceptance",
            conflicting_clauses="Section 4.2 subjective sign-off vs Section 2.1 automated test suites.",
            risk_impact="Risk of prolonged review cycle.",
            recommended_clarification="Align sign-off to automated pytest pass criteria.",
            status="Open",
            source_reference=ref
        )
    ]
    checklist = [
        ReadinessChecklistItem(
            item_id=f"G01-{i:02d}",
            gate_criterion=f"Gate Criterion {i}",
            related_section4_artifact="Artifact",
            owner="Sarah Connor",
            reviewer="Jane Doe",
            approver="Sarah Connor",
            status="Complete" if i not in (3, 4, 5, 8, 14) else "Exception Required",
            evidence=f"Evidence for criterion {i}",
            exception_required=(i in (3, 4, 5, 8, 14)),
            exception_details=f"Open exception on G01-{i:02d}" if i in (3, 4, 5, 8, 14) else None,
            approval_status="Approved" if i not in (3, 4, 5, 8, 14) else "Exception Required"
        )
        for i in range(1, 16)
    ]

    base = StartupKitBaseline(
        project_name="Multi-Cloud Analytics",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        charter=charter,
        governance_context=gov_ctx,
        deliverables=deliverables,
        milestones=milestones,
        raid_items=raid_items,
        talent_onboarding=talent_onboarding,
        contract_ambiguities=contract_ambiguities,
        readiness_checklist=checklist,
        open_questions=[
            "Confirm Pfizer UAT sign-off criteria for automated data pipeline.",
            "Validate whether staging environment is provided by client."
        ],
        author_name="Sarah Connor",
        delivery_manager_name="Jane Doe",
        talent_pm_name="John Smith",
    )
    return base


# =============================================================================
# Recommendation 1: Defect-Driven Action Generation
# =============================================================================
def test_defect_driven_action_generation(multi_defect_baseline: StartupKitBaseline):
    """Verify that discrete ActionRequiredItems are generated for specific cell-level defects."""
    actions = ReadinessScoringEngine.generate_action_required_items(multi_defect_baseline)
    assert len(actions) > 0

    # Ensure every action item contains discrete location metadata
    for act in actions:
        assert act.action_id.startswith("ACT-")
        assert act.target_table_title, f"Action {act.action_id} must have a target table title"
        assert act.target_column_header, f"Action {act.action_id} must have a target column header"
        assert act.owner, f"Action {act.action_id} must have an assigned owner"
        assert act.score_recovery_delta > 0.0, f"Action {act.action_id} must have a positive recovery delta"

    # Verify specific entity defect mappings
    deliv_act = next((a for a in actions if a.checklist_id == "G01-03"), None)
    assert deliv_act is not None
    assert deliv_act.target_table_title == "Deliverables and Acceptance Matrix"
    assert deliv_act.target_entity_id in ("DEL-02", "DEL-03")

    ms_act = next((a for a in actions if a.checklist_id == "G01-04"), None)
    assert ms_act is not None
    assert ms_act.target_table_title == "Milestone Delivery Plan"
    assert ms_act.target_entity_id == "M2"

    raid_act = next((a for a in actions if a.checklist_id == "G01-05"), None)
    assert raid_act is not None
    assert raid_act.target_table_title == "RAID Log"

    roster_act = next((a for a in actions if a.checklist_id == "G01-08"), None)
    assert roster_act is not None
    assert roster_act.target_table_title == "Talent Onboarding Record"
    assert roster_act.target_entity_id == "Cloud Architect"


# =============================================================================
# Recommendation 2: Unique Cell-to-Action Binding (No Broadcasting)
# =============================================================================
def test_unique_cell_to_action_binding_no_broadcasting(multi_defect_baseline: StartupKitBaseline, tmp_path: Path):
    """Verify that no action badge is broadcasted across multiple distinct cells or tables."""
    aggregator = BaselineAggregator()
    baseline = aggregator.recalculate_readiness(multi_defect_baseline)

    generator = DocxGenerator()
    out_file = generator.write_docx(baseline, tmp_path / "One_To_One_Traceability_Doc.docx")
    assert out_file.exists()

    doc = docx.Document(str(out_file))

    # Exclude metadata, gate decision, action required, and checklist tables
    artifact_tables = [
        t for t in doc.tables[3:]
        if not any(c.text.strip() == "Action ID" for c in t.rows[0].cells)
        and not any("gate criterion" in c.text.lower() for c in t.rows[0].cells)
    ]

    import re
    act_badge_regex = re.compile(r'\[(ACT-\d{2}):')

    # Collect all occurrences of action badges in Section 4 artifact tables
    seen_action_locations = {}  # act_id -> list of (table_idx, row_idx, col_idx)

    for t_idx, tbl in enumerate(artifact_tables):
        for r_idx, row in enumerate(tbl.rows[1:], start=1):
            for c_idx, cell in enumerate(row.cells):
                cell_text = cell.text.strip()
                matches = act_badge_regex.findall(cell_text)
                for act_id in matches:
                    seen_action_locations.setdefault(act_id, []).append((t_idx, r_idx, c_idx))

    # Strict 1-to-1 Verification: Every action ID appears in exactly ONE table cell in Section 4
    for act_id, locations in seen_action_locations.items():
        assert len(locations) == 1, (
            f"Action {act_id} violated 1-to-1 traceability by appearing {len(locations)} times at locations: {locations}"
        )


# =============================================================================
# Recommendation 3: Exact Marginal Score Attribution
# =============================================================================
def test_exact_marginal_score_attribution(multi_defect_baseline: StartupKitBaseline):
    """Verify that each action has a positive marginal score delta and composite score bounds hold."""
    aggregator = BaselineAggregator()
    baseline = aggregator.recalculate_readiness(multi_defect_baseline)

    initial_score = baseline.readiness_score
    total_delta = sum(a.score_recovery_delta for a in baseline.action_required_items)

    assert total_delta > 0.0
    # Invariant: current score + sum of recovery deltas <= 100.0
    assert round(initial_score + total_delta, 1) <= 100.0

    for act in baseline.action_required_items:
        assert act.score_recovery_delta >= 0.5, (
            f"Action {act.action_id} has invalid score recovery delta: {act.score_recovery_delta}"
        )


# =============================================================================
# Recommendation 4: Automated Status Synchronization During Re-ingestion
# =============================================================================
def test_automated_status_synchronization_during_reingestion(multi_defect_baseline: StartupKitBaseline, tmp_path: Path):
    """Verify that editing a flagged cell in Word clears the action, resolves gate exception, and improves score."""
    aggregator = BaselineAggregator()
    baseline = aggregator.recalculate_readiness(multi_defect_baseline)
    initial_score = baseline.readiness_score
    initial_actions_count = len(baseline.action_required_items)

    generator = DocxGenerator()
    doc_path = generator.write_docx(baseline, tmp_path / "Pre_Remediation_Doc.docx")

    # Simulate user editing the Word document to fix DEL-02 acceptance criteria and owner
    doc = docx.Document(str(doc_path))

    # 1. Remediate Deliverables table: fill DEL-02 criteria and owner
    deliv_table = next(
        t for t in doc.tables
        if any("acceptance criteria" in c.text.lower() for c in t.rows[0].cells)
    )
    for row in deliv_table.rows[1:]:
        if row.cells[0].text.strip() == "DEL-02":
            row.cells[2].text = "Objective UAT automated test suite passing with 100% assertions"
            row.cells[5].text = "Jane Specialist"
        elif row.cells[0].text.strip() == "DEL-03":
            row.cells[2].text = "Fully validated against 21 CFR Part 11 requirements"

    # 2. Remediate Milestone table: assign external date
    ms_table = next(
        t for t in doc.tables
        if any("milestone id" in c.text.lower() for c in t.rows[0].cells)
    )
    for row in ms_table.rows[1:]:
        if row.cells[0].text.strip() == "M2":
            row.cells[2].text = "2026-11-30"
            row.cells[3].text = "2026-11-23"

    # 3. Remediate Talent Roster: staff Cloud Architect
    roster_table = next(
        t for t in doc.tables
        if any("named talent" in c.text.lower() for c in t.rows[0].cells)
    )
    for row in roster_table.rows[1:]:
        if "cloud architect" in row.cells[0].text.lower():
            row.cells[1].text = "Robert Cloudmaster"
            row.cells[3].text = "Confirmed"

    # 4. Remediate RAID: assign owner and mitigation
    raid_table = next(
        t for t in doc.tables
        if any("mitigation / response" in c.text.lower() for c in t.rows[0].cells)
    )
    for row in raid_table.rows[1:]:
        if "IAM" in row.cells[1].text:
            row.cells[3].text = "Sarah Connor"
            row.cells[4].text = "Utilize local Terraform mock sandbox for sprint 1"

    # 5. Clear G-01 Checklist Exceptions in Checklist Table
    checklist_table = next(
        t for t in doc.tables
        if any("gate criterion" in c.text.lower() for c in t.rows[0].cells)
    )
    for row in checklist_table.rows[1:]:
        item_id = row.cells[0].text.strip()
        if item_id in ("G01-03", "G01-04", "G01-05", "G01-08"):
            row.cells[3].text = "Complete"
            row.cells[7].text = "Fully resolved and approved"

    remediated_doc_path = tmp_path / "Post_Remediation_Doc.docx"
    doc.save(str(remediated_doc_path))

    # Re-ingest and re-score
    parser = StartupKitDocxParser()
    parsed_baseline = parser.parse_startup_kit_docx(remediated_doc_path)
    rescored_baseline = aggregator.recalculate_readiness(parsed_baseline)

    # Assert score improved
    assert rescored_baseline.readiness_score > initial_score, (
        f"Score should have increased from {initial_score}, but got: {rescored_baseline.readiness_score}"
    )

    # Assert resolved actions were cleared
    assert len(rescored_baseline.action_required_items) < initial_actions_count

    # Assert G01-03 exception is cleared
    g01_03_item = next(i for i in rescored_baseline.readiness_checklist if i.item_id == "G01-03")
    assert not g01_03_item.exception_required
    assert g01_03_item.status == "Complete"

    # Assert DEL-02 clean extracted text
    deliv_02 = next(d for d in rescored_baseline.deliverables if d.id == "DEL-02")
    assert deliv_02.owner == "Jane Specialist"
    assert "Objective UAT" in deliv_02.acceptance_criteria
    assert "[ACT-" not in deliv_02.acceptance_criteria


# =============================================================================
# Cell Context & Defect-Action Alignment Verification
# =============================================================================
def test_cell_context_action_alignment(tmp_path: Path):
    """Verify that every [ACT-XX] action in a table cell directly relates to the issue in that cell."""
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="3.1", confidence_score=0.9)
    charter = ProjectStartupCharter(
        project_name="Context Alignment Test",
        client_name="Pfizer",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        delivery_manager="Jane Doe",
        talent_pm="John Smith",
        pmo_lead="Sarah Connor",
        project_purpose="Clinical Modernization",
        delivery_model="Toptal Partnered Delivery",
        governance_model="PMO Weekly PSR",
        escalation_path="TPM -> DM -> PMO Lead",
        unresolved_assumptions_status="Logged",
        delivery_objectives=["Deploy pipeline"],
        success_criteria=["Zero loss"],
        high_level_scope=["Cloud"],
        exclusions=["None"],
        source_reference=ref,
    )
    gov_ctx = GovernanceContext(
        project_name="Context Alignment Test",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        client_name="Pfizer",
        delivery_manager="Jane Doe",
        talent_pm="John Smith",
        pmo_lead="Sarah Connor",
        workflow_state="Ready for G-01 Gate Review",
        sla_met=True,
    )
    # DEL-01 is fully complete and assigned
    # DEL-02 has unassigned owner and missing criteria
    # DEL-03 has unconfirmed criteria
    deliverables = [
        Deliverable(
            id="DEL-01",
            name="Architecture Design",
            description="Architecture Design",
            source_reference=ref,
            owner="Talent PM",
            acceptance_criteria="Approved by Architecture Board",
            client_approver="Chief Architect",
        ),
        Deliverable(
            id="DEL-02",
            name="CI/CD Data Ingestion Pipeline",
            description="CI/CD Data Ingestion Pipeline",
            source_reference=ref,
            owner="Unassigned",
            acceptance_criteria="[CONFIRMATION REQUIRED]",
            client_approver="Data Lead",
        ),
        Deliverable(
            id="DEL-03",
            name="Compliance Documentation",
            description="Compliance Documentation",
            source_reference=ref,
            owner="Talent PM",
            acceptance_criteria="[CONFIRMATION REQUIRED]",
            client_approver="Compliance Officer",
        ),
    ]
    milestones = [
        Milestone(
            id="M1",
            description="Kickoff Baseline",
            external_date=date(2026, 10, 15),
            internal_buffer_date=date(2026, 10, 8),
            owner="Delivery Manager",
            source_reference=ref,
        ),
        Milestone(
            id="M2",
            description="Production Go-Live",
            external_date=None,  # Missing date
            internal_buffer_date=None,
            owner="Delivery Manager",
            source_reference=ref,
        ),
    ]
    raid_items = [
        RiskAssumption(
            type="Risk",
            description="IAM access delay",
            category="Technical",
            owner="Unassigned",
            mitigation_or_response="TBD",
            status="Open",
            source_reference=ref,
        )
    ]
    talent = TalentOnboardingRecord(
        talent_pm="John Smith",
        delivery_manager="Jane Doe",
        pmo_lead="Sarah Connor",
        delivery_talent_roster=[
            TalentMember(
                role="Data Engineer",
                name="[UNASSIGNED - TO BE CONFIRMED]",
                required_skills="Python, SQL",
                status="Pending",
            )
        ],
    )
    checklist = [
        ReadinessChecklistItem(
            item_id=f"G01-{i:02d}",
            gate_criterion=f"Control {i}",
            related_section4_artifact="Section 4 Artifact",
            owner="PMO Lead",
            approver="PMO Director",
            status="Approved" if i not in (3, 4, 5, 8) else "Exception Required",
            exception_required=i in (3, 4, 5, 8),
            exception_details="Defect noted" if i in (3, 4, 5, 8) else None,
        )
        for i in range(1, 16)
    ]

    base = StartupKitBaseline(
        project_name="Context Alignment Test",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        charter=charter,
        governance_context=gov_ctx,
        deliverables=deliverables,
        milestones=milestones,
        raid_items=raid_items,
        talent_onboarding=talent,
        readiness_checklist=checklist,
        open_questions=[
            "Confirm Pfizer UAT sign-off criteria for CI/CD pipeline.",
            "Clarify and confirm acceptance criteria for DEL-03.",
        ],
        author_name="Sarah Connor",
        delivery_manager_name="Jane Doe",
        talent_pm_name="John Smith",
    )

    aggregator = BaselineAggregator()
    baseline = aggregator.recalculate_readiness(base)

    generator = DocxGenerator()
    out_file = generator.write_docx(baseline, tmp_path / "Context_Alignment_Doc.docx")
    doc = docx.Document(str(out_file))

    # Find Deliverables table
    deliv_tbl = next(t for t in doc.tables if any("acceptance criteria" in c.text.lower() for c in t.rows[0].cells))

    # Row 1: DEL-01 (Fully complete)
    del_01_row = next(r for r in deliv_tbl.rows[1:] if r.cells[0].text.strip() == "DEL-01")
    assert "[ACT-" not in del_01_row.cells[2].text, f"DEL-01 Acceptance Criteria must not have actions: {del_01_row.cells[2].text}"
    assert "[ACT-" not in del_01_row.cells[5].text, f"DEL-01 Owner must NOT have DEL-03 action: {del_01_row.cells[5].text}"
    assert del_01_row.cells[5].text.strip() == "Talent PM"

    # Row 2: DEL-02 (Defect: criteria & owner)
    del_02_row = next(r for r in deliv_tbl.rows[1:] if r.cells[0].text.strip() == "DEL-02")
    assert "DEL-02" in del_02_row.cells[2].text or "pipeline" in del_02_row.cells[2].text.lower()
    assert "DEL-03" not in del_02_row.cells[2].text, "DEL-02 must NOT contain DEL-03 action"
    assert "DEL-03" not in del_02_row.cells[5].text, "DEL-02 owner must NOT contain DEL-03 action"

    # Row 3: DEL-03 (Defect: criteria)
    del_03_row = next(r for r in deliv_tbl.rows[1:] if r.cells[0].text.strip() == "DEL-03")
    assert "DEL-03" in del_03_row.cells[2].text, f"DEL-03 criteria must contain DEL-03 action: {del_03_row.cells[2].text}"
    assert "[ACT-" not in del_03_row.cells[5].text, f"DEL-03 Owner is assigned to Talent PM and must have no action: {del_03_row.cells[5].text}"
    assert del_03_row.cells[5].text.strip() == "Talent PM"

    # Find Milestone table
    ms_tbl = next(t for t in doc.tables if any("milestone id" in c.text.lower() for c in t.rows[0].cells))
    m1_row = next(r for r in ms_tbl.rows[1:] if r.cells[0].text.strip() == "M1")
    assert "[ACT-" not in m1_row.cells[2].text, "M1 date is locked and must have no action"
    assert "[ACT-" not in m1_row.cells[4].text, "M1 owner is assigned and must have no action"

    m2_row = next(r for r in ms_tbl.rows[1:] if r.cells[0].text.strip() == "M2")
    assert "M2" in m2_row.cells[2].text, f"M2 external date must have action for M2: {m2_row.cells[2].text}"


def test_strictly_one_action_per_cell_and_no_corrupted_tokens(tmp_path: Path):
    """Verifies that no table cell ever contains multiple actions or corrupted confirmation tags."""
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="3.1", confidence_score=0.9)
    charter = ProjectStartupCharter(
        project_name="Multi-Question Traceability Test",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        project_purpose="Clinical Modernization",
        delivery_manager="Jane Doe",
        talent_pm="John Smith",
        pmo_lead="Sarah Connor",
    )
    sow_interp = SOWInterpretationSummary(
        contracted_deliverables=["Cloud Architecture", "Data Pipeline", "Validation Report"],
        out_of_scope_items=["Legacy Cleanup"],
        customer_obligations=["Provide AWS account access and role credentials", "Deliver anonymized clinical test datasets", "Review deliverable submissions within 5 business days"],
        assumptions=["Standard assumptions"],
        constraints=["HIPAA"],
        platform_environment_commitments=["AWS"],
        dependencies=["EDC system access"],
        approval_expectations="Client sign-off in 5 days",
        ambiguity_notes=["Phase 2 Build Plan approval threshold undefined in Section 4.2 of SOW."],
    )
    deliverables = [
        Deliverable(
            id="DEL-01",
            name="Cloud Architecture & Security Design",
            description="Cloud Architecture & Security Design",
            source_reference=ref,
            owner="Talent PM",
            acceptance_criteria="[CONFIRMATION REQUIRED]",
            client_approver="Pfizer Chief Architect",
        ),
        Deliverable(
            id="DEL-02",
            name="Automated CI/CD Data Ingestion Pipeline",
            description="Automated CI/CD Data Ingestion Pipeline",
            source_reference=ref,
            owner="Unassigned",
            acceptance_criteria="[CONFIRMATION REQUIRED]",
            client_approver="Pfizer Data Engineering Lead",
        ),
        Deliverable(
            id="DEL-03",
            name="Validation and Compliance Documentation",
            description="Validation and Compliance Documentation",
            source_reference=ref,
            owner="Talent PM",
            acceptance_criteria="Signed off by Compliance Lead",
            client_approver="Pfizer Regulatory Officer",
        ),
    ]
    milestones = [
        Milestone(id="M1", description="Kickoff", external_date=date(2026, 10, 15), internal_buffer_date=date(2026, 10, 8), owner="Delivery Manager", source_reference=ref),
        Milestone(id="M2", description="Go-Live", external_date=None, internal_buffer_date=None, owner="Delivery Manager", source_reference=ref),
    ]
    checklist = [
        ReadinessChecklistItem(item_id=f"G01-{i:02d}", gate_criterion=f"Control {i}", related_section4_artifact="Section 4 Artifact", owner="PMO Lead", approver="PMO Director", status="Complete")
        for i in range(1, 16)
    ]
    checklist[2].status = "Exception Required"
    checklist[2].exception_required = True
    checklist[2].exception_details = "DEL-01 & DEL-02 missing acceptance criteria"

    many_questions = [
        "What are the specific acceptance criteria for each deliverable mentioned in the SOW?",
        "Can the exact milestone dates be confirmed, especially for those that are currently expected to occur on or around certain dates?",
        "What is the detailed Phase 2 Build Plan, and when will it be approved by Pfizer?",
        "What are the specific roles and responsibilities of the Toptal-sourced talent, and how will their performance be measured?",
        "What is the process for handling any deviations from the approved Phase 2 Build Plan?",
        "What are the specific standards and guidelines that Pfizer will provide to the Supplier, and when will these be available?",
        "What are the criteria for project acceptance, and how will it be determined that the final deliverable meets these criteria?",
        "What are the specific terms and conditions for the transition assistance if Pfizer decides to transition services to another supplier or internally?",
        "What are the specific change control procedures, and how will they be implemented throughout the project?",
        "What are the specific risks associated with the project, and what are the detailed mitigation plans for each?",
        "What are the specific assumptions underlying the project, and how will they be validated?",
        "What are the specific payment schedule and procedures, and how will they be managed?",
        "Clarify and confirm acceptance criteria for DEL-01.",
        "Clarify and confirm acceptance criteria for DEL-02.",
        "Clarify and confirm acceptance criteria for DEL-03.",
    ]

    baseline = StartupKitBaseline(
        project_name="Pfizer Multi Question Traceability",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        charter=charter,
        sow_interpretation=sow_interp,
        deliverables=deliverables,
        milestones=milestones,
        readiness_checklist=checklist,
        open_questions=many_questions,
        author_name="Sarah Connor",
        delivery_manager_name="Jane Doe",
        talent_pm_name="John Smith",
    )

    baseline = ReadinessScoringEngine.evaluate_and_rescore(baseline)
    output_file = tmp_path / "Multi_Question_Output.docx"
    DocxGenerator().write_docx(baseline, output_file)

    doc = docx.Document(str(output_file))

    # 1. Assert every table cell has at most ONE action badge
    action_badge_regex = re.compile(r'\[ACT(?:-REQ)?-[^\]]+\]')
    corrupted_tag_regex = re.compile(r'\[CONFIRMATION REQUIRED\]\s*\(\+\d+\.?\d*%\s*Recovery\)\]')

    for table_idx, tbl in enumerate(doc.tables):
        for row_idx, row in enumerate(tbl.rows):
            for cell_idx, cell in enumerate(row.cells):
                txt = cell.text
                badges = action_badge_regex.findall(txt)
                assert len(badges) <= 1, (
                    f"Table {table_idx} row {row_idx} col {cell_idx} contains multiple action badges: {badges}\nFull text: {txt}"
                )
                assert not corrupted_tag_regex.search(txt), (
                    f"Table {table_idx} row {row_idx} col {cell_idx} contains corrupted confirmation tag: {txt}"
                )

    # 2. Assert DEL-01 has exactly 1 action in Acceptance Criteria
    deliv_tbl = next(t for t in doc.tables if any("acceptance criteria" in c.text.lower() for c in t.rows[0].cells))
    del01_row = next(r for r in deliv_tbl.rows[1:] if r.cells[0].text.strip() == "DEL-01")
    del01_ac_badges = action_badge_regex.findall(del01_row.cells[2].text)
    assert len(del01_ac_badges) == 1, f"DEL-01 acceptance criteria must have exactly 1 action badge, found: {del01_ac_badges}"

    # 3. Assert Ambiguities cell has at most 1 action
    sow_tbl = next(t for t in doc.tables if any("sow interpretation" in c.text.lower() for c in t.rows[0].cells))
    amb_row = next(r for r in sow_tbl.rows[1:] if "ambiguities" in r.cells[0].text.lower())
    amb_badges = action_badge_regex.findall(amb_row.cells[1].text)
    assert len(amb_badges) <= 1, f"Ambiguities cell must have at most 1 action badge, found: {amb_badges}"

    # 4. Assert Customer Obligations has no corrupted tag or raw placeholder
    cust_row = next(r for r in sow_tbl.rows[1:] if "obligations" in r.cells[0].text.lower())
    assert "[CONFIRMATION REQUIRED] (+1.2% Recovery)]" not in cust_row.cells[1].text
    assert "CONFIRMATION REQUIRED" not in cust_row.cells[1].text


def test_customer_obligations_placeholder_subsumption_and_remediation(tmp_path: Path):
    """Verifies that [CONFIRMATION REQUIRED] in customer obligations is cleanly subsumed across all variants."""
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="3.1", confidence_score=0.9)
    charter = ProjectStartupCharter(
        project_name="Customer Obligations Edge Case Test",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        project_purpose="Testing",
        delivery_manager="Jane Doe",
        talent_pm="John Smith",
        pmo_lead="Sarah Connor",
    )

    test_variations = [
        # Case A: Explicit [CONFIRMATION REQUIRED] list item
        ["[CONFIRMATION REQUIRED]"],
        # Case B: Unbracketed CONFIRMATION REQUIRED
        ["CONFIRMATION REQUIRED"],
        # Case C: Multiple items with one unconfirmed
        ["Provide cloud accounts", "[CONFIRMATION REQUIRED]"],
        # Case D: Empty list
        [],
    ]

    for idx, obligations in enumerate(test_variations):
        sow_interp = SOWInterpretationSummary(
            contracted_deliverables=["Cloud Architecture"],
            out_of_scope_items=[],
            customer_obligations=obligations,
            assumptions=["Standard assumptions"],
            constraints=["Standard constraints"],
            platform_environment_commitments=["AWS"],
            dependencies=[],
            approval_expectations="Client sign-off in 5 days",
            ambiguity_notes=[],
        )
        checklist = [
            ReadinessChecklistItem(item_id=f"G01-{i:02d}", gate_criterion=f"Control {i}", related_section4_artifact="Section 4 Artifact", owner="PMO Lead", approver="PMO Director", status="Complete")
            for i in range(1, 16)
        ]
        baseline = StartupKitBaseline(
            project_name=f"Obligations Test {idx}",
            governance_tier="Partnered",
            contract_type="Time and Materials",
            charter=charter,
            sow_interpretation=sow_interp,
            deliverables=[Deliverable(id="DEL-01", name="Cloud Arch", description="Arch", source_reference=ref, owner="Talent PM", acceptance_criteria="Approved", client_approver="Pfizer Lead")],
            milestones=[Milestone(id="M1", description="Kickoff", external_date=date(2026, 10, 15), internal_buffer_date=date(2026, 10, 8), owner="Delivery Manager", source_reference=ref)],
            readiness_checklist=checklist,
            author_name="Sarah Connor",
            delivery_manager_name="Jane Doe",
            talent_pm_name="John Smith",
        )

        res_baseline = ReadinessScoringEngine.evaluate_and_rescore(baseline)
        output_file = tmp_path / f"Obligations_Test_{idx}.docx"
        DocxGenerator().write_docx(res_baseline, output_file)

        doc = docx.Document(str(output_file))
        sow_tbl = next(t for t in doc.tables if any("sow interpretation" in c.text.lower() for c in t.rows[0].cells))
        cust_row = next(r for r in sow_tbl.rows[1:] if "obligations" in r.cells[0].text.lower())
        cell_text = cust_row.cells[1].text

        # Assert no raw CONFIRMATION REQUIRED token appears in cell
        assert "CONFIRMATION REQUIRED" not in cell_text, f"Variation {idx} failed: {cell_text}"
        # Assert action badge is present
        assert "[ACT-" in cell_text or "[ACT-REQ-" in cell_text, f"Variation {idx} missing action badge: {cell_text}"
        # Assert no stray bullet point
        assert not cell_text.startswith("• [ACT-"), f"Variation {idx} has orphaned bullet point: {cell_text}"


def test_readiness_score_heading_action_highlighting_and_no_page_break(multi_defect_baseline, tmp_path: Path):
    """Verifies:
    1. 'Startup Kit Readiness Score: [score]%' heading is placed directly before 'Layer 1: Executive Startup Pack'.
    2. Every action tag in artifact table cells is highlighted with WD_COLOR_INDEX.YELLOW.
    3. No page break exists between the G-01 Gate Decision callout box and the Checklist table.
    4. No raw placeholders remain unreplaced.
    """
    from docx.enum.text import WD_COLOR_INDEX

    baseline = ReadinessScoringEngine.evaluate_and_rescore(multi_defect_baseline)
    output_file = tmp_path / "Readiness_Score_Heading_Highlight_Test.docx"
    DocxGenerator().write_docx(baseline, output_file)

    doc = docx.Document(str(output_file))

    # 1. Verify heading sequence
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert f"Startup Kit Readiness Score: {baseline.readiness_score:.1f}%" in full_text
    score_idx = full_text.find(f"Startup Kit Readiness Score: {baseline.readiness_score:.1f}%")
    layer1_idx = full_text.find("Layer 1: Executive Startup Pack")
    assert score_idx != -1
    assert layer1_idx != -1
    assert score_idx < layer1_idx, "Readiness Score heading must precede Layer 1 heading"

    # 2. Verify action tag runs are highlighted in yellow and cell background is not changed to warning color
    action_tag_regex = re.compile(r'\[(?:ACT|ACT-REQ)(?:-[A-Za-z0-9_]+)?(?::[^\n\]]*)?\]', re.IGNORECASE)
    highlighted_tag_count = 0

    for table_idx, tbl in enumerate(doc.tables):
        # Skip Action Required table where type column may use custom badges
        if any(c.text.strip() == "Action ID" for c in tbl.rows[0].cells):
            continue
        # Exclude header row
        for row_idx, row in enumerate(tbl.rows[1:], start=1):
            for cell_idx, cell in enumerate(row.cells):
                cell_text = cell.text.strip()
                assert "CONFIRMATION REQUIRED" not in cell_text.upper()
                if action_tag_regex.search(cell_text):
                    # Check that at least one run in this cell is highlighted in YELLOW
                    yellow_runs = [
                        r for p in cell.paragraphs for r in p.runs
                        if r.font.highlight_color == WD_COLOR_INDEX.YELLOW or r.font.highlight_color == 7
                    ]
                    assert len(yellow_runs) > 0, (
                        f"Table {table_idx} Row {row_idx} Col {cell_idx} with action tag '{cell_text}' "
                        f"does not have yellow highlighted run."
                    )
                    # Verify cell background is NOT changed to warning yellow/amber color (preserves original alternating background)
                    tcPr = cell._tc.get_or_add_tcPr()
                    w_shd = tcPr.find(docx.oxml.ns.qn("w:shd"))
                    fill_val = w_shd.get(docx.oxml.ns.qn("w:fill")) if w_shd is not None else None
                    assert fill_val != "FEF3C7", (
                        f"Table {table_idx} Row {row_idx} Col {cell_idx} with action tag '{cell_text}' "
                        f"has warning background shading '{fill_val}', but background should remain original."
                    )
                    highlighted_tag_count += 1

    assert highlighted_tag_count > 0, "Expected multiple highlighted action tags in artifact table cells"

    # 3. Verify no page break between Gate Decision callout box and Checklist table
    has_page_break = any('<w:br w:type="page"' in p._p.xml for p in doc.paragraphs)
    assert not has_page_break, "No page break should be inserted between G-01 Gate Decision and Checklist table"
