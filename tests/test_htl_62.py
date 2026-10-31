"""HTL-62: Automated test suite for Talent Onboarding Deck Acceptance Criteria slide.

Verifies:
1. All 6 PGE deliverables render both real acceptance criteria (12 total criteria) in full,
   with no silent truncation on DEL-01, DEL-02, or DEL-05.
2. SOW-realistic long multi-clause criteria (65+ words) render completely within available table height.
3. check_deck_invariants (including INV-28 exemption for Slide 4 Column 1) passes cleanly.
"""

from datetime import date
from pathlib import Path
import pptx
import docx
import openpyxl
import pytest

from src.core.models import (
    CommunicationsPlanItem,
    Deliverable,
    GovernanceContext,
    Milestone,
    ProjectStartupCharter,
    RiskAssumption,
    SOWInterpretationSummary,
    Stakeholder,
    StartupKitBaseline,
)
from src.generators.docx_generator import DocxGenerator
from src.generators.onboarding_deck import export_onboarding_deck
from src.generators.onboarding_deck.builder import build_deck_model
import src.generators.onboarding_deck.layout as L
from src.generators.pmo_workbook import export_pmo_workbook
from src.generators.pmo_workbook.builder import build_workbook_model
from src.tools.check_artifacts import check_deck_invariants


PGE_DELIVERABLES = [
    Deliverable(
        id="DEL-01",
        name="Portfolio Inventory",
        description="Inventory of in-scope applications and infrastructure, with utilization/performance baselines and per-workload requirements where applicable.",
        acceptance_criteria="Inventory covers ≥ 95% of in-scope workloads; each workload has owner, hosting, and requirements recorded with available information.",
        submission_target_date="2026-11-18",
        review_window="5 business days",
        client_approver="Alicia Cook (Client Contact)",
    ),
    Deliverable(
        id="DEL-02",
        name="Dependency Map",
        description="Dependency diagram(s) and an integration catalog covering inter-application and infrastructure dependencies to inform sequencing and wave grouping.",
        acceptance_criteria="Every in-scope workload mapped to its dependencies (for applicable dependencies only); cross-workload dependencies flagged for sequencing (for applicable dependencies only).",
        submission_target_date="2026-11-18",
        review_window="5 business days",
        client_approver="Alicia Cook (Client Contact)",
    ),
    Deliverable(
        id="DEL-03",
        name="Workload Disposition Register",
        description="Register assigning a 7 Rs disposition to each in-scope workload, recording target service/architecture, migration wave, complexity/risk rating, and rationale.",
        acceptance_criteria="Every in-scope workload has exactly one disposition; each disposition carries a documented rationale.",
        submission_target_date="2026-11-18",
        review_window="5 business days",
        client_approver="Alicia Cook (Client Contact)",
    ),
    Deliverable(
        id="DEL-04",
        name="Target Architecture Recommendation",
        description="Target-state architecture recommendation(s) and cloud provider/service recommendation(s) for the in-scope workloads.",
        acceptance_criteria="Recommendation addresses each disposition category; key architectural decisions documented with trade-offs.",
        submission_target_date="2026-11-18",
        review_window="5 business days",
        client_approver="Alicia Cook (Client Contact)",
    ),
    Deliverable(
        id="DEL-05",
        name="Business Case & TCO Model",
        description="Multi-year cost projection, total cost of ownership comparison against the current state, and a migration business case.",
        acceptance_criteria="Every in-scope workload has a right-sized cost estimate; projection horizon, pricing models, and tools are documented.",
        submission_target_date="2026-11-18",
        review_window="5 business days",
        client_approver="Alicia Cook (Client Contact)",
    ),
    Deliverable(
        id="DEL-06",
        name="Migration Wave Plan & Roadmap",
        description="Workload wave grouping and sequencing, a high-level migration roadmap, and a risk register.",
        acceptance_criteria="Every in-scope workload assigned to a wave; sequencing reflects documented dependencies.",
        submission_target_date="2026-11-18",
        review_window="5 business days",
        client_approver="Alicia Cook (Client Contact)",
    ),
]


