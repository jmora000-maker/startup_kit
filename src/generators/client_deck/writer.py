"""PPTX Presentation writer and dynamic shape tree engine for Client Kickoff Deck (OUT-14)."""

import copy
import re
from pathlib import Path
from typing import List, Optional, Tuple
from lxml import etree
import pptx
from pptx.util import Length, Pt
from pptx.dml.color import RGBColor

from src.config import CLIENT_DECK_TEMPLATE_PATH
from src.generators.deck_header import apply_slide_header_formatting
from src.generators.client_deck.fit import (
    condense_problem_statement,
    condense_solution_overview,
    condense_why_are_we_doing_this,
    estimate_text_height,
    fit_deliverables_for_block,
    select_fitting_font_size,
    truncate_at_clause,
    wrap_lines,
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
    font_name: str = "Proxima Nova",
) -> None:
    """Replace all text in a shape text frame ensuring Proxima Nova font styling."""
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
        r = p.add_run()
        r.text = new_text
        r.font.name = font_name
        if default_font_size is not None:
            r.font.size = default_font_size
        return

    first_p = tf.paragraphs[0]
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


def _format_table_header_fill(
    cell,
    fill_hex: str = "0F256E",
    font_name: str = "Proxima Nova",
    font_size_pt: float = 11.0,
    font_color_rgb: RGBColor = RGBColor(0xFF, 0xFF, 0xFF),
    bold: bool = True,
) -> None:
    """Format table header cell with literal RGB background fill (#0F256E) and bold white text (HTL-89 / HTL-103)."""
    tcPr = cell._tc.get_or_add_tcPr()
    for child in list(tcPr):
        if child.tag.endswith("solidFill"):
            tcPr.remove(child)
    ns_a = "http://schemas.openxmlformats.org/drawingml/2006/main"
    solidFill = etree.SubElement(tcPr, f"{{{ns_a}}}solidFill")
    etree.SubElement(solidFill, f"{{{ns_a}}}srgbClr", val=fill_hex)

    tf = cell.text_frame
    for p in tf.paragraphs:
        for r in p.runs:
            r.font.name = font_name
            r.font.size = Pt(font_size_pt)
            r.font.bold = bold
            r.font.color.rgb = font_color_rgb


def write_slide1(slide, model: ClientDeckModel) -> None:
    """Populate Slide 1 [Client Name] and [Project Name] placeholders at flat 24pt (HTL-72 / HTL-85)."""
    title_sz = 24.0
    client_name = model.slide1.client_name or "Client"
    project_name = model.slide1.project_name or "Project Baseline"

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
    """Populate Slide 5 (Why We're Here) with uniform 10pt font scaling across all three cards, strict 3-line bounding on Card 2, and top anchoring (HTL-48 / HTL-52 / HTL-54 / HTL-95 / HTL-109)."""
    candidate_sizes = [10.0, 9.5, 9.0, 8.5, 8.0]

    # Card 1 (Why are we doing this): condensed via LLM / deterministic model to preserve meaning without clipping
    why_raw = condense_why_are_we_doing_this(model.slide5.why_are_we_doing_this)

    # Card 2 (Problem Statement): condensed via LLM / deterministic model to preserve meaning without "..." truncation
    prob_raw = condense_problem_statement(model.slide5.what_problem_are_we_solving)

    # Pass 1: Compute fitting font sizes across all three cards (HTL-52 / HTL-54 / HTL-95)
    sz_why, fitted_why = select_fitting_font_size(
        why_raw,
        width_in=7.75,
        max_height_in=0.46,
        candidate_sizes=candidate_sizes,
        min_font_floor=10.0,
    )
    sz_prob, fitted_prob = select_fitting_font_size(
        prob_raw,
        width_in=7.75,
        max_height_in=0.46,
        candidate_sizes=candidate_sizes,
        min_font_floor=10.0,
    )
    sz_succ, fitted_succ = select_fitting_font_size(
        model.slide5.what_does_success_look_like,
        width_in=7.75,
        max_height_in=0.74,
        candidate_sizes=candidate_sizes,
        min_font_floor=10.0,
    )
    uniform_sz = min(sz_why, sz_prob, sz_succ)

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
    etree.SubElement(solidFill, f"{{{ns_a}}}srgbClr", {"val": "0F256E"})
    etree.SubElement(rPr, f"{{{ns_a}}}latin", {"typeface": "Proxima Nova Semibold"})
    etree.SubElement(rPr, f"{{{ns_a}}}ea", {"typeface": "Proxima Nova Semibold"})
    etree.SubElement(rPr, f"{{{ns_a}}}cs", {"typeface": "Proxima Nova Semibold"})
    etree.SubElement(rPr, f"{{{ns_a}}}sym", {"typeface": "Proxima Nova Semibold"})

    t = etree.SubElement(r, f"{{{ns_a}}}t")
    t.text = text

    endRPr = etree.SubElement(p_elem, f"{{{ns_a}}}endParaRPr", {"sz": sz_val, "b": "1"})
    solidFill_end = etree.SubElement(endRPr, f"{{{ns_a}}}solidFill")
    etree.SubElement(solidFill_end, f"{{{ns_a}}}srgbClr", {"val": "0F256E"})
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


