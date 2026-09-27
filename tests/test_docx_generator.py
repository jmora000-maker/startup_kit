"""Unit tests for Word document generation and G-01 checklist rendering."""

import pytest
from pathlib import Path
import docx
from src.core.models import StartupKitBaseline
from src.generators.docx_generator import DocxGenerator, sanitize_filename
from src.generators.checklist import G01ChecklistRenderer


def test_sanitize_filename():
    assert sanitize_filename("Pfizer Cloud Migration") == "Pfizer_Cloud_Migration"
    assert sanitize_filename("Project: Alpha / Beta (v1)") == "Project_Alpha__Beta_v1"
    assert sanitize_filename("") == "Project"


def test_docx_generator_output(sample_baseline, tmp_path):
    output_dir = tmp_path / "output"
    generator = DocxGenerator()
    generated_file = generator.write_docx(sample_baseline, output_dir)

    assert generated_file.exists()
    assert generated_file.name == "Pfizer_Cloud_Migration_Startup_Kit.docx"
    assert generated_file.suffix == ".docx"

    # Open and inspect the generated Word document
    doc = docx.Document(str(generated_file))

    # Verify headings and text
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "TOPTAL PMO STARTUP KIT" in full_text
    assert "Pfizer Cloud Migration" in full_text
    assert "Startup Kit Readiness Score:" in full_text

    # Verify Layer 1 is the first section and G-01 Executive Readiness Gateway comes AFTER Layer 3
    score_idx = full_text.find("Startup Kit Readiness Score:")
    layer1_idx = full_text.find("Layer 1: Executive Startup Pack")
    layer2_idx = full_text.find("Layer 2: Delivery Control Pack")
    layer3_idx = full_text.find("Layer 3: Assurance Pack")
    g01_idx = full_text.find("Executive Readiness Gateway: Startup Readiness Checklist (G-01)")

    assert score_idx != -1, "Startup Kit Readiness Score heading must be present"
    assert layer1_idx != -1, "Layer 1 must be present"
    assert layer2_idx != -1, "Layer 2 must be present"
    assert layer3_idx != -1, "Layer 3 must be present"
    assert g01_idx != -1, "G-01 Executive Readiness Gateway must be present"
    assert score_idx < layer1_idx < layer2_idx < layer3_idx < g01_idx, "Document sections must follow: Readiness Score -> Layer 1 -> Layer 2 -> Layer 3 -> G-01 Gateway"

    # Verify all Section 4 layer headings
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
    assert "Commercial and Margin Guardrails" in full_text
    assert "Talent Onboarding Record" in full_text

    # Verify tables
    assert len(doc.tables) >= 5

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
    assert "G01-01" in all_table_content  # Checklist item
    assert "G01-07" in all_table_content  # Checklist item


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
    """Verify that after Layer 3 Artifacts, the Executive Readiness Gateway callout box and G-01 Checklist table are rendered as the final section."""
    # Ensure baseline has action required items
    sample_baseline.open_questions = [
        "Confirm deliverable DEL-01 named owner and acceptance test criteria.",
        "Verify third-party API dependencies.",
    ]
    generator = DocxGenerator()
    out_file = generator.write_docx(sample_baseline, tmp_path / "Action_Order_Test.docx")
    doc = docx.Document(str(out_file))

    # Verify order of body elements (paragraphs and tables in document flow)
    body_elements = []
    for child in doc.element.body:
        if child.tag.endswith("p"):
            p = docx.text.paragraph.Paragraph(child, doc)
            if p.text.strip():
                body_elements.append(p.text.strip())
        elif child.tag.endswith("tbl"):
            tbl = docx.table.Table(child, doc)
            tbl_text = " ".join(c.text.strip() for row in tbl.rows for c in row.cells)
            if tbl_text:
                body_elements.append(tbl_text)

    full_body_text = "\n---\n".join(body_elements)
    action_heading_idx = full_body_text.find("Action Required: Unresolved Validation Points / Clarifications")
    gateway_heading_idx = full_body_text.find("Executive Readiness Gateway: Startup Readiness Checklist (G-01) & Gate Decision")
    checklist_heading_idx = full_body_text.find("Startup Readiness Checklist Table (G-01)")

    assert action_heading_idx == -1, "Action Required heading must not be present in report"
    assert gateway_heading_idx != -1, "Executive Readiness Gateway heading must be present"
    assert checklist_heading_idx != -1, "Startup Readiness Checklist Table heading must be present"
    assert gateway_heading_idx < checklist_heading_idx, (
        "Document flow order must strictly be: Executive Readiness Gateway -> Startup Readiness Checklist"
    )

    # Find the tables
    table_headers = []
    for tbl in doc.tables:
        header_row = [c.text.strip() for c in tbl.rows[0].cells]
        table_headers.append(header_row)

    # Check for Action Required Table header (should be absent) and Checklist Table header (should be last)
    action_tbl_idx = -1
    checklist_tbl_idx = -1
    for idx, headers in enumerate(table_headers):
        if "Action ID" in headers and "Score Impact" in headers:
            action_tbl_idx = idx
        elif "Gate ID" in headers and "Gate Criterion" in headers:
            checklist_tbl_idx = idx

    assert action_tbl_idx == -1, "Action Required Table must not be present in generated document"
    assert checklist_tbl_idx != -1, "G-01 Checklist Table must be present in document"
    assert checklist_tbl_idx == len(table_headers) - 1, (
        f"G-01 Checklist Table (idx={checklist_tbl_idx}) must be the last table in document (total={len(table_headers)})"
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
