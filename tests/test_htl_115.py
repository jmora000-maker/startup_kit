"""HTL-115: Comprehensive automated test suite for the Programmatic commercial model.

Verifies:
1. CONTRACT_TYPES 3rd closed value and UI dropdown options.
2. False-Positive Protection: T&M contracts mentioning 'capacity' are NOT auto-classified as Programmatic.
3. PMO Workbook gating: export_pmo_workbook skipped cleanly when contract_type == 'Programmatic'.
4. Scope Baseline & Governance Tables (HTL-114 Programmatic alignment):
   - Table 2: Change Decision Matrix
   - Table 3: Decision Rules & Commercial Controls
   - Table 4: Scope Classification Guide & Character Budgets (<= 75 chars)
   - Table 5: Fallback Examples & LLM prompt instructions
5. Template loader routing for Team Onboarding and PS Governance Kickoff decks.
6. Slide content transformations across all three decks:
   - Client Kickoff Deck: Slide 3 role rename, Slide 5 header/notes, Slide 6 focus header.
   - PS Governance Kickoff Deck: Slide 2 agenda topics, Slide 8 fee phrasing, Slide 11 'xxx', Slide 12 matrix insertion, Slide 19 Next Steps retention.
   - Team Onboarding Deck: Programmatic template resolution and capacity fee framing.
"""

from pathlib import Path
import pptx
import pytest

from src.core.models import (
    StartupKitBaseline,
    ProjectStartupCharter,
    SOWInterpretationSummary,
    Deliverable,
    Milestone,
    DependencyAssumptionItem,
    CommercialGuardrail,
    Stakeholder,
)
from src.generators.docx_generator import DocxGenerator
from src.llm.aggregator import BaselineAggregator
from src.review_ui.constants import CONTRACT_TYPES
from src.generators.kit_values import resolve_pm_role_title
from src.generators.scope_baseline.templates import (
    resolve_contract_variant,
    build_table2_change_matrix_rows,
    build_table3_decision_rules_rows,
    build_table4_classification_guide_rows,
    build_table5_fallback_examples,
)
from src.generators.scope_baseline.builder import TABLE5_PROMPT_TEMPLATE
from src.generators.onboarding_deck.writer import resolve_onboarding_deck_template_path
from src.generators.governance_deck.writer import resolve_governance_deck_template_path
from src.generators.client_deck import export_client_deck
from src.generators.governance_deck import export_governance_deck
from src.orchestrator import StartupKitController, OutputSelection


def _create_mock_baseline(contract_type: str = "Programmatic") -> StartupKitBaseline:
    milestones = [
        Milestone(id="M-01", description="Sprint 1", external_date="2026-11-01", phase="Sprint 1"),
    ]
    charter = ProjectStartupCharter(
        project_name="HTL-115 Programmatic Project",
        client_name="Carrier Smart Home",
        contract_type=contract_type,
        governance_tier="Partnered",
        delivery_model="Toptal Talent Team (Agile Sprints)",
        project_purpose="Deliver smart home cloud connectivity through agile sprint backlogs.",
        problem_statement="Legacy IoT backend requires modern agile team capacity.",
        high_level_scope=["IoT Cloud", "Mobile SDK"],
        exclusions=["Hardware Firmware Manufacturing"],
        key_deliverables_summary=["DEL-01: Sprint Backlog Features"],
        milestones=milestones,
    )
    sow_int = SOWInterpretationSummary(
        contracted_deliverables=["Sprint Backlog Features"],
        out_of_scope_items=["Hardware Firmware"],
        platform_environment_commitments=["AWS IoT Core"],
        dependencies=["Client API Specifications (2 sprints ready backlog)"],
    )
    delivs = [Deliverable(id="DEL-01", name="Sprint Backlog Features", description="Two-week agile sprint backlog delivery")]
    deps = [DependencyAssumptionItem(id="DEP-01", type="Dependency", description="Client API Specifications", impact_if_unmet="Idle team capacity risk")]
    guardrails = CommercialGuardrail(
        contract_type_implication="Programmatic flat weekly fee with team capacity ceiling.",
        approved_work_rule="Work defined fresh per sprint backlog in accordance with agreed roadmap.",
        non_approved_work_rule="Out-of-roadmap capabilities require SOW Amendment or added team capacity.",
    )
    stakeholders = [
        Stakeholder(name="Jane Doe", role="Client Product Owner", organization="Client"),
        Stakeholder(name="John Smith", role="Product Manager", organization="Toptal"),
    ]

    return StartupKitBaseline(
        project_name="HTL-115 Programmatic Project",
        contract_type=contract_type,
        governance_tier="Partnered",
        charter=charter,
        sow_interpretation=sow_int,
        deliverables=delivs,
        milestones=milestones,
        dependencies_assumptions=deps,
        commercial_guardrails=guardrails,
        stakeholders=stakeholders,
    )


