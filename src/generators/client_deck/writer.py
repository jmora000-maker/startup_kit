"""PPTX Presentation writer and dynamic shape tree engine for Client Kickoff Deck (OUT-14)."""

import copy
import re
from pathlib import Path
from typing import List, Optional, Tuple
import pptx
from pptx.util import Length, Pt
from pptx.dml.color import RGBColor

from src.config import CLIENT_DECK_TEMPLATE_PATH
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
    if not tf.paragraphs:
        p = tf.add_paragraph()
        p.text = new_text
        return

    first_p = tf.paragraphs[0]
    font_name = first_p.runs[0].font.name if first_p.runs and first_p.runs[0].font.name else "Proxima Nova"
    font_size = (
        first_p.runs[0].font.size
        if first_p.runs and first_p.runs[0].font.size
        else (default_font_size or Pt(11))
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


def write_slide1(slide, model: ClientDeckModel) -> None:
    """Populate Slide 1 [Client Name] and [Project Name] placeholders."""
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        text = shape.text_frame.text
        if "[Client Name]" in text or "[Project Name]" in text:
            # Handle runs
            for p in shape.text_frame.paragraphs:
                for r in p.runs:
                    if "[Client Name]" in r.text:
                        _set_run_text_preserve_font(r, r.text.replace("[Client Name]", model.slide1.client_name))
                    if "[Project Name]" in r.text:
                        _set_run_text_preserve_font(r, r.text.replace("[Project Name]", model.slide1.project_name))


def write_slide5(slide, model: ClientDeckModel) -> None:
    """Populate Slide 5 (Why We're Here)."""
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        text = shape.text_frame.text
        if "[Pre-filled: the business initiative" in text or shape.shape_id == 176:
            _replace_shape_text(shape, model.slide5.why_are_we_doing_this, Pt(11))
        elif "[Pre-filled: the current pain point" in text or shape.shape_id == 180:
            _replace_shape_text(shape, model.slide5.what_problem_are_we_solving, Pt(11))
        elif "[Pre-filled: the desired business outcomes" in text or shape.shape_id == 184:
            _replace_shape_text(shape, model.slide5.what_does_success_look_like, Pt(11))


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

    # Collect items to display
    items_to_display: List[Tuple[str, bool]] = []
    for d_text in deliverables:
        items_to_display.append((d_text, False))

    if overflow_count > 0:
        items_to_display.append(
            (f"+ {overflow_count} additional deliverables (see Project Delivery Workbook)", True)
        )

    # Clear extra paragraphs
    for p in list(tf.paragraphs[1:]):
        tf._txBody.remove(p._p)

    font_pt = float(font_size.pt)

    for idx, (item_text, is_ovf) in enumerate(items_to_display):
        if idx == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        _set_paragraph_bullet_format(p, font_pt, item_text, is_overflow=is_ovf)


def write_slide6(slide, model: ClientDeckModel) -> None:
    """Populate Slide 6 and dynamically manipulate XML shape tree for N workstreams."""
    white_color = RGBColor(255, 255, 255)

    # 1. Solution Overview & Out of Scope
    for shape in list(slide.shapes):
        if not shape.has_text_frame:
            continue
        text = shape.text_frame.text
        if shape.shape_id == 193 or (shape.has_text_frame and "Solution Overview" in text):
            # Strip placeholder attribute so renderer treats it as a standard top-anchored textbox
            for ph in shape._element.xpath(".//p:ph"):
                ph.getparent().remove(ph)
            shape.top = 580000
            shape.left = 6484400
            shape.width = 2417400
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
            shape.left = 6484400
            shape.width = 2417400
            shape.height = 2500000
            tf = shape.text_frame
            tf.margin_top = 0
            tf.margin_bottom = 0
            tf.margin_left = 0
            tf.margin_right = 0
            _replace_shape_text(shape, model.slide6.solution_overview, Pt(10.0), font_color_rgb=white_color)
            if tf.paragraphs and tf.paragraphs[0].runs:
                tf.paragraphs[0].runs[0].font.color.rgb = white_color
        elif shape.shape_id == 202 or "Out of Scope:" in text:
            shape.top = 3896250
            shape.left = 6347125
            shape.width = 2683500
            shape.height = 1000000
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
                    p.runs[0].font.size = Pt(10)
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
    elif n_ws == 3:
        h_font_size = Pt(10.5)
        d_font_size = Pt(10.0)
        top_offset = int(slot_h * 0.06)
    elif n_ws == 4:
        h_font_size = Pt(10.0)
        d_font_size = Pt(9.5)
        top_offset = int(slot_h * 0.05)
    elif n_ws == 5:
        h_font_size = Pt(9.0)
        d_font_size = Pt(8.5)
        top_offset = int(slot_h * 0.04)
    else:  # n_ws >= 6
        h_font_size = Pt(8.0)
        d_font_size = Pt(7.5)
        top_offset = int(slot_h * 0.03)

    # Get max current shape ID in tree
    max_sp_id = max([int(el.get("id", "0")) for el in slide.shapes._spTree.xpath(".//p:cNvPr")] + [500])

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
        item_height = int(slot_h * 0.88)

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
        h_font_pt = float(h_font_size.pt)
        _set_header_paragraph_format(tf_h.paragraphs[0], h_font_pt, ws.title)

        # Position Deliverables (Column 2 - Right)
        d_shape.left = 2726700
        d_shape.width = 3000000
        d_shape.top = item_top
        d_shape.height = item_height

        for bpr in d_shape._element.xpath(".//a:bodyPr"):
            bpr.set("anchor", "t")

        _populate_deliverables_box(
            d_shape,
            ws.deliverables,
            d_font_size,
            overflow_count=ws.overflow_count,
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
    """Populate Slide 12 Initial Risk Register table."""
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

    # Template has header + 3 data rows = 4 rows
    for i in range(min(num_risks, 3)):
        risk = risks[i]
        row = table.rows[i + 1]
        row.cells[0].text = risk.description
        row.cells[1].text = risk.prob_impact
        row.cells[2].text = risk.mitigation
        row.cells[3].text = risk.target_date

    # If fewer than 3 risks, remove surplus data rows from table XML
    if num_risks < 3:
        surplus_count = 3 - num_risks
        for _ in range(surplus_count):
            tr_elements = table._tbl.xpath("./a:tr")
            if len(tr_elements) > 1:
                table._tbl.remove(tr_elements[-1])


def write_slide15(slide, model: ClientDeckModel) -> None:
    """Populate Slide 15 Next Steps table."""
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

        row.cells[0].text = step.owner
        row.cells[1].text = step.action
        row.cells[2].text = "TBD"

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