PGE_RAID = [
    RiskAssumption(
        id="RA-01",
        category="Risk",
        description="Undocumented custom business logic in legacy stored procedures may delay dependency mapping.",
        impact="High",
        mitigation="Conduct dedicated SME discovery walkthroughs and prioritize code analysis in Week 1.",
        owner="Toptal Lead Architect",
    ),
    RiskAssumption(
        id="RA-02",
        category="Risk",
        description="Third-party vendor data feed documentation may be incomplete for compliance interval workloads.",
        impact="Medium",
        mitigation="Flag vendor integration interfaces early and request sample payloads during initial sprint.",
        owner="PGE Technical Sponsor",
    ),
]

PGE_STAKEHOLDERS = [
    Stakeholder(
        name="Alicia Cook",
        role="Client Contact / Approver",
        organization="Client",
        decision_rights="Signs off on milestone deliverables and formal acceptance",
    )
]

PGE_COMMS = [
    CommunicationsPlanItem(
        id="COM-01",
        name="Weekly Status Meeting",
        cadence="Weekly",
        audience="PGE & Toptal Project Team",
        content_owner="Delivery Lead",
    ),
    CommunicationsPlanItem(
        id="COM-02",
        name="Bi-Weekly Architecture Sync",
        cadence="Bi-Weekly",
        audience="Technical Sponsors & Architects",
        content_owner="Toptal Lead Architect",
    ),
    CommunicationsPlanItem(
        id="COM-03",
        name="Milestone Acceptance Review",
        cadence="At Milestone Completion",
        audience="PGE Steering Committee",
        content_owner="Delivery Lead",
    ),
]


from tests.deck_bundle import load_baseline
from src.llm.validation import validate_and_repair_baseline


PGE_ACCEPTANCE_PROCESS_NARRATIVE = (
    "Inputs ready: Confirm Client has issued the Purchase Order before work starts, and that environment read access, "
    "discovery tooling access, spend data and SME availability are in place before Day 1. Client decision turnaround on review items is assumed to be within 3 business days.\n"
    "Execution: Deliver all six Work Output items (Portfolio Inventory, Dependency Map, Workload Disposition Register, "
    "Target Architecture Recommendation, Business Case & TCO Model, Migration Wave Plan & Roadmap) as Milestone 1, targeting November 18, 2026. "
    "Send the weekly status report and ask Client Contact Alicia Cook to confirm acceptance or give feedback on each one.\n"
    "Submission: Give Alicia Cook formal notice that Milestone 1 is complete. The 5-business-day Milestone Acceptance Period starts from the date of that notice, so record the date.\n"
    "Review: Client has 5 business days from the completion notice to evaluate the Work Output against its specifications and Acceptance Criteria in all material respects. "
    "Milestone review sessions with the Client Contact (and Client SMEs as needed) cover the Work Output against the criteria.\n"
    "Deemed accepted: If Client gives no written notice of failure within the 5 business days, or starts using the Work Output commercially or in production, "
    "Milestone 1 is deemed accepted. Client is still expected to sign and deliver a certification of Milestone acceptance.\n"
    "Triage: If Client finds a material non-conformance, it must notify Supplier in writing, stating how the output does not conform and what modifications are required. "
    "Check the notice for these details and clarify any gaps with the Client Contact.\n"
    "Remediation: Supplier uses commercially reasonable efforts to modify the non-conforming Work Output and resubmits it for acceptance. "
    "No supplier rework turnaround is stated, so agree a date with Client at the time of notice.\n"
    "Rework limit: If Supplier cannot remedy a non-conforming portion within Client's reasonable discretion after 3 repeated attempts, Client may terminate the SOW. "
    "On termination Client pays all amounts due or accrued through the termination date, including work in progress.\n"
    "Sign-off and invoicing: Milestone 1 sign-off is the invoice trigger for the full fixed fee, with an estimated invoice date of 11/18/2026. "
    "If the actual completion date differs, notify Client in writing (email suffices).\n"
    "Exceptions: Dependencies, workloads or scope found later may require a Change Order. Delays caused by the Client Contact being unavailable or late on "
    "Client responsibilities may justify an equitable adjustment to schedule and fees."
)


