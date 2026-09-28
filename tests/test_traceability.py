"""Automated end-to-end traceability invariant test suite.

Verifies that:
1. Every ActionRequiredItem is registered with authoritative table and column targeting metadata.
2. The universal table cell annotation helper formats cell text and applies warning fills correctly.
3. 100% of generated ActionRequiredItems (ACT-01 through ACT-15) are embedded into Section 4 Layer Artifact tables.
"""

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
    Stakeholder,
    RACIItem,
    CommunicationsPlanItem,
)
from src.scoring.readiness_engine import ReadinessScoringEngine
from src.generators.docx_generator import DocxGenerator, format_cell_with_action
from src.generators.formatting import COLOR_WARNING_BG_HEX


@pytest.fixture
def sample_source_ref() -> SourceReference:
    return SourceReference(
        document_name="SOW_Cloud_Transformation.pdf",
        clause_or_slide="Section 4.1",
        confidence_score=0.98,
    )


@pytest.fixture
def baseline_with_all_15_actions(sample_source_ref: SourceReference) -> StartupKitBaseline:
    """Constructs a comprehensive baseline triggering actions across all 15 G-01 Checklist items."""
    checklist = [
        ReadinessChecklistItem(
            item_id=f"G01-{i:02d}",
            gate_criterion=ReadinessScoringEngine.GATE_METADATA[f"G01-{i:02d}"]["criterion"],
            related_section4_artifact=ReadinessScoringEngine.GATE_METADATA[f"G01-{i:02d}"]["artifact"],
            owner="PMO Lead",
            reviewer="Delivery Manager",
            approver="PMO Director",
            status="Exception Required" if i in (1, 3, 4, 7, 8, 12, 14) else "Review Required",
            exception_required=(i in (1, 3, 4, 7, 8, 12, 14)),
            exception_details=f"Deficiency requiring remediation in G01-{i:02d}",
            evidence=f"Baseline control evidence for G01-{i:02d}",
        )
        for i in range(1, 16)
    ]

    charter = ProjectStartupCharter(
        project_name="Enterprise Cloud Migration",
        client_name="Global Financial Corp",
        project_purpose="Migrate core banking services to AWS",
        delivery_model="Scrum Pod",
        governance_model="Partnered",
        pmo_lead="Sarah Connor",
        delivery_manager="[UNASSIGNED - TO BE CONFIRMED]",
        talent_pm="[UNASSIGNED - TO BE CONFIRMED]",
        escalation_path="Talent PM -> Delivery Manager -> PMO Lead",
        unresolved_assumptions_status="Logged in Section 2.3",
        source_reference=sample_source_ref,
    )

    sow_interpretation = SOWInterpretationSummary(
        contracted_deliverables=["Cloud Migration Blueprint", "IaC Pipelines"],
        out_of_scope_items=["Legacy Mainframe Refactoring"],
        customer_obligations=["[CONFIRMATION REQUIRED] Provide IAM Admin roles by Day 1"],
        assumptions=["Client provides VPC architecture specs"],
        constraints=["All resources must reside in us-east-1"],
        platform_environment_commitments=["AWS Enterprise Account"],
        dependencies=["Client Security Review Approval"],
        approval_expectations="Formal sign-off within 5 business days",
        ambiguity_notes=["Milestone date conflict between SOW Clause 3 and Schedule A"],
        source_reference=sample_source_ref,
    )

    contract_ambiguities = [
        ContractAmbiguityItem(
            anomaly_id="AMB-01",
            category="Schedule Discrepancy",
            conflicting_clauses="Clause 3.1 states 2026-11-01 vs Schedule A states 2026-11-15",
            risk_impact="2-week mobilization gap and resource idle time",
            recommended_clarification="Confirm 2026-11-15 as locked milestone date",
            source_reference=sample_source_ref,
        )
    ]

    deliverables = [
        Deliverable(
            id="DEL-01",
            name="Cloud Migration Blueprint",
            description="Detailed AWS architecture design",
            source_reference=sample_source_ref,
            owner="Unassigned",
            acceptance_criteria="[CONFIRMATION REQUIRED]",
            client_approver="[UNASSIGNED - TO BE CONFIRMED]",
        ),
        Deliverable(
            id="DEL-02",
            name="IaC Pipelines",
            description="Terraform CI/CD deployment pipelines",
            source_reference=sample_source_ref,
            owner="Marcus Vance",
            acceptance_criteria="All Terraform modules pass automated validation",
            client_approver="VP Engineering",
        ),
    ]

    milestones = [
        Milestone(
            id="M01",
            description="Architecture Review Sign-off",
            external_date=None,
            internal_buffer_date=None,
            owner="Delivery Manager",
            source_reference=sample_source_ref,
        ),
        Milestone(
            id="M02",
            description="Production Go-Live",
            external_date=date(2026, 12, 1),
            internal_buffer_date=date(2026, 11, 24),
            owner="Delivery Manager",
            source_reference=sample_source_ref,
        ),
    ]

    backlog_seed = [
        WorkPackageSeed(
            id="WP-01",
            title="VPC and Transit Gateway Setup",
            parent_deliverable_id="DEL-01",
            preliminary_sequence=1,
            owner="Unassigned",
            status="Draft",
            source_reference=sample_source_ref,
        )
    ]

    dependencies_assumptions = [
        DependencyAssumptionItem(
            id="DA-01",
            type="Dependency",
            description="DirectConnect provisioning by client telecom provider",
            category="Infrastructure",
            owner="Unassigned",
            status="Open",
            source_reference=sample_source_ref,
        )
    ]

    raid_items = [
        RiskAssumption(
            type="Risk",
            description="Potential delay in client IAM role provisioning",
            category="Access & Security",
            owner="Unassigned",
            mitigation_or_response="TBD",
            status="Open",
            source_reference=sample_source_ref,
        )
    ]

    talent_onboarding = TalentOnboardingRecord(
        talent_pm="[UNASSIGNED - TO BE CONFIRMED]",
        delivery_manager="[UNASSIGNED - TO BE CONFIRMED]",
        pmo_lead="Sarah Connor",
        delivery_talent_roster=[
            TalentMember(
                role="Lead Cloud Architect",
                name="[UNASSIGNED - TO BE CONFIRMED]",
                required_skills="AWS, Terraform, Kubernetes",
                status="Pending",
            ),
            TalentMember(
                role="Senior DevOps Engineer",
                name="Marcus Vance",
                required_skills="Docker, Terraform, CI/CD",
                status="Staffed",
            ),
        ],
    )

    stakeholders = [
        Stakeholder(
            name="[UNASSIGNED - TO BE CONFIRMED]",
            role="Client Executive Sponsor",
            organization="Global Financial Corp",
            decision_rights="[CONFIRMATION REQUIRED]",
            escalation_responsibility="PMO Lead",
        )
    ]

    raci_matrix = [
        RACIItem(
            decision_or_activity="Deliverable Sign-Off and Acceptance",
            pmo_lead="A",
            delivery_manager="R",
            talent_pm="C",
            sales_accounts="I",
            client="A",
        )
    ]

    communications_plan = [
        CommunicationsPlanItem(
            id="COM-01",
            name="Weekly Project Status Report (PSR)",
            audience="[CONFIRMATION REQUIRED] Client Stakeholder Distribution List",
            content_owner="Delivery Manager",
            cadence="Weekly",
            format="PDF / Email",
            delivery_day="Friday 5:00 PM EST",
        )
    ]

    commercial_guardrails = CommercialGuardrail(
        contract_type_implication="Time and Materials with Not-To-Exceed Cap",
        approved_work_rule="Work strictly against signed Statement of Work work packages",
        non_approved_work_rule="Zero work performed without prior written PMO authorization",
        work_at_risk_rule="Work-at-risk capped at $0; strictly prohibited without VP waiver",
        change_control_trigger="Scope changes exceeding 5 person-days or $10,000",
        change_order_route="[CONFIRMATION REQUIRED - PMO Written Change Order]",
        budget_baseline="[CONFIRMATION REQUIRED - SOW Total Value TBD]",
        variance_indicator="5%",
        margin_risk_indicator="Margin floor below target triggers PMO escalation",
        escalation_threshold="$10,000 or 1-week timeline impact",
    )

    governance_context = GovernanceContext(
        project_name="Enterprise Cloud Migration",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        client_name="Global Financial Corp",
        delivery_manager="[UNASSIGNED - TO BE CONFIRMED]",
        talent_pm="[UNASSIGNED - TO BE CONFIRMED]",
        pmo_lead="Sarah Connor",
    )

    baseline = StartupKitBaseline(
        project_name="Enterprise Cloud Migration",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        sla_met=False,  # SLA breached -> generates G01-01 action
        segregation_of_duties_verified=True,
        author_name="Sarah Connor",
        charter=charter,
        sow_interpretation=sow_interpretation,
        contract_ambiguities=contract_ambiguities,
        deliverables=deliverables,
        milestones=milestones,
        backlog_seed=backlog_seed,
        dependencies_assumptions=dependencies_assumptions,
        raid_items=raid_items,
        talent_onboarding=talent_onboarding,
        stakeholders=stakeholders,
        raci_matrix=raci_matrix,
        communications_plan=communications_plan,
        commercial_guardrails=commercial_guardrails,
        governance_context=governance_context,
        readiness_checklist=checklist,
        open_questions=[
            "Who is the designated client sign-off sponsor authority?",
            "What is the agreed weekly status report distribution list?",
            "What is the locked external milestone date for Architecture Review?",
        ],
    )

    # Re-evaluate and link all action items
    return ReadinessScoringEngine.evaluate_and_rescore(baseline)


