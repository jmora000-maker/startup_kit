"""Unit and integration tests for Startup Kit DOCX Re-ingestion and Readiness Recalculation."""

import pytest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from src.core.models import (
    StartupKitBaseline,
    ProjectStartupCharter,
    Deliverable,
    Milestone,
    RiskAssumption,
    DependencyAssumptionItem,
    DecisionItem,
    WorkPackageSeed,
    Stakeholder,
    RACIItem,
    CommunicationsPlanItem,
    CommercialGuardrail,
    TalentOnboardingRecord,
    TalentMember,
    ReadinessChecklistItem,
    GateDecision,
    GovernanceContext,
    SourceReference,
    SOWInterpretationSummary,
    ContractAmbiguityItem,
)
from src.generators.docx_generator import DocxGenerator
from src.extractors.startup_kit_docx_parser import StartupKitDocxParser, parse_date_safely
from src.llm.aggregator import BaselineAggregator
from src.orchestrator import StartupKitController
import main


@pytest.fixture
def sample_baseline() -> StartupKitBaseline:
    """Create a fully populated baseline for generating test DOCX files."""
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="Sec 1", confidence_score=1.0)
    charter = ProjectStartupCharter(
        project_name="Alpha Core Platform",
        client_name="Acme Corp",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        delivery_manager="Jane Doe",
        talent_pm="Taylor Brown",
        pmo_lead="Sarah Connor",
        project_purpose="Deliver core platform modernization.",
        delivery_model="Toptal Partnered Delivery",
        governance_model="PMO Governance",
        escalation_path="TPM -> DM -> PMO",
        unresolved_assumptions_status="None",
        delivery_objectives=["Deploy microservices architecture", "Automate CI/CD"],
        success_criteria=["99.9% uptime achieved", "Zero critical defects"],
        high_level_scope=["Core API services", "Database migration"],
        exclusions=["Legacy mainframe support"],
        source_reference=ref
    )
    gov_ctx = GovernanceContext(
        project_name="Alpha Core Platform",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        client_name="Acme Corp",
        delivery_manager="Jane Doe",
        talent_pm="Taylor Brown",
        pmo_lead="Sarah Connor",
        workflow_state="Ready for G-01 Gate Review",
        sla_met=True
    )
    deliverables = [
        Deliverable(
            id="DEL-01",
            name="API Architecture Blueprint",
            description="Detailed microservices architectural design.",
            source_reference=ref,
            owner="Lead Architect",
            acceptance_criteria="Approved architecture design document with sequence diagrams.",
            client_approver="VP of Engineering",
            review_window="5 business days"
        ),
        Deliverable(
            id="DEL-02",
            name="CI/CD Deployment Pipeline",
            description="Automated GitHub Actions workflow.",
            source_reference=ref,
            owner="DevOps Engineer",
            acceptance_criteria="Passing automated pipeline with container deployment.",
            client_approver="Director of Infrastructure",
            review_window="5 business days"
        )
    ]
    milestones = [
        Milestone(
            id="M01",
            description="Architecture Baseline Complete",
            external_date=date(2026, 10, 15),
            internal_buffer_date=date(2026, 10, 10),
            owner="Delivery Manager",
            key_dependencies=["Environment Provisioning"],
            source_reference=ref
        ),
        Milestone(
            id="M02",
            description="Production Go-Live",
            external_date=date(2026, 12, 1),
            internal_buffer_date=date(2026, 11, 20),
            owner="Delivery Manager",
            key_dependencies=["User Acceptance Testing"],
            source_reference=ref
        )
    ]
    raid_items = [
        RiskAssumption(
            id="R-01",
            type="Risk",
            description="Third-party API rate limiting",
            owner="Lead Architect",
            status="Open",
            mitigation_strategy="Implement distributed caching and request queueing",
            impact="High",
            source_reference=ref
        )
    ]
    talent_onboarding = TalentOnboardingRecord(
        pmo_lead="Sarah Connor",
        delivery_manager="Jane Doe",
        talent_pm="Taylor Brown",
        delivery_talent_roster=[
            TalentMember(role="Lead Architect", name="Alex Vance", required_skills="Python, AWS", status="Confirmed"),
            TalentMember(role="DevOps Engineer", name="Gordon Freeman", required_skills="Terraform, Docker", status="Confirmed")
        ],
        source_reference=ref
    )
    checklist = [
        ReadinessChecklistItem(
            item_id=f"G01-{i:02d}",
            gate_criterion=f"Criterion {i}",
            related_section4_artifact="Charter",
            owner="Sarah Connor",
            reviewer="Jane Doe",
            approver="Sarah Connor",
            status="Complete",
            evidence=f"Evidence for criterion {i}",
            exception_required=False,
            approval_status="Approved"
        )
        for i in range(1, 16)
    ]
    gate_dec = GateDecision(
        gate_decision_status="Approved for Mobilize",
        approver_name="Sarah Connor",
        approval_date=date.today(),
        decision_comments="All G-01 criteria complete.",
        approved_with_exception=False,
        rework_required=False,
        readiness_score=95.0,
        readiness_breakdown={
            "mandatory_g01_controls": 100.0,
            "deliverable_acceptance_rigor": 100.0,
            "talent_staffing_readiness": 100.0,
            "commercial_risk_mitigation": 100.0,
        },
        workflow_state="Approved for Mobilize",
        sla_met=True,
        author_name="Sarah Connor"
    )
    sow_interp = SOWInterpretationSummary(
        contracted_deliverables=["API Architecture Blueprint", "CI/CD Deployment Pipeline"],
        out_of_scope_items=["Legacy mainframe support"],
        customer_obligations=["Cloud account access provided by Day 3"],
        assumptions=["Standard sprint cycle"],
        constraints=["SOC2 compliance"],
        platform_environment_commitments=["AWS us-east-1"],
        dependencies=["Client IdP integration"],
        approval_expectations="5 business days",
        ambiguity_notes=[],
        source_reference=ref
    )
    comm_guardrail = CommercialGuardrail(
        contract_type_implication="Time and Materials with weekly reporting.",
        approved_work_rule="Hours mapped to contracted deliverables.",
        non_approved_work_rule="Change Order required for out-of-scope work.",
        work_at_risk_rule="Strictly prohibited.",
        change_control_trigger="Material scope modifications.",
        change_order_route="TPM -> DM -> PMO -> Client",
        budget_baseline="$150,000",
        variance_indicator="Weekly burn rate review",
        margin_risk_indicator="Monitored weekly",
        escalation_threshold="Budget variance > 5%",
        source_reference=ref
    )

    return StartupKitBaseline(
        project_name="Alpha Core Platform",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        governance_context=gov_ctx,
        charter=charter,
        sow_interpretation=sow_interp,
        deliverables=deliverables,
        milestones=milestones,
        backlog_seed=[
            WorkPackageSeed(
                id="WP-01",
                parent_deliverable_id="DEL-01",
                title="Auth Endpoint",
                description="Core API Auth Endpoint",
                preliminary_sequence=1,
                owner="Lead Architect",
                status="Draft"
            )
        ],
        dependencies_assumptions=[
            DependencyAssumptionItem(
                id="DEP-01",
                type="Assumption",
                description="Standard sprint cycle",
                source_reference=ref
            )
        ],
        raid_items=raid_items,
        decisions=[
            DecisionItem(id="DEC-01", decision_text="Adopt FastAPI framework", decision_owner="Lead Architect", status="Approved")
        ],
        communications_plan=[
            CommunicationsPlanItem(
                id="COM-01",
                name="Weekly Status Report",
                audience="Client Leadership",
                content_owner="Delivery Manager",
                cadence="Weekly",
                format="Email & PDF",
                delivery_day="Friday"
            )
        ],
        stakeholders=[
            Stakeholder(
                name="Alice Smith",
                role="VP Engineering",
                organization="Acme Corp",
                decision_rights="Final Deliverable Sign-off",
                escalation_responsibility="Commercial Escalations"
            )
        ],
        raci_matrix=[
            RACIItem(
                decision_or_activity="Deliverable Sign-off",
                pmo_lead="A",
                delivery_manager="R",
                talent_pm="C",
                sales_accounts="I",
                client="A"
            )
        ],
        commercial_guardrails=comm_guardrail,
        talent_onboarding=talent_onboarding,
        readiness_checklist=checklist,
        gate_decision=gate_dec,
        open_questions=[],
        contract_ambiguities=[],
        readiness_score=95.0,
        readiness_breakdown=gate_dec.readiness_breakdown,
        workflow_state="Approved for Mobilize",
        sow_awarded_date=date.today(),
        kit_drafted_date=date.today(),
        sla_met=True,
        author_name="Sarah Connor"
    )