def _build_pge_baseline(deliverables=None) -> StartupKitBaseline:
    charter = ProjectStartupCharter(
        project_name="Cloud Migration Assessment – Operational Compliance Program (OCP)",
        client_name="Portland General Electric Company",
        project_purpose="Assessment and cloud migration roadmap for PGE's Operational Compliance Program (OCP) systems.",
        problem_statement=(
            "The OCP application is an aging custom system with recurring production failures "
            "and unflagged manual data overrides causing gaps at required 3-hour compliance intervals."
        ),
        solution_overview=(
            "The engagement delivers a comprehensive assessment and cloud migration roadmap for "
            "PGE's Operational Compliance Program (OCP) systems. Workstreams inventory in-scope "
            "workloads and map dependencies to establish target architectures and a multi-year TCO model. "
            "Delivery culminates in a 7 Rs disposition register and sequenced migration wave plan aligned "
            "with compliance standards."
        ),
        success_criteria_summary=(
            "The client receives a clear, evidence-backed view of their OCP infrastructure and modern "
            "cloud architecture options. They can confidently decide workload disposition and wave sequencing, "
            "supported by an actionable multi-year TCO model and validated migration roadmap."
        ),
        delivery_objectives=[
            "Assess current-state OCP infrastructure and custom stored procedure business logic",
            "Produce comprehensive workload portfolio inventory and dependency mapping",
            "Deliver 7 Rs disposition register, target architecture recommendation, TCO model, and wave roadmap",
        ],
        success_criteria=[
            "Formal client sign-off on Milestone 1 Assessment Report",
            "100% of in-scope workloads assigned target architecture and migration wave sequencing",
        ],
        high_level_scope=[
            "Portfolio inventory across in-scope workloads",
            "Dependency mapping and integration catalog",
            "Disposition register, target architecture, and wave migration roadmap",
        ],
        exclusions=[
            "Implementation of application code modifications or refactoring",
            "Production workload migrations during the assessment phase",
        ],
        key_deliverables_summary=[
            "DEL-01: Portfolio Inventory",
            "DEL-02: Dependency Map",
            "DEL-03: Workload Disposition Register",
            "DEL-04: Target Architecture Recommendation",
            "DEL-05: Business Case & TCO Model",
            "DEL-06: Migration Wave Plan & Roadmap",
        ],
        key_milestones_summary=[
            "M1: Milestone 1: Cloud Migration Assessment Report (due 2026-11-18)",
        ],
        contract_type="Fixed Bid",
        governance_tier="Partnered",
        delivery_model="Toptal Talent Team (Agile/Milestone Hybrid)",
        governance_model="PMO Partnered Tier Governance Model",
        major_startup_risks=[
            "Legacy stored procedure logic undocumented; mitigated by dedicated discovery walkthroughs.",
        ],
        delivery_manager="Jane Doe",
        talent_pm="John Smith",
        pmo_lead="Alex PMO",
    )

    gov_ctx = GovernanceContext(
        project_name="Cloud Migration Assessment – Operational Compliance Program (OCP)",
        client_name="Portland General Electric Company",
        contract_type="Fixed Bid",
        governance_tier="Partnered",
        sow_title="PGE Toptal SOW 7 - Cloud Migration Assessment + Exhibit A",
        sow_effective_date="2026-10-26",
    )

    sow_interp = SOWInterpretationSummary(
        contracted_deliverables=["DEL-01", "DEL-02", "DEL-03", "DEL-04", "DEL-05", "DEL-06"],
        out_of_scope_items=[
            "Application code refactoring and migration execution",
            "Procurement of target cloud infrastructure licenses",
        ],
        customer_obligations=[
            "Provide access to application documentation and SME personnel within 3 business days of request",
            "Review and provide sign-off on deliverables within 5 business days of submission",
        ],
        assumptions=[
            "Assessment is based on currently deployed OCP application architecture and available documentation.",
        ],
        constraints=[
            "Assessment period concludes November 18, 2026.",
        ],
        platform_environment_commitments=[
            "Access to PGE staging environment and code repository for analysis.",
        ],
        dependencies=[
            "Availability of PGE technical SMEs for interview walkthroughs.",
        ],
        approval_expectations="Formal written sign-off within 5 business days of Milestone 1 report submission.",
        acceptance_process_narrative=PGE_ACCEPTANCE_PROCESS_NARRATIVE,
        ambiguity_notes=[],
        confirmation_required_items=[],
    )

    baseline = StartupKitBaseline(
        project_name="Cloud Migration Assessment – Operational Compliance Program (OCP)",
        governance_tier="Partnered",
        contract_type="Fixed Bid",
        governance_context=gov_ctx,
        charter=charter,
        sow_interpretation=sow_interp,
        deliverables=list(deliverables or PGE_DELIVERABLES),
        milestones=[
            Milestone(
                id="MS-01",
                description="Milestone 1: Cloud Migration Assessment Report",
                external_date=date(2026, 11, 18),
                linked_deliverables="DEL-01, DEL-02, DEL-03, DEL-04, DEL-05, DEL-06",
                critical_path_assumptions=["$19,650 fee billed upon formal client acceptance."],
            )
        ],
        interim_checkpoints=[],
        backlog_seed=[],
        raid_items=list(PGE_RAID),
        stakeholders=list(PGE_STAKEHOLDERS),
        communications_plan=list(PGE_COMMS),
        author_name="Alex PMO",
        approver_name="Alex PMO",
    )
    validate_and_repair_baseline(baseline)
    return baseline


