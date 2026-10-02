"""Unit tests for Word document generation and G-01 checklist rendering."""

import pytest
from pathlib import Path
import docx
from src.core.models import StartupKitBaseline
from src.generators.docx_generator import DocxGenerator
from src.generators.formatting import sanitize_filename
from src.generators.checklist import G01ChecklistRenderer


def test_sanitize_filename():
    assert sanitize_filename("Pfizer Cloud Migration") == "Pfizer_Cloud_Migration"
    assert sanitize_filename("Project: Alpha / Beta (v1)") == "Project_Alpha_Beta_v1"
    assert sanitize_filename("") == "Project"


def test_b6_cell_text_formatting_preserves_parentheses_and_text():
    """Verify B6 fix preserves balanced parentheses, brackets, and bare words like undefined (spec v4 B6)."""
    from src.generators.docx_generator import format_cell_with_action
    
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


def test_docx_generator_output(sample_baseline, tmp_path):
    output_dir = tmp_path / "output"
    generator = DocxGenerator()
    generated_file = generator.write_docx(sample_baseline, output_dir)

    assert generated_file.exists()
    assert generated_file.name == "Pfizer_Cloud_Migration_Startup_Kit.docx"
    assert generated_file.suffix == ".docx"

    # Verify second document (Startup_Readiness_Checklist) is created
    checklist_file = output_dir / "Pfizer_Cloud_Migration_Startup_Readiness_Checklist.docx"
    assert checklist_file.exists()
    assert checklist_file.suffix == ".docx"

    # Open and inspect the generated Word document (Startup Kit)
    doc = docx.Document(str(generated_file))

    # Verify headings and text in Startup Kit
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "TOPTAL PMO STARTUP KIT" in full_text
    assert "Pfizer Cloud Migration" in full_text
    assert "Startup Kit Readiness Score:" in full_text

    # Verify Layer 1 is the first section and G-01 Executive Readiness Gateway is moved to second document
    score_idx = full_text.find("Startup Kit Readiness Score:")
    layer1_idx = full_text.find("Layer 1: Executive Startup Pack")
    layer2_idx = full_text.find("Layer 2: Delivery Control Pack")
    layer3_idx = full_text.find("Layer 3: Assurance Pack")
    g01_idx = full_text.find("Executive Readiness Gateway: Startup Readiness Checklist (G-01)")

    assert score_idx != -1, "Startup Kit Readiness Score heading must be present"
    assert layer1_idx != -1, "Layer 1 must be present"
    assert layer2_idx != -1, "Layer 2 must be present"
    assert layer3_idx != -1, "Layer 3 must be present"
    assert g01_idx == -1, "G-01 Executive Readiness Gateway must be moved to the second document"
    assert score_idx < layer1_idx < layer2_idx < layer3_idx, "Document sections must follow: Readiness Score -> Layer 1 -> Layer 2 -> Layer 3"

    # Open and inspect the second Word document (Startup Readiness Checklist)
    cl_doc = docx.Document(str(checklist_file))
    cl_text = "\n".join(p.text for p in cl_doc.paragraphs)
    assert "Executive Readiness Gateway: Startup Readiness Checklist (G-01) & Gate Decision" in cl_text
    assert "Startup Readiness Checklist Table (G-01)" in cl_text
    assert "Commercial and Margin Guardrails" in cl_text

    cl_table_content = "\n".join(" | ".join(c.text.strip() for c in r.cells) for tbl in cl_doc.tables for r in tbl.rows)
    assert "G01-01" in cl_table_content
    assert "G01-07" in cl_table_content
    assert "Contract Type Implications" in cl_table_content
    assert "Work-at-Risk Rules (PMO Lead owned)" in cl_table_content
    assert "Change Control Triggers & Change Order Route" in cl_table_content

    # Verify all Section 4 layer headings in Startup Kit
    assert "Layer 1: Executive Startup Pack" in full_text
    assert "Project Startup Charter" in full_text
    assert "SOW Interpretation Summary" in full_text
    assert "Milestone Delivery Plan" in full_text
    assert "Layer 2: Delivery Control Pack" in full_text
    assert "Scope Decomposition / Backlog Seed" in full_text
    assert "Deliverables and Acceptance Matrix" in full_text
    assert "Dependency and Assumption Log" in full_text
    assert "RAID Log" in full_text
    assert "Communications and Reporting Plan" in full_text
    assert "Layer 3: Assurance Pack" in full_text
    assert "Stakeholder and Responsibility Model" in full_text
    assert "RACI / Decision Rights Matrix" in full_text
    assert "Commercial and Margin Guardrails" not in full_text
    assert "Talent Onboarding Record" in full_text

    # Verify tables
    assert len(doc.tables) >= 4
    assert len(cl_doc.tables) >= 1

    table_texts = []
    for tbl in doc.tables:
        for row in tbl.rows:
            row_str = " | ".join(c.text.strip() for c in row.cells)
            table_texts.append(row_str)

    all_table_content = "\n".join(table_texts)
    assert "DEL-01" in all_table_content
    assert "Cloud Migration Architecture Design" in all_table_content
    assert "ACT-" in all_table_content  # DEL-02 in-table action item annotation
    assert "M1" in all_table_content
    assert "2026-10-15" in all_table_content