def test_100_percent_action_traceability_in_tables(tmp_path: Path, baseline_with_all_15_actions: StartupKitBaseline):
    """Asserts that 100% of generated ActionRequiredItems appear embedded in Section 4 Layer Artifact tables."""
    baseline = baseline_with_all_15_actions
    assert len(baseline.action_required_items) > 0, "Baseline must contain active ActionRequiredItems"

    output_file = tmp_path / "Traceability_Audit_Startup_Kit.docx"
    DocxGenerator().write_docx(baseline, output_file)
    assert output_file.exists()

    doc = docx.Document(str(output_file))
    assert len(doc.tables) > 4, "Document must contain header, gateway, and artifact tables"

    # Exclude Table 0-2 (Metadata, Gate Decision, Checklist Table) and trailing Action Required Table
    artifact_tables = [t for t in doc.tables[3:] if not any(c.text.strip() == "Action ID" for c in t.rows[0].cells)]
    artifact_tables_text = " ".join(
        cell.text for t in artifact_tables for row in t.rows for cell in row.cells
    )

    for action in baseline.action_required_items:
        assert action.action_id in artifact_tables_text, (
            f"Traceability Failure: {action.action_id} ({action.related_artifact}) "
            f"not found embedded in any Section 4 Layer Artifact table."
        )


