"""Word (.docx) writer for Scope Baseline document (HTL-108)."""

from pathlib import Path
from typing import Optional
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from src.generators.formatting import (
    add_section_heading,
    add_callout_box,
    style_table,
    format_cell_text_and_highlight,
    COLOR_NAVY_HEX,
    COLOR_PRIMARY_BLUE_HEX,
    COLOR_LIGHT_BG_HEX,
    set_cell_background,
    set_cell_margins,
)
from src.generators.scope_baseline.models import ScopeBaselineDocument


def write_scope_baseline_docx(doc_model: ScopeBaselineDocument, target_path: Path) -> Path:
    """Render and save formatted .docx Scope Baseline document."""
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    doc = docx.Document()

    # Set page margins (1.0 inch)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

        # Header / Footer
        footer = section.footer
        p_foot = footer.paragraphs[0]
        p_foot.text = f"{doc_model.project_name} -- Scope Baseline ({doc_model.contract_variant}) | Toptal PMO Baseline Control"
        p_foot.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if p_foot.runs:
            p_foot.runs[0].font.name = "Arial"
            p_foot.runs[0].font.size = Pt(8.5)
            p_foot.runs[0].font.color.rgb = RGBColor(100, 116, 139)

    # Document Header Title
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(2)
    run_title = title_p.add_run(f"{doc_model.project_name} -- Scope Baseline")
    run_title.font.name = "Arial"
    run_title.font.size = Pt(20)
    run_title.bold = True
    run_title.font.color.rgb = RGBColor(15, 33, 55)  # Navy

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_before = Pt(0)
    sub_p.paragraph_format.space_after = Pt(12)
    sub_text = (
        f"Commercial Structure: {doc_model.contract_variant}  |  "
        f"Governance Tier: {doc_model.governance_tier}  |  "
        f"Delivery Model: {doc_model.delivery_model}"
    )
    if doc_model.client_name:
        sub_text = f"Client: {doc_model.client_name}  |  " + sub_text
    run_sub = sub_p.add_run(sub_text)
    run_sub.font.name = "Arial"
    run_sub.font.size = Pt(10)
    run_sub.font.color.rgb = RGBColor(71, 85, 105)

    # Executive Overview Callout Box
    overview_text = (
        f"This Scope Baseline establishes the definitive boundary of authorized work, exclusions, and commercial governance "
        f"for {doc_model.project_name}. All project activities, backlog prioritization, and delivery commitments are governed "
        f"by the decision rules and change pathways defined herein under {doc_model.contract_variant} commercial terms. "
        f"Any work requested beyond these authorized boundaries requires formal adherence to the Change Decision Matrix."
    )
    add_callout_box(doc, overview_text, title="Baseline Purpose & Governance Directive")

    # ==========================================
    # Section 1: Scope Baseline Summary (Table 1)
    # ==========================================
    add_section_heading(doc, "1. Scope Baseline Summary", level=1)
    doc.add_paragraph(
        "The following matrix summarizes the authorized scope baseline across key project dimensions, explicitly contrasting "
        "included delivery work against out-of-scope boundaries."
    )

    t1 = doc.add_table(rows=1, cols=3)
    t1.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr1 = t1.rows[0].cells
    hdr1[0].text = "Dimension"
    hdr1[1].text = "Baseline Definition & Authorized Work"
    hdr1[2].text = "Excluded / Out-of-Scope"

    for r in doc_model.table1_summary:
        row = t1.add_row().cells
        format_cell_text_and_highlight(row[0], r.dimension)
        format_cell_text_and_highlight(row[1], r.authorized_work)
        format_cell_text_and_highlight(row[2], r.excluded_scope)

    style_table(t1, col_widths=[1.8, 2.5, 2.2])
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # ==========================================
    # Section 2: Change Decision Matrix (Table 2)
    # ==========================================
    add_section_heading(doc, "2. Change Decision Matrix", level=1)
    doc.add_paragraph(
        "Governing if/then rules for classifying and processing potential scope shifts, requirement adjustments, and dependency events."
    )

    t2 = doc.add_table(rows=1, cols=4)
    t2.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr2 = t2.rows[0].cells
    hdr2[0].text = "Classification"
    hdr2[1].text = "Scope Shift / Trigger Condition"
    hdr2[2].text = "Required Governance & Approval Pathway"
    hdr2[3].text = "Commercial & Contractual Impact"

    for r in doc_model.table2_change_matrix:
        row = t2.add_row().cells
        format_cell_text_and_highlight(row[0], r.classification)
        format_cell_text_and_highlight(row[1], r.trigger_condition)
        format_cell_text_and_highlight(row[2], r.governance_action)
        format_cell_text_and_highlight(row[3], r.commercial_impact)

    style_table(t2, col_widths=[1.2, 2.0, 1.8, 1.5])
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # ==========================================
    # Section 3: Decision Rules & Commercial Controls (Table 3)
    # ==========================================
    add_section_heading(doc, "3. Decision Rules & Commercial Controls", level=1)
    doc.add_paragraph(
        f"Operational controls and commercial mechanisms enforced across 5 critical delivery dimensions under {doc_model.contract_variant} framing."
    )

    t3 = doc.add_table(rows=1, cols=4)
    t3.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr3 = t3.rows[0].cells
    hdr3[0].text = "Control Dimension"
    hdr3[1].text = "Governing Rule & Authorized Standard"
    hdr3[2].text = "Boundary Violation & Action Trigger"
    hdr3[3].text = "Contract Relief / Control Route"

    for r in doc_model.table3_decision_rules:
        row = t3.add_row().cells
        format_cell_text_and_highlight(row[0], r.control_dimension)
        format_cell_text_and_highlight(row[1], r.governing_rule)
        format_cell_text_and_highlight(row[2], r.boundary_violation_trigger)
        format_cell_text_and_highlight(row[3], r.commercial_control_route)

    style_table(t3, col_widths=[1.4, 1.8, 1.8, 1.5])
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # ==========================================
    # Section 4: Scope Classification Guide (Table 4)
    # ==========================================
    add_section_heading(doc, "4. Scope Classification Guide", level=1)
    doc.add_paragraph(
        "Operational criteria and approval thresholds for classifying incoming requests during project execution."
    )

    t4 = doc.add_table(rows=1, cols=4)
    t4.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr4 = t4.rows[0].cells
    hdr4[0].text = "Classification"
    hdr4[1].text = "Operational Characteristics"
    hdr4[2].text = "Budget & Milestone Impact"
    hdr4[3].text = "Decision Pathway & Authority"

    for r in doc_model.table4_classification_guide:
        row = t4.add_row().cells
        format_cell_text_and_highlight(row[0], r.classification)
        format_cell_text_and_highlight(row[1], r.operational_characteristics)
        format_cell_text_and_highlight(row[2], r.budget_milestone_impact)
        format_cell_text_and_highlight(row[3], r.approval_pathway)

    style_table(t4, col_widths=[1.2, 2.0, 1.8, 1.5])
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # ==========================================
    # Section 5: Practical Example Decisions (Table 5)
    # ==========================================
    add_section_heading(doc, "5. Practical Example Decisions", level=1)
    doc.add_paragraph(
        "Concrete, hypothetical delivery scenarios illustrating how scope baseline rules and commercial protocols apply to realistic situations."
    )

    t5 = doc.add_table(rows=1, cols=4)
    t5.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr5 = t5.rows[0].cells
    hdr5[0].text = "Classification"
    hdr5[1].text = "Scenario Description"
    hdr5[2].text = "Scope Baseline Analysis"
    hdr5[3].text = "Resolution & Governance Protocol"

    for r in doc_model.table5_examples:
        row = t5.add_row().cells
        format_cell_text_and_highlight(row[0], r.classification)
        format_cell_text_and_highlight(row[1], r.scenario_description)
        format_cell_text_and_highlight(row[2], r.analysis)
        format_cell_text_and_highlight(row[3], r.resolution_and_governance)

    style_table(t5, col_widths=[1.2, 2.0, 1.8, 1.5])
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    doc.save(str(target_path))
    return target_path