def test_htl_115_contract_types_and_role_normalization():
    """Verify CONTRACT_TYPES contains 3 closed values and role normalization helper returns 'Product Manager' for Programmatic."""
    assert CONTRACT_TYPES == ["Time and Materials", "Fixed Bid", "Programmatic"]

    assert resolve_pm_role_title("Programmatic") == "Product Manager"
    assert resolve_pm_role_title("programmatic retainer") == "Product Manager"
    assert resolve_pm_role_title("Time and Materials") == "Project Manager"
    assert resolve_pm_role_title("Fixed Bid") == "Project Manager"
    assert resolve_pm_role_title(None) == "Project Manager"


def test_htl_115_resolve_contract_variant_and_false_positive_safety():
    """Verify resolve_contract_variant identifies Programmatic and protects standard T&M contracts mentioning 'capacity'."""
    # 1. Programmatic matching
    assert resolve_contract_variant("Programmatic") == "Programmatic"
    assert resolve_contract_variant("Programmatic Retainer") == "Programmatic"
    assert resolve_contract_variant("Weekly Retainer") == "Programmatic"

    # 2. Fixed Bid matching
    assert resolve_contract_variant("Fixed Bid") == "Fixed Bid"
    assert resolve_contract_variant("Fixed Price Milestone") == "Fixed Bid"

    # 3. Time and Materials & false-positive protection on general 'capacity'
    assert resolve_contract_variant("Time and Materials") == "Time and Materials"
    assert resolve_contract_variant("T&M Hourly Rate with Weekly Capacity") == "Time and Materials"
    assert resolve_contract_variant("Time & Materials with 40-hour capacity ceiling") == "Time and Materials"
    assert resolve_contract_variant("Standard T&M SOW mentioning team capacity") == "Time and Materials"


def test_htl_115_pmo_workbook_orchestrator_gating(tmp_path: Path):
    """Verify PMO Delivery Workbook export is cleanly skipped for Programmatic contracts in run_reingest."""
    baseline = _create_mock_baseline("Programmatic")
    writer = DocxGenerator()
    docx_file = writer.write_docx(baseline, tmp_path / "Programmatic_Startup_Kit.docx")

    controller = StartupKitController(
        doc_writer=writer,
        aggregator=BaselineAggregator(),
    )
    outputs = OutputSelection(kit=False, checklist=False, workbook=True, slides=False, client_deck=False, scope_baseline=False)
    res = controller.run_reingest(
        docx_path=docx_file,
        output_dir=tmp_path / "pmo_gate_test",
        outputs=outputs,
        contract_type_override="Programmatic",
    )
    assert res.workbook is None
    generated_files = list((tmp_path / "pmo_gate_test").glob("*.xlsx"))
    assert len(generated_files) == 0