def test_parse_date_safely():
    """Verify safe date parser handles multiple formats and invalid/placeholder strings."""
    assert parse_date_safely("2026-10-15") == date(2026, 10, 15)
    assert parse_date_safely("10/15/2026") == date(2026, 10, 15)
    assert parse_date_safely("October 15, 2026") == date(2026, 10, 15)
    assert parse_date_safely("15-Oct-2026") == date(2026, 10, 15)
    assert parse_date_safely("2026-10-15 (Internal Buffer)") == date(2026, 10, 15)
    assert parse_date_safely("TBD") is None
    assert parse_date_safely("To be determined") is None
    assert parse_date_safely("[CONFIRMATION REQUIRED]") is None
    assert parse_date_safely("Unassigned") is None
    assert parse_date_safely(None) is None
    assert parse_date_safely("") is None


def test_docx_parser_and_roundtrip(sample_baseline: StartupKitBaseline, tmp_path: Path):
    """Test generating a Word document and deterministically parsing it back into domain models."""
    writer = DocxGenerator()
    doc_path = writer.write_docx(sample_baseline, tmp_path)
    assert doc_path.exists()

    parser = StartupKitDocxParser()
    parsed_baseline = parser.parse_startup_kit_docx(doc_path)

    # Validate Core Properties
    assert parsed_baseline.project_name == "Alpha Core Platform"
    assert parsed_baseline.governance_tier == "Partnered"
    assert parsed_baseline.contract_type == "Time and Materials"
    assert parsed_baseline.charter.delivery_manager == "Jane Doe"
    assert parsed_baseline.charter.talent_pm == "Taylor Brown"
    assert parsed_baseline.charter.pmo_lead == "Sarah Connor"
    assert parsed_baseline.sla_met is True

    # Validate Deliverables
    assert len(parsed_baseline.deliverables) == 2
    assert parsed_baseline.deliverables[0].name == "API Architecture Blueprint"
    assert parsed_baseline.deliverables[0].owner == "Lead Architect"
    assert parsed_baseline.deliverables[0].client_approver == "VP of Engineering"

    # Validate Milestones
    assert len(parsed_baseline.milestones) == 2
    assert parsed_baseline.milestones[0].external_date == date(2026, 10, 15)
    assert parsed_baseline.milestones[1].external_date == date(2026, 12, 1)

    # Validate RAID items & Decisions
    assert len(parsed_baseline.raid_items) == 1
    assert parsed_baseline.raid_items[0].owner == "Lead Architect"
    assert len(parsed_baseline.decisions) == 1
    assert parsed_baseline.decisions[0].decision_text == "Adopt FastAPI framework"

    # Validate Checklist
    assert len(parsed_baseline.readiness_checklist) == 15
    assert parsed_baseline.readiness_checklist[0].status == "Complete"

    # Validate Talent Onboarding
    assert parsed_baseline.talent_onboarding is not None
    assert len(parsed_baseline.talent_onboarding.delivery_talent_roster) == 2
    assert parsed_baseline.talent_onboarding.delivery_talent_roster[0].name == "Alex Vance"
    assert parsed_baseline.talent_onboarding.delivery_talent_roster[0].status == "Confirmed"

    # Validate Objectives, Success Criteria, and Exclusions
    assert parsed_baseline.charter.delivery_objectives == ["Deploy microservices architecture", "Automate CI/CD"]
    assert parsed_baseline.charter.success_criteria == ["99.9% uptime achieved", "Zero critical defects"]
    assert parsed_baseline.charter.exclusions == ["Legacy mainframe support"]