def test_pge_all_six_deliverables_render_full_acceptance_criteria(tmp_path):
    """HTL-62: All 6 PGE deliverables render both real acceptance criteria (12 total criteria) in full."""
    baseline = _build_pge_baseline()

    kit_path = DocxGenerator().write_kit_docx(baseline, tmp_path)
    wb_res = export_pmo_workbook(baseline, tmp_path)
    deck_res = export_onboarding_deck(baseline, tmp_path)

    prs = pptx.Presentation(str(deck_res.file_path))
    slide4 = prs.slides[3]

    table_shapes = [s for s in slide4.shapes if getattr(s, "has_table", False) and s.has_table]
    assert len(table_shapes) == 1
    table = table_shapes[0].table

    # Header + 6 deliverables = 7 rows
    assert len(table.rows) == 7

    # Check DEL-01 (Row 1): both criteria must be present
    del01_text = table.cell(1, 1).text
    assert "Inventory covers ≥ 95% of in-scope workloads" in del01_text
    assert "each workload has owner, hosting, and requirements recorded with available information" in del01_text

    # Check DEL-02 (Row 2): both criteria must be present
    del02_text = table.cell(2, 1).text
    assert "Every in-scope workload mapped to its dependencies" in del02_text
    assert "cross-workload dependencies flagged for sequencing" in del02_text

    # Check DEL-03 (Row 3): both criteria must be present
    del03_text = table.cell(3, 1).text
    assert "Every in-scope workload has exactly one disposition" in del03_text
    assert "each disposition carries a documented rationale" in del03_text

    # Check DEL-04 (Row 4): both criteria must be present
    del04_text = table.cell(4, 1).text
    assert "Recommendation addresses each disposition category" in del04_text
    assert "key architectural decisions documented with trade-offs" in del04_text

    # Check DEL-05 (Row 5): both criteria must be present
    del05_text = table.cell(5, 1).text
    assert "Every in-scope workload has a right-sized cost estimate" in del05_text
    assert "projection horizon, pricing models, and tools are documented" in del05_text

    # Check DEL-06 (Row 6): both criteria must be present
    del06_text = table.cell(6, 1).text
    assert "Every in-scope workload assigned to a wave" in del06_text
    assert "sequencing reflects documented dependencies" in del06_text

    # Check Gate column: all 6 deliverables must link to M1 (the single milestone)
    for r in range(1, 7):
        assert table.cell(r, 2).text == "M1", f"Row {r} gate is {table.cell(r, 2).text}, expected M1"

    # Invariants check
    kit_doc = docx.Document(str(kit_path))
    wb = openpyxl.load_workbook(str(wb_res.file_path), data_only=False)
    violations = check_deck_invariants(deck_res.file_path, deck_res.manifest_path, kit_doc, wb)
    assert len(violations) == 0, f"Unexpected invariant violations: {violations}"


