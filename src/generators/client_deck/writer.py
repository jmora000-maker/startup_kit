"""PPTX Presentation writer and dynamic shape tree engine for Client Kickoff Deck (OUT-14)."""

import copy
import re
from pathlib import Path
from typing import List, Optional, Tuple
import pptx
from pptx.util import Length, Pt
from pptx.dml.color import RGBColor

from src.config import CLIENT_DECK_TEMPLATE_PATH
from src.generators.client_deck.fit import (
    estimate_text_height,
    fit_deliverables_for_block,
    select_fitting_font_size,
    truncate_at_clause,
)
from src.generators.client_deck.spec import ClientDeckModel, WorkstreamBlock


def _set_run_text_preserve_font(run, new_text: str) -> None:
    """Set run text while preserving font properties."""
    font = run.font
    f_name = font.name
    f_size = font.size
    f_bold = font.bold
    f_italic = font.italic
    f_color = font.color.rgb if font.color and font.color.type == 1 else None

    run.text = new_text

    if f_name:
        font.name = f_name
    if f_size:
        font.size = f_size
    if f_bold is not None:
        font.bold = f_bold
    if f_italic is not None:
        font.italic = f_italic
    if f_color:
        font.color.rgb = f_color


def _replace_shape_text(
    shape,
    new_text: str,
    default_font_size: Optional[Pt] = None,
    font_color_rgb: Optional[RGBColor] = None,
) -> None:
    """Replace all text in a shape text frame preserving the original formatting style."""
    if not shape.has_text_frame:
        return
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.margin_left = 0
    tf.margin_right = 0
    for bpr in shape._element.xpath(".//a:bodyPr"):
        bpr.set("anchor", "t")

    if not tf.paragraphs:
        p = tf.add_paragraph()
        p.text = new_text
        return

    first_p = tf.paragraphs[0]
    font_name = first_p.runs[0].font.name if first_p.runs and first_p.runs[0].font.name else "Proxima Nova"
    font_size = (
        default_font_size
        if default_font_size is not None
        else (first_p.runs[0].font.size if first_p.runs and first_p.runs[0].font.size else Pt(11))
    )
    bold = first_p.runs[0].font.bold if first_p.runs else None

    # Clear paragraphs
    # Keep only the first paragraph
    for p in list(tf.paragraphs[1:]):
        tf._txBody.remove(p._p)

    first_p.text = new_text
    if first_p.runs:
        first_p.runs[0].font.name = font_name
        first_p.runs[0].font.size = font_size
        if bold is not None:
            first_p.runs[0].font.bold = bold
        if font_color_rgb is not None:
            first_p.runs[0].font.color.rgb = font_color_rgb


def _format_table_cell(
    cell,
    text: str,
    font_size_pt: float,
    bold: bool = False,
    color_rgb: Optional[RGBColor] = None,
) -> None:
    """Format table cell with Proxima Nova font styling, top alignment, and zero cell margins."""
    cell.text = text
    tf = cell.text_frame
    tf.word_wrap = True
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.margin_left = 0
    tf.margin_right = 0
    for bpr in cell._tc.xpath(".//a:tcPr"):
        bpr.set("anchor", "t")
    for p in tf.paragraphs:
        for run in p.runs:
            run.font.name = "Proxima Nova"
            run.font.size = Pt(font_size_pt)
            if bold:
                run.font.bold = True
            if color_rgb:
                run.font.color.rgb = color_rgb


def write_slide1(slide, model: ClientDeckModel) -> None:
    """Populate Slide 1 [Client Name] and [Project Name] placeholders with deterministic text-fitting (HTL-49)."""
    candidate_sizes = [28.0, 24.0, 22.0, 20.0, 18.0, 16.0, 14.0]
    client_name = model.slide1.client_name or "Client"
    project_name = model.slide1.project_name or "Project Baseline"

    # Composite text for title line-wrapping and height estimation
    composite_title = f"{client_name}\n{project_name} Kickoff"

    # Available geometry on Slide 1:
    # Title box top = 2.97 in (2,712,227 EMUs), Subtitle box top = 4.54 in (4,153,150 EMUs).
    # Total distance between title top and subtitle top is 1.576 in.
    # Leaving an explicit 0.15 in visual separation buffer above the subtitle yields max_height_in = 1.42 in.
    title_sz, _ = select_fitting_font_size(
        composite_title,
        width_in=3.30,
        max_height_in=1.42,
        candidate_sizes=candidate_sizes,
        is_bold=True,
    )

    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        text = shape.text_frame.text
        if "[Client Name]" in text or "[Project Name]" in text or shape.shape_id == 92:
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

            # Populate text and apply explicit font size to runs
            for p in tf.paragraphs:
                for r in p.runs:
                    if "[Client Name]" in r.text:
                        r.text = r.text.replace("[Client Name]", client_name)
                    if "[Project Name]" in r.text:
                        r.text = r.text.replace("[Project Name]", project_name)
                    r.font.name = "Proxima Nova"
                    r.font.size = Pt(title_sz)
                    r.font.bold = True