def test_no_double_bullets_in_delivery_objectives_and_success_criteria(sample_baseline: StartupKitBaseline, tmp_path: Path):
    """Verify that generated DOCX does not include literal bullet characters in List Bullet paragraphs."""
    import docx as docx_module

    # Include inputs with and without leading bullet points to verify cleaning
    sample_baseline.charter.delivery_objectives = ["• Deploy microservices architecture", "- Automate CI/CD pipeline", "Establish telemetry"]
    sample_baseline.charter.success_criteria = ["• 99.9% uptime achieved", "Zero critical defects in UAT"]
    sample_baseline.charter.exclusions = ["• Legacy mainframe support", "* On-premise hardware provisioning"]

    writer = DocxGenerator()
    doc_path = writer.write_docx(sample_baseline, tmp_path / "Bullet_Test_Startup_Kit.docx")

    doc = docx_module.Document(str(doc_path))
    in_objectives_or_exclusions = False
    list_bullet_texts = []

    for p in doc.paragraphs:
        t = p.text.strip()
        if "Delivery Objectives & Success Criteria:" in t or "High-Level Scope Exclusions:" in t:
            in_objectives_or_exclusions = True
            continue
        elif "SOW Interpretation Summary" in t or "Layer 2" in t:
            in_objectives_or_exclusions = False
            continue

        if in_objectives_or_exclusions and getattr(p.style, 'name', '') == 'List Bullet':
            list_bullet_texts.append(t)
            # Ensure the raw text does NOT begin with literal bullets (which would render double bullets in Word)
            assert not t.startswith("•"), f"Found double bullet in paragraph: '{t}'"
            assert not t.startswith("-"), f"Found literal dash bullet in paragraph: '{t}'"
            assert not t.startswith("*"), f"Found literal asterisk bullet in paragraph: '{t}'"

    assert len(list_bullet_texts) == 7
    assert "Deploy microservices architecture" in list_bullet_texts
    assert "Automate CI/CD pipeline" in list_bullet_texts
    assert "Establish telemetry" in list_bullet_texts
    assert "Success Criteria: 99.9% uptime achieved" in list_bullet_texts
    assert "Success Criteria: Zero critical defects in UAT" in list_bullet_texts
    assert "Legacy mainframe support" in list_bullet_texts
    assert "On-premise hardware provisioning" in list_bullet_texts


