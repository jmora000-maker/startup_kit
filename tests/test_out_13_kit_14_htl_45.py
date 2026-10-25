"""Tests for OUT-13 (OUT-13a, OUT-13b, OUT-13c, OUT-13d), KIT-14, and HTL-45."""

import re
from datetime import date
from pathlib import Path
import docx
import pytest

from src.core.models import (
    CommunicationsPlanItem,
    DecisionItem,
    Deliverable,
    DependencyAssumptionItem,
    Milestone,
    ProjectStartupCharter,
    RACIItem,
    RiskAssumption,
    SOWInterpretationSummary,
    Stakeholder,
    StartupKitBaseline,
    TalentOnboardingRecord,
)
from src.core.outputs import OutputSelection
from src.generators.docx_generator import DocxGenerator, obfuscate_financials
from src.llm.aggregator import BaselineAggregator
from src.orchestrator import StartupKitController


@pytest.fixture
def sample_full_baseline():
    """Create a rich baseline for testing document generation."""
    return StartupKitBaseline(
        project_name="Acme Global Platform",
        contract_type="Time and Materials",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 11, 1),
        charter=ProjectStartupCharter(
            client_name="Acme Corporation",
            project_purpose="Migrate legacy CRM into modern cloud microservices.",
            delivery_manager="Jane Doe",
            pmo_lead="Sarah Connor",
            talent_pm="Alex Rivera",
            delivery_objectives=["Deploy microservices on AWS with budgeted $150/hr rate"],
            success_criteria=["Complete migration within total budget cap of $250,000 USD"],
            exclusions=["Legacy mainframe hardware decommissioning"],
        ),
        sow_interpretation=SOWInterpretationSummary(
            contracted_deliverables=["Core API Gateway", "Authentication Service"],
            out_of_scope_items=["Hardware procurement"],
            customer_obligations=["Provide AWS IAM credentials within 5 business days"],
            assumptions=["Engineers billed at standard $175/hour consulting rate across all milestones"],
            constraints=["Total engagement spend capped at $300,000 USD"],
            dependencies=["Single Sign-On federation with Okta"],
            approval_expectations="Formal sign-off within 5 business days of UAT completion",
            ambiguity_notes=["Open question on SLA tier"],
        ),
        milestones=[
            Milestone(id="M1", description="Architecture & Kickoff", external_date=date(2026, 12, 1), owner="Jane Doe"),
            Milestone(id="M2", description="Core Platform Build ($100k milestone)", external_date=date(2027, 1, 15), owner="Jane Doe"),
        ],
        deliverables=[
            Deliverable(
                id="DEL-01",
                name="Architecture Blueprint",
                acceptance_criteria="Approved architecture specification document",
                evidence_required="Architecture Design Document v1.0 signed off",
                client_approver="John Smith",
                owner="Jane Doe",
                review_window="5 business days",
            )
        ],
        dependencies_assumptions=[
            DependencyAssumptionItem(
                id="ASM-01",
                type="Assumption",
                description="Assumes blended billing rate of $150.00/hr for senior talent across 40 hours/week",
                category="Commercial",
                owner="Jane Doe",
                status="Active",
            )
        ],
        raid_items=[
            RiskAssumption(
                id="RSK-04",
                type="Risk",
                description="Budget overrun risk if additional scope exceeds the $250,000 fee ceiling",
                category="Financial Risk",
                probability="Medium",
                impact="High",
                owner="Jane Doe",
                mitigation_or_response="Implement weekly burn review to cap expenses at $200k",
                status="Open",
            )
        ],
        decisions=[
            DecisionItem(
                id="DEC-01",
                decision_text="Agreed to proceed with T&M pricing at $160/hr with maximum commitment of $180,000",
                decision_owner="Sarah Connor",
                status="Approved",
            )
        ],
        stakeholders=[
            Stakeholder(name="Sarah Connor", role="PMO Lead", organization="Toptal PMO", decision_rights="G-01 Gate", escalation_responsibility="Director, PMO"),
            Stakeholder(name="Jane Doe", role="Delivery Manager", organization="Toptal", decision_rights="Scope", escalation_responsibility="PMO Lead"),
            Stakeholder(name="John Smith", role="Client Sponsor / Approver", organization="Acme Corp", decision_rights="Deliverable Sign-off", escalation_responsibility="Executive Leadership"),
            Stakeholder(name="Alice CFO", role="CFO / Executive Signatory", organization="Toptal", decision_rights="Commercial Sign-off", escalation_responsibility="CEO"),
            Stakeholder(name="Bob VP", role="Vice President / Client Executive Signatory", organization="Acme Corp", decision_rights="Contract Execution", escalation_responsibility="Board"),
        ],
        raci_matrix=[
            RACIItem(decision_or_activity="Startup readiness (G-01 gate)", pmo_lead="R, A", delivery_manager="R", talent_pm="C", sales_accounts="I", client="C"),
            RACIItem(decision_or_activity="Talent staffing & replacement", pmo_lead="R", delivery_manager="R, A", talent_pm="I", sales_accounts="I", client="I"),
            RACIItem(decision_or_activity="Work at risk", pmo_lead="R, A", delivery_manager="C", talent_pm="C", sales_accounts="I", client="I"),
            RACIItem(decision_or_activity="Scope & change", pmo_lead="R", delivery_manager="R", talent_pm="C", sales_accounts="I", client="A"),
            RACIItem(decision_or_activity="Delivery risk & recovery", pmo_lead="R, A", delivery_manager="C", talent_pm="R", sales_accounts="I", client="I"),
        ],
        communications_plan=[
            CommunicationsPlanItem(id="COM-01", name="Weekly PSR", audience="Client Sponsor, PMO", content_owner="Jane Doe", cadence="Weekly", format="PDF", delivery_day="Friday")
        ],
        talent_onboarding=TalentOnboardingRecord(
            pmo_lead="Sarah Connor",
            delivery_manager="Jane Doe",
            talent_pm="Alex Rivera",
        ),
    )