def write_slide5(slide, model: ClientDeckModel) -> None:
    """Populate Slide 5 (Why We're Here) with uniform font scaling across all three cards, strict 3-line bounding on Card 2, and top anchoring (HTL-48 / HTL-52 / HTL-54)."""
    candidate_sizes = [11.0, 10.5, 10.0, 9.5, 9.0, 8.5, 8.0]

    # Card 2 (Problem Statement): max height is 0.40 in (~28.8 pt / max 3 lines at 8.0pt)
    prob_raw = model.slide5.what_problem_are_we_solving
    if estimate_text_height(prob_raw, width_in=7.75, size_pt=8.0) > 0.40 * 72.0:
        prob_raw = truncate_at_clause(prob_raw, max_chars=220, suffix="...")
        while estimate_text_height(prob_raw, width_in=7.75, size_pt=8.0) > 0.40 * 72.0 and len(prob_raw) > 30:
            prob_raw = truncate_at_clause(prob_raw[:-4], max_chars=len(prob_raw) - 20, suffix="...")

    # Pass 1: Compute fitting font sizes across all three cards (HTL-52 / HTL-54)
    sz_why, fitted_why = select_fitting_font_size(
        model.slide5.why_are_we_doing_this,
        width_in=7.75,
        max_height_in=0.40,
        candidate_sizes=candidate_sizes,
    )
    sz_prob, fitted_prob = select_fitting_font_size(
        prob_raw,
        width_in=7.75,
        max_height_in=0.40,
        candidate_sizes=candidate_sizes,
    )
    sz_succ, fitted_succ = select_fitting_font_size(
        model.slide5.what_does_success_look_like,
        width_in=7.75,
        max_height_in=0.40,
        candidate_sizes=candidate_sizes,
    )
    uniform_sz = min(sz_why, sz_prob, sz_succ)

    # Re-fit texts at uniform_sz if needed to ensure no overflow
    if estimate_text_height(fitted_prob, width_in=7.75, size_pt=uniform_sz) > 0.40 * 72.0:
        fitted_prob = truncate_at_clause(fitted_prob, max_chars=200, suffix="...")
        while estimate_text_height(fitted_prob, width_in=7.75, size_pt=uniform_sz) > 0.40 * 72.0 and len(fitted_prob) > 30:
            fitted_prob = truncate_at_clause(fitted_prob[:-4], max_chars=len(fitted_prob) - 20, suffix="...")

    # Pass 2: Render cards with uniform font size
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        text = shape.text_frame.text

        # Enforce top-anchored alignment and zero top margin for all cards
        for bpr in shape._element.xpath(".//a:bodyPr"):
            bpr.set("anchor", "t")
        shape.text_frame.margin_top = 0
        shape.text_frame.word_wrap = True

        if "[Pre-filled: the business initiative" in text or shape.shape_id == 176:
            _replace_shape_text(shape, fitted_why, Pt(uniform_sz))
        elif "[Pre-filled: the current pain point" in text or shape.shape_id == 180:
            _replace_shape_text(shape, fitted_prob, Pt(uniform_sz))
        elif "[Pre-filled: the desired business outcomes" in text or shape.shape_id == 184:
            _replace_shape_text(shape, fitted_succ, Pt(uniform_sz))