def _set_dark_panel_bullet_format(p, font_size_pt: float, text: str) -> None:
    """Apply native PPTX bullet point formatting with white font styling for dark right-panel boxes (HTL-96)."""
    from lxml import etree

    clean_text = text.strip()
    if clean_text.startswith("•") or clean_text.startswith("●"):
        clean_text = clean_text[1:].strip()

    p_elem = p._p
    for child in list(p_elem):
        p_elem.remove(child)

    sz_val = str(int(font_size_pt * 100))

    ns_a = "http://schemas.openxmlformats.org/drawingml/2006/main"
    pPr = etree.SubElement(p_elem, f"{{{ns_a}}}pPr", {
        "indent": "-180000",
        "marL": "240000",
        "rtl": "0",
        "algn": "l",
    })

    lnSpc = etree.SubElement(pPr, f"{{{ns_a}}}lnSpc")
    etree.SubElement(lnSpc, f"{{{ns_a}}}spcPct", {"val": "110000"})

    spcBef = etree.SubElement(pPr, f"{{{ns_a}}}spcBef")
    etree.SubElement(spcBef, f"{{{ns_a}}}spcPts", {"val": "100" if font_size_pt < 9.0 else "150"})

    spcAft = etree.SubElement(pPr, f"{{{ns_a}}}spcAft")
    etree.SubElement(spcAft, f"{{{ns_a}}}spcPts", {"val": "0"})

    buClr = etree.SubElement(pPr, f"{{{ns_a}}}buClr")
    etree.SubElement(buClr, f"{{{ns_a}}}srgbClr", {"val": "FFFFFF"})

    etree.SubElement(pPr, f"{{{ns_a}}}buSzPts", {"val": sz_val})
    etree.SubElement(pPr, f"{{{ns_a}}}buFont", {"typeface": "Proxima Nova"})
    etree.SubElement(pPr, f"{{{ns_a}}}buChar", {"char": "●"})

    r = etree.SubElement(p_elem, f"{{{ns_a}}}r")
    rPr = etree.SubElement(r, f"{{{ns_a}}}rPr", {
        "lang": "en",
        "sz": sz_val,
    })
    solidFill = etree.SubElement(rPr, f"{{{ns_a}}}solidFill")
    etree.SubElement(solidFill, f"{{{ns_a}}}srgbClr", {"val": "FFFFFF"})
    etree.SubElement(rPr, f"{{{ns_a}}}latin", {"typeface": "Proxima Nova"})
    etree.SubElement(rPr, f"{{{ns_a}}}ea", {"typeface": "Proxima Nova"})
    etree.SubElement(rPr, f"{{{ns_a}}}cs", {"typeface": "Proxima Nova"})
    etree.SubElement(rPr, f"{{{ns_a}}}sym", {"typeface": "Proxima Nova"})

    t = etree.SubElement(r, f"{{{ns_a}}}t")
    t.text = clean_text

    endRPr = etree.SubElement(p_elem, f"{{{ns_a}}}endParaRPr", {"sz": sz_val})
    solidFill_end = etree.SubElement(endRPr, f"{{{ns_a}}}solidFill")
    etree.SubElement(solidFill_end, f"{{{ns_a}}}srgbClr", {"val": "FFFFFF"})
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