def test_docx_parser_validation_errors(tmp_path: Path):
    """Verify parser enforces file existence and .docx schema constraints."""
    parser = StartupKitDocxParser()

    # Non-existent file
    with pytest.raises(FileNotFoundError):
        parser.parse_startup_kit_docx(tmp_path / "non_existent.docx")

    # Non-docx extension
    invalid_file = tmp_path / "test.txt"
    invalid_file.write_text("Hello")
    with pytest.raises(ValueError, match=r"Target file must be a \.docx file"):
        parser.parse_startup_kit_docx(invalid_file)


def test_recalculate_readiness_score_transitions(sample_baseline: StartupKitBaseline):
    """Verify readiness score recalculation, dimensional weights, and gate decision transitions."""
    aggregator = BaselineAggregator()

    # 1. Optimal baseline -> Score >= 85.0%, Approved for Mobilize (Green)
    recalculated = aggregator.recalculate_readiness(sample_baseline)
    assert recalculated.readiness_score >= 85.0
    assert recalculated.gate_decision.gate_decision_status == "Approved for Mobilize"
    assert recalculated.workflow_state == "Approved for Mobilize"

    # 2. Introduce unassigned roles and unconfirmed deliverables -> Score drops
    sample_baseline.charter.delivery_manager = "[UNASSIGNED - TO BE CONFIRMED]"
    sample_baseline.charter.talent_pm = "[UNASSIGNED - TO BE CONFIRMED]"
    if sample_baseline.talent_onboarding:
        sample_baseline.talent_onboarding.delivery_manager = "[UNASSIGNED - TO BE CONFIRMED]"
        sample_baseline.talent_onboarding.talent_pm = "[UNASSIGNED - TO BE CONFIRMED]"
    sample_baseline.deliverables[0].acceptance_criteria = "[CONFIRMATION REQUIRED]"
    sample_baseline.deliverables[0].owner = "Unassigned"
    sample_baseline.deliverables[0].client_approver = "[UNASSIGNED - TO BE CONFIRMED]"
    sample_baseline.milestones[0].external_date = None
    sample_baseline.open_questions = ["Clarify client authentication requirements", "Confirm SOC2 compliance tier"]
    # Mark checklist items
    sample_baseline.readiness_checklist[0].status = "Exception Required"
    sample_baseline.readiness_checklist[0].exception_required = True

    recalculated_low = aggregator.recalculate_readiness(sample_baseline)
    assert recalculated_low.readiness_score < 85.0
    assert recalculated_low.gate_decision.gate_decision_status in ("Approved with Exception", "Rework Required")

    # 3. Resolve all issues -> Transitions back to Green
    sample_baseline.charter.delivery_manager = "John DeliveryLead"
    sample_baseline.charter.talent_pm = "Jane TalentPM"
    if sample_baseline.talent_onboarding:
        sample_baseline.talent_onboarding.delivery_manager = "John DeliveryLead"
        sample_baseline.talent_onboarding.talent_pm = "Jane TalentPM"
    sample_baseline.deliverables[0].acceptance_criteria = "Sign-off on API spec"
    sample_baseline.deliverables[0].owner = "Lead Architect"
    sample_baseline.deliverables[0].client_approver = "VP Engineering"
    sample_baseline.milestones[0].external_date = date(2026, 10, 15)
    sample_baseline.open_questions = []
    sample_baseline.readiness_checklist[0].status = "Complete"
    sample_baseline.readiness_checklist[0].exception_required = False

    recalculated_fixed = aggregator.recalculate_readiness(sample_baseline)
    assert recalculated_fixed.readiness_score >= 85.0
    assert recalculated_fixed.gate_decision.gate_decision_status == "Approved for Mobilize"