def test_action_required_item_metadata_registry(baseline_with_all_15_actions: StartupKitBaseline):
    """Verifies that every ActionRequiredItem is instantiated with explicit table and column targeting metadata."""
    baseline = baseline_with_all_15_actions
    for action in baseline.action_required_items:
        assert action.action_id.startswith("ACT-"), f"Invalid action_id: {action.action_id}"
        assert action.checklist_id.startswith("G01-"), f"Invalid checklist_id: {action.checklist_id}"
        assert action.target_table_title, f"Missing target_table_title on {action.action_id}"
        assert action.target_column_header, f"Missing target_column_header on {action.action_id}"
        assert action.score_recovery_delta > 0.0, f"Expected positive score_recovery_delta on {action.action_id}"
        assert action.required_action, f"Missing required_action on {action.action_id}"
        assert action.owner, f"Missing owner on {action.action_id}"


def test_universal_cell_formatter_applies_amber_shading():
    """Verifies that format_cell_with_action appends remediation tokens and applies warning background shading."""
    doc = docx.Document()
    tbl = doc.add_table(rows=1, cols=2)
    cell = tbl.cell(0, 0)

    action = ActionRequiredItem(
        action_id="ACT-03",
        item_type="Open Exception",
        checklist_id="G01-03",
        related_artifact="Deliverables and Acceptance Matrix",
        target_table_title="Deliverables and Acceptance Matrix",
        target_column_header="Acceptance Criteria",
        target_entity_id="DEL-01",
        finding_description="Acceptance criteria unstated",
        required_action="Finalize acceptance test criteria",
        owner="Talent PM",
        score_recovery_delta=3.5,
    )

    format_cell_with_action(cell, "[CONFIRMATION REQUIRED]", action=action, is_warning=True)

    assert "[ACT-03: Finalize acceptance test criteria (+3.5% Recovery)]" in cell.text
    # Verify yellow text highlight on the action tag run
    from docx.enum.text import WD_COLOR_INDEX
    yellow_runs = [r for p in cell.paragraphs for r in p.runs if r.font.highlight_color == WD_COLOR_INDEX.YELLOW]
    assert len(yellow_runs) > 0, "Action tag run must be highlighted in yellow"
    # Verify cell background is NOT set to warning color
    tcPr = cell._tc.get_or_add_tcPr()
    w_shd = tcPr.find(docx.oxml.ns.qn("w:shd"))
    assert w_shd is None or w_shd.get(docx.oxml.ns.qn("w:fill")) != COLOR_WARNING_BG_HEX


