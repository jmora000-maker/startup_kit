"""PPTX Presentation writer and dynamic shape tree engine for PS Governance Kickoff Deck (HTL-72)."""

import copy
import os
from pathlib import Path
import re
from typing import List, Optional, Tuple
from lxml import etree
import pptx
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Length, Pt
from pptx.dml.color import RGBColor

from src.config import CLIENT_DECK_TEMPLATE_PATH, GOVERNANCE_DECK_TEMPLATE_PATH
from src.generators.deck_header import apply_slide_header_formatting
from src.generators.client_deck.fit import (
    BOLD_CHAR_WIDTH_FACTOR,
    estimate_text_height,
    fit_deliverables_for_block,
    select_fitting_font_size,
    truncate_at_clause,
    wrap_lines,
)
from src.generators.client_deck.spec import (
    ClientDeckModel,
    Slide1Model as ClientSlide1Model,
    Slide5Model as ClientSlide5Model,
    Slide6Model as ClientSlide6Model,
    Slide12Model as ClientSlide12Model,
    Slide15Model as ClientSlide15Model,
    RiskItem as ClientRiskItem,
    NextStepItem as ClientNextStepItem,
    WorkstreamBlock as ClientWorkstreamBlock,
)
from src.generators.client_deck.writer import (
    _format_table_cell,
    _replace_shape_text,
    _set_header_paragraph_format,
    _set_paragraph_bullet_format,
    _populate_deliverables_box,
    chunk_workstreams_for_deliverables_table,
    write_slide5,
    write_slide6,
    write_slide6_deliverables_page,
    write_slide12,
    write_slide15,
)
from src.generators.governance_deck.builder import _build_acceptance_cards, parse_step_line
from src.generators.governance_deck.spec import GovernanceDeckModel


def resolve_governance_deck_template_path(custom_path: Optional[Path] = None) -> Path:
    """Resolve the PS Governance Kickoff Deck template path with fallback resolution (HTL-72)."""
    if custom_path and custom_path.exists():
        return custom_path

    env_path = os.getenv("GOVERNANCE_DECK_TEMPLATE_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    primary_path = Path("templates/PS_Governance Kickoff_TEMPLATE.pptx")
    if primary_path.exists():
        return primary_path

    fallback_path = Path("templates/PS_Governance_Kickoff_TEMPLATE.pptx")
    if fallback_path.exists():
        return fallback_path

    return primary_path


def resolve_client_deck_template_path(custom_path: Optional[Path] = None) -> Path:
    """Resolve the Client Kickoff Deck template path with fallback resolution (HTL-72)."""
    if custom_path and custom_path.exists():
        return custom_path
    if CLIENT_DECK_TEMPLATE_PATH.exists():
        return CLIENT_DECK_TEMPLATE_PATH
    fallback = Path("templates/Project_Kickoff_Deck_TEMPLATE.pptx")
    if fallback.exists():
        return fallback
    return CLIENT_DECK_TEMPLATE_PATH


def write_slide1(slide, model: GovernanceDeckModel) -> None:
    """Populate Slide 1 [Client Name] and [Project Name] placeholders with 'Governance Kickoff' at 24pt and fixed subtitle (HTL-72)."""
    title_sz = 24.0
    client_name = model.slide1.client_name or "Client"
    project_name = model.slide1.project_name or "Project Baseline"

    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        text = shape.text_frame.text

        # Title Shape
        if "[Client Name]" in text or "[Project Name]" in text or shape.shape_id == 93:
            tf = shape.text_frame
            tf.word_wrap = True
            tf.margin_top = 0
            tf.margin_bottom = 0
            tf.margin_left = 0
            tf.margin_right = 0

            # Strip normAutofit if present and enforce top anchor
            for bpr in shape._element.xpath(".//a:bodyPr"):
                bpr.set("anchor", "t")
                for autofit in list(bpr.xpath("./a:normAutofit")):
                    bpr.remove(autofit)
                if not bpr.xpath("./a:noAutofit"):
                    from lxml import etree
                    ns_a = "http://schemas.openxmlformats.org/drawingml/2006/main"
                    bpr.append(etree.Element(f"{{{ns_a}}}noAutofit"))

            # Clear paragraphs except first
            for p in list(tf.paragraphs[1:]):
                tf._txBody.remove(p._p)

            p0 = tf.paragraphs[0]
            p0.text = f"{client_name}\n{project_name} Governance Kickoff"
            for r in p0.runs:
                r.font.name = "Proxima Nova"
                r.font.size = Pt(title_sz)
                r.font.bold = True

        # Subtitle Shape
        elif "Onboarding for Project Managers" in text or "Aligning on governance" in text or "Alignment on governance" in text or "Aligning on outcomes" in text or shape.shape_id == 94:
            shape.top = 4153150  # 4.542 in (template default)
            tf = shape.text_frame
            tf.word_wrap = True
            tf.margin_top = 0
            tf.margin_bottom = 0
            tf.margin_left = 0
            tf.margin_right = 0

            for bpr in shape._element.xpath(".//a:bodyPr"):
                bpr.set("anchor", "t")

            for p in list(tf.paragraphs[1:]):
                tf._txBody.remove(p._p)

            p0 = tf.paragraphs[0]
            p0.text = "Aligning on governance, outcomes and project plan."
            for r in p0.runs:
                r.font.name = "Proxima Nova"
                r.font.size = Pt(11)


def _format_table_header_cell(
    cell,
    text: str,
    font_size_pt: float = 9.5,
    bold: bool = True,
    border_hex: str = "D3DCEC",
    fill_hex: str = "0F256E",
) -> None:
    """Format table header cell with dark navy background (#0F256E), white bold text, and D3DCEC borders (HTL-89 / HTL-103)."""
    cell.text = text
    tf = cell.text_frame
    tf.word_wrap = True
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.margin_left = 0
    tf.margin_right = 0

    tcPr = cell._tc.get_or_add_tcPr()
    tcPr.set("anchor", "t")
    tcPr.set("marT", "18288")
    tcPr.set("marB", "18288")
    tcPr.set("marL", "36576")
    tcPr.set("marR", "36576")

    for child in list(tcPr):
        if child.tag.endswith("solidFill") or child.tag.endswith(("lnL", "lnR", "lnT", "lnB")):
            tcPr.remove(child)

    ns_a = "http://schemas.openxmlformats.org/drawingml/2006/main"
    for side in ["lnL", "lnR", "lnT", "lnB"]:
        ln = etree.SubElement(tcPr, f"{{{ns_a}}}{side}", w="12700", cap="flat", cmpd="sng")
        sfill = etree.SubElement(ln, f"{{{ns_a}}}solidFill")
        etree.SubElement(sfill, f"{{{ns_a}}}srgbClr", val=border_hex)

    solidFill = etree.SubElement(tcPr, f"{{{ns_a}}}solidFill")
    etree.SubElement(solidFill, f"{{{ns_a}}}srgbClr", val=fill_hex)

    for p in tf.paragraphs:
        for run in p.runs:
            run.font.name = "Proxima Nova"
            run.font.size = Pt(font_size_pt)
            run.font.bold = bold
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)