def test_orchestrator_run_reingest(sample_baseline: StartupKitBaseline, tmp_path: Path):
    """Verify StartupKitController.run_reingest parses, recalculates, backs up, and regenerates DOCX."""
    writer = DocxGenerator()
    original_docx = writer.write_docx(sample_baseline, tmp_path / "MyProject_Startup_Kit.docx")

    controller = StartupKitController(
        doc_writer=writer,
        aggregator=BaselineAggregator(),
        docx_parser=StartupKitDocxParser()
    )

    # Execute re-ingestion with in-place overwrite and export_tools
    updated_file = controller.run_reingest(
        docx_path=original_docx,
        pmo_lead="Alice PMO",
        delivery_lead="Bob Delivery",
        talent_pm="Charlie Talent",
        export_tools=True,
        create_backup=True
    )

    assert updated_file.exists()
    assert updated_file.resolve() == original_docx.resolve()

    # Verify backup was created
    backups = list(tmp_path.glob("MyProject_Startup_Kit_backup_*.docx"))
    assert len(backups) == 1

    # Verify CSV and JSON tools were exported
    csv_files = list(tmp_path.glob("*.csv"))
    json_files = list(tmp_path.glob("*.json"))
    assert len(csv_files) > 0
    assert len(json_files) > 0

    # Verify parsed regenerated content has updated roles
    parser = StartupKitDocxParser()
    reloaded = parser.parse_startup_kit_docx(updated_file)
    assert reloaded.charter.pmo_lead == "Alice PMO"
    assert reloaded.charter.delivery_manager == "Bob Delivery"
    assert reloaded.charter.talent_pm == "Charlie Talent"


def test_cli_execution_mode_and_reingest_flag(sample_baseline: StartupKitBaseline, tmp_path: Path):
    """Test CLI behavior with --reingest-docx flag in non-interactive mode."""
    writer = DocxGenerator()
    test_docx = writer.write_docx(sample_baseline, tmp_path / "CLI_Project_Startup_Kit.docx")

    # Run CLI with --reingest-docx and --non-interactive
    test_args = [
        "main.py",
        "--reingest-docx", str(test_docx),
        "--non-interactive",
        "--pmo-lead", "Lead Sarah",
        "--export-tools"
    ]
    with patch("sys.argv", test_args):
        ret = main.main()
        assert ret == 0


def test_cli_interactive_execution_mode_prompt(sample_baseline: StartupKitBaseline, tmp_path: Path):
    """Test interactive execution mode prompt selecting Option 2."""
    writer = DocxGenerator()
    test_docx = writer.write_docx(sample_baseline, tmp_path / "Interactive_Startup_Kit.docx")

    # Mock user typing '2' for re-ingestion mode, entering docx path, and pressing Enter for roles
    user_inputs = ["2", str(test_docx), "Alice PMO", "", ""]
    with patch("builtins.input", side_effect=user_inputs):
        test_args = ["main.py"]
        with patch("sys.argv", test_args):
            ret = main.main()
            assert ret == 0


def test_cli_interactive_execution_mode_option_2_empty_retry(sample_baseline: StartupKitBaseline, tmp_path: Path):
    """Test Option 2 reprompting on empty inputs until valid path is provided."""
    writer = DocxGenerator()
    test_docx = writer.write_docx(sample_baseline, tmp_path / "Interactive_Retry_Startup_Kit.docx")

    # User inputs: '2', empty string '', whitespace '   ', valid path, then roles
    user_inputs = ["2", "", "   ", str(test_docx), "Alice PMO", "", ""]
    with patch("builtins.input", side_effect=user_inputs):
        test_args = ["main.py"]
        with patch("sys.argv", test_args):
            ret = main.main()
            assert ret == 0