def test_checklist_renderer(sample_baseline, tmp_path):
    doc = docx.Document()
    renderer = G01ChecklistRenderer()
    renderer.render(doc, sample_baseline)

    assert len(doc.tables) >= 1
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Startup Readiness Checklist" in full_text

    # Verify that no page break is inserted between Gate Decision box and Checklist table
    has_page_break = any('<w:br w:type="page"' in p._p.xml for p in doc.paragraphs)
    assert not has_page_break, "No page break should be inserted between G-01 Readiness Gate Decision box and the Checklist table"


def test_checklist_artifact_coverage_and_exceptions(sample_source_ref):
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

    aggregator = BaselineAggregator()
    charter = CharterExtraction(
        project_name="Compliance Audit System",
        governance_tier="Partnered",
        contract_type="Fixed Bid",
        source_reference=sample_source_ref
    )

    # Deliverable with missing criteria to trigger Review Required
    deliverables = DeliverablesExtraction(deliverables=[
        Deliverable(
            id="DEL-01",
            description="Audit Reporting Engine",
            source_reference=sample_source_ref,
            acceptance_criteria=None  # Triggers unconfirmed criteria
        )
    ])

    # Milestone with missing date to trigger Confirmation Required
    milestones = MilestonesExtraction(milestones=[
        Milestone(
            id="M1",
            description="Production Readiness",
            external_date=None,  # Triggers unconfirmed date
            source_reference=sample_source_ref
        )
    ])

    raid = RAIDExtraction(items=[
        RiskAssumption(
            type="Risk",
            description="Regulatory review timeline slip",
            source_reference=sample_source_ref
        )
    ])

    baseline = aggregator.aggregate(
        charter=charter,
        deliverables_ext=deliverables,
        milestones_ext=milestones,
        raid_ext=raid
    )

    # Verify checklist covers all Section 4 artifacts
    assert len(baseline.readiness_checklist) >= 13

    # Check that each item has owner, status, evidence, reviewer, approver
    for item in baseline.readiness_checklist:
        assert item.item_id.startswith("G01-")
        assert item.gate_criterion != ""
        assert item.related_section4_artifact != ""
        assert item.owner != ""
        assert item.reviewer != ""
        assert item.approver != ""
        assert item.status in [
            "Not Started",
            "In Progress",
            "Review Required",
            "Confirmation Required",
            "Complete",
            "Exception Required",
            "Approved",
            "Approved with Exception",
            "Rework Required"
        ]

    # Verify incomplete items have Review/Confirmation/Exception flags
    deliv_check = next(c for c in baseline.readiness_checklist if "Deliverables" in c.related_section4_artifact)
    assert deliv_check.status == "Review Required"
    assert deliv_check.exception_required is True

    ms_check = next(c for c in baseline.readiness_checklist if "Milestone" in c.related_section4_artifact)
    assert ms_check.status == "Confirmation Required"
    assert ms_check.exception_required is True