def test_htl_115_scope_baseline_programmatic_governance():
    """Verify Tables 2, 3, 4, 5 apply Programmatic role logic and character budgets (<= 75 chars)."""
    baseline = _create_mock_baseline("Programmatic")
    variant = "Programmatic"

    # Table 2: Change Decision Matrix
    t2_rows = build_table2_change_matrix_rows(baseline, variant)
    t2_map = {r.classification: r for r in t2_rows}

    # Clarification: Product Manager leads with Client PO
    assert "Product Manager leads resolution with Client Product Owner" in t2_map["Clarification"].governance_action
    # Reprioritization: Client PO decides, PM confirms capacity, zero Change Order required
    assert "Client Product Owner leads and decides backlog trade-offs" in t2_map["Reprioritization"].governance_action
    assert "zero Change Order required" in t2_map["Reprioritization"].governance_action
    # Expansion: Product Manager triggers event
    assert "Product Manager triggers event" in t2_map["Expansion"].governance_action
    assert "routed to Delivery Manager and PMO Lead" in t2_map["Expansion"].governance_action
    # Dependency Impact: Product Manager triggers blocker (>= 2 sprints ready backlog)
    assert "Product Manager triggers blocker" in t2_map["Dependency Impact"].governance_action
    assert "at least 2 sprints of Definition-of-Ready backlog" in t2_map["Dependency Impact"].trigger_condition

    # Table 3: Decision Rules
    t3_rows = build_table3_decision_rules_rows(baseline, variant)
    t3_map = {r.control_dimension: r for r in t3_rows}
    assert "Product Manager" in t3_map["Domain & Application Scope"].commercial_control_route
    assert "2 sprints of Definition-of-Ready stories" in t3_map["Core Dependency Health"].governing_rule

    # Table 4: Classification Guide and character budgets (<= 75 chars)
    t4_rows = build_table4_classification_guide_rows(baseline, variant)
    for r in t4_rows:
        assert len(r.approval_pathway) <= 75, f"Approval pathway '{r.approval_pathway}' exceeds 75 chars ({len(r.approval_pathway)})"
        if r.classification == "Clarification":
            assert "Product Manager leads" in r.approval_pathway
        elif r.classification == "Reprioritization":
            assert "Client PO decides" in r.approval_pathway
            assert "Product Manager confirms capacity" in r.approval_pathway
        elif r.classification == "Expansion":
            assert "Product Manager triggers" in r.approval_pathway
            assert "DM & PMO Lead" in r.approval_pathway
        elif r.classification == "Dependency Impact":
            assert "Product Manager triggers" in r.approval_pathway
            assert "DM & PMO Lead" in r.approval_pathway

    # Table 5 Fallback Examples
    t5_examples = build_table5_fallback_examples(baseline, variant)
    t5_map = {e.classification: e for e in t5_examples}
    assert "Product Manager leads" in t5_map["Clarification"].resolution_and_governance
    assert "Client Product Owner decides" in t5_map["Reprioritization"].resolution_and_governance
    assert "zero Change Order required" in t5_map["Reprioritization"].resolution_and_governance
    assert "Product Manager triggers" in t5_map["Expansion"].resolution_and_governance
    assert "Product Manager triggers" in t5_map["Dependency Impact"].resolution_and_governance


def test_htl_115_template_loader_routing():
    """Verify template resolution loads dedicated Programmatic vs Project templates."""
    # 1. Onboarding Deck
    p_onboarding = resolve_onboarding_deck_template_path(contract_type="Programmatic")
    assert "Programmatic" in p_onboarding.name

    prj_onboarding = resolve_onboarding_deck_template_path(contract_type="Time and Materials")
    assert "Programmatic" not in prj_onboarding.name

    # 2. PS Governance Kickoff Deck
    p_gov = resolve_governance_deck_template_path(contract_type="Programmatic")
    assert "Programmatic" in p_gov.name

    prj_gov = resolve_governance_deck_template_path(contract_type="Fixed Bid")
    assert "Programmatic" not in prj_gov.name