# =========================================================================
# 1. OUT-13a: Stop Generating Readiness Checklist
# =========================================================================

def test_out_13a_docx_generator_stops_producing_checklist(sample_full_baseline, tmp_path):
    """OUT-13a: DocxGenerator.write_documents and write_docx produce only the Startup Kit, not the Checklist."""
    generator = DocxGenerator()
    kit_path, cl_path = generator.write_documents(sample_full_baseline, tmp_path / "out_13a")

    assert kit_path.exists()
    assert kit_path.name == "Acme_Global_Platform_Startup_Kit.docx"
    assert cl_path is None
    # Confirm no checklist file was written to disk
    assert not (tmp_path / "out_13a" / "Acme_Global_Platform_Startup_Readiness_Checklist.docx").exists()


def test_out_13a_orchestrator_stops_generating_checklist(sample_full_baseline, tmp_path):
    """OUT-13a: Orchestrator generate_from_baseline does not generate checklist even if requested."""
    controller = StartupKitController(doc_writer=DocxGenerator())
    outputs = OutputSelection(kit=True, checklist=True, workbook=True, slides=True)

    result = controller.generate_from_baseline(sample_full_baseline, output_dir=tmp_path / "orch_out", outputs=outputs)
    assert result.kit_path is not None and result.kit_path.exists()
    assert result.checklist_path is None
    assert not (tmp_path / "orch_out" / "Acme_Global_Platform_Startup_Readiness_Checklist.docx").exists()


# =========================================================================
# 2. OUT-13b: Remove Two Fields from Project Info Table
# =========================================================================