def test_sow_interpretation_platform_environment_commitments_fallback(sample_source_ref, tmp_path):
    """Verify that when platform commitments are unassigned or empty, [UNDEFINED] is used as fallback."""
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

    aggregator = BaselineAggregator()
    charter = CharterExtraction(
        project_name="Platform Test Project",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        source_reference=sample_source_ref
    )

    baseline = aggregator.aggregate(
        charter=charter,
        deliverables_ext=DeliverablesExtraction(deliverables=[Deliverable(id="D1", description="Test Deliv", source_reference=sample_source_ref)]),
        milestones_ext=MilestonesExtraction(milestones=[Milestone(id="M1", description="Test MS", source_reference=sample_source_ref)]),
        raid_ext=RAIDExtraction(items=[RiskAssumption(type="Risk", description="Test Risk", source_reference=sample_source_ref)])
    )

    # Baseline SOW interpretation should have ["[UNDEFINED]"]
    assert baseline.sow_interpretation is not None
    assert baseline.sow_interpretation.platform_environment_commitments == ["[UNDEFINED]"]

    # When rendered to docx, table cell should contain authoritative [ACT-XX] tag
    generator = DocxGenerator()
    out_file = generator.write_docx(baseline, tmp_path / "output")
    doc = docx.Document(str(out_file))

    table_cells = []
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                table_cells.append(cell.text.strip())

    assert any("[ACT-" in cell for cell in table_cells)
    assert "Cloud Infrastructure: AWS / Azure / GCP" not in "\n".join(table_cells)


def test_checklist_table_rendered_as_last_section(sample_baseline, tmp_path):
    """Verify that the Executive Readiness Gateway callout box and G-01 Checklist table are rendered in the Startup Readiness Checklist document."""
    # Ensure baseline has action required items
    sample_baseline.open_questions = [
        "Confirm deliverable DEL-01 named owner and acceptance test criteria.",
        "Verify third-party API dependencies.",
    ]
    generator = DocxGenerator()
    out_file = generator.write_docx(sample_baseline, tmp_path / "Action_Order_Test.docx")
    doc = docx.Document(str(out_file))

    # Verify main Startup Kit document does not contain the Checklist gateway heading (moved to second document)
    main_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Executive Readiness Gateway: Startup Readiness Checklist (G-01)" not in main_text

    # Verify second document contains the Gateway and Checklist
    cl_file = tmp_path / "Action_Order_Test_Startup_Readiness_Checklist.docx"
    assert cl_file.exists()
    cl_doc = docx.Document(str(cl_file))

    body_elements = []
    for child in cl_doc.element.body:
        if child.tag.endswith("p"):
            p = docx.text.paragraph.Paragraph(child, cl_doc)
            if p.text.strip():
                body_elements.append(p.text.strip())
        elif child.tag.endswith("tbl"):
            tbl = docx.table.Table(child, cl_doc)
            tbl_text = " ".join(c.text.strip() for row in tbl.rows for c in row.cells)
            if tbl_text:
                body_elements.append(tbl_text)

    full_body_text = "\n---\n".join(body_elements)
    action_heading_idx = full_body_text.find("Action Required: Unresolved Validation Points / Clarifications")
    gateway_heading_idx = full_body_text.find("Executive Readiness Gateway: Startup Readiness Checklist (G-01) & Gate Decision")
    checklist_heading_idx = full_body_text.find("Startup Readiness Checklist Table (G-01)")

    assert action_heading_idx == -1, "Action Required heading must not be present in checklist document"
    assert gateway_heading_idx != -1, "Executive Readiness Gateway heading must be present in checklist document"
    assert checklist_heading_idx != -1, "Startup Readiness Checklist Table heading must be present in checklist document"
    assert gateway_heading_idx < checklist_heading_idx, (
        "Document flow order must strictly be: Executive Readiness Gateway -> Startup Readiness Checklist"
    )

    # Find the tables in checklist doc
    table_headers = []
    for tbl in cl_doc.tables:
        header_row = [c.text.strip() for c in tbl.rows[0].cells]
        table_headers.append(header_row)

    checklist_tbl_idx = -1
    cg_tbl_idx = -1
    questions_tbl_idx = -1
    ambiguities_tbl_idx = -1
    for idx, headers in enumerate(table_headers):
        if "Gate ID" in headers and "Gate Criterion" in headers:
            checklist_tbl_idx = idx
        if "Commercial Guardrail Area" in headers:
            cg_tbl_idx = idx
        if "Question ID" in headers:
            questions_tbl_idx = idx
        if "Anomaly ID" in headers:
            ambiguities_tbl_idx = idx

    assert checklist_tbl_idx != -1, "G-01 Checklist Table must be present in checklist document"
    assert cg_tbl_idx != -1, "Commercial and Margin Guardrails Table must be present in checklist document"
    assert questions_tbl_idx != -1, "Actionable Questions Table must be present in checklist document"
    assert ambiguities_tbl_idx != -1, "Contract Ambiguities Table must be present in checklist document"
    assert checklist_tbl_idx < cg_tbl_idx < questions_tbl_idx < ambiguities_tbl_idx, (
        f"Document table order must strictly be G-01 Checklist (idx={checklist_tbl_idx}) -> Commercial Guardrails (idx={cg_tbl_idx}) -> Actionable Questions (idx={questions_tbl_idx}) -> Contract Ambiguities (idx={ambiguities_tbl_idx})"
    )