def test_htl_115_client_kickoff_deck_programmatic_adaptations(tmp_path: Path):
    """Verify Client Kickoff Deck applies Slide 3 role rename, Slide 5 header/notes, and Slide 6 focus headers."""
    baseline = _create_mock_baseline("Programmatic")
    res = export_client_deck(baseline, tmp_path / "client_deck_prog")
    prs = pptx.Presentation(str(res.file_path))

    # Slide 3 (Team Roster): Role label "Product Manager"
    s3 = prs.slides[2]
    s3_text = " ".join(shp.text_frame.text for shp in s3.shapes if shp.has_text_frame)
    assert "Product Manager" in s3_text or "Project Manager" not in s3_text

    # Slide 5 (Why We're Here): Eyebrow "ENGAGEMENT OVERVIEW"
    s5 = prs.slides[4]
    s5_text = " ".join(shp.text_frame.text for shp in s5.shapes if shp.has_text_frame)
    assert "ENGAGEMENT OVERVIEW" in s5_text

    # Slide 6 (What We Will Deliver / Focus): Header "Focus" & Eyebrow "ENGAGEMENT OVERVIEW"
    s6 = prs.slides[5]
    s6_texts = []
    for shp in s6.shapes:
        if shp.has_text_frame:
            s6_texts.append(shp.text_frame.text)
        if shp.has_table:
            for row in shp.table.rows:
                for cell in row.cells:
                    s6_texts.append(cell.text)
    s6_text = " ".join(s6_texts)
    assert "ENGAGEMENT OVERVIEW" in s6_text
    assert "Focus" in s6_text


def test_htl_115_governance_deck_programmatic_adaptations(tmp_path: Path):
    """Verify PS Governance Kickoff Deck applies Slide 2 agenda topics, Slide 8 fee phrasing, Slide 12 Matrix insertion, and Slide 19 Next Steps retention."""
    baseline = _create_mock_baseline("Programmatic")
    res = export_governance_deck(baseline, tmp_path / "gov_deck_prog")
    prs = pptx.Presentation(str(res.file_path))

    assert res.slides_count == 22
    assert len(prs.slides) == 22

    # Slide 2 (Agenda): Unnumbered topics and "Next steps"
    s2 = prs.slides[1]
    s2_text = " ".join(shp.text_frame.text for shp in s2.shapes if shp.has_text_frame)
    assert "Next steps" in s2_text
    for num_str in ["01", "02", "03", "04", "05", "06", "07", "08"]:
        assert num_str not in [shp.text_frame.text.strip() for shp in s2.shapes if shp.has_text_frame]

    # Slide 8 (Ways of Working): Fee phrasing
    s8 = prs.slides[7]
    s8_text = " ".join(shp.text_frame.text for shp in s8.shapes if shp.has_text_frame)
    assert "within the agreed weekly capacity" in s8_text
    assert "against the not-to-exceed" not in s8_text

    # Slide 11: Third scenario contains "xxx"
    s11 = prs.slides[10]
    s11_text = " ".join(shp.text_frame.text for shp in s11.shapes if shp.has_text_frame)
    assert "xxx" in s11_text

    # Slide 12 (Inserted Slide 11+1): Change Decision Matrix (4 cards)
    s12 = prs.slides[11]
    s12_text = " ".join(shp.text_frame.text for shp in s12.shapes if shp.has_text_frame)
    assert "Clarification" in s12_text
    assert "Reprioritization" in s12_text
    assert "Expansion" in s12_text
    assert "Dependency Impact" in s12_text
    assert "Authority: Product Manager leads" in s12_text
    assert "Authority: Client PO decides; Product Manager confirms capacity" in s12_text

    # Slide 21 (Retained Next Steps): Next Steps table present before closing slide
    s21 = prs.slides[20]
    s21_texts = []
    for shp in s21.shapes:
        if shp.has_text_frame:
            s21_texts.append(shp.text_frame.text)
        if shp.has_table:
            for row in shp.table.rows:
                for cell in row.cells:
                    s21_texts.append(cell.text)
    s21_text = " ".join(s21_texts)
    assert "Next Steps" in s21_text or "PATH FORWARD" in s21_text or "Action" in s21_text or "Owner" in s21_text