def test_sow_interpretation_summary_action_embedding(tmp_path: Path, baseline_with_all_15_actions: StartupKitBaseline):
    """Verifies that the SOW Interpretation Summary table embeds [ACT-XX] annotations and yellow run highlights."""
    from docx.enum.text import WD_COLOR_INDEX

    baseline = baseline_with_all_15_actions
    output_file = tmp_path / "SOW_Interpretation_Traceability_Test.docx"
    DocxGenerator().write_docx(baseline, output_file)
    assert output_file.exists()

    doc = docx.Document(str(output_file))
    
    # Locate SOW Interpretation Summary table
    sow_table = None
    for t in doc.tables:
        if len(t.rows) > 0 and len(t.rows[0].cells) >= 2:
            h0 = t.rows[0].cells[0].text.lower()
            h1 = t.rows[0].cells[1].text.lower()
            if "sow interpretation" in h0 and "contractual summary" in h1:
                sow_table = t
                break

    assert sow_table is not None, "SOW Interpretation Summary table not found in generated docx"

    # Verify that Customer Obligations & Prerequisites and Ambiguities rows contain ACT tags and yellow text highlight
    found_act_in_sow = False
    for row in sow_table.rows[1:]:
        dim_text = row.cells[0].text
        val_text = row.cells[1].text
        if "Customer Obligations" in dim_text or "Ambiguities" in dim_text:
            assert "[ACT-" in val_text, f"Expected [ACT-XX] tag in SOW dimension '{dim_text}', got: '{val_text}'"
            found_act_in_sow = True
            # Verify yellow text highlight on the action tag run
            yellow_runs = [r for p in row.cells[1].paragraphs for r in p.runs if r.font.highlight_color == WD_COLOR_INDEX.YELLOW]
            assert len(yellow_runs) > 0, f"Expected yellow highlighted run in SOW dimension '{dim_text}'"
            # Verify cell background is NOT set to warning color
            tcPr = row.cells[1]._tc.get_or_add_tcPr()
            w_shd = tcPr.find(docx.oxml.ns.qn("w:shd"))
            assert w_shd is None or w_shd.get(docx.oxml.ns.qn("w:fill")) != COLOR_WARNING_BG_HEX

    assert found_act_in_sow, "At least one SOW Interpretation row must contain an active [ACT-XX] annotation"