def test_action_required_table_columns_and_formatting(sample_baseline, tmp_path):
    """Verify that standalone rendering of Action Required table produces all 8 specified column headers and contents."""
    from src.generators.checklist import G01ChecklistRenderer
    sample_baseline.open_questions = ["Clarify milestone delivery schedule."]
    doc = docx.Document()
    renderer = G01ChecklistRenderer()
    renderer.render_action_required_table(doc, sample_baseline)

    action_tbl = None
    for tbl in doc.tables:
        if len(tbl.columns) == 8 and tbl.rows[0].cells[0].text.strip() == "Action ID":
            action_tbl = tbl
            break

    assert action_tbl is not None, "Action Required Table with 8 columns must be found when rendered standalone"
    headers = [c.text.strip() for c in action_tbl.rows[0].cells]
    expected_headers = [
        "Action ID",
        "Type",
        "Gate ID",
        "Related Artifact",
        "Validation Finding & Required Action",
        "Owner",
        "Deadline",
        "Score Impact",
    ]
    assert headers == expected_headers

    # Check first row content
    first_row = [c.text.strip() for c in action_tbl.rows[1].cells]
    assert first_row[0] == "ACT-01"
    assert first_row[1] in ("Open Exception", "Open Clarification")
    assert first_row[2].startswith("G01-")
    assert first_row[5] != ""
    assert first_row[6] == "Prior to Mobilize Kickoff"
    assert first_row[7].startswith("+") and first_row[7].endswith("%")


def test_no_duplicate_trailing_action_callout(sample_baseline, tmp_path):
    """Verify that Action Required callout does not appear in generated report."""
    sample_baseline.open_questions = ["Verify API security protocols."]
    generator = DocxGenerator()
    out_file = generator.write_docx(sample_baseline, tmp_path / "No_Dup_Callout_Test.docx")
    doc = docx.Document(str(out_file))

    all_texts = [p.text for p in doc.paragraphs]
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                all_texts.append(cell.text)
    full_text = "\n".join(all_texts)

    # Count occurrences of the Action Required callout title
    callout_count = full_text.count("Action Required: Unresolved Validation Points / Clarifications")
    assert callout_count == 0, (
        f"Action Required heading should be removed from report, found {callout_count}"
    )


def test_report_text_sanitization(sample_baseline, tmp_path):
    """Verify that report text sanitizes references to SOW, contracts, or source documents and simplifies descriptions."""
    from src.config import sanitize_report_text
    raw = "Deliverable per the SOW as stated in SOW Section 3.2 is required."
    clean = sanitize_report_text(raw)
    assert "SOW" not in clean
    assert "Section 3.2" not in clean

    # Verify document generation with raw strings does not leak SOW citations in formatted cells
    sample_baseline.deliverables[0].description = "Cloud Migration Architecture per the SOW Section 4"
    generator = DocxGenerator()
    out_file = generator.write_docx(sample_baseline, tmp_path / "Sanitization_Test.docx")
    doc = docx.Document(str(out_file))

    deliv_tbl = next(t for t in doc.tables if any("deliverable name" in c.text.lower() for c in t.rows[0].cells))
    cell_text = deliv_tbl.rows[1].cells[1].text
    assert "per the SOW" not in cell_text
    assert "Section 4" not in cell_text