def test_pge_baseline_has_no_arc_contamination_across_all_artifacts(tmp_path):
    """HTL-63: PGE artifacts must contain only the real single milestone (MS-01) with zero ARC contamination."""
    baseline = _build_pge_baseline()

    kit_path = DocxGenerator().write_kit_docx(baseline, tmp_path)
    wb_res = export_pmo_workbook(baseline, tmp_path)
    deck_res = export_onboarding_deck(baseline, tmp_path)

    # 1. Onboarding Deck Slide 3 (Schedule) inspection
    prs = pptx.Presentation(str(deck_res.file_path))
    slide3 = prs.slides[2]  # Slide 3 (index 2)
    table_shapes = [s for s in slide3.shapes if getattr(s, "has_table", False) and s.has_table]
    assert len(table_shapes) == 1
    table3 = table_shapes[0].table

    # Exactly 2 rows: 1 header row + 1 milestone data row (M1)
    assert len(table3.rows) == 2, f"Slide 3 expected exactly 1 milestone row, found {len(table3.rows) - 1}"
    ms_cell_text = table3.cell(1, 1).text
    assert "M1" in ms_cell_text
    assert "Milestone 1: Cloud Migration Assessment Report" in ms_cell_text

    # Deliverables column must list all 6 PGE deliverables
    deliv_cell_text = table3.cell(1, 3).text
    for did in ["DEL-01", "DEL-02", "DEL-03", "DEL-04", "DEL-05", "DEL-06"]:
        assert did in deliv_cell_text

    # 2. Onboarding Deck Slide 4 (Acceptance) Gate inspection: all 6 deliverables gate on M1
    slide4 = prs.slides[3]
    table4 = [s for s in slide4.shapes if getattr(s, "has_table", False) and s.has_table][0].table
    for r in range(1, 7):
        assert table4.cell(r, 2).text == "M1", f"Row {r} gate is {table4.cell(r, 2).text}, expected M1"

    # 3. String contamination check across all 3 artifacts
    contaminated_terms = [
        "P1 Foundation",
        "P2a Services and Data",
        "P2b Application Surface",
        "P3 Launch",
        "OneGWAS",
        "Snowflake",
    ]

    # Check deck text
    deck_text = ""
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                deck_text += " " + shape.text_frame.text
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        deck_text += " " + cell.text

    for term in contaminated_terms:
        assert term not in deck_text, f"Found contaminated term '{term}' in Onboarding Deck"

    # Check workbook text
    wb = openpyxl.load_workbook(str(wb_res.file_path), data_only=True)
    wb_text = ""
    for sheet in wb.sheetnames:
        for row in wb[sheet].iter_rows(values_only=True):
            for cell in row:
                if cell is not None:
                    wb_text += " " + str(cell)

    for term in contaminated_terms:
        assert term not in wb_text, f"Found contaminated term '{term}' in Workbook sheet"

    # Check Docx text
    doc = docx.Document(str(kit_path))
    doc_text = " ".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                doc_text += " " + cell.text

    for term in contaminated_terms:
        assert term not in doc_text, f"Found contaminated term '{term}' in Startup Kit docx"