def _set_header_paragraph_format(p, font_size_pt: float, text: str) -> None:
    """Apply top-aligned header formatting with Proxima Nova Semibold and matching baseline spacing."""
    from lxml import etree

    p_elem = p._p
    for child in list(p_elem):
        p_elem.remove(child)

    sz_val = str(int(font_size_pt * 100))
    ns_a = "http://schemas.openxmlformats.org/drawingml/2006/main"
    pPr = etree.SubElement(p_elem, f"{{{ns_a}}}pPr", {
        "indent": "0",
        "marL": "0",
        "rtl": "0",
        "algn": "l",
    })

    lnSpc = etree.SubElement(pPr, f"{{{ns_a}}}lnSpc")
    etree.SubElement(lnSpc, f"{{{ns_a}}}spcPct", {"val": "110000"})

    spcBef = etree.SubElement(pPr, f"{{{ns_a}}}spcBef")
    etree.SubElement(spcBef, f"{{{ns_a}}}spcPts", {"val": "100" if font_size_pt < 9.0 else "150"})

    spcAft = etree.SubElement(pPr, f"{{{ns_a}}}spcAft")
    etree.SubElement(spcAft, f"{{{ns_a}}}spcPts", {"val": "0"})

    etree.SubElement(pPr, f"{{{ns_a}}}buNone")

    r = etree.SubElement(p_elem, f"{{{ns_a}}}r")
    rPr = etree.SubElement(r, f"{{{ns_a}}}rPr", {
        "lang": "en",
        "sz": sz_val,
        "b": "1",
    })
    solidFill = etree.SubElement(rPr, f"{{{ns_a}}}solidFill")
    etree.SubElement(solidFill, f"{{{ns_a}}}srgbClr", {"val": "041133"})
    etree.SubElement(rPr, f"{{{ns_a}}}latin", {"typeface": "Proxima Nova Semibold"})
    etree.SubElement(rPr, f"{{{ns_a}}}ea", {"typeface": "Proxima Nova Semibold"})
    etree.SubElement(rPr, f"{{{ns_a}}}cs", {"typeface": "Proxima Nova Semibold"})
    etree.SubElement(rPr, f"{{{ns_a}}}sym", {"typeface": "Proxima Nova Semibold"})

    t = etree.SubElement(r, f"{{{ns_a}}}t")
    t.text = text

    endRPr = etree.SubElement(p_elem, f"{{{ns_a}}}endParaRPr", {"sz": sz_val, "b": "1"})
    solidFill_end = etree.SubElement(endRPr, f"{{{ns_a}}}solidFill")
    etree.SubElement(solidFill_end, f"{{{ns_a}}}srgbClr", {"val": "041133"})
    etree.SubElement(endRPr, f"{{{ns_a}}}latin", {"typeface": "Proxima Nova Semibold"})


def _set_paragraph_bullet_format(p, font_size_pt: float, text: str, is_overflow: bool = False) -> None:
    """Apply native PPTX bullet point formatting and Proxima Nova font styling to a paragraph."""
    from lxml import etree

    clean_text = text.strip()
    if clean_text.startswith("•") or clean_text.startswith("●"):
        clean_text = clean_text[1:].strip()

    # Clear existing p children
    p_elem = p._p
    for child in list(p_elem):
        p_elem.remove(child)

    sz_val = str(int(font_size_pt * 100))

    # Construct pPr with native bullet
    ns_a = "http://schemas.openxmlformats.org/drawingml/2006/main"
    pPr = etree.SubElement(p_elem, f"{{{ns_a}}}pPr", {
        "indent": "-180000",
        "marL": "240000",
        "rtl": "0",
        "algn": "l",
    })

    # Line spacing and space before
    lnSpc = etree.SubElement(pPr, f"{{{ns_a}}}lnSpc")
    etree.SubElement(lnSpc, f"{{{ns_a}}}spcPct", {"val": "110000"})

    spcBef = etree.SubElement(pPr, f"{{{ns_a}}}spcBef")
    etree.SubElement(spcBef, f"{{{ns_a}}}spcPts", {"val": "100" if font_size_pt < 9.0 else "150"})

    spcAft = etree.SubElement(pPr, f"{{{ns_a}}}spcAft")
    etree.SubElement(spcAft, f"{{{ns_a}}}spcPts", {"val": "0"})

    # Bullet formatting
    buClr = etree.SubElement(pPr, f"{{{ns_a}}}buClr")
    etree.SubElement(buClr, f"{{{ns_a}}}srgbClr", {"val": "444746"})

    etree.SubElement(pPr, f"{{{ns_a}}}buSzPts", {"val": sz_val})
    etree.SubElement(pPr, f"{{{ns_a}}}buFont", {"typeface": "Proxima Nova"})
    etree.SubElement(pPr, f"{{{ns_a}}}buChar", {"char": "●"})

    # Run element
    r = etree.SubElement(p_elem, f"{{{ns_a}}}r")
    rPr = etree.SubElement(r, f"{{{ns_a}}}rPr", {
        "lang": "en",
        "sz": sz_val,
        "i": "1" if is_overflow else "0",
    })
    solidFill = etree.SubElement(rPr, f"{{{ns_a}}}solidFill")
    etree.SubElement(solidFill, f"{{{ns_a}}}srgbClr", {"val": "5F6368" if is_overflow else "444746"})
    etree.SubElement(rPr, f"{{{ns_a}}}latin", {"typeface": "Proxima Nova"})
    etree.SubElement(rPr, f"{{{ns_a}}}ea", {"typeface": "Proxima Nova"})
    etree.SubElement(rPr, f"{{{ns_a}}}cs", {"typeface": "Proxima Nova"})
    etree.SubElement(rPr, f"{{{ns_a}}}sym", {"typeface": "Proxima Nova"})

    t = etree.SubElement(r, f"{{{ns_a}}}t")
    t.text = clean_text

    # endParaRPr
    endRPr = etree.SubElement(p_elem, f"{{{ns_a}}}endParaRPr", {"sz": sz_val})
    solidFill_end = etree.SubElement(endRPr, f"{{{ns_a}}}solidFill")
    etree.SubElement(solidFill_end, f"{{{ns_a}}}srgbClr", {"val": "444746"})
    etree.SubElement(endRPr, f"{{{ns_a}}}latin", {"typeface": "Proxima Nova"})