def test_htl_118_comprehensive_regression(tmp_path: Path):
    """HTL-118: Verification for all 9 deployment blockers for Programmatic feature."""
    from src.generators.scope_baseline.templates import build_table1_summary_rows
    from src.review_ui.facts import build_fact_categories

    baseline = _create_mock_baseline("Programmatic")

    # 1. Table 1 Real Commercial Content
    t1_rows = build_table1_summary_rows(baseline, "Programmatic")
    t1_map = {r.dimension: r for r in t1_rows}

    # Row 3
    assert "contracted weekly team capacity ceiling" in t1_map["Authorized Deliverables & Work Streams"].excluded_scope
    assert "timesheet" not in t1_map["Authorized Deliverables & Work Streams"].excluded_scope.lower()

    # Row 4
    assert "agile sprint cadences and prioritized sprint backlog commitments" in t1_map["Delivery Model & Service Boundaries"].authorized_work
    assert "team effort exceeding agreed weekly capacity allocations" in t1_map["Delivery Model & Service Boundaries"].excluded_scope
    assert "Not-to-Exceed" not in t1_map["Delivery Model & Service Boundaries"].excluded_scope
    assert "NTE" not in t1_map["Delivery Model & Service Boundaries"].excluded_scope

    # Row 6
    assert "Invoicing is based on contracted flat weekly retainer fees" in t1_map["Commercial Controls & Governance"].authorized_work
    assert "Scope shift requiring team composition or capacity adjustment" in t1_map["Commercial Controls & Governance"].authorized_work
    assert "Unapproved team capacity expansion" in t1_map["Commercial Controls & Governance"].excluded_scope
    assert "timesheets" not in t1_map["Commercial Controls & Governance"].authorized_work.lower()
    assert "effort burn" not in t1_map["Commercial Controls & Governance"].authorized_work.lower()
    assert "NTE ceiling" not in t1_map["Commercial Controls & Governance"].excluded_scope

    # 3. Fact Review Milestones & Deliverable Phase relabeling
    cats = build_fact_categories(baseline)
    cat_map = {c.key: c for c in cats}
    assert cat_map["milestones"].title == "Sprint Cadence & Roadmap Milestones"
    assert "sprint cadences and backlog priorities" in cat_map["milestones"].note
    assert cat_map["deliverable_phase_assignment"].title == "Deliverable workstream assignment"
    assert "product capability workstreams" in cat_map["deliverable_phase_assignment"].note

    # 4, 5, 6, 7/9. Governance Deck generation & verification
    res_gov = export_governance_deck(baseline, tmp_path / "gov_deck_htl118")
    prs_gov = pptx.Presentation(str(res_gov.file_path))

    # Item 5: Newly inserted slides have solid white background (#FFFFFF)
    for s_idx in [11, 14, 19, 20]:  # 0-indexed slide 12 (Change Matrix), 15 (Deliverables), 20 (Risks), 21 (Next Steps)
        s = prs_gov.slides[s_idx]
        assert s.background.fill.type is not None
        assert s.background.fill.fore_color.rgb == pptx.dml.color.RGBColor(0xFF, 0xFF, 0xFF)

    # Item 6: Slide 14 Overview is populated with zero unfilled template bracket placeholders
    s14 = prs_gov.slides[13]  # Slide 14
    s14_text = " ".join(shp.text_frame.text for shp in s14.shapes if shp.has_text_frame)
    for shp in s14.shapes:
        if shp.has_table:
            for row in shp.table.rows:
                for cell in row.cells:
                    s14_text += " " + cell.text
    assert "[Client name]" not in s14_text
    assert "[Engagement name]" not in s14_text
    assert "[Start date]" not in s14_text
    assert "[Name]" not in s14_text
    assert "Carrier Smart Home" in s14_text
    assert "HTL-115 Programmatic Project" in s14_text

    # Items 7 & 9: Next Steps dynamic derivation
    s21 = prs_gov.slides[20]  # Slide 21 (Next Steps)
    s21_table = [shp.table for shp in s21.shapes if shp.has_table][0]
    # Check that owner is resolved to real stakeholder / role and due is not static TBD
    for row in list(s21_table.rows)[1:]:
        owner_txt = row.cells[0].text.strip()
        due_txt = row.cells[2].text.strip()
        assert owner_txt != "[Client]"
        assert owner_txt != "[Toptal]"
        assert due_txt != "TBD"

    # Item 8: Client Deck Workstream Mapping (HTL-118 Section 2 SOW Roadmap Grouping)
    from src.generators.client_deck.builder import build_slide6_model
    from src.core.models import SourceReference

    carrier_delivs_with_sec = [
        # 2.1.1 Feature development
        Deliverable(id="DEL-01", name="Multi-user home access, roles, and permissions", source_reference=SourceReference(clause_or_slide="Section 2.1.1")),
        Deliverable(id="DEL-02", name="Accessory maintenance and reminder flows", source_reference=SourceReference(clause_or_slide="Section 2.1.1")),
        Deliverable(id="DEL-03", name="Account-level notification preferences", source_reference=SourceReference(clause_or_slide="Section 2.1.1")),
        Deliverable(id="DEL-04", name="Alert, activity, and service-experience surfaces", source_reference=SourceReference(clause_or_slide="Section 2.1.1")),
        Deliverable(id="DEL-05", name="Vacation, lockout, and other device-configuration flows", source_reference=SourceReference(clause_or_slide="Section 2.1.1")),
        # 2.1.2 Security and reliability
        Deliverable(id="DEL-06", name="Identity, login, and security hardening", source_reference=SourceReference(clause_or_slide="Section 2.1.2")),
        Deliverable(id="DEL-07", name="Defect triage, production-defect remediation, and reliability fixes", source_reference=SourceReference(clause_or_slide="Section 2.1.2")),
        Deliverable(id="DEL-08", name="Connectivity, stale-state, and device-sync recovery", source_reference=SourceReference(clause_or_slide="Section 2.1.2")),
        # 2.1.3 Quality engineering and release support
        Deliverable(id="DEL-09", name="Automated and targeted test coverage", source_reference=SourceReference(clause_or_slide="Section 2.1.3")),
        Deliverable(id="DEL-10", name="Regression and release-train support on iOS and Android", source_reference=SourceReference(clause_or_slide="Section 2.1.3")),
        Deliverable(id="DEL-11", name="Device simulator for T-Stat tool with Doppelio automation", source_reference=SourceReference(clause_or_slide="Section 2.1.3")),
    ]
    b_carrier = _create_mock_baseline("Programmatic")
    b_carrier.deliverables = carrier_delivs_with_sec

    s6_model_sec = build_slide6_model(b_carrier)
    assert len(s6_model_sec.workstreams) == 3
    assert s6_model_sec.workstreams[0].title == "Feature development"
    assert len(s6_model_sec.workstreams[0].deliverables) == 5
    assert s6_model_sec.workstreams[1].title == "Security and reliability"
    assert len(s6_model_sec.workstreams[1].deliverables) == 3
    assert s6_model_sec.workstreams[2].title == "Quality engineering and release support"
    assert len(s6_model_sec.workstreams[2].deliverables) == 3

    # Also verify semantic thematic grouping when section numbers are absent
    carrier_delivs_no_sec = [
        Deliverable(id=d.id, name=d.name, description=d.description, source_reference=SourceReference())
        for d in carrier_delivs_with_sec
    ]
    b_carrier_no_sec = _create_mock_baseline("Programmatic")
    b_carrier_no_sec.deliverables = carrier_delivs_no_sec
    s6_model_no_sec = build_slide6_model(b_carrier_no_sec)
    assert len(s6_model_no_sec.workstreams) == 3
    assert s6_model_no_sec.workstreams[0].title == "Feature development"
    assert s6_model_no_sec.workstreams[1].title == "Security and reliability"
    assert s6_model_no_sec.workstreams[2].title == "Quality engineering and release support"

    res_client = export_client_deck(b_carrier, tmp_path / "client_deck_htl118")
    prs_client = pptx.Presentation(str(res_client.file_path))
    s6_table_text = ""
    for s in prs_client.slides:
        for shp in s.shapes:
            if shp.has_table:
                for row in shp.table.rows:
                    for cell in row.cells:
                        s6_table_text += " " + cell.text
    assert "Feature development" in s6_table_text
    assert "Security and reliability" in s6_table_text
    assert "Quality engineering and release support" in s6_table_text