def test_cli_interactive_execution_mode_option_2_exit():
    """Test Option 2 typing 'exit' cancels and exits cleanly with 0."""
    user_inputs = ["2", "exit"]
    with patch("builtins.input", side_effect=user_inputs):
        test_args = ["main.py"]
        with patch("sys.argv", test_args):
            ret = main.main()
            assert ret == 0


def test_prompt_reingest_file_behaviors(tmp_path: Path):
    """Test unit behaviors of prompt_reingest_file for explicit args, exit keywords, and retry."""
    # 1. Explicit path passed directly
    assert main.prompt_reingest_file(tmp_path / "test.docx", interactive=False) == tmp_path / "test.docx"
    assert main.prompt_reingest_file(str(tmp_path / "test.docx"), interactive=False) == tmp_path / "test.docx"

    # 2. Non-interactive without path returns None
    assert main.prompt_reingest_file(None, interactive=False) is None

    # 3. Interactive typing exit / quit
    with patch("builtins.input", side_effect=["exit"]):
        assert main.prompt_reingest_file(interactive=True) is None

    with patch("builtins.input", side_effect=["QUIT"]):
        assert main.prompt_reingest_file(interactive=True) is None

    # 4. Interactive empty input retries until valid
    target = tmp_path / "valid.docx"
    with patch("builtins.input", side_effect=["", "  ", str(target)]):
        result = main.prompt_reingest_file(interactive=True)
        assert result == target


def test_docx_reingestion_rescores_with_engine(tmp_path: Path):
    """Test that modifying a Word doc to resolve gaps recalculates dimensions and increases score."""
    import docx as docx_module
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="Sec 1", confidence_score=1.0)
    baseline = StartupKitBaseline(
        project_name="Reingest Test",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        deliverables=[
            Deliverable(
                id="DEL-01",
                name="Architecture Blueprint",
                description="Architecture Blueprint",
                source_reference=ref,
                owner="Unassigned",
                acceptance_criteria="[CONFIRMATION REQUIRED]",
            )
        ],
        milestones=[
            Milestone(
                id="M01",
                description="Kickoff",
                external_date=None,
                owner="Delivery Manager",
                source_reference=ref,
            )
        ],
        readiness_checklist=[
            ReadinessChecklistItem(
                item_id="G01-03",
                gate_criterion="Deliverables mapped to owners",
                related_section4_artifact="Deliverables and Acceptance Matrix",
                owner="Talent PM",
                reviewer="Delivery Manager",
                approver="PMO Lead",
                status="Exception Required",
                exception_required=True,
            )
        ],
        open_questions=["Confirm acceptance route"],
    )

    aggregator = BaselineAggregator()
    writer = DocxGenerator()
    initial_base = aggregator.recalculate_readiness(baseline)
    initial_score = initial_base.readiness_score
    initial_docx = writer.write_docx(initial_base, tmp_path / "Initial_Gap_Startup_Kit.docx")

    # Open docx and simulate user edits: resolve deliverable owner & acceptance criteria, update checklist status
    doc = docx_module.Document(str(initial_docx))

    # Update Deliverables table
    for tbl in doc.tables:
        if len(tbl.rows) > 1 and any("acceptance criteria" in c.text.lower() for c in tbl.rows[0].cells):
            tbl.rows[1].cells[2].text = "Formally approved by Client Architect"
            tbl.rows[1].cells[5].text = "Lead Architect Jane"
        if len(tbl.rows) > 1 and any("gate criterion" in c.text.lower() for c in tbl.rows[0].cells):
            tbl.rows[1].cells[3].text = "Complete"
            tbl.rows[1].cells[7].text = "Fully assigned and approved"

    edited_docx = tmp_path / "Edited_Startup_Kit.docx"
    doc.save(str(edited_docx))

    parser = StartupKitDocxParser()
    parsed_base = parser.parse_startup_kit_docx(edited_docx)
    rescored_base = aggregator.recalculate_readiness(parsed_base)

    assert rescored_base.readiness_score > initial_score
    # G01-03 exception should be cleared
    assert not any(i.item_id == "G01-03" and i.exception_required for i in rescored_base.readiness_checklist)