def test_write_documents_and_write_checklist_docx(sample_baseline, tmp_path):
    """Verify write_documents and write_checklist_docx API methods."""
    generator = DocxGenerator()

    # Test write_checklist_docx directly with directory target
    cl_dir_path = generator.write_checklist_docx(sample_baseline, tmp_path / "cl_dir")
    assert cl_dir_path.exists()
    assert cl_dir_path.name == "Pfizer_Cloud_Migration_Startup_Readiness_Checklist.docx"

    # Test write_checklist_docx with explicit filename
    cl_custom_file = tmp_path / "custom_checklist.docx"
    cl_res = generator.write_checklist_docx(sample_baseline, cl_custom_file)
    assert cl_res == cl_custom_file
    assert cl_custom_file.exists()

    # Test write_documents with directory
    kit_p, cl_p = generator.write_documents(sample_baseline, tmp_path / "docs_dir")
    assert kit_p.exists() and kit_p.name == "Pfizer_Cloud_Migration_Startup_Kit.docx"
    assert cl_p.exists() and cl_p.name == "Pfizer_Cloud_Migration_Startup_Readiness_Checklist.docx"

    # Test write_documents with explicit file path
    target_kit = tmp_path / "custom_dir" / "ProjectX_Startup_Kit.docx"
    kit_p2, cl_p2 = generator.write_documents(sample_baseline, target_kit)
    assert kit_p2 == target_kit
    assert kit_p2.exists()
    assert cl_p2.exists()
    assert cl_p2.name == "ProjectX_Startup_Readiness_Checklist.docx"


def test_commercial_and_margin_guardrails_table_rendering_and_reingest(sample_baseline, tmp_path):
    """Verify Commercial and Margin Guardrails table contents in checklist document and reingestion."""
    from src.extractors.startup_kit_docx_parser import StartupKitDocxParser
    from src.core.models import CommercialGuardrail

    sample_baseline.commercial_guardrails = CommercialGuardrail(
        contract_type_implication="Managed delivery under Time and Materials governance rules.",
        billing_consumption_assumption="Weekly timesheet approval and hourly/daily burn rate tracking against budget cap.",
        staffing_assumption="Dedicated 3-person engineering team.",
        commercial_exposure_note="Client dependency delays must be logged immediately.",
        approved_work_rule="All milestones must map directly to contracted deliverables.",
        non_approved_work_rule="No out-of-scope work without approved Change Order.",
        work_at_risk_rule="Work-at-risk requires PMO Lead written sign-off.",
        change_control_trigger="Material scope modifications or milestone shifts > 5 days.",
        change_order_route="PMO Lead leads -> DM aligns client -> Client approves -> Contracting issues change order",
        budget_baseline="$250,000 USD Budget Cap",
        variance_indicator="Green (<5% variance)",
        margin_risk_indicator="Low",
        escalation_threshold="Budget variance > 10% or milestone delay > 3 days"
    )

    generator = DocxGenerator()
    kit_file, cl_file = generator.write_documents(sample_baseline, tmp_path / "CG_Test_Startup_Kit.docx")

    assert cl_file.exists()
    cl_doc = docx.Document(str(cl_file))

    # Verify table headers and rows
    cg_tbl = None
    for tbl in cl_doc.tables:
        headers = [c.text.strip() for c in tbl.rows[0].cells]
        if "Commercial Guardrail Area" in headers:
            cg_tbl = tbl
            break

    assert cg_tbl is not None, "Commercial and Margin Guardrails table must be present in checklist doc"
    assert len(cg_tbl.rows) >= 9, f"Expected at least 9 rows in commercial guardrails table, got {len(cg_tbl.rows)}"

    rows_text = [" | ".join(c.text.strip() for c in row.cells) for row in cg_tbl.rows]
    all_cg_text = "\n".join(rows_text)

    # Verify all 8 core requirements are present in the table
    assert "Contract Type Implications" in all_cg_text
    assert "Billing or Consumption Assumptions" in all_cg_text
    assert "Staffing Assumptions & Commercial Exposure" in all_cg_text
    assert "Approved & Non-Approved Work Rules" in all_cg_text
    assert "Work-at-Risk Rules (PMO Lead owned)" in all_cg_text
    assert "PMO Lead (Exclusive Sign-off Authority)" in all_cg_text
    assert "Change Control Triggers & Change Order Route" in all_cg_text
    assert "PMO Lead leads → DM aligns client → Client approves → Contracting issues change order" in all_cg_text
    assert "Budget vs. Actuals & Variance Baseline" in all_cg_text
    assert "$250,000 USD Budget Cap" in all_cg_text
    assert "Margin Risk Indicators" in all_cg_text
    assert "Internal Escalation Thresholds" in all_cg_text

    # Verify reingestion round-trip parses commercial guardrails from companion document
    parser = StartupKitDocxParser()
    reparsed = parser.parse_startup_kit_docx(kit_file)
    assert reparsed.commercial_guardrails is not None
    assert "Time and Materials" in reparsed.commercial_guardrails.contract_type_implication
    assert "Weekly timesheet" in reparsed.commercial_guardrails.billing_consumption_assumption
    assert "PMO Lead" in reparsed.commercial_guardrails.work_at_risk_rule
    assert "PMO Lead leads" in reparsed.commercial_guardrails.change_order_route