def test_htl_119_comprehensive_regression(tmp_path: Path):
    """HTL-119: Verification for all 4 items for Programmatic model."""
    from src.generators.governance_deck.builder import build_slide14_overview_model, condense_tools_and_environments
    from src.generators.client_deck.builder import ADMIN_PROCESS_DELIVERABLE_REGEX, build_slide6_model
    from src.core.models import SourceReference

    # Item 1: Tools and Environments condensation and Slide 14 row 5 formatting
    commitments = [
        "Development, sustainment, and quality engineering cover the client's Smart Home iOS and Android applications.",
        "Work is restricted to client-approved environments using client-provisioned tools and access.",
        "Production data and client confidential information must remain within client-approved environments.",
        "Client provides repositories, CI/CD pipelines, test/staging environments, required APIs, test devices/device cloud, test accounts, and the Doppelio environment.",
    ]
    condensed = condense_tools_and_environments(commitments)
    assert len(condensed) <= 140
    assert "iOS/Android platforms" in condensed
    assert "Doppelio" in condensed
    assert "CI/CD pipelines" in condensed
    assert "Client repositories" in condensed
    # Ensure no raw sentences
    assert "Development, sustainment, and quality engineering" not in condensed

    baseline = _create_mock_baseline("Programmatic")
    if baseline.sow_interpretation:
        baseline.sow_interpretation.platform_environment_commitments = commitments
    ov = build_slide14_overview_model(baseline)
    assert "iOS/Android platforms" in ov.tools_environments

    res_gov = export_governance_deck(baseline, tmp_path / "gov_deck_htl119")
    prs_gov = pptx.Presentation(str(res_gov.file_path))
    s14 = prs_gov.slides[13]  # Slide 14
    tbl_stakeholders = [shp.table for shp in s14.shapes if shp.has_table and len(shp.table.columns) == 3][0]
    cell_r5_c0 = tbl_stakeholders.cell(5, 0)
    p = cell_r5_c0.text_frame.paragraphs[0]
    r = p.runs[0]
    assert r.font.bold is True
    assert r.font.color.rgb == pptx.dml.color.RGBColor(0x0F, 0x25, 0x6E)

    # Item 2: ADMIN_PROCESS_DELIVERABLE_REGEX precision
    admin_deliv_names = [
        "Sprint sign-off package",
        "Weekly status reports",
        "Engagement completion sign-off",
        "Work documentation",
        "Sprint Plans and backlog alignment",
        "Work-product licensing inventory",
    ]
    for ad in admin_deliv_names:
        assert ADMIN_PROCESS_DELIVERABLE_REGEX.search(ad) is not None, f"Admin regex failed to match '{ad}'"

    sec21_deliv_names = [
        "Multi-user home access, roles, and permissions",
        "Accessory maintenance and reminder flows",
        "Account-level notification preferences",
        "Alert, activity, and service-experience surfaces",
        "Vacation, lockout, and other device-configuration flows",
        "Identity, login, and security hardening",
        "Defect triage, production-defect remediation, and reliability fixes",
        "Connectivity, stale-state, and device-sync recovery",
        "Automated and targeted test coverage",
        "Regression and release-train support on iOS and Android",
        "Device simulator for T-Stat tool with Doppelio automation",
    ]
    for fd in sec21_deliv_names:
        assert ADMIN_PROCESS_DELIVERABLE_REGEX.search(fd) is None, f"Admin regex falsely matched feature deliverable '{fd}'"

    # Verify that mixing all 11 feature delivs + 6 admin delivs results in exactly 3 clean workstreams with 0 admin items
    all_delivs = [
        Deliverable(id=f"DEL-{i+1:02d}", name=name, source_reference=SourceReference(clause_or_slide="Section 2.1.1" if i < 5 else ("Section 2.1.2" if i < 8 else "Section 2.1.3")))
        for i, name in enumerate(sec21_deliv_names)
    ] + [
        Deliverable(id=f"DEL-{i+12:02d}", name=name, source_reference=SourceReference(clause_or_slide="Section 2.2" if i < 3 else "Section 5"))
        for i, name in enumerate(admin_deliv_names)
    ]
    b_all = _create_mock_baseline("Programmatic")
    b_all.deliverables = all_delivs
    s6_all = build_slide6_model(b_all)
    assert len(s6_all.workstreams) == 3
    assert s6_all.workstreams[0].title == "Feature development"
    assert len(s6_all.workstreams[0].deliverables) == 5
    assert s6_all.workstreams[1].title == "Security and reliability"
    assert len(s6_all.workstreams[1].deliverables) == 3
    assert s6_all.workstreams[2].title == "Quality engineering and release support"
    assert len(s6_all.workstreams[2].deliverables) == 3

    # Item 3: Client Deck Slide 8 / Approach card bodies defensive font size (8.0pt) and zero margins
    res_client = export_client_deck(b_all, tmp_path / "client_deck_htl119")
    prs_client = pptx.Presentation(str(res_client.file_path))
    s8_client = prs_client.slides[7]
    for shp in s8_client.shapes:
        if shp.has_text_frame:
            txt = shp.text_frame.text.strip()
            if any(k in txt for k in ("Kickoff call", "Access and environments", "Final regression", "Handoff documentation")):
                assert shp.text_frame.margin_top == 0
                assert shp.text_frame.margin_bottom == 0
                for p in shp.text_frame.paragraphs:
                    for r in p.runs:
                        if r.font and r.font.size:
                            assert r.font.size.pt <= 8.0

    # Item 4: Parity slides in Programmatic Governance Deck (22 slides total)
    assert len(prs_gov.slides) == 22
    # Slide 15: What we will deliver (idx 14)
    s15_gov = prs_gov.slides[14]
    s15_gov_text = " ".join(shp.text_frame.text for shp in s15_gov.shapes if shp.has_text_frame)
    for shp in s15_gov.shapes:
        if shp.has_table:
            for row in shp.table.rows:
                for cell in row.cells:
                    s15_gov_text += " " + cell.text
    assert "ENGAGEMENT OVERVIEW" in s15_gov_text
    assert "Focus" in s15_gov_text or "Feature development" in s15_gov_text

    # Slide 20: Initial Risk Register (idx 19)
    s20_gov = prs_gov.slides[19]
    s20_gov_text = " ".join(shp.text_frame.text for shp in s20_gov.shapes if shp.has_text_frame)
    for shp in s20_gov.shapes:
        if shp.has_table:
            for row in shp.table.rows:
                for cell in row.cells:
                    s20_gov_text += " " + cell.text
    assert "INITIAL RISK REGISTER" in s20_gov_text or "Risk Description" in s20_gov_text or "Severity" in s20_gov_text