def test_out_13b_project_info_table_removes_sla_status_and_workflow_state(sample_full_baseline, tmp_path):
    """OUT-13b: The generated Startup Kit's metadata header table contains exactly 4 rows (8 fields).
    '1-Day SLA Status' and 'Workflow State' are completely absent."""
    generator = DocxGenerator()
    kit_file = generator.write_docx(sample_full_baseline, tmp_path / "test_13b.docx")

    doc = docx.Document(str(kit_file))
    meta_table = doc.tables[0]

    # Exactly 4 rows and 4 columns
    assert len(meta_table.rows) == 4
    assert len(meta_table.columns) == 4

    all_table_text = "\n".join(" | ".join(c.text.strip() for c in r.cells) for r in meta_table.rows)

    # Required fields are present
    assert "Project Name" in all_table_text
    assert "Client Sponsor" in all_table_text
    assert "Governance Tier" in all_table_text
    assert "Contract Type" in all_table_text
    assert "Delivery Manager" in all_table_text
    assert "Talent PM" in all_table_text
    assert "PMO Lead" in all_table_text
    assert "Generated Date" in all_table_text

    # Removed fields MUST NOT be present
    assert "1-Day SLA Status" not in all_table_text
    assert "Workflow State" not in all_table_text


# =========================================================================
# 3. OUT-13c: Remove CFO and Client Executive Signatory Rows
# =========================================================================

def test_out_13c_stakeholder_table_removes_executive_signatories(sample_full_baseline, tmp_path):
    """OUT-13c: CFO / Executive Signatory and VP / Client Executive Signatory rows are removed from the Stakeholder table."""
    generator = DocxGenerator()
    kit_file = generator.write_docx(sample_full_baseline, tmp_path / "test_13c.docx")

    doc = docx.Document(str(kit_file))

    # Find Stakeholder and Responsibility Model table
    stk_tbl = next(t for t in doc.tables if any("stakeholder name" in c.text.lower() for c in t.rows[0].cells))
    stk_text = "\n".join(" | ".join(c.text.strip() for c in r.cells) for r in stk_tbl.rows)

    # Core operational stakeholders are present
    assert "Sarah Connor" in stk_text
    assert "Jane Doe" in stk_text
    assert "John Smith" in stk_text

    # Executive signatories MUST NOT be present
    assert "Alice CFO" not in stk_text
    assert "CFO" not in stk_text
    assert "Bob VP" not in stk_text
    assert "Signatory" not in stk_text


def test_out_13c_aggregator_filters_signatories():
    """OUT-13c: BaselineAggregator filters out CFO and signatory roles during extraction aggregation."""
    from src.core.models import (
        CharterExtraction,
        DeliverablesExtraction,
        MilestonesExtraction,
        RAIDExtraction,
        StakeholdersExtraction,
    )

    aggregator = BaselineAggregator()
    charter = CharterExtraction(project_name="Signatory Test", contract_type="Time and Materials")
    stakeholders_ext = StakeholdersExtraction(stakeholders=[
        Stakeholder(name="Lead Eng", role="Technical Lead", organization="Toptal"),
        Stakeholder(name="Toptal CFO", role="CFO / Executive Signatory", organization="Toptal"),
        Stakeholder(name="Client Exec", role="Vice President / Client Executive Signatory", organization="Client"),
    ])

    baseline = aggregator.aggregate(
        charter=charter,
        deliverables_ext=DeliverablesExtraction(),
        milestones_ext=MilestonesExtraction(),
        raid_ext=RAIDExtraction(),
        stakeholders_ext=stakeholders_ext,
    )
    roles = [s.role for s in baseline.stakeholders]

    assert "Technical Lead" in roles
    assert not any("cfo" in r.lower() or "signatory" in r.lower() for r in roles)


# =========================================================================
# 4. OUT-13d: Financial Figures Obfuscation
# =========================================================================

def test_out_13d_obfuscate_financials_function():
    """OUT-13d: Unit test for systematic financial figures obfuscation."""
    tm_placeholder = "Time & Materials engagement -- rate and total value withheld from Talent-facing copy"
    fb_placeholder = "Fixed Bid engagement -- rate and total value withheld from Talent-facing copy"

    # T&M cases
    assert obfuscate_financials("Billed at $150/hr for engineering.", "Time and Materials") == f"Billed at {tm_placeholder} for engineering."
    assert obfuscate_financials("Total fee capped at $250,000 USD.", "Time and Materials") == f"Total fee capped at {tm_placeholder}."
    assert obfuscate_financials("Rate of $120 / hr and budget of $150,000", "Time and Materials") == f"Rate of {tm_placeholder} and budget of {tm_placeholder}"

    # Fixed Bid cases
    assert obfuscate_financials("Fixed milestone payment of $50,000", "Fixed Bid") == f"Fixed milestone payment of {fb_placeholder}"
    assert obfuscate_financials("Total contract price is $500,000.00 USD", "Fixed Bid") == f"Total contract price is {fb_placeholder}"

    # Non-financial numbers remain intact
    non_fin = "Phase 2 delivers DEL-01 in 5 business days on 2026-10-24 with 99.9% SLA."
    assert obfuscate_financials(non_fin, "Time and Materials") == non_fin