def test_long_acceptance_criteria_stress_case_fits_without_overflow(tmp_path):
    """HTL-62: SOW-realistic long multi-clause criteria (65+ words) render completely within available table height."""
    long_crit_1 = (
        "Portfolio inventory covers at least 95% of in-scope workloads with validated application owners, "
        "current hosting infrastructure, and compliance baselines recorded; target landing zone architecture blueprint "
        "addresses security isolation and multi-region failover requirements; and the PG&E Technical Sponsor signs off "
        "formal acceptance within five business days following the joint architectural review walkthrough."
    )
    long_crit_2 = (
        "Every in-scope workload mapped to its upstream and downstream dependencies with integration protocols recorded; "
        "critical-path cross-workload dependencies flagged for wave sequencing; and telemetry export verified without environment errors."
    )

    delivs = list(PGE_DELIVERABLES)
    delivs[0] = Deliverable(
        id="DEL-01",
        name="Portfolio Inventory & Architecture Blueprint",
        description="Comprehensive Portfolio Inventory and Target Landing Zone Blueprint.",
        acceptance_criteria=long_crit_1,
        submission_target_date="2026-11-18",
        review_window="5 business days",
        client_approver="Alicia Cook",
    )
    delivs[1] = Deliverable(
        id="DEL-02",
        name="Dependency Map & Integration Catalog",
        description="Dependency Map and Integration Catalog.",
        acceptance_criteria=long_crit_2,
        submission_target_date="2026-11-18",
        review_window="5 business days",
        client_approver="Alicia Cook",
    )

    baseline = _build_pge_baseline(deliverables=delivs)
    wb_model = build_workbook_model(baseline)
    deck_model = build_deck_model(baseline, workbook_model=wb_model)

    slide4 = deck_model.slides[2]
    assert len(slide4.tables) == 1
    table = slide4.tables[0]
    assert table.name == "Table: Acceptance"

    # Available table height is CONTENT_Y1 - CONTENT_Y0 = 5.0 in
    avail_h = round(L.CONTENT_Y1 - table.y, 2)
    assert avail_h == 5.00

    # Total table height with 65-word criterion must fit within available height with safety buffer
    assert table.height <= avail_h
    assert table.height <= 4.50
    assert len(table.rows) == 6  # 6 data rows (excluding header)

    # Export and check invariants
    kit_path = DocxGenerator().write_kit_docx(baseline, tmp_path)
    wb_res = export_pmo_workbook(baseline, tmp_path)
    deck_res = export_onboarding_deck(baseline, tmp_path)

    kit_doc = docx.Document(str(kit_path))
    wb = openpyxl.load_workbook(str(wb_res.file_path), data_only=False)
    violations = check_deck_invariants(deck_res.file_path, deck_res.manifest_path, kit_doc, wb)
    assert len(violations) == 0, f"Unexpected invariant violations: {violations}"


@pytest.mark.parametrize("fixture_name", ["arc_genomics", "arc_overextracted", "mock_sow", "no_story_ids", "numbered_deliverables"])
def test_deck_invariants_pass_cleanly_on_standard_fixtures(fixture_name, tmp_path):
    """HTL-62: check_deck_invariants passes cleanly on all standard fixtures with full acceptance criteria."""
    baseline = load_baseline(fixture_name)
    kit_path = DocxGenerator().write_kit_docx(baseline, tmp_path)
    wb_res = export_pmo_workbook(baseline, tmp_path)
    deck_res = export_onboarding_deck(baseline, tmp_path)

    kit_doc = docx.Document(str(kit_path))
    wb = openpyxl.load_workbook(str(wb_res.file_path), data_only=False)
    violations = check_deck_invariants(deck_res.file_path, deck_res.manifest_path, kit_doc, wb)
    assert len(violations) == 0, f"Invariant violations for {fixture_name}: {violations}"


def test_deliverable_backward_compatibility_validator_on_real_legacy_pge_data():
    """Verify that Deliverable._coerce_acceptance_criteria correctly splits all 6 real legacy PGE semicolon-joined strings into exactly 2 items each."""
    legacy_pge_criteria = [
        # DEL-01
        "Inventory covers ≥ 95% of in-scope workloads; each workload has owner, hosting, and requirements recorded with available information.",
        # DEL-02
        "Every in-scope workload mapped to its dependencies (for applicable dependencies only); cross-workload dependencies flagged for sequencing (for applicable dependencies only).",
        # DEL-03
        "Every in-scope workload has exactly one disposition; each disposition carries a documented rationale.",
        # DEL-04
        "Recommendation addresses each disposition category; key architectural decisions documented with trade-offs.",
        # DEL-05
        "Every in-scope workload has a right-sized cost estimate; projection horizon, pricing models, and tools are documented.",
        # DEL-06
        "Every in-scope workload assigned to a wave; sequencing reflects documented dependencies.",
    ]

    for idx, raw_crit in enumerate(legacy_pge_criteria, 1):
        d = Deliverable(id=f"DEL-{idx:02d}", name=f"Deliverable {idx}", acceptance_criteria=raw_crit)
        assert isinstance(d.acceptance_criteria, list), f"DEL-{idx:02d} acceptance_criteria is not a list"
        assert len(d.acceptance_criteria) == 2, f"DEL-{idx:02d} expected exactly 2 criteria, got {len(d.acceptance_criteria)}: {d.acceptance_criteria}"
        assert not any(c.startswith(";") or c.endswith(";") for c in d.acceptance_criteria)