def _populate_deliverables_box(shape, deliverables: List[str], font_size: Pt, overflow_count: int = 0) -> None:
    """Populate bulleted deliverables in a deliverable text box with consistent native PPTX bullets."""
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.margin_left = 0
    tf.margin_right = 0

    # Clear extra paragraphs
    for p in list(tf.paragraphs[1:]):
        tf._txBody.remove(p._p)

    # Collect items to display
    items_to_display: List[Tuple[str, bool]] = []
    for d_text in deliverables:
        is_ovf = d_text.strip().startswith("+") and ("more:" in d_text or "additional deliverables" in d_text or "Project Delivery Workbook" in d_text)
        items_to_display.append((d_text, is_ovf))

    if not items_to_display:
        p_elem = tf.paragraphs[0]._p
        for child in list(p_elem):
            p_elem.remove(child)
        return

    font_pt = float(font_size.pt)

    for idx, (item_text, is_ovf) in enumerate(items_to_display):
        if idx == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        _set_paragraph_bullet_format(p, font_pt, item_text, is_overflow=is_ovf)


def write_slide6(slide, model: ClientDeckModel) -> None:
    """Populate Slide 6 and dynamically manipulate XML shape tree for N workstreams (HTL-61)."""
    white_color = RGBColor(255, 255, 255)

    # 1. Solution Overview & Out of Scope: uniform font sizing across both text boxes (HTL-61)
    candidate_sizes = [10.0, 9.5, 9.0, 8.5, 8.0]
    sz_so, so_text = select_fitting_font_size(
        model.slide6.solution_overview,
        width_in=2.84,
        max_height_in=2.20,
        candidate_sizes=candidate_sizes,
    )
    total_oos_text = "\n".join([f"• {item}" for item in model.slide6.out_of_scope])
    sz_oos, _ = select_fitting_font_size(
        total_oos_text,
        width_in=2.84,
        max_height_in=0.75,
        candidate_sizes=candidate_sizes,
    )
    uniform_panel_sz = min(sz_so, sz_oos)
    if uniform_panel_sz < sz_so:
        _, so_text = select_fitting_font_size(
            model.slide6.solution_overview,
            width_in=2.84,
            max_height_in=2.20,
            candidate_sizes=[uniform_panel_sz],
        )

    for shape in list(slide.shapes):
        if not shape.has_text_frame:
            continue
        text = shape.text_frame.text
        if shape.shape_id == 193 or (shape.has_text_frame and "Solution Overview" in text):
            # Strip placeholder attribute so renderer treats it as a standard top-anchored textbox
            for ph in shape._element.xpath(".//p:ph"):
                ph.getparent().remove(ph)
            shape.top = 580000
            shape.left = 6347125
            shape.width = 2600000
            shape.height = 420000
            tf = shape.text_frame
            tf.margin_top = 0
            tf.margin_bottom = 0
            tf.margin_left = 0
            tf.margin_right = 0
            _replace_shape_text(shape, "Solution Overview", Pt(16), font_color_rgb=white_color)
            if tf.paragraphs and tf.paragraphs[0].runs:
                tf.paragraphs[0].runs[0].font.bold = True
                tf.paragraphs[0].runs[0].font.name = "Proxima Nova"
                tf.paragraphs[0].runs[0].font.color.rgb = white_color
        elif shape.shape_id == 194 or "[high level summary of the work" in text:
            for ph in shape._element.xpath(".//p:ph"):
                ph.getparent().remove(ph)
            shape.top = 1150000
            shape.left = 6347125
            shape.width = 2600000
            shape.height = 2500000
            tf = shape.text_frame
            tf.margin_top = 0
            tf.margin_bottom = 0
            tf.margin_left = 0
            tf.margin_right = 0
            _replace_shape_text(shape, so_text, Pt(uniform_panel_sz), font_color_rgb=white_color)
            if tf.paragraphs and tf.paragraphs[0].runs:
                tf.paragraphs[0].runs[0].font.color.rgb = white_color
        elif shape.shape_id == 202 or "Out of Scope:" in text:
            shape.top = 3800000
            shape.left = 6347125
            shape.width = 2600000
            shape.height = 850000
            tf = shape.text_frame
            tf.margin_top = 0
            tf.margin_bottom = 0
            tf.margin_left = 0
            tf.margin_right = 0
            for p in list(tf.paragraphs[1:]):
                tf._txBody.remove(p._p)
            tf.paragraphs[0].text = "Out of Scope:"
            if tf.paragraphs[0].runs:
                tf.paragraphs[0].runs[0].font.name = "Proxima Nova"
                tf.paragraphs[0].runs[0].font.size = Pt(11)
                tf.paragraphs[0].runs[0].font.bold = True
                tf.paragraphs[0].runs[0].font.color.rgb = white_color

            for item in model.slide6.out_of_scope:
                p = tf.add_paragraph()
                p.text = f"• {item}"
                if p.runs:
                    p.runs[0].font.name = "Proxima Nova"
                    p.runs[0].font.size = Pt(uniform_panel_sz)
                    p.runs[0].font.color.rgb = white_color

    # 2. Dynamic Workstreams
    workstreams = model.slide6.workstreams
    n_ws = max(1, len(workstreams))

    # Pre-identified template shapes
    header_ids = [217, 207, 209, 211]
    deliv_ids = [205, 206, 208, 210]
    line_ids = [196, 195, 197, 198, 199]

    # Map shape IDs to shapes
    shapes_by_id = {s.shape_id: s for s in slide.shapes}

    template_headers = [shapes_by_id.get(hid) for hid in header_ids if hid in shapes_by_id]
    template_delivs = [shapes_by_id.get(did) for did in deliv_ids if did in shapes_by_id]
    template_lines = [shapes_by_id.get(lid) for lid in line_ids if lid in shapes_by_id]

    # Clean duplicate redundant lines (IDs 212-216)
    for dup_lid in [212, 213, 214, 215, 216]:
        dup_s = shapes_by_id.get(dup_lid)
        if dup_s is not None and dup_s._element in slide.shapes._spTree:
            slide.shapes._spTree.remove(dup_s._element)

    # Bounds
    y_start = 1534864
    y_end = 4873114
    total_h = y_end - y_start
    slot_h = int(total_h / n_ws)

    # Geometry & Typography according to workstream count N
    if n_ws <= 2:
        h_font_size = Pt(11.0)
        d_font_size = Pt(10.5)
        top_offset = int(slot_h * 0.08)
        bottom_margin = int(slot_h * 0.10)
    elif n_ws == 3:
        h_font_size = Pt(10.5)
        d_font_size = Pt(10.0)
        top_offset = int(slot_h * 0.06)
        bottom_margin = int(slot_h * 0.09)
    elif n_ws == 4:
        h_font_size = Pt(10.0)
        d_font_size = Pt(9.5)
        top_offset = int(slot_h * 0.05)
        bottom_margin = int(slot_h * 0.08)
    elif n_ws == 5:
        h_font_size = Pt(9.0)
        d_font_size = Pt(8.5)
        top_offset = int(slot_h * 0.04)
        bottom_margin = int(slot_h * 0.07)
    else:  # n_ws >= 6
        h_font_size = Pt(8.0)
        d_font_size = Pt(7.5)
        top_offset = int(slot_h * 0.03)
        bottom_margin = int(slot_h * 0.06)

    # Get max current shape ID in tree
    max_sp_id = max([int(el.get("id", "0")) for el in slide.shapes._spTree.xpath(".//p:cNvPr")] + [500])

    item_height = max(100000, slot_h - top_offset - bottom_margin)
    deliv_max_h = item_height / 914400.0
    header_max_h = min(0.45 * slot_h / 914400.0, deliv_max_h)

    h_candidate_sizes = [s for s in [11.0, 10.5, 10.0, 9.5, 9.0, 8.5, 8.0] if s <= float(h_font_size.pt)]
    if not h_candidate_sizes:
        h_candidate_sizes = [float(h_font_size.pt)]

    d_candidate_sizes = [s for s in [10.5, 10.0, 9.5, 9.0, 8.5, 8.0, 7.5] if s <= float(d_font_size.pt)]
    if not d_candidate_sizes:
        d_candidate_sizes = [float(d_font_size.pt)]

    # Pass 1: Compute uniform column font sizes across all blocks (HTL-49 / HTL-50)
    header_sizes = []
    processed_titles = []

    for ws in workstreams:
        ws_title_raw = ws.title
        if estimate_text_height(ws_title_raw, width_in=2.15, size_pt=8.0) > header_max_h * 72.0:
            ws_title_raw = truncate_at_clause(ws_title_raw, max_chars=80, suffix="...")
        processed_titles.append(ws_title_raw)
        h_pt, _ = select_fitting_font_size(ws_title_raw, width_in=2.15, max_height_in=header_max_h, candidate_sizes=h_candidate_sizes)
        header_sizes.append(h_pt)

    # Deliverables column font size: check candidate sizes from highest to lowest (10.5 down to 8.0)
    col_deliv_font_pt = d_candidate_sizes[-1]
    for sz in d_candidate_sizes:
        all_blocks_fit = True
        for ws in workstreams:
            if ws.deliverables:
                cand_items, ovf = fit_deliverables_for_block(ws.deliverables, width_in=3.00, max_height_in=deliv_max_h, font_size_pt=sz)
                if ovf > 0 or len(cand_items) != len([d for d in ws.deliverables if d and d.strip()]):
                    all_blocks_fit = False
                    break
        if all_blocks_fit:
            col_deliv_font_pt = sz
            break

    col_header_font_pt = min(header_sizes) if header_sizes else float(h_font_size.pt)

    # Pass 2: Render workstream blocks using uniform column font sizes
    for i in range(n_ws):
        if i < len(template_headers):
            h_shape = template_headers[i]
            d_shape = template_delivs[i]
        else:
            # Clone from Block 1
            max_sp_id += 1
            h_elem = copy.deepcopy(template_headers[0]._element)
            h_elem.xpath(".//p:cNvPr")[0].set("id", str(max_sp_id))
            h_elem.xpath(".//p:cNvPr")[0].set("name", f"Google Shape;{max_sp_id};p25")
            slide.shapes._spTree.append(h_elem)
            h_shape = slide.shapes[-1]

            max_sp_id += 1
            d_elem = copy.deepcopy(template_delivs[0]._element)
            d_elem.xpath(".//p:cNvPr")[0].set("id", str(max_sp_id))
            d_elem.xpath(".//p:cNvPr")[0].set("name", f"Google Shape;{max_sp_id};p25")
            slide.shapes._spTree.append(d_elem)
            d_shape = slide.shapes[-1]

        slot_top = y_start + i * slot_h
        item_top = slot_top + top_offset

        # Position Header (Column 1 - Left)
        h_shape.left = 502750
        h_shape.width = 2150000
        h_shape.top = item_top
        h_shape.height = item_height

        for bpr in h_shape._element.xpath(".//a:bodyPr"):
            bpr.set("anchor", "t")

        tf_h = h_shape.text_frame
        tf_h.word_wrap = True
        tf_h.margin_top = 0
        tf_h.margin_bottom = 0
        tf_h.margin_left = 0
        tf_h.margin_right = 0

        for p in list(tf_h.paragraphs[1:]):
            tf_h._txBody.remove(p._p)

        ws = workstreams[i]
        ws_title_final = processed_titles[i] if i < len(processed_titles) else ws.title
        _set_header_paragraph_format(tf_h.paragraphs[0], col_header_font_pt, ws_title_final)

        # Position Deliverables (Column 2 - Right)
        d_shape.left = 2726700
        d_shape.width = 3000000
        d_shape.top = item_top
        d_shape.height = item_height

        for bpr in d_shape._element.xpath(".//a:bodyPr"):
            bpr.set("anchor", "t")

        fitted_delivs, ovf_count = fit_deliverables_for_block(
            ws.deliverables,
            width_in=3.00,
            max_height_in=deliv_max_h,
            font_size_pt=col_deliv_font_pt,
        )

        _populate_deliverables_box(
            d_shape,
            fitted_delivs,
            Pt(col_deliv_font_pt),
            overflow_count=ovf_count,
        )

    # Remove surplus template shapes if N < 4
    if n_ws < len(template_headers):
        for surplus_h in template_headers[n_ws:]:
            if surplus_h and surplus_h._element in slide.shapes._spTree:
                slide.shapes._spTree.remove(surplus_h._element)
        for surplus_d in template_delivs[n_ws:]:
            if surplus_d and surplus_d._element in slide.shapes._spTree:
                slide.shapes._spTree.remove(surplus_d._element)

    # Position divider lines
    for i in range(n_ws + 1):
        line_y = y_start + i * slot_h
        if i < len(template_lines):
            line_shape = template_lines[i]
            line_shape.left = 503325
            line_shape.width = 5218500
            line_shape.top = line_y
        else:
            # Clone line
            max_sp_id += 1
            line_elem = copy.deepcopy(template_lines[0]._element)
            line_elem.xpath(".//p:cNvPr")[0].set("id", str(max_sp_id))
            line_elem.xpath(".//p:cNvPr")[0].set("name", f"Google Shape;{max_sp_id};p25")
            slide.shapes._spTree.append(line_elem)
            line_shape = slide.shapes[-1]
            line_shape.left = 503325
            line_shape.width = 5218500
            line_shape.top = line_y

    # Remove surplus lines if n_ws + 1 < len(template_lines)
    if n_ws + 1 < len(template_lines):
        for surplus_l in template_lines[n_ws + 1 :]:
            if surplus_l and surplus_l._element in slide.shapes._spTree:
                slide.shapes._spTree.remove(surplus_l._element)