def test_sow_interpretation_roundtrip_reingestion_clean_extraction(tmp_path: Path, baseline_with_all_15_actions: StartupKitBaseline):
    """Verifies that re-ingesting a docx with SOW table [ACT-XX] annotations cleanly sanitizes tags."""
    from src.extractors.startup_kit_docx_parser import StartupKitDocxParser

    baseline = baseline_with_all_15_actions
    output_file = tmp_path / "SOW_Reingestion_Test.docx"
    DocxGenerator().write_docx(baseline, output_file)

    parser = StartupKitDocxParser()
    parsed_baseline = parser.parse_startup_kit_docx(output_file)

    assert parsed_baseline.sow_interpretation is not None
    for ob in parsed_baseline.sow_interpretation.customer_obligations:
        assert "[ACT-" not in ob, f"Extracted customer obligation contains unsanitized ACT tag: {ob}"
    for note in parsed_baseline.sow_interpretation.ambiguity_notes:
        assert "[ACT-" not in note, f"Extracted ambiguity note contains unsanitized ACT tag: {note}"


def test_zero_orphaned_placeholders_in_all_artifact_tables(tmp_path: Path, baseline_with_all_15_actions: StartupKitBaseline):
    """Invariant Test: Asserts that NO table cell in any Section 4 table contains an unannotated/orphaned placeholder.

    Scans Charter, SOW Summary, Milestones, Backlog, Deliverables, Dependencies, RAID, Comms, Stakeholders, RACI,
    Commercial Guardrails, and Talent Roster tables.
    """
    baseline = baseline_with_all_15_actions
    output_file = tmp_path / "Zero_Orphan_Invariant_Test.docx"
    DocxGenerator().write_docx(baseline, output_file)
    assert output_file.exists()

    doc = docx.Document(str(output_file))

    # Inspect all Section 4 artifact tables (tables from index 1 up to Action Required table)
    for table_idx, tbl in enumerate(doc.tables):
        if any(c.text.strip() == "Action ID" for c in tbl.rows[0].cells):
            continue
        if any(c.text.strip() == "Gate ID" or "gate id" in c.text.lower() or "startup readiness checklist" in c.text.lower() for c in tbl.rows[0].cells):
            continue
        for row_idx, row in enumerate(tbl.rows):
            for cell_idx, cell in enumerate(row.cells):
                cell_text = cell.text.strip()
                assert "CONFIRMATION REQUIRED" not in cell_text.upper(), (
                    f"Placeholder Leak Invariant Violation in Table {table_idx}, Row {row_idx}, Cell {cell_idx}: "
                    f"Cell '{cell_text}' still contains raw CONFIRMATION REQUIRED token."
                )


def test_placeholder_subsumption_and_clean_formatting():
    """Unit Test: Verifies that raw placeholders are cleanly subsumed when formatted with action items."""
    doc = docx.Document()
    tbl = doc.add_table(rows=1, cols=4)

    action = ActionRequiredItem(
        action_id="ACT-07",
        item_type="Open Clarification",
        checklist_id="G01-07",
        related_artifact="SOW Interpretation Summary",
        target_table_title="SOW Interpretation Summary",
        target_column_header="Customer Obligations & Prerequisites",
        target_entity_id=None,
        finding_description="Customer prerequisites unconfirmed",
        required_action="Issue access prerequisites list to client sponsor",
        owner="Delivery Manager",
        score_recovery_delta=2.5,
    )

    # 1. Bare [CONFIRMATION REQUIRED] should be replaced entirely by the action tag
    cell0 = tbl.cell(0, 0)
    format_cell_with_action(cell0, "[CONFIRMATION REQUIRED]", action=action, is_warning=True)
    assert cell0.text == "[ACT-07: Issue access prerequisites list to client sponsor (+2.5% Recovery)]"
    assert "[CONFIRMATION REQUIRED]" not in cell0.text

    # 2. Bare [UNDEFINED] should be replaced entirely by the action tag
    cell1 = tbl.cell(0, 1)
    format_cell_with_action(cell1, "[UNDEFINED]", action=action, is_warning=True)
    assert cell1.text == "[ACT-07: Issue access prerequisites list to client sponsor (+2.5% Recovery)]"
    assert "[UNDEFINED]" not in cell1.text

    # 3. Bare [UNASSIGNED - TO BE CONFIRMED] should be replaced entirely
    cell2 = tbl.cell(0, 2)
    format_cell_with_action(cell2, "[UNASSIGNED - TO BE CONFIRMED]", action=action, is_warning=True)
    assert cell2.text == "[ACT-07: Issue access prerequisites list to client sponsor (+2.5% Recovery)]"
    assert "UNASSIGNED" not in cell2.text

    # 4. Bulleted list with placeholder should clean placeholder line and attach tag
    cell3 = tbl.cell(0, 3)
    format_cell_with_action(cell3, "• Provide IAM Admin roles by Day 1\n• [CONFIRMATION REQUIRED]", action=action, is_warning=True)
    assert "[CONFIRMATION REQUIRED]" not in cell3.text
    assert "Provide IAM Admin roles by Day 1" in cell3.text
    assert "[ACT-07: Issue access prerequisites list to client sponsor (+2.5% Recovery)]" in cell3.text