def _fit_out_of_scope_items(items: Sequence[str], inner_w_in: float = 2.58, max_h_pt: float = 120.0) -> List[str]:
    """Truncate Out of Scope bullet items at natural clause boundaries so they reliably fit within fixed box height (HTL-96)."""
    if not items:
        return []
    fitted = [it.strip() for it in items if it and it.strip()]

    def _calc_h(cand: List[str]) -> float:
        h = 0.0
        for it in cand:
            lines = wrap_lines(it, width_in=inner_w_in, size_pt=10.0, char_width_factor=0.55)
            h += lines * 10.0 * 1.15 + 1.5
        return h

    if _calc_h(fitted) <= max_h_pt:
        return fitted

    n = max(1, len(fitted))
    target_chars = max(45, int((9.0 / n) * 32))
    fitted = [truncate_at_clause(it, max_chars=target_chars, suffix="...") for it in fitted]

    while _calc_h(fitted) > max_h_pt:
        longest_idx = max(range(len(fitted)), key=lambda i: len(fitted[i]))
        curr = fitted[longest_idx]
        if len(curr) <= 25:
            break
        fitted[longest_idx] = truncate_at_clause(curr[:-4], max_chars=len(curr) - 15, suffix="...")

    return fitted


def chunk_workstreams_for_deliverables_table(
    workstreams: Sequence[WorkstreamBlock],
    max_delivs_per_page: int = 6,
    single_page_threshold: int = 7,
) -> List[List[WorkstreamBlock]]:
    """Chunk workstream blocks into slide pages (HTL-100)."""
    if not workstreams:
        return [[]]
    total_delivs = sum(len(ws.deliverables) for ws in workstreams)
    if total_delivs <= single_page_threshold:
        return [list(workstreams)]

    chunks: List[List[WorkstreamBlock]] = []
    current_chunk: List[WorkstreamBlock] = []
    current_count = 0

    for ws in workstreams:
        ws_count = len(ws.deliverables)
        if current_chunk and (current_count + ws_count > max_delivs_per_page):
            chunks.append(current_chunk)
            current_chunk = [ws]
            current_count = ws_count
        else:
            current_chunk.append(ws)
            current_count += ws_count

    if current_chunk:
        chunks.append(current_chunk)

    return chunks if chunks else [[]]


def _format_table_header_cell(
    cell,
    text: str,
    font_size_pt: float = 9.5,
    bold: bool = True,
    border_hex: str = "D3DCEC",
    fill_hex: str = "0F256E",
) -> None:
    """Format table header cell with dark navy background (#0F256E), white bold text, and D3DCEC borders (HTL-89 / HTL-100 / HTL-103)."""
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
    """Apply solid white fill, subtle gray-blue borders, and standard margins to table data cell (HTL-89 / HTL-100)."""
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