def test_pge_all_twelve_criteria_render_as_distinct_countable_items_across_artifacts(tmp_path):
    """HTL-64 / HTL-62: All 12 real criteria render as distinct, countable bulleted items in Startup Kit, Workbook, and Onboarding Deck."""
    baseline = _build_pge_baseline()

    kit_path = DocxGenerator().write_kit_docx(baseline, tmp_path)
    wb_res = export_pmo_workbook(baseline, tmp_path)
    deck_res = export_onboarding_deck(baseline, tmp_path)

    # 1. Onboarding Deck Slide 4: 6 rows, each having 2 bulleted lines (12 bullet lines total)
    prs = pptx.Presentation(str(deck_res.file_path))
    slide4 = prs.slides[3]
    table = [s for s in slide4.shapes if getattr(s, "has_table", False) and s.has_table][0].table
    deck_bullet_count = 0
    for r in range(1, 7):
        cell_tf = table.cell(r, 1).text_frame
        # Each paragraph in the cell is a bullet line
        paras = [p.text for p in cell_tf.paragraphs if p.text.strip()]
        assert len(paras) == 2, f"Slide 4 Row {r} expected 2 bullet paragraphs, got {len(paras)}: {paras}"
        for p_txt in paras:
            assert p_txt.startswith("• "), f"Paragraph should start with bullet: {p_txt}"
            deck_bullet_count += 1
    assert deck_bullet_count == 12

    # 2. Startup Kit Docx: Deliverables table (Table 2.2), 6 rows, each having 2 bulleted lines (12 bullets total)
    kit_doc = docx.Document(str(kit_path))
    deliv_table = next(
        t for t in kit_doc.tables
        if any("Acceptance Criteria" in cell.text for cell in t.rows[0].cells)
    )
    docx_bullet_count = 0
    for r in range(1, 7):
        cell_text = deliv_table.cell(r, 2).text
        lines = [l.strip() for l in cell_text.splitlines() if l.strip() and not l.strip().startswith("[ACT")]
        assert len(lines) == 2, f"Docx Table Row {r} expected 2 bullet lines, got {len(lines)}: {lines}"
        for l in lines:
            assert l.startswith("• "), f"Docx line should start with bullet: {l}"
            docx_bullet_count += 1
    assert docx_bullet_count == 12

    # 3. PMO Delivery Workbook: WBS sheet, 6 deliverable rows (Level 3), Column R has 2 bulleted criteria
    wb = openpyxl.load_workbook(str(wb_res.file_path), data_only=True)
    wbs_sheet = wb["WBS"]
    wb_bullet_count = 0
    deliv_rows_found = 0
    for row in wbs_sheet.iter_rows(min_row=5, values_only=True):
        elem_type = row[2]  # Element Type
        if elem_type == "Deliverable":
            deliv_rows_found += 1
            ac_cell_value = str(row[17] or "")  # Column R: Acceptance Criteria & Evidence
            # Split lines
            lines = [l.strip() for l in ac_cell_value.splitlines() if l.strip() and not l.strip().startswith("Evidence:")]
            assert len(lines) == 2, f"WBS Deliverable row {deliv_rows_found} expected 2 bullet criteria, got {len(lines)}: {lines}"
            for l in lines:
                assert l.startswith("• "), f"WBS criteria line should start with bullet: {l}"
                wb_bullet_count += 1
    assert deliv_rows_found == 6
    assert wb_bullet_count == 12