def test_out_13d_systematic_obfuscation_in_generated_document(sample_full_baseline, tmp_path):
    """OUT-13d: Real generated Startup Kit contains no raw dollar figures or rates in any table/section."""
    generator = DocxGenerator()
    kit_file = generator.write_docx(sample_full_baseline, tmp_path / "test_13d.docx")

    doc = docx.Document(str(kit_file))

    all_doc_text = "\n".join(
        [p.text for p in doc.paragraphs] +
        [c.text for t in doc.tables for r in t.rows for c in r.cells]
    )

    # Dollar amounts and hourly rates from baseline must NOT appear
    assert "$150/hr" not in all_doc_text
    assert "$150.00/hr" not in all_doc_text
    assert "$175/hour" not in all_doc_text
    assert "$160/hr" not in all_doc_text
    assert "$250,000" not in all_doc_text
    assert "$300,000" not in all_doc_text
    assert "$180,000" not in all_doc_text
    assert "$100k" not in all_doc_text

    # The systematic talent-facing placeholder MUST be present
    assert "Time & Materials engagement -- rate and total value withheld from Talent-facing copy" in all_doc_text


# =========================================================================
# 5. KIT-14: RACI / Decision Rights Matrix
# =========================================================================

def test_kit_14_raci_matrix_headers_and_values(sample_full_baseline, tmp_path):
    """KIT-14: RACI matrix has 'Decision Activity' header, 'Work at risk' row label, and exact cell values."""
    generator = DocxGenerator()
    kit_file = generator.write_docx(sample_full_baseline, tmp_path / "test_kit_14.docx")

    doc = docx.Document(str(kit_file))

    # Find RACI table
    raci_tbl = next(t for t in doc.tables if any("pmo lead" in c.text.lower() for c in t.rows[0].cells) and any("client" in c.text.lower() for c in t.rows[0].cells))

    # Column headers
    headers = [c.text.strip() for c in raci_tbl.rows[0].cells]
    assert headers == ["Decision Activity", "PMO Lead", "Delivery Manager", "Talent PM", "Sales / Accts", "Client"]

    # Table rows
    rows_data = [[c.text.strip() for c in r.cells] for r in raci_tbl.rows[1:]]

    expected_rows = [
        ["Startup readiness (G-01 gate)", "R, A", "R", "C", "I", "C"],
        ["Talent staffing & replacement", "R", "R, A", "I", "I", "I"],
        ["Work at risk", "R, A", "C", "C", "I", "I"],
        ["Scope & change", "R", "R", "C", "I", "A"],
        ["Delivery risk & recovery", "R, A", "C", "R", "I", "I"],
    ]

    assert len(rows_data) == 5
    for idx, expected in enumerate(expected_rows):
        assert rows_data[idx] == expected


def test_kit_14_aggregator_default_raci_matrix():
    """KIT-14: BaselineAggregator populates the exact 5 rows and values per KIT-14 spec."""
    from src.core.models import CharterExtraction, DeliverablesExtraction, MilestonesExtraction, RAIDExtraction
    aggregator = BaselineAggregator()
    charter = CharterExtraction(project_name="RACI Test Project", contract_type="Time and Materials")
    baseline = aggregator.aggregate(
        charter=charter,
        deliverables_ext=DeliverablesExtraction(),
        milestones_ext=MilestonesExtraction(),
        raid_ext=RAIDExtraction()
    )

    raci_rows = [
        [r.decision_or_activity, r.pmo_lead, r.delivery_manager, r.talent_pm, r.sales_accounts, r.client]
        for r in baseline.raci_matrix
    ]
    expected_rows = [
        ["Startup readiness (G-01 gate)", "R, A", "R", "C", "I", "C"],
        ["Talent staffing & replacement", "R", "R, A", "I", "I", "I"],
        ["Work at risk", "R, A", "C", "C", "I", "I"],
        ["Scope & change", "R", "R", "C", "I", "A"],
        ["Delivery risk & recovery", "R, A", "C", "R", "I", "I"],
    ]
    assert raci_rows == expected_rows