def write_slide6_deliverables_page(
    slide,
    workstreams: List[WorkstreamBlock],
    model: ClientDeckModel,
    page_num: int = 1,
    total_pages: int = 1,
) -> None:
    """Populate one Slide 6 'What we will deliver' page with 2-column navy-header deliverables table on left and dark panel on right (HTL-100)."""
    # 1. Slide Header
    if total_pages > 1:
        sub_text = f"Contracted project deliverables and workstream outcomes mapped to delivery phases (Part {page_num} of {total_pages})."
    else:
        sub_text = "Contracted project deliverables and workstream outcomes mapped to delivery phases."
    k_shape, t_shape, s_shape = apply_slide_header_formatting(
        slide,
        kicker_text="PROJECT SUCCESS AGREEMENT",
        title_text="What we will deliver",
        subtitle_text=sub_text,
    )
    if s_shape is not None:
        s_shape.width = 5240000

    # 2. Identify right dark panel shapes (Solution Overview and Out of Scope) across Client and Governance templates
    so_shape = None
    oos_shape = None

    for shp in slide.shapes:
        if shp._element in (
            k_shape._element if k_shape else None,
            t_shape._element if t_shape else None,
            s_shape._element if s_shape else None,
        ):
            continue
        if shp.has_text_frame:
            txt = shp.text_frame.text
            if ("Solution Overview" in txt or shp.shape_id in (193, 395)) and so_shape is None:
                so_shape = shp
            elif ("Out of Scope" in txt or shp.shape_id in (202, 399)) and oos_shape is None:
                oos_shape = shp

    # 3. Clean up ALL other surplus shapes (legacy divider lines, legacy workstream boxes, template tables, old Rimage/JD Edwards body shape 396, etc.)
    preserved_elements = {
        shp._element
        for shp in (k_shape, t_shape, s_shape, so_shape, oos_shape)
        if shp is not None
    }
    for shp in list(slide.shapes):
        if shp._element not in preserved_elements:
            slide.shapes._spTree.remove(shp._element)

    # 4. Populate Right Dark Panel (Solution Overview & Out of Scope - HTL-96)
    white_color = RGBColor(255, 255, 255)
    so_top = 580000
    so_left = 6347125
    so_width = 2600000
    so_height = 2150000

    oos_top = 2850000
    oos_left = 6347125
    oos_width = 2600000
    oos_height = 1850000

    so_text = condense_solution_overview(model.slide6.solution_overview)

    oos_items = _fit_out_of_scope_items(model.slide6.out_of_scope, inner_w_in=2.58, max_h_pt=120.0)

    # Populate Solution Overview
    if so_shape is None:
        so_shape = slide.shapes.add_textbox(so_left, so_top, so_width, so_height)
    for ph in so_shape._element.xpath(".//p:ph"):
        ph.getparent().remove(ph)
    so_shape.top = so_top
    so_shape.left = so_left
    so_shape.width = so_width
    so_shape.height = so_height
    tf_so = so_shape.text_frame
    tf_so.word_wrap = True
    tf_so.margin_top = 0
    tf_so.margin_bottom = 0
    tf_so.margin_left = 0
    tf_so.margin_right = 0
    for bpr in so_shape._element.xpath(".//a:bodyPr"):
        bpr.set("anchor", "t")

    for p in list(tf_so.paragraphs[1:]):
        tf_so._txBody.remove(p._p)

    p0 = tf_so.paragraphs[0]
    p0.text = "Solution Overview"
    p0.space_before = Pt(0)
    p0.space_after = Pt(5)
    if p0.runs:
        p0.runs[0].font.name = "Proxima Nova"
        p0.runs[0].font.size = Pt(14)  # HTL-96: Fixed 14pt header
        p0.runs[0].font.bold = True
        p0.runs[0].font.color.rgb = white_color

    p1 = tf_so.add_paragraph()
    p1.text = so_text
    p1.space_before = Pt(0)
    p1.space_after = Pt(0)
    if p1.runs:
        p1.runs[0].font.name = "Proxima Nova"
        p1.runs[0].font.size = Pt(10)  # HTL-96: Fixed 10pt body
        p1.runs[0].font.bold = False
        p1.runs[0].font.color.rgb = white_color

    # Populate Out of Scope
    if oos_shape is None:
        oos_shape = slide.shapes.add_textbox(oos_left, oos_top, oos_width, oos_height)
    for ph in oos_shape._element.xpath(".//p:ph"):
        ph.getparent().remove(ph)
    oos_shape.top = oos_top
    oos_shape.left = oos_left
    oos_shape.width = oos_width
    oos_shape.height = oos_height
    tf_oos = oos_shape.text_frame
    tf_oos.word_wrap = True
    tf_oos.margin_top = 0
    tf_oos.margin_bottom = 0
    tf_oos.margin_left = 0
    tf_oos.margin_right = 0
    for bpr in oos_shape._element.xpath(".//a:bodyPr"):
        bpr.set("anchor", "t")

    for p in list(tf_oos.paragraphs[1:]):
        tf_oos._txBody.remove(p._p)

    p0_oos = tf_oos.paragraphs[0]
    p0_oos.text = "Out of Scope:"
    p0_oos.space_before = Pt(0)
    p0_oos.space_after = Pt(5)  # HTL-96: Fixed 14pt header & 5pt space after (63500 EMU)
    if p0_oos.runs:
        p0_oos.runs[0].font.name = "Proxima Nova"
        p0_oos.runs[0].font.size = Pt(14)  # HTL-96: Fixed 14pt header
        p0_oos.runs[0].font.bold = True
        p0_oos.runs[0].font.color.rgb = white_color

    for item in oos_items:
        p = tf_oos.add_paragraph()
        _set_dark_panel_bullet_format(p, 10.0, item)  # HTL-96: Fixed 10pt body

    # 5. Add 2-Column Deliverables Table on Left
    num_rows = len(workstreams)
    table_rows = max(2, num_rows + 1)
    table_left = 480073
    table_top = 1600200
    table_width = 5240000  # Total table width bounded to left column space (~5.73 in)
    table_height = 1828800
    table_shape = slide.shapes.add_table(table_rows, 2, table_left, table_top, table_width, table_height)
    table = table_shape.table

    table.columns[0].width = 2150000  # Workstream / Feature Set: ~2.35 in
    table.columns[1].width = 3090000  # Outcomes / Deliverables: ~3.38 in (2150000 + 3090000 = 5240000)

    # Header Row
    table.rows[0].height = Pt(22)
    _format_table_header_cell(table.cell(0, 0), "Workstream / Feature Set", font_size_pt=9.5, bold=True)
    _format_table_header_cell(table.cell(0, 1), "Outcomes / Deliverables", font_size_pt=9.5, bold=True)

    if not workstreams:
        cell0 = table.rows[1].cells[0]
        table.rows[1].height = Pt(20)
        _format_table_data_cell_styling(cell0)
        _format_table_data_cell_styling(table.rows[1].cells[1])
        _format_table_cell(cell0, "[CONFIRMATION REQUIRED]", font_size_pt=8.0)
        return

    # Data Rows
    for r_idx, ws in enumerate(workstreams):
        row = table.rows[r_idx + 1]
        row.height = Pt(20)

        # Col 0: Workstream / Feature Set
        cell0 = row.cells[0]
        _format_table_data_cell_styling(cell0)
        cell0.text = ""
        tf0 = cell0.text_frame
        tf0.word_wrap = True
        tf0.margin_top = 0
        tf0.margin_bottom = 0
        tf0.margin_left = 0
        tf0.margin_right = 0

        p0 = tf0.paragraphs[0]
        p0.text = ws.title
        if p0.runs:
            p0.runs[0].font.name = "Proxima Nova"
            p0.runs[0].font.size = Pt(8.0)
            p0.runs[0].font.bold = True
            p0.runs[0].font.color.rgb = RGBColor(0x0F, 0x25, 0x6E)

        # Col 1: Outcomes / Deliverables
        cell1 = row.cells[1]
        _format_table_data_cell_styling(cell1)
        cell1.text = ""
        tf1 = cell1.text_frame
        tf1.word_wrap = True
        tf1.margin_top = 0
        tf1.margin_bottom = 0
        tf1.margin_left = 0
        tf1.margin_right = 0

        delivs = ws.deliverables or ["[No deliverables listed]"]
        for d_idx, deliv_str in enumerate(delivs):
            p = tf1.paragraphs[0] if d_idx == 0 else tf1.add_paragraph()
            p.space_before = Pt(0)
            p.space_after = Pt(2)
            p.line_spacing = 1.05

            m_del = re.match(r"^(DEL-\d{2}[:\s]?)(.*)$", deliv_str.strip())
            if m_del:
                del_id = m_del.group(1).rstrip(": ") + ": "
                del_desc = m_del.group(2).strip()

                r_bullet = p.add_run()
                r_bullet.text = "• "
                r_bullet.font.name = "Proxima Nova"
                r_bullet.font.size = Pt(7.5)
                r_bullet.font.bold = False
                r_bullet.font.color.rgb = RGBColor(0x1D, 0x29, 0x39)

                r_id = p.add_run()
                r_id.text = del_id
                r_id.font.name = "Proxima Nova"
                r_id.font.size = Pt(8.0)
                r_id.font.bold = True
                r_id.font.color.rgb = RGBColor(0x0F, 0x25, 0x6E)

                r_desc = p.add_run()
                r_desc.text = del_desc
                r_desc.font.name = "Proxima Nova"
                r_desc.font.size = Pt(7.5)
                r_desc.font.bold = False
                r_desc.font.color.rgb = RGBColor(0x1D, 0x29, 0x39)
            else:
                p.text = f"• {deliv_str}" if len(delivs) > 1 and not deliv_str.startswith("•") else deliv_str
                for r in p.runs:
                    r.font.name = "Proxima Nova"
                    r.font.size = Pt(7.5)
                    r.font.color.rgb = RGBColor(0x1D, 0x29, 0x39)