def write_slide12(slide, model: ClientDeckModel) -> None:
    """Populate Slide 12 Initial Risk Register table with true table-wide uniform font sizing and row-bounding (HTL-48 / HTL-52 / HTL-54)."""
    table_shape = None
    for shape in slide.shapes:
        if shape.has_table:
            table_shape = shape
            break

    if not table_shape:
        return

    table = table_shape.table
    risks = model.slide12.risks
    num_risks = len(risks)
    rendered_risks = risks[: min(num_risks, 3)]

    cell_candidate_sizes = [10.0, 9.5, 9.0, 8.5, 8.0]

    # Pass 1: Compute fitting font sizes across all rendered rows and cells (HTL-54)
    desc_sizes = []
    desc_texts = []
    mitigation_sizes = []
    mitigation_texts = []

    for risk in rendered_risks:
        # Col 0: Risk Description (width ~2.2 in, max height 0.85 in)
        desc_raw = risk.description
        if estimate_text_height(desc_raw, width_in=2.2, size_pt=8.0) > 0.85 * 72.0:
            desc_raw = truncate_at_clause(desc_raw, max_chars=140, suffix="...")
        sz0, desc_text = select_fitting_font_size(
            desc_raw,
            width_in=2.2,
            max_height_in=0.85,
            candidate_sizes=cell_candidate_sizes,
        )
        desc_sizes.append(sz0)
        desc_texts.append(desc_text)

        # Col 2: Mitigation (width ~3.7 in, max height 0.85 in)
        mitigation_raw = risk.mitigation
        if estimate_text_height(mitigation_raw, width_in=3.7, size_pt=8.0) > 0.85 * 72.0:
            mitigation_raw = truncate_at_clause(mitigation_raw, max_chars=180, suffix="... (see RAID Log)")
        sz2, mitigation_text = select_fitting_font_size(
            mitigation_raw,
            width_in=3.7,
            max_height_in=0.85,
            candidate_sizes=cell_candidate_sizes,
        )
        mitigation_sizes.append(sz2)
        mitigation_texts.append(mitigation_text)

    all_sizes = desc_sizes + mitigation_sizes + [9.5]
    table_font_sz = min(all_sizes) if all_sizes else 9.5

    # Pass 2: Populate table rows with true table-wide uniform font size across all cells
    for i, risk in enumerate(rendered_risks):
        row = table.rows[i + 1]
        _format_table_cell(row.cells[0], desc_texts[i], table_font_sz)
        _format_table_cell(row.cells[1], risk.prob_impact, table_font_sz)
        _format_table_cell(row.cells[2], mitigation_texts[i], table_font_sz)
        _format_table_cell(row.cells[3], risk.target_date, table_font_sz)

    # If fewer than 3 risks, remove surplus data rows from table XML
    if num_risks < 3:
        surplus_count = 3 - num_risks
        for _ in range(surplus_count):
            tr_elements = table._tbl.xpath("./a:tr")
            if len(tr_elements) > 1:
                table._tbl.remove(tr_elements[-1])