def test_reingest_clears_resolved_action_items(tmp_path: Path):
    """Test that resolving deliverable owner removes the corresponding ActionRequiredItem."""
    import docx as docx_module
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="Sec 1", confidence_score=1.0)
    baseline = StartupKitBaseline(
        project_name="Action Clear Test",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        deliverables=[
            Deliverable(
                id="DEL-01",
                name="Architecture Blueprint",
                description="Architecture Blueprint",
                source_reference=ref,
                owner="Unassigned",
                acceptance_criteria="[CONFIRMATION REQUIRED]",
            )
        ],
        readiness_checklist=[
            ReadinessChecklistItem(
                item_id="G01-03",
                gate_criterion="Deliverables mapped to owners",
                related_section4_artifact="Deliverables and Acceptance Matrix",
                owner="Talent PM",
                reviewer="Delivery Manager",
                approver="PMO Lead",
                status="Exception Required",
                exception_required=True,
            )
        ],
    )

    aggregator = BaselineAggregator()
    writer = DocxGenerator()
    initial_base = aggregator.recalculate_readiness(baseline)
    assert any(a.checklist_id == "G01-03" for a in initial_base.action_required_items)
    initial_docx = writer.write_docx(initial_base, tmp_path / "Action_Gap_Startup_Kit.docx")

    # Edit docx to resolve DEL-01 and G01-03
    doc = docx_module.Document(str(initial_docx))
    for tbl in doc.tables:
        if len(tbl.rows) > 1 and any("acceptance criteria" in c.text.lower() for c in tbl.rows[0].cells):
            tbl.rows[1].cells[2].text = "Explicit sign-off criteria verified"
            tbl.rows[1].cells[5].text = "Jane Architect"
        if len(tbl.rows) > 1 and any("gate criterion" in c.text.lower() for c in tbl.rows[0].cells):
            tbl.rows[1].cells[3].text = "Complete"

    doc.save(str(initial_docx))

    parser = StartupKitDocxParser()
    parsed_base = parser.parse_startup_kit_docx(initial_docx)
    rescored_base = aggregator.recalculate_readiness(parsed_base)

    assert not any(a.checklist_id == "G01-03" for a in rescored_base.action_required_items)


def test_docx_reingestion_idempotence(sample_baseline: StartupKitBaseline, tmp_path: Path):
    """Test that re-ingesting an unedited Word doc produces identical scores down to 0.1%."""
    aggregator = BaselineAggregator()
    writer = DocxGenerator()
    parser = StartupKitDocxParser()

    initial_base = aggregator.recalculate_readiness(sample_baseline)
    doc_path = writer.write_docx(initial_base, tmp_path / "Idempotence_Startup_Kit.docx")

    # Re-ingest without edits
    parsed_base = parser.parse_startup_kit_docx(doc_path)
    reingested_base = aggregator.recalculate_readiness(parsed_base)

    assert round(reingested_base.readiness_score, 1) == round(initial_base.readiness_score, 1)
    assert len(reingested_base.action_required_items) == len(initial_base.action_required_items)


def test_parser_strips_action_tags(tmp_path: Path):
    """Test that extracted cell text strips [ACT-XX] badges completely."""
    import docx as docx_module
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="Sec 1", confidence_score=1.0)
    baseline = StartupKitBaseline(
        project_name="Strip Tag Test",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        deliverables=[
            Deliverable(
                id="DEL-01",
                name="Blueprint",
                description="Blueprint",
                source_reference=ref,
                owner="[UNASSIGNED - TO BE CONFIRMED]",
                acceptance_criteria="[CONFIRMATION REQUIRED]",
            )
        ],
        readiness_checklist=[
            ReadinessChecklistItem(
                item_id="G01-03",
                gate_criterion="Deliverables mapped to owners",
                related_section4_artifact="Deliverables and Acceptance Matrix",
                owner="Talent PM",
                reviewer="Delivery Manager",
                approver="PMO Lead",
                status="Exception Required",
                exception_required=True,
            )
        ],
    )

    aggregator = BaselineAggregator()
    writer = DocxGenerator()
    base = aggregator.recalculate_readiness(baseline)
    doc_path = writer.write_docx(base, tmp_path / "Tagged_Startup_Kit.docx")

    parser = StartupKitDocxParser()
    reloaded = parser.parse_startup_kit_docx(doc_path)

    for d in reloaded.deliverables:
        assert "[ACT-" not in d.owner
        assert "[ACT-" not in (d.acceptance_criteria or "")