def write_slide6(slide, model: ClientDeckModel) -> None:
    """Populate Slide 6 (What we will deliver) single page (HTL-100)."""
    write_slide6_deliverables_page(slide, model.slide6.workstreams, model, page_num=1, total_pages=1)


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
    for cell in table.rows[0].cells:
        _format_table_header_fill(cell, fill_hex="0F256E")

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
    for cell in table.rows[0].cells:
        _format_table_header_fill(cell, fill_hex="0F256E")

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
    """Load template presentation, populate slides, and save output file (OUT-14 / HTL-100)."""
    src_template = template_path or CLIENT_DECK_TEMPLATE_PATH
    if not src_template.exists():
        raise FileNotFoundError(f"Client Deck template not found at {src_template}")

    prs = pptx.Presentation(str(src_template))

    chunks_s6 = chunk_workstreams_for_deliverables_table(model.slide6.workstreams)
    total_s6_pages = len(chunks_s6)

    # Extra slides for Slide 6 continuation pages
    layout_default = prs.slides[5].slide_layout
    extra_s6_indices = []
    if total_s6_pages > 1:
        for _ in range(total_s6_pages - 1):
            s_extra = prs.slides.add_slide(layout_default)
            # Remove default shapes on new slide
            for s in list(s_extra.shapes):
                s_extra.shapes._spTree.remove(s._element)
            for s in prs.slides[5].shapes:
                s_extra.shapes._spTree.append(copy.deepcopy(s._element))
            extra_s6_indices.append(len(prs.slides) - 1)

    s6_indices = [5] + extra_s6_indices
    # Desired order for client deck:
    # 0, 1, 2, 3, 4 (Slides 1..5)
    # s6_indices (Slide 6 pages)
    # 6, 7, 8, 9, 10 (Slides 7..11)
    # 11 (Slide 12 - Risk Register)
    # 12, 13 (Slides 13, 14)
    # 14 (Slide 15 - Next Steps)
    desired_indices = [0, 1, 2, 3, 4] + s6_indices + [6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    sldIdLst = prs.slides._sldIdLst
    all_sld_ids = list(sldIdLst)
    for child in list(sldIdLst):
        sldIdLst.remove(child)
    for idx in desired_indices:
        sldIdLst.append(all_sld_ids[idx])

    # Format canonical slide headers across all content slides (HTL-88)
    apply_slide_header_formatting(prs.slides[1], has_subtitle=False)
    apply_slide_header_formatting(prs.slides[2], has_subtitle=False)
    apply_slide_header_formatting(prs.slides[4])
    apply_slide_header_formatting(prs.slides[4 + total_s6_pages + 2])  # Slide 8
    apply_slide_header_formatting(prs.slides[4 + total_s6_pages + 3])  # Slide 9
    apply_slide_header_formatting(prs.slides[4 + total_s6_pages + 4])  # Slide 10
    apply_slide_header_formatting(prs.slides[4 + total_s6_pages + 5])  # Slide 11
    apply_slide_header_formatting(prs.slides[4 + total_s6_pages + 6])  # Slide 12
    apply_slide_header_formatting(prs.slides[4 + total_s6_pages + 7])  # Slide 13
    apply_slide_header_formatting(prs.slides[4 + total_s6_pages + 9])  # Slide 15

    # Populate slides
    write_slide1(prs.slides[0], model)
    write_slide5(prs.slides[4], model)

    for c_idx, chunk_ws in enumerate(chunks_s6):
        write_slide6_deliverables_page(
            prs.slides[5 + c_idx],
            chunk_ws,
            model,
            page_num=c_idx + 1,
            total_pages=total_s6_pages,
        )

    # Slide 12 (Initial Risk Register): index is 10 + total_s6_pages
    write_slide12(prs.slides[10 + total_s6_pages], model)

    # Slide 15 (Next Steps): index is 13 + total_s6_pages
    write_slide15(prs.slides[13 + total_s6_pages], model)

    # Ensure any remaining template shapes with legacy #041133 are sanitized to canonical #0F256E (HTL-103)
    for slide in prs.slides:
        for shape in slide.shapes:
            xml_str = etree.tostring(shape._element).decode()
            if "041133" in xml_str or "041133" in xml_str.lower():
                new_xml = xml_str.replace("041133", "0F256E").replace("041133", "0F256E")
                new_elem = etree.fromstring(new_xml.encode())
                parent = shape._element.getparent()
                if parent is not None:
                    parent.replace(shape._element, new_elem)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(target_path))

    # Write companion trace manifest
    manifest_path = target_path.with_name(f"{target_path.stem}.trace.json")
    model.manifest.write_json(manifest_path)

    return target_path