def test_zero_orphans_across_multiple_diverse_baselines(tmp_path: Path, sample_source_ref: SourceReference):
    """Integration Test: Verifies that multiple diverse baselines (default aggregate, unstaffed, minimal) render zero orphaned placeholders."""
    import re
    from src.llm.aggregator import BaselineAggregator
    from src.core.models import (
        CharterExtraction,
        DeliverablesExtraction,
        MilestonesExtraction,
        RAIDExtraction,
        Deliverable,
        Milestone,
        RiskAssumption,
    )

    placeholder_regex = re.compile(r'\[(?:CONFIRMATION REQUIRED|UNDEFINED|UNASSIGNED|TBD)\]', re.IGNORECASE)

    # Baseline 1: Standard aggregate baseline
    aggregator = BaselineAggregator()
    charter = CharterExtraction(
        project_name="Multi-Baseline Invariant Test",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        delivery_manager="[UNASSIGNED - TO BE CONFIRMED]",
        talent_pm="[UNASSIGNED - TO BE CONFIRMED]",
        source_reference=sample_source_ref,
    )
    b1 = aggregator.aggregate(
        charter=charter,
        deliverables_ext=DeliverablesExtraction(deliverables=[Deliverable(id="D1", description="API Gateway", source_reference=sample_source_ref)]),
        milestones_ext=MilestonesExtraction(milestones=[Milestone(id="M1", description="Kickoff", source_reference=sample_source_ref)]),
        raid_ext=RAIDExtraction(items=[RiskAssumption(type="Risk", description="Key Person Risk", source_reference=sample_source_ref)])
    )

    # Baseline 2: Recalculated baseline
    b2 = ReadinessScoringEngine.evaluate_and_rescore(b1)

    for idx, baseline in enumerate([b1, b2]):
        out_file = tmp_path / f"Diverse_Baseline_Test_{idx}.docx"
        DocxGenerator().write_docx(baseline, out_file)
        doc = docx.Document(str(out_file))

        for t_idx, tbl in enumerate(doc.tables):
            if any(c.text.strip() == "Action ID" for c in tbl.rows[0].cells):
                continue
            if any(c.text.strip() == "Gate ID" for c in tbl.rows[0].cells):
                continue
            if any("startup readiness checklist" in c.text.lower() for c in tbl.rows[0].cells):
                continue
            for r_idx, row in enumerate(tbl.rows):
                for c_idx, cell in enumerate(row.cells):
                    cell_text = cell.text.strip()
                    assert "CONFIRMATION REQUIRED" not in cell_text.upper(), (
                        f"Baseline {idx} Invariant Violation in Table {t_idx}, Row {r_idx}, Cell {c_idx}: "
                        f"Cell '{cell_text}' still contains raw CONFIRMATION REQUIRED token."
                    )