# =========================================================================
# 6. HTL-45: Generate Page Output Checkboxes Default to False
# =========================================================================

def test_htl_45_generate_tab_output_checkboxes_default_to_false():
    """HTL-45: All document output checkboxes on Generate tab default to unchecked (False), and checklist is removed."""
    import time
    from streamlit.testing.v1 import AppTest

    app_path = str(Path(__file__).parent.parent / "src" / "review_ui" / "app.py")
    at = AppTest.from_file(app_path, default_timeout=10)
    at.session_state["generation_unlocked"] = True
    at.session_state["generation_unlocked_at"] = time.time()
    at.run()

    assert not at.exception

    # Generate tab checkboxes
    assert len([cb for cb in at.checkbox if cb.key == "gen_out_checklist"]) == 0

    kit_cb = next(cb for cb in at.checkbox if cb.key == "gen_out_kit")
    wb_cb = next(cb for cb in at.checkbox if cb.key == "gen_out_workbook")
    slides_cb = next(cb for cb in at.checkbox if cb.key == "gen_out_slides")

    assert kit_cb.value is False
    assert wb_cb.value is False
    assert slides_cb.value is False

    # Review before finalizing remains True
    review_cb = next(cb for cb in at.checkbox if cb.key == "gen_review_before_finalizing")
    assert review_cb.value is True


# =========================================================================
# 7. End-to-End Freshly-Generated Startup Kit Artifact Verification
# =========================================================================

def test_end_to_end_freshly_generated_startup_kit(sample_full_baseline):
    """Generates an actual document to output/OUT13_KIT14_HTL45_Verified_Startup_Kit.docx
    and validates all 6 changes on the real generated document."""
    out_file = Path("output/OUT13_KIT14_HTL45_Verified_Startup_Kit.docx")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    generator = DocxGenerator()
    generated_path = generator.write_docx(sample_full_baseline, out_file)

    assert generated_path.exists()
    assert not Path("output/OUT13_KIT14_HTL45_Verified_Startup_Readiness_Checklist.docx").exists()

    doc = docx.Document(str(generated_path))

    # 1. Info Table (OUT-13b)
    meta_table = doc.tables[0]
    assert len(meta_table.rows) == 4
    meta_text = " ".join(c.text for r in meta_table.rows for c in r.cells)
    assert "1-Day SLA Status" not in meta_text
    assert "Workflow State" not in meta_text

    # 2. Stakeholders (OUT-13c)
    stk_table = next(t for t in doc.tables if any("stakeholder name" in c.text.lower() for c in t.rows[0].cells))
    stk_text = " ".join(c.text for r in stk_table.rows for c in r.cells)
    assert "Alice CFO" not in stk_text
    assert "Bob VP" not in stk_text
    assert "Signatory" not in stk_text

    # 3. Financials (OUT-13d)
    all_text = "\n".join([p.text for p in doc.paragraphs] + [c.text for t in doc.tables for r in t.rows for c in r.cells])
    assert "$150/hr" not in all_text
    assert "$250,000" not in all_text
    assert "Time & Materials engagement -- rate and total value withheld from Talent-facing copy" in all_text

    # 4. RACI Matrix (KIT-14)
    raci_table = next(t for t in doc.tables if any("pmo lead" in c.text.lower() for c in t.rows[0].cells) and any("client" in c.text.lower() for c in t.rows[0].cells))
    headers = [c.text.strip() for c in raci_table.rows[0].cells]
    assert headers[0] == "Decision Activity"
    row_activities = [r.cells[0].text.strip() for r in raci_table.rows[1:]]
    assert "Work at risk" in row_activities
    assert "Work at risk / commercial exceptions" not in row_activities