def _format_table_data_cell_styling(
    cell,
    border_hex: str = "D3DCEC",
    fill_hex: str = "FFFFFF",
) -> None:
    """Apply solid white fill, subtle gray-blue borders, and standard margins to table data cell (HTL-89)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcPr.set("anchor", "t")
    tcPr.set("marT", "18288")
    tcPr.set("marB", "18288")
    tcPr.set("marL", "36576")
    tcPr.set("marR", "36576")

    for child in list(tcPr):
        if child.tag.endswith("solidFill") or child.tag.endswith(("lnL", "lnR", "lnT", "lnB")):
            tcPr.remove(child)

    ns_a = "http://schemas.openxmlformats.org/drawingml/2006/main"
    for side in ["lnL", "lnR", "lnT", "lnB"]:
        ln = etree.SubElement(tcPr, f"{{{ns_a}}}{side}", w="12700", cap="flat", cmpd="sng")
        sfill = etree.SubElement(ln, f"{{{ns_a}}}solidFill")
        etree.SubElement(sfill, f"{{{ns_a}}}srgbClr", val=border_hex)

    solidFill = etree.SubElement(tcPr, f"{{{ns_a}}}solidFill")
    etree.SubElement(solidFill, f"{{{ns_a}}}srgbClr", val=fill_hex)


def write_slide15_acceptance_criteria_page(
    slide,
    rows: List[AcceptanceCriterionRow],
    page_num: int = 1,
    total_pages: int = 1,
) -> None:
    """Populate one Slide 15 Deliverable Acceptance Criteria table page with multi-bullet criteria and uniform font fitting (HTL-62/63/64/72/88/89)."""
    # 1. Clear any placeholder shapes
    for s in list(slide.shapes):
        slide.shapes._spTree.remove(s._element)

    # 2. Add Header (HTL-88)
    if total_pages > 1:
        sub_text = f"Contractual criteria and verification requirements mapped to milestone gates (Part {page_num} of {total_pages})."
    else:
        sub_text = "Contractual criteria and verification requirements mapped to milestone gates."
    apply_slide_header_formatting(
        slide,
        kicker_text="PROJECT SUCCESS AGREEMENT",
        title_text="Deliverable acceptance criteria",
        subtitle_text=sub_text,
    )

    # 3. Add Table (Left: 0.525 in, Top: 1.75 in, Width: 9.00 in, Height: 2.00 in)
    num_rows = len(rows)
    table_rows = max(2, num_rows + 1)
    table_shape = slide.shapes.add_table(table_rows, 3, 480073, 1600200, 8229600, 1828800)
    table = table_shape.table

    # Column widths: Col 0: 2.00 in (1,828,800), Col 1: 5.70 in (5,212,080), Col 2: 1.30 in (1,188,720)
    table.columns[0].width = 1828800
    table.columns[1].width = 5212080
    table.columns[2].width = 1188720

    # Header Row (Row 0)
    table.rows[0].height = Pt(22)
    _format_table_header_cell(table.cell(0, 0), "Deliverable", font_size_pt=9.5, bold=True)
    _format_table_header_cell(table.cell(0, 1), "Acceptance Criteria", font_size_pt=9.5, bold=True)
    _format_table_header_cell(table.cell(0, 2), "Milestone Gate", font_size_pt=9.5, bold=True)

    if not rows:
        cell0 = table.rows[1].cells[0]
        table.rows[1].height = Pt(20)
        _format_table_data_cell_styling(cell0)
        _format_table_data_cell_styling(table.rows[1].cells[1])
        _format_table_data_cell_styling(table.rows[1].cells[2])
        _format_table_cell(cell0, "[CONFIRMATION REQUIRED]", font_size_pt=8.0)
        return

    # Pass 2: Populate Data Rows
    for r_idx, row_data in enumerate(rows):
        row = table.rows[r_idx + 1]
        row.height = Pt(20)

        # Col 0: Deliverable (ID bold + Name)
        cell0 = row.cells[0]
        _format_table_data_cell_styling(cell0)
        cell0.text = ""
        tf0 = cell0.text_frame
        tf0.margin_top = 0
        tf0.margin_bottom = 0
        tf0.margin_left = 0
        tf0.margin_right = 0

        p0_1 = tf0.paragraphs[0]
        p0_1.text = row_data.deliverable_id
        if p0_1.runs:
            p0_1.runs[0].font.name = "Proxima Nova"
            p0_1.runs[0].font.size = Pt(8.0)
            p0_1.runs[0].font.bold = True
            p0_1.runs[0].font.color.rgb = RGBColor(0x0F, 0x25, 0x6E)

        if row_data.deliverable_name:
            p0_2 = tf0.add_paragraph()
            p0_2.text = row_data.deliverable_name
            if p0_2.runs:
                p0_2.runs[0].font.name = "Proxima Nova"
                p0_2.runs[0].font.size = Pt(7.5)
                p0_2.runs[0].font.color.rgb = RGBColor(0x1D, 0x29, 0x39)

        # Col 1: Acceptance Criteria (Multi-bullet)
        cell1 = row.cells[1]
        _format_table_data_cell_styling(cell1)
        cell1.text = ""
        tf1 = cell1.text_frame
        tf1.margin_top = 0
        tf1.margin_bottom = 0
        tf1.margin_left = 0
        tf1.margin_right = 0

        crits = row_data.acceptance_criteria or ["[CONFIRMATION REQUIRED]"]
        for c_idx, crit in enumerate(crits):
            p = tf1.paragraphs[0] if c_idx == 0 else tf1.add_paragraph()
            p.text = f"• {crit}" if len(crits) > 1 else crit
            if p.runs:
                p.runs[0].font.name = "Proxima Nova"
                p.runs[0].font.size = Pt(7.5)
                p.runs[0].font.color.rgb = RGBColor(0x1D, 0x29, 0x39)
            p.line_spacing = 1.05
            p.space_after = Pt(2)

        # Col 2: Milestone Gate
        cell2 = row.cells[2]
        _format_table_data_cell_styling(cell2)
        cell2.text = ""
        tf2 = cell2.text_frame
        tf2.margin_top = 0
        tf2.margin_bottom = 0
        tf2.margin_left = 0
        tf2.margin_right = 0

        p2 = tf2.paragraphs[0]
        p2.text = row_data.milestone_gate or "—"
        if p2.runs:
            p2.runs[0].font.name = "Proxima Nova"
            p2.runs[0].font.size = Pt(8.0)
            p2.runs[0].font.bold = True
            p2.runs[0].font.color.rgb = RGBColor(0x0F, 0x25, 0x6E)


def write_slide15_acceptance_criteria(slide, model: GovernanceDeckModel) -> None:
    """Populate Slide 15 Deliverable Acceptance Criteria table (HTL-62/63/64/72)."""
    write_slide15_acceptance_criteria_page(slide, model.slide15.rows, page_num=1, total_pages=1)


_parse_step_line = parse_step_line


def write_slide16_acceptance_narrative(slide, model: GovernanceDeckModel) -> None:
    """Populate Slide 16 How Milestone Acceptance Works visual flowchart with loop-back and 3 deep-dive cards (HTL-72 / HTL-74 Option C / HTL-88)."""
    # 1. Clear placeholder shapes
    for s in list(slide.shapes):
        slide.shapes._spTree.remove(s._element)

    # 2. Add Header (HTL-88)
    kicker_txt = getattr(model.slide16, "kicker", None) or "PROJECT SUCCESS AGREEMENT"
    title_txt = getattr(model.slide16, "title", None) or "How milestone acceptance works"
    subtitle_txt = getattr(model.slide16, "subtitle", None) or "Workflow, review turnarounds, remediation thresholds, and sign-off protocols for the Talent Team."
    apply_slide_header_formatting(
        slide,
        kicker_text=kicker_txt,
        title_text=title_txt,
        subtitle_text=subtitle_txt,
    )

    # -------------------------------------------------------------
    # 3. Upper Zone: 4-Node Visual Flowchart with Remediation Loop
    # -------------------------------------------------------------
    flowchart_top = 1536192  # 1.68 in (comfortably below canonical 1.35 in + 0.30 in subtitle)
    node_h = 201168         # 0.22 in
    total_w = 8229600       # 9.00 in
    node_gap = 219456       # 0.24 in
    node_w = (total_w - 3 * node_gap) // 4  # 1892832 EMU (2.07 in)

    flow_nodes = [
        "1. Formal Submission",
        "2. Client Review & SLAs",
        "3. Decision / Defect Check",
        "4. Sign-Off & Deemed Accepted",
    ]

    node_lefts = []
    for idx, node_title in enumerate(flow_nodes):
        n_left = 457200 + idx * (node_w + node_gap)
        node_lefts.append(n_left)

        # Node rounded box
        node_shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, n_left, flowchart_top, node_w, node_h)
        node_shape.fill.solid()
        node_shape.fill.fore_color.rgb = RGBColor(0x0F, 0x25, 0x6E)
        node_shape.line.color.rgb = RGBColor(0x0F, 0x25, 0x6E)

        tf_node = node_shape.text_frame
        tf_node.margin_top = 0
        tf_node.margin_bottom = 0
        tf_node.margin_left = 0
        tf_node.margin_right = 0
        p_node = tf_node.paragraphs[0]
        p_node.alignment = pptx.enum.text.PP_ALIGN.CENTER
        r_node = p_node.add_run()
        r_node.text = node_title
        r_node.font.name = "Proxima Nova"
        r_node.font.size = Pt(8.0)
        r_node.font.bold = True
        r_node.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        # Connector arrow to next node
        if idx < 3:
            arrow_w = 128016   # 0.14 in
            arrow_h = 128016   # 0.14 in
            arrow_l = n_left + node_w + (node_gap - arrow_w) // 2
            arrow_t = flowchart_top + (node_h - arrow_h) // 2
            arrow = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, arrow_l, arrow_t, arrow_w, arrow_h)
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = RGBColor(0x98, 0xA2, 0xB3)
            arrow.line.color.rgb = RGBColor(0x98, 0xA2, 0xB3)

    # Remediation Loop-Back Band (Returns from Step 3 Decision Check back to Step 1/2)
    loop_top = flowchart_top + node_h + 18288   # 1.92 in
    loop_h = 137160                            # 0.15 in
    loop_left = node_lefts[0] + 73152
    loop_right = node_lefts[2] + node_w - 73152
    loop_w = loop_right - loop_left

    loop_shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, loop_left, loop_top, loop_w, loop_h)
    loop_shape.fill.solid()
    loop_shape.fill.fore_color.rgb = RGBColor(0xF2, 0xF4, 0xF7)
    loop_shape.line.color.rgb = RGBColor(0xD0, 0xD5, 0xDD)
    loop_shape.line.width = Pt(0.75)

    tf_loop = loop_shape.text_frame
    tf_loop.margin_top = 0
    tf_loop.margin_bottom = 0
    tf_loop.margin_left = 0
    tf_loop.margin_right = 0
    p_loop = tf_loop.paragraphs[0]
    p_loop.alignment = pptx.enum.text.PP_ALIGN.CENTER
    r_loop = p_loop.add_run()
    r_loop.text = "<- Deficiency Notice / Defect Triage & Remediation Loop (Rework & Resubmit)"
    r_loop.font.name = "Proxima Nova"
    r_loop.font.size = Pt(7.0)
    r_loop.font.bold = True
    r_loop.font.color.rgb = RGBColor(0x34, 0x40, 0x54)

    # -------------------------------------------------------------
    # 4. Lower Zone: 3 Deep-Dive Governance Cards
    # -------------------------------------------------------------
    cards = getattr(model.slide16, "cards", None)
    if not cards:
        narrative_text = model.slide16.narrative or "[CONFIRMATION REQUIRED]"
        cards = _build_acceptance_cards(narrative_text)

    card_top = 1975104   # 2.16 in
    card_h = 2807208     # 3.07 in  (bottom = 5.23 in <= 5.25 in ceiling)
    gap = 146304         # 0.16 in
    card_w = (total_w - 2 * gap) // 3  # 2645664 EMU (2.893 in)

    badge_h = 173736     # 0.19 in
    badge_inset = 45720  # 0.05 in

    cat_top = card_top + badge_h + badge_inset + 9144   # +0.01 in
    cat_h = 137160                                      # 0.15 in
    tb_top = cat_top + cat_h + 9144                     # +0.01 in
    tb_h = card_h - (tb_top - card_top) - badge_inset
    avail_w_in = (card_w - 2 * badge_inset) / 914400.0  # ~2.79 in
    avail_h_pt = tb_h / 12700.0                        # ~188 pt

    body_font_sz = 8.5
    line_spacing = 1.08
    space_after_pt = 4.0

    # Render all 3 cards with uniform fixed font size (8.5 pt), vertical centering, and balanced spacing (HTL-105 / HTL-110)
    for c_idx, card in enumerate(cards[:3]):
        c_left = 457200 + c_idx * (card_w + gap)

        # Container Card Background
        bg_card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, c_left, card_top, card_w, card_h)
        bg_card.fill.solid()
        bg_card.fill.fore_color.rgb = RGBColor(0xF8, 0xF9, 0xFA)
        bg_card.line.color.rgb = RGBColor(0xEA, 0xEC, 0xF0)
        bg_card.line.width = Pt(1)

        # Stage Pill Badge at Top of Card
        badge = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            c_left + badge_inset,
            card_top + badge_inset,
            card_w - (2 * badge_inset),
            badge_h,
        )
        badge.fill.solid()
        badge.fill.fore_color.rgb = RGBColor(0x0F, 0x25, 0x6E)
        badge.line.color.rgb = RGBColor(0x0F, 0x25, 0x6E)
        tf_badge = badge.text_frame
        tf_badge.margin_top = 0
        tf_badge.margin_bottom = 0
        tf_badge.margin_left = 0
        tf_badge.margin_right = 0
        p_badge = tf_badge.paragraphs[0]
        p_badge.alignment = pptx.enum.text.PP_ALIGN.CENTER
        r_badge = p_badge.add_run()
        r_badge.text = card.stage_label
        r_badge.font.name = "Proxima Nova"
        r_badge.font.size = Pt(8.0)
        r_badge.font.bold = True
        r_badge.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        # Category Title Box below badge
        cat_box = slide.shapes.add_textbox(c_left + badge_inset, cat_top, card_w - (2 * badge_inset), cat_h)
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        tf_cat.margin_top = 0
        tf_cat.margin_bottom = 0
        tf_cat.margin_left = 0
        tf_cat.margin_right = 0
        p_cat = tf_cat.paragraphs[0]
        r_cat = p_cat.add_run()
        r_cat.text = card.title
        r_cat.font.name = "Proxima Nova"
        r_cat.font.size = Pt(8.0)
        r_cat.font.bold = True
        r_cat.font.color.rgb = RGBColor(0x0F, 0x25, 0x6E)

        # Content Text Box (HTL-105 / HTL-110: uniform fixed height, vertical centering, and balanced spacing across all 3 cards)
        body_box = slide.shapes.add_textbox(c_left + badge_inset, tb_top, card_w - (2 * badge_inset), tb_h)
        tf_b = body_box.text_frame
        tf_b.word_wrap = True
        tf_b.margin_top = 0
        tf_b.margin_bottom = 0
        tf_b.margin_left = 0
        tf_b.margin_right = 0
        for bpr in body_box._element.xpath(".//a:bodyPr"):
            bpr.set("anchor", "ctr")

        for p_idx, (label, body) in enumerate(card.steps):
            p_elem = tf_b.paragraphs[0] if p_idx == 0 else tf_b.add_paragraph()
            p_elem.space_before = Pt(0)
            p_elem.space_after = Pt(space_after_pt)
            p_elem.line_spacing = line_spacing

            if label:
                clean_lbl = label.rstrip(" :")
                lead_run = p_elem.add_run()
                lead_run.text = f"{clean_lbl}: "
                lead_run.font.name = "Proxima Nova"
                lead_run.font.size = Pt(body_font_sz)
                lead_run.font.bold = True
                lead_run.font.color.rgb = RGBColor(0x0F, 0x25, 0x6E)

                rest_run = p_elem.add_run()
                rest_run.text = body
                rest_run.font.name = "Proxima Nova"
                rest_run.font.size = Pt(body_font_sz)
                rest_run.font.bold = False
                rest_run.font.color.rgb = RGBColor(0x1D, 0x29, 0x39)
            else:
                run = p_elem.add_run()
                run.text = body
                run.font.name = "Proxima Nova"
                run.font.size = Pt(body_font_sz)
                run.font.bold = False
                run.font.color.rgb = RGBColor(0x1D, 0x29, 0x39)


def write_slide11_change_decision_matrix(slide, model: GovernanceDeckModel) -> None:
    """Populate Slide 11 Change Decision Matrix 4-card layout and bottom footer banner matching Slides 9/10 exactly (HTL-109)."""
    # 1. Clear any placeholder shapes
    for s in list(slide.shapes):
        slide.shapes._spTree.remove(s._element)

    # 2. Add Header (kicker + title)
    kicker_txt = model.slide11.kicker or "DECISION RIGHTS IN PRACTICE"
    title_txt = model.slide11.title or "Change Decision Matrix"
    apply_slide_header_formatting(
        slide,
        kicker_text=kicker_txt,
        title_text=title_txt,
        has_subtitle=False,
    )

    # 3. Add 4 Cards (Clarification, Reprioritization, Expansion, Dependency Impact)
    # Available total width: 8.665 in (7,923,022 EMU)
    # 4 cards: width 2.04 in (1,865,376 EMU), gap 0.168 in (153,618 EMU)
    # Left positions: 0.6675 in (610,350 EMU), 2.8755 in (2,629,344 EMU), 5.0835 in (4,648,338 EMU), 7.2915 in (6,667,332 EMU)
    # Top: 1.6684 in (1,525,630 EMU), Height: 2.7106 in (2,478,600 EMU)
    card_w = 1865376
    card_h = 2478600
    card_top = 1525630
    left_positions = [610350, 2629344, 4648338, 6667332]

    cards = model.slide11.cards
    for idx, c_left in enumerate(left_positions):
        if idx >= len(cards):
            break
        card = cards[idx]

        # Card Outer Rounded Rectangle
        card_shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, c_left, card_top, card_w, card_h)
        card_shape.fill.solid()
        card_shape.fill.fore_color.rgb = RGBColor(0xFD, 0xFD, 0xFE)
        card_shape.line.color.rgb = RGBColor(0xDD, 0xE3, 0xEE)
        card_shape.line.width = 7150

        # Section 1: Title + Characteristics Textbox
        sec1_left = c_left + 109728   # 0.12 in padding
        sec1_top = 1627632            # 1.780 in top (1627632 EMU)
        sec1_w = 1645920              # 1.800 in width
        sec1_h = 731520               # 0.800 in height (731520 EMU / 57.6 pt)

        tb1 = slide.shapes.add_textbox(sec1_left, sec1_top, sec1_w, sec1_h)
        tf1 = tb1.text_frame
        tf1.word_wrap = True
        tf1.margin_top = 0
        tf1.margin_bottom = 0
        tf1.margin_left = 0
        tf1.margin_right = 0
        for bpr in tb1._element.xpath(".//a:bodyPr"):
            bpr.set("anchor", "t")

        # 1. Classification Title (11pt Bold #1B2336)
        p_title = tf1.paragraphs[0]
        p_title.space_before = Pt(0)
        p_title.space_after = Pt(2)
        r_title = p_title.add_run()
        r_title.text = card.classification
        r_title.font.name = "Proxima Nova"
        r_title.font.size = Pt(11.0)
        r_title.font.bold = True
        r_title.font.color.rgb = RGBColor(0x1B, 0x23, 0x36)

        # 2. Operational Characteristics (8.5pt Regular #5B6475)
        p_desc = tf1.add_paragraph()
        p_desc.space_before = Pt(0)
        p_desc.space_after = Pt(0)
        p_desc.line_spacing = 1.15
        r_desc = p_desc.add_run()
        r_desc.text = card.operational_characteristics
        r_desc.font.name = "Proxima Nova"
        r_desc.font.size = Pt(8.5)
        r_desc.font.bold = False
        r_desc.font.color.rgb = RGBColor(0x5B, 0x64, 0x75)

        # Section 2: "WHAT IT MEANS" Header + Budget/Milestone Impact Textbox
        sec2_top = 2505456            # 2.740 in top (2505456 EMU)
        sec2_h = 685800               # 0.750 in height (685800 EMU / 54.0 pt)

        tb2 = slide.shapes.add_textbox(sec1_left, sec2_top, sec1_w, sec2_h)
        tf2 = tb2.text_frame
        tf2.word_wrap = True
        tf2.margin_top = 0
        tf2.margin_bottom = 0
        tf2.margin_left = 0
        tf2.margin_right = 0
        for bpr in tb2._element.xpath(".//a:bodyPr"):
            bpr.set("anchor", "t")

        # 3. "WHAT IT MEANS" Header (8.5pt Bold #204ECF)
        p_lbl = tf2.paragraphs[0]
        p_lbl.space_before = Pt(0)
        p_lbl.space_after = Pt(2)
        r_lbl = p_lbl.add_run()
        r_lbl.text = "WHAT IT MEANS"
        r_lbl.font.name = "Proxima Nova"
        r_lbl.font.size = Pt(8.5)
        r_lbl.font.bold = True
        r_lbl.font.color.rgb = RGBColor(0x20, 0x4E, 0xCF)

        # 4. Budget / Milestone Impact (8.5pt Regular #5B6475)
        p_imp = tf2.add_paragraph()
        p_imp.space_before = Pt(0)
        p_imp.space_after = Pt(0)
        p_imp.line_spacing = 1.15
        r_imp = p_imp.add_run()
        r_imp.text = card.budget_milestone_impact
        r_imp.font.name = "Proxima Nova"
        r_imp.font.size = Pt(8.5)
        r_imp.font.bold = False
        r_imp.font.color.rgb = RGBColor(0x5B, 0x64, 0x75)

        # Section 3: Bottom Pill Box (Fill #EAEFF8, Line #EAEFF8) + Pathway Text
        # Anchored to card bottom edge (card_top + card_h) with fixed offset
        pill_left = c_left + 73152   # 0.08 in inset
        pill_bottom_margin = 137101 # ~0.15 in margin from card bottom
        pill_h = 514500             # 0.5627 in height
        pill_top = card_top + card_h - pill_h - pill_bottom_margin  # 3352629 EMU (3.6665 in)
        pill_w = 1719072            # 1.88 in width

        pill_shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, pill_left, pill_top, pill_w, pill_h)
        pill_shape.fill.solid()
        pill_shape.fill.fore_color.rgb = RGBColor(0xEA, 0xEF, 0xF8)
        pill_shape.line.color.rgb = RGBColor(0xEA, 0xEF, 0xF8)
        pill_shape.line.width = 9525

        tb3 = slide.shapes.add_textbox(sec1_left, pill_top, sec1_w, pill_h)
        tf3 = tb3.text_frame
        tf3.word_wrap = True
        tf3.margin_top = 0
        tf3.margin_bottom = 0
        tf3.margin_left = 0
        tf3.margin_right = 0
        for bpr in tb3._element.xpath(".//a:bodyPr"):
            bpr.set("anchor", "ctr")

        p_pill = tf3.paragraphs[0]
        p_pill.space_before = Pt(0)
        p_pill.space_after = Pt(0)
        p_pill.line_spacing = 1.15

        r_lead = p_pill.add_run()
        r_lead.text = "Authority: "
        r_lead.font.name = "Proxima Nova"
        r_lead.font.size = Pt(8.5)
        r_lead.font.bold = True
        r_lead.font.color.rgb = RGBColor(0x1B, 0x23, 0x36)

        r_path = p_pill.add_run()
        r_path.text = card.decision_pathway
        r_path.font.name = "Proxima Nova"
        r_path.font.size = Pt(8.5)
        r_path.font.bold = False
        r_path.font.color.rgb = RGBColor(0x1B, 0x23, 0x36)

    # 4. Bottom Full-Width Footer Banner
    # Container box: Left 610350 EMU (0.6675 in), Top 4199920 EMU (4.5934 in), Width 7923022 EMU (8.6647 in), Height 480240 EMU (0.5252 in)
    foot_left = 610350
    foot_top = 4199920
    foot_w = 7923022
    foot_h = 480240

    foot_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, foot_left, foot_top, foot_w, foot_h)
    foot_box.fill.solid()
    foot_box.fill.fore_color.rgb = RGBColor(0x0F, 0x25, 0x6E)
    foot_box.line.color.rgb = RGBColor(0x0F, 0x25, 0x6E)
    foot_box.line.width = 9525

    # Accent bar on left of banner
    bar_left = 816150   # 0.8925 in
    bar_top = 4289134   # 4.6909 in
    bar_w = 41160       # 0.0450 in
    bar_h = 301980      # 0.3302 in
    bar_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, bar_left, bar_top, bar_w, bar_h)
    bar_box.fill.solid()
    bar_box.fill.fore_color.rgb = RGBColor(0x00, 0xCC, 0x83)
    bar_box.line.color.rgb = RGBColor(0x00, 0xCC, 0x83)
    bar_box.line.width = 9525

    # Banner text
    txt_left = 987570   # 1.0800 in
    txt_w = 7545802     # 8.2522 in
    tb_foot = slide.shapes.add_textbox(txt_left, foot_top, txt_w, foot_h)
    tf_foot = tb_foot.text_frame
    tf_foot.word_wrap = True
    tf_foot.margin_top = 0
    tf_foot.margin_bottom = 0
    tf_foot.margin_left = 0
    tf_foot.margin_right = 0
    for bpr in tb_foot._element.xpath(".//a:bodyPr"):
        bpr.set("anchor", "ctr")

    p_foot = tf_foot.paragraphs[0]
    p_foot.space_before = Pt(0)
    p_foot.space_after = Pt(0)
    r_foot = p_foot.add_run()
    r_foot.text = model.slide11.footer_banner
    r_foot.font.name = "Proxima Nova"
    r_foot.font.size = Pt(11.0)
    r_foot.font.bold = False
    r_foot.font.color.rgb = RGBColor(0xF4, 0xF6, 0xFB)


def write_slide17_approach(slide, model: GovernanceDeckModel) -> None:
    """Populate Slide 17 Approach 3-card layout with uniform font fitting and Proxima Nova typography (HTL-72 / HTL-88)."""
    # 1. Clear any placeholder shapes
    for s in list(slide.shapes):
        slide.shapes._spTree.remove(s._element)

    # 2. Add Header (HTL-88)
    kicker_txt = model.slide17.kicker or "PROJECT SUCCESS AGREEMENT"
    title_txt = model.slide17.title or "Approach"
    subtitle_txt = model.slide17.subtitle or "Execution phases, workstream deliverables, and governance model."
    apply_slide_header_formatting(
        slide,
        kicker_text=kicker_txt,
        title_text=title_txt,
        subtitle_text=subtitle_txt,
    )

    # 3. Add 3 Cards (Left, Middle, Right)
    # Card geometry matching Governance Slide 5/10 (Inches -> EMUs):
    # Width: 2.778 in (2,540,092 EMU), Height: 3.350 in (3,063,240 EMU), Top: 1.75 in (1,600,200 EMU)
    # Left positions: 0.668 in (610,870 EMU), 3.611 in (3,301,898 EMU), 6.554 in (5,992,926 EMU)
    card_w = 2540092
    card_h = 3063240
    top_pos = 1600200
    left_positions = [610870, 3301898, 5992926]

    cards = model.slide17.cards
    if not cards:
        return

    # Pass 1: Compute uniform fitting font size across all cards for bullets
    candidate_sizes = [10.5, 10.0, 9.5, 9.0, 8.5, 8.0]
    avail_w_in = 2.40
    avail_h_in = 2.15

    card_best_sizes = []
    for c in cards[:3]:
        c_sz = 8.0
        for sz in candidate_sizes:
            tot_h = 0.0
            for b in c.bullets:
                lines = wrap_lines(f"• {b}", width_in=avail_w_in, size_pt=sz)
                tot_h += lines * sz * 1.15 + 5.0
            if (tot_h / 72.0) <= avail_h_in:
                c_sz = sz
                break
        card_best_sizes.append(c_sz)

    uniform_sz = min(card_best_sizes) if card_best_sizes else 9.0

    # Pass 2: Render card background shapes and text boxes
    for idx, (c, left_pos) in enumerate(zip(cards[:3], left_positions)):
        # Card container rectangle
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left_pos, top_pos, card_w, card_h)
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor(0xF8, 0xF9, 0xF8)
        shape.line.color.rgb = RGBColor(0xEA, 0xEC, 0xF0)
        shape.line.width = Pt(1)

        # Inset text box
        # Inset: left + 0.18 in (164,592 EMU), top + 0.16 in (146,304 EMU), width - 0.36 in (2,210,908 EMU), height - 0.32 in (2,770,632 EMU)
        tb = slide.shapes.add_textbox(left_pos + 164592, top_pos + 146304, 2210908, card_h - 292608)
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_top = 0
        tf.margin_bottom = 0
        tf.margin_left = 0
        tf.margin_right = 0
        for bpr in tb._element.xpath(".//a:bodyPr"):
            bpr.set("anchor", "t")

        # Paragraph 0: Category / Kicker
        p_cat = tf.paragraphs[0]
        p_cat.text = c.category
        p_cat.space_after = Pt(2)
        for r in p_cat.runs:
            r.font.name = "Proxima Nova"
            r.font.size = Pt(8.5)
            r.font.bold = True
            r.font.color.rgb = RGBColor(0x2E, 0x5A, 0xAC)

        # Paragraph 1: Card Title
        p_title = tf.add_paragraph()
        p_title.text = c.title
        p_title.space_after = Pt(2)
        for r in p_title.runs:
            r.font.name = "Proxima Nova"
            r.font.size = Pt(13)
            r.font.bold = True
            r.font.color.rgb = RGBColor(0x0F, 0x25, 0x6E)

        # Paragraph 2: Card Lead / Subtitle
        p_lead = tf.add_paragraph()
        p_lead.text = c.lead
        p_lead.space_after = Pt(8)
        for r in p_lead.runs:
            r.font.name = "Proxima Nova"
            r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(0x47, 0x54, 0x67)

        # Paragraphs 3+: Bullets
        for b in c.bullets:
            p_b = tf.add_paragraph()
            _set_paragraph_bullet_format(p_b, font_size_pt=uniform_sz, text=b)


def write_governance_deck(
    model: GovernanceDeckModel,
    target_path: Path,
    template_path: Optional[Path] = None,
    client_template_path: Optional[Path] = None,
) -> Path:
    """Load template presentation, assemble 19 slides, populate lifted and new slides, and save output file (HTL-72)."""
    src_template = resolve_governance_deck_template_path(template_path)
    if not src_template.exists():
        raise FileNotFoundError(f"Governance Deck template not found at {src_template}")

    src_client_template = resolve_client_deck_template_path(client_template_path)
    if not src_client_template.exists():
        raise FileNotFoundError(f"Client Deck template not found at {src_client_template}")

    prs_gov = pptx.Presentation(str(src_template))
    prs_client = pptx.Presentation(str(src_client_template))

    layout_default = prs_gov.slide_layouts[14]

    # Add Acceptance Criteria (Slide 15 - Phase 2 placeholder)
    s_acc_crit = prs_gov.slides.add_slide(layout_default)
    for s in list(s_acc_crit.shapes):
        s_acc_crit.shapes._spTree.remove(s._element)

    # Add How Acceptance Works (Slide 16 - Phase 2 placeholder)
    s_acc_works = prs_gov.slides.add_slide(layout_default)
    for s in list(s_acc_works.shapes):
        s_acc_works.shapes._spTree.remove(s._element)

    # Add Risk Register (Slide 18) - Copy shapes from Client Deck Slide 12
    s_risk = prs_gov.slides.add_slide(layout_default)
    for s in list(s_risk.shapes):
        s_risk.shapes._spTree.remove(s._element)
    for shape in prs_client.slides[11].shapes:
        s_risk.shapes._spTree.append(copy.deepcopy(shape._element))

    # Copy Slide 3 shapes (Team Roster placeholders) and images from Client Deck onto Gov Slide 12 (index 11)
    s_gov_12 = prs_gov.slides[11]
    for s in list(s_gov_12.shapes):
        s_gov_12.shapes._spTree.remove(s._element)

    # Drop existing image relationships from s_gov_12.part to avoid stale/wrong photo targets
    for rId in list(s_gov_12.part.rels.keys()):
        rel = s_gov_12.part.rels[rId]
        if "image" in rel.reltype:
            s_gov_12.part.drop_rel(rId)

    # Map client slide 3 image relationships into s_gov_12.part
    rId_map = {}
    import io
    for old_rId, rel in prs_client.slides[2].part.rels.items():
        if "image" in rel.reltype:
            client_img_part = rel.target_part
            image_stream = io.BytesIO(client_img_part.blob)
            target_img_part, new_rId = s_gov_12.part.get_or_add_image_part(image_stream)
            rId_map[old_rId] = new_rId

    # Copy shapes and update blip r:embed to faithful client template image references
    ns_r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    for shape in prs_client.slides[2].shapes:
        elem = copy.deepcopy(shape._element)
        for blip in elem.xpath(".//a:blip"):
            old_embed = blip.get(f"{{{ns_r}}}embed")
            if old_embed and old_embed in rId_map:
                blip.set(f"{{{ns_r}}}embed", rId_map[old_embed])
        s_gov_12.shapes._spTree.append(elem)

    # Override Slide 12 title to "The people delivering this project" (Governance template wording, HTL-72)
    for shape in s_gov_12.shapes:
        if shape.has_text_frame and "The people delivering" in shape.text_frame.text:
            for p in shape.text_frame.paragraphs:
                for r in p.runs:
                    if "your project" in r.text:
                        r.text = r.text.replace("your project", "this project")
                if "your project" in p.text:
                    p.text = p.text.replace("your project", "this project")

    # Copy Slide 5 shapes (Why We're Here) from Client Deck onto Gov Slide 13 (index 12)
    s_gov_13 = prs_gov.slides[12]
    for s in list(s_gov_13.shapes):
        s_gov_13.shapes._spTree.remove(s._element)
    for s in prs_client.slides[4].shapes:
        s_gov_13.shapes._spTree.append(copy.deepcopy(s._element))

    # Calculate Slide 14 chunks (max 7 deliverables on a single page if <= 7 total, otherwise chunked)
    chunks_s14 = chunk_workstreams_for_deliverables_table(model.slide14.workstreams)
    total_s14_pages = len(chunks_s14)

    # Extra slides for Slide 14 continuation pages
    layout_deliver = prs_gov.slides[13].slide_layout
    extra_deliver_indices = []
    if total_s14_pages > 1:
        for _ in range(total_s14_pages - 1):
            s_extra = prs_gov.slides.add_slide(layout_deliver)
            for s in list(s_extra.shapes):
                s_extra.shapes._spTree.remove(s._element)
            for s in prs_gov.slides[13].shapes:
                s_extra.shapes._spTree.append(copy.deepcopy(s._element))
            extra_deliver_indices.append(len(prs_gov.slides) - 1)

    # Calculate Slide 15 chunks (max 7 deliverables on a single page if <= 7 total, otherwise max 4 per slide page)
    rows_s15 = model.slide15.rows
    max_per_page = len(rows_s15) if len(rows_s15) <= 7 else 4
    chunks_s15 = [rows_s15[i : i + max_per_page] for i in range(0, len(rows_s15), max_per_page)] if rows_s15 else [[]]
    total_s15_pages = len(chunks_s15)

    # Extra slides for Slide 15 continuation pages (clean layout without Slide 14 dark panel)
    layout_clean = prs_gov.slide_layouts[14]
    extra_crit_indices = []
    for _ in range(total_s15_pages - 1):
        s_extra = prs_gov.slides.add_slide(layout_clean)
        for s in list(s_extra.shapes):
            s_extra.shapes._spTree.remove(s._element)
        extra_crit_indices.append(len(prs_gov.slides) - 1)

    # Slide 11: Change Decision Matrix (HTL-109)
    s_change_matrix = prs_gov.slides.add_slide(layout_clean)
    for s in list(s_change_matrix.shapes):
        s_change_matrix.shapes._spTree.remove(s._element)
    change_matrix_index = len(prs_gov.slides) - 1

    # Reorder slides into exact sequence:
    # 0..9: Slides 1..10
    # change_matrix_index: Slide 11 (Change Decision Matrix - index 10)
    # 10: Slide 12 (Project Details - index 11)
    # 11: Slide 13 (Team Roster - index 12)
    # 12: Slide 14 (Why We're Here - index 13)
    # deliver_indices: Slide 15 pages (What We Deliver - index 13 + extra_deliver_indices)
    # crit_indices: Slide 16 pages (Acceptance Criteria - index 17 + extra_crit_indices)
    # 18: Slide 17 (How Acceptance Works - index 18)
    # 14: Slide 18 (Approach - index 14)
    # 19: Slide 19 (Initial Risk Register - index 19)
    # 15: Slide 20 (Next Steps - index 15)
    deliver_indices = [13] + extra_deliver_indices
    crit_indices = [17] + extra_crit_indices
    desired_indices = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, change_matrix_index, 10, 11, 12] + deliver_indices + crit_indices + [18, 14, 19, 15]
    sldIdLst = prs_gov.slides._sldIdLst
    all_sld_ids = list(sldIdLst)

    # Drop relationships for any unused slide from presentation.xml.rels to prevent orphaned slide/notes parts (HTL-109)
    unused_indices = set(range(len(all_sld_ids))) - set(desired_indices)
    ns_r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    for idx in unused_indices:
        sld_id_elem = all_sld_ids[idx]
        rId = sld_id_elem.get(f"{{{ns_r}}}id")
        if rId and rId in prs_gov.part.rels:
            prs_gov.part.drop_rel(rId)

    for child in list(sldIdLst):
        sldIdLst.remove(child)

    for idx in desired_indices:
        sldIdLst.append(all_sld_ids[idx])

    # Convert governance deck models to client models for slide writers
    client_deck_adapter = ClientDeckModel(
        project_name=model.project_name,
        slide1=ClientSlide1Model(client_name=model.slide1.client_name, project_name=model.slide1.project_name),
        slide5=ClientSlide5Model(
            why_are_we_doing_this=model.slide13.why_are_we_doing_this,
            what_problem_are_we_solving=model.slide13.what_problem_are_we_solving,
            what_does_success_look_like=model.slide13.what_does_success_look_like,
        ),
        slide6=ClientSlide6Model(
            workstreams=[
                ClientWorkstreamBlock(
                    title=ws.title,
                    deliverables=list(ws.deliverables),
                    overflow_count=ws.overflow_count,
                )
                for ws in model.slide14.workstreams
            ],
            solution_overview=model.slide14.solution_overview,
            out_of_scope=list(model.slide14.out_of_scope),
        ),
        slide12=ClientSlide12Model(
            risks=[
                ClientRiskItem(
                    id=r.id,
                    description=r.description,
                    prob_impact=r.prob_impact,
                    mitigation=r.mitigation,
                    target_date=r.target_date,
                    severity_score=r.severity_score,
                )
                for r in model.slide18.risks
            ]
        ),
        slide15=ClientSlide15Model(
            next_steps=[
                ClientNextStepItem(
                    owner=st.owner,
                    action=st.action,
                    due=st.due,
                )
                for st in model.slide19.next_steps
            ]
        ),
    )

    # Format canonical slide headers across template and lifted content slides (HTL-88 / HTL-109)
    apply_slide_header_formatting(prs_gov.slides[1], has_subtitle=False)
    apply_slide_header_formatting(prs_gov.slides[3], has_subtitle=False)
    apply_slide_header_formatting(prs_gov.slides[4], has_subtitle=False)
    apply_slide_header_formatting(prs_gov.slides[5], title_text="The PM owns the plan and the day-to-day work", has_subtitle=False)
    apply_slide_header_formatting(prs_gov.slides[6], has_subtitle=False)
    apply_slide_header_formatting(prs_gov.slides[7], has_subtitle=False)
    apply_slide_header_formatting(prs_gov.slides[8], has_subtitle=False)
    apply_slide_header_formatting(prs_gov.slides[9], has_subtitle=False)
    apply_slide_header_formatting(prs_gov.slides[11], has_subtitle=False)
    apply_slide_header_formatting(prs_gov.slides[12], has_subtitle=False)
    apply_slide_header_formatting(prs_gov.slides[13])
    apply_slide_header_formatting(prs_gov.slides[15 + total_s14_pages + total_s15_pages])  # Slide 18 Approach
    apply_slide_header_formatting(prs_gov.slides[16 + total_s14_pages + total_s15_pages])  # Slide 19 Risk Register
    apply_slide_header_formatting(prs_gov.slides[17 + total_s14_pages + total_s15_pages])  # Slide 20 Next Steps

    # Populate slides:
    # Slide 1 (index 0)
    write_slide1(prs_gov.slides[0], model)

    # Slide 11 (index 10): Change Decision Matrix (HTL-109)
    write_slide11_change_decision_matrix(prs_gov.slides[10], model)

    # Slide 14 (index 13): Why We're Here (Client Slide 5)
    write_slide5(prs_gov.slides[13], client_deck_adapter)

    # Slide 15 pages (starting at index 14): What We Deliver (HTL-100)
    for c_idx, chunk_ws in enumerate(chunks_s14):
        write_slide6_deliverables_page(
            prs_gov.slides[14 + c_idx],
            chunk_ws,
            client_deck_adapter,
            page_num=c_idx + 1,
            total_pages=total_s14_pages,
        )

    # Slide 16 pages (starting at index 14 + total_s14_pages): Acceptance Criteria Table (HTL-72 / HTL-88 / HTL-89)
    for c_idx, chunk_rows in enumerate(chunks_s15):
        write_slide15_acceptance_criteria_page(
            prs_gov.slides[14 + total_s14_pages + c_idx],
            chunk_rows,
            page_num=c_idx + 1,
            total_pages=total_s15_pages,
        )

    # Slide 17: How Milestone Acceptance Works Narrative (HTL-72 / HTL-88)
    write_slide16_acceptance_narrative(prs_gov.slides[14 + total_s14_pages + total_s15_pages], model)

    # Slide 18: Approach 3-Card Layout (HTL-72 / HTL-88)
    write_slide17_approach(prs_gov.slides[15 + total_s14_pages + total_s15_pages], model)

    # Slide 19: Initial Risk Register (Client Slide 12)
    write_slide12(prs_gov.slides[16 + total_s14_pages + total_s15_pages], client_deck_adapter)

    # Slide 20: Next Steps (Client Slide 15)
    write_slide15(prs_gov.slides[17 + total_s14_pages + total_s15_pages], client_deck_adapter)

    # Ensure any remaining template shapes with legacy #041133 are sanitized to canonical #0F256E (HTL-103)
    for slide in prs_gov.slides:
        for shape in slide.shapes:
            for clr in shape._element.iter():
                val = clr.attrib.get("val")
                if val and val.upper() == "041133":
                    clr.attrib["val"] = "0F256E"

    target_path.parent.mkdir(parents=True, exist_ok=True)
    prs_gov.save(str(target_path))

    # Write companion trace manifest: {project}_PS_Governance_Kickoff.trace.json
    manifest_path = target_path.with_name(f"{target_path.stem}.trace.json")
    model.manifest.write_json(manifest_path)

    return target_path