def write_slide15(slide, model: ClientDeckModel) -> None:
    """Populate Slide 15 Next Steps table with true table-wide uniform font sizing and row-bounding (HTL-48 / HTL-54)."""
    table_shape = None
    for shape in slide.shapes:
        if shape.has_table:
            table_shape = shape
            break

    if not table_shape:
        return

    table = table_shape.table
    steps = model.slide15.next_steps
    num_steps = len(steps)

    cell_candidate_sizes = [10.0, 9.5, 9.0, 8.5, 8.0]

    # Pass 1: Compute fitting font sizes across all action items (HTL-54)
    action_sizes = []
    action_texts = []
    for step in steps:
        action_raw = step.action
        if estimate_text_height(action_raw, width_in=5.2, size_pt=8.0) > 0.75 * 72.0:
            action_raw = truncate_at_clause(action_raw, max_chars=200, suffix="... (see Startup Kit)")
        sz1, action_text = select_fitting_font_size(
            action_raw,
            width_in=5.2,
            max_height_in=0.75,
            candidate_sizes=cell_candidate_sizes,
        )
        action_sizes.append(sz1)
        action_texts.append(action_text)

    all_sizes = action_sizes + [9.5]
    table_font_sz = min(all_sizes) if all_sizes else 9.5

    # Pass 2: Populate table rows with true table-wide uniform font size across all cells
    for i in range(num_steps):
        step = steps[i]
        if i + 1 < len(table.rows):
            row = table.rows[i + 1]
        else:
            # Clone last row element
            tr_elements = table._tbl.xpath("./a:tr")
            tr_elem = copy.deepcopy(tr_elements[-1])
            table._tbl.append(tr_elem)
            row = table.rows[len(table.rows) - 1]

        _format_table_cell(row.cells[0], step.owner, table_font_sz)
        _format_table_cell(row.cells[1], action_texts[i], table_font_sz)
        _format_table_cell(row.cells[2], "TBD", table_font_sz)

    # If fewer than 3 steps, remove surplus data rows
    if num_steps < 3:
        surplus_count = 3 - num_steps
        for _ in range(surplus_count):
            tr_elements = table._tbl.xpath("./a:tr")
            if len(tr_elements) > 1:
                table._tbl.remove(tr_elements[-1])


def write_client_deck(
    model: ClientDeckModel,
    target_path: Path,
    template_path: Optional[Path] = None,
) -> Path:
    """Load template presentation, populate slides, and save output file."""
    src_template = template_path or CLIENT_DECK_TEMPLATE_PATH
    if not src_template.exists():
        raise FileNotFoundError(f"Client Deck template not found at {src_template}")

    prs = pptx.Presentation(str(src_template))

    # Populate slides 1, 5, 6, 12, 15 (0-indexed: 0, 4, 5, 11, 14)
    write_slide1(prs.slides[0], model)
    write_slide5(prs.slides[4], model)
    write_slide6(prs.slides[5], model)
    write_slide12(prs.slides[11], model)
    write_slide15(prs.slides[14], model)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(target_path))

    # Write companion trace manifest
    manifest_path = target_path.with_name(f"{target_path.stem}.trace.json")
    model.manifest.write_json(manifest_path)

    return target_path