def test_actionable_questions_and_contract_ambiguities_tables_rendering_and_reingest(sample_baseline, tmp_path):
    """Verify Actionable Questions and Contract Ambiguities tables in checklist document and round-trip reingestion."""
    from src.extractors.startup_kit_docx_parser import StartupKitDocxParser
    from src.core.models import ContractAmbiguityItem

    sample_baseline.open_questions = [
        "What is the target sign-off approver for DEL-01? [CONFIRMATION REQUIRED]",
        "Who is the primary client escalation authority for security incidents? [CONFIRMATION REQUIRED]",
    ]
    sample_baseline.contract_ambiguities = [
        ContractAmbiguityItem(
            anomaly_id="AMB-01",
            category="Date Conflict",
            conflicting_clauses="Proposal schedule specifies 2026-10-15 while SOW states 2026-10-31.",
            risk_impact="2-week delivery schedule variance.",
            recommended_clarification="Confirm 2026-10-31 as binding delivery milestone date.",
            status="Open"
        ),
        ContractAmbiguityItem(
            anomaly_id="AMB-02",
            category="Ambiguous Acceptance",
            conflicting_clauses="Section 5 states subjective acceptance without quantifiable metrics.",
            risk_impact="Client sign-off disputes during UAT.",
            recommended_clarification="Agree on automated test pass threshold as acceptance gate.",
            status="Open"
        )
    ]

    generator = DocxGenerator()
    kit_file, cl_file = generator.write_documents(sample_baseline, tmp_path / "Tables_Test_Startup_Kit.docx")

    assert cl_file.exists()
    cl_doc = docx.Document(str(cl_file))

    # Verify Actionable Questions table
    q_tbl = None
    amb_tbl = None
    for tbl in cl_doc.tables:
        headers = [c.text.strip() for c in tbl.rows[0].cells]
        if "Question ID" in headers:
            q_tbl = tbl
        if "Anomaly ID" in headers:
            amb_tbl = tbl

    assert q_tbl is not None, "Actionable Questions table must be present in checklist document"
    assert amb_tbl is not None, "Contract Ambiguities table must be present in checklist document"

    # Verify Actionable Questions table rows & contents
    assert len(q_tbl.rows) == 3  # Header + 2 questions
    q_rows_text = [" | ".join(c.text.strip() for c in r.cells) for r in q_tbl.rows]
    all_q_text = "\n".join(q_rows_text)
    assert "Q-01" in all_q_text
    assert "target sign-off approver" in all_q_text
    assert "Q-02" in all_q_text
    assert "security incidents" in all_q_text

    # Verify Contract Ambiguities table rows & contents
    assert len(amb_tbl.rows) == 3  # Header + 2 ambiguities
    amb_rows_text = [" | ".join(c.text.strip() for c in r.cells) for r in amb_tbl.rows]
    all_amb_text = "\n".join(amb_rows_text)
    assert "AMB-01" in all_amb_text
    assert "Date Conflict" in all_amb_text
    assert "2026-10-15" in all_amb_text
    assert "AMB-02" in all_amb_text
    assert "Ambiguous Acceptance" in all_amb_text

    # Verify reingestion round-trip parses open questions and contract ambiguities
    parser = StartupKitDocxParser()
    reparsed = parser.parse_startup_kit_docx(kit_file)

    assert len(reparsed.open_questions) >= 2
    assert any("target sign-off approver" in q for q in reparsed.open_questions)

    assert len(reparsed.contract_ambiguities) == 2
    assert reparsed.contract_ambiguities[0].anomaly_id == "AMB-01"
    assert reparsed.contract_ambiguities[0].category == "Date Conflict"
    assert reparsed.contract_ambiguities[1].anomaly_id == "AMB-02"
    assert reparsed.contract_ambiguities[1].category == "Ambiguous Acceptance"
