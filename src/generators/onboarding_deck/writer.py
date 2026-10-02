"""Presentation writer for the Talent Team Onboarding Deck (DECK-12, DECK-13, DECK-21, Appendix K.1).

The writer sets every style explicitly rather than relying on layout defaults: the layout default renders
the title blue and the kicker large (Appendix L, L2). Geometry, fonts, and row heights come from the
DeckModel, which sized them with the fit estimate.
"""

from pathlib import Path
from typing import Any, List, Optional

import pptx
from lxml import etree
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from src.config import DECK_TEMPLATE_PATH, config
from src.generators.onboarding_deck import layout as L
from src.generators.onboarding_deck.spec import (
    BODY,
    BULLET,
    ITALIC,
    LABEL,
    MORE,
    MUTED,
    PLACEHOLDER,
    STRONG,
    SUBHEADING,
    CardSpec,
    CellSpec,
    DeckModel,
    ParaSpec,
    Run,
    SlideSpec,
    TableSpec,
    TextBoxSpec,
)

FONT_HEAD = "Proxima Nova"
FONT_SEMIBOLD = "Proxima Nova Semibold"
FONT_BODY = "Calibri"

NAVY = RGBColor(0x0F, 0x17, 0x2A)
SLATE = RGBColor(0x47, 0x55, 0x69)
MUTED_GRAY = RGBColor(0x64, 0x74, 0x8B)
BLUE = RGBColor(0x20, 0x4E, 0xCF)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BORDER = RGBColor(0xE2, 0xE8, 0xF0)
BAND = RGBColor(0xF8, 0xFA, 0xFC)

BULLET_MARGIN_EMU = int(L.BULLET_INDENT_IN * 914400)


def _rgb(hex_str: str) -> RGBColor:
    return RGBColor.from_string(hex_str.upper())


def _style_run(run: Any, spec_run: Run, size_pt: float, force_bold_navy: bool = False) -> None:
    """Set font, size, colour, weight, and slant explicitly on a run."""
    run.font.name = FONT_BODY
    run.font.size = Pt(size_pt)
    kind = spec_run.kind
    bold, italic, color = False, False, SLATE
    if kind in (LABEL, STRONG):
        bold, color = True, NAVY
    elif kind == PLACEHOLDER:
        italic, color = True, BLUE
    elif kind == MUTED:
        italic, color = True, MUTED_GRAY
    elif kind == ITALIC:
        italic = True
    elif force_bold_navy:
        bold, color = True, NAVY
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color


def _style_plain(run: Any, name: str, size_pt: float, bold: bool, color: RGBColor) -> None:
    run.font.name = name
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.italic = False
    run.font.color.rgb = color


def _set_bullet(paragraph: Any) -> None:
    """Paragraph bullet formatting: character `•`, left margin 0.17 in, hanging indent 0.17 in (DECK-21 (1))."""
    pPr = paragraph._p.get_or_add_pPr()
    pPr.set("marL", str(BULLET_MARGIN_EMU))
    pPr.set("indent", str(-BULLET_MARGIN_EMU))
    for tag in ("a:buNone", "a:buChar", "a:buFont", "a:buAutoNum"):
        for el in pPr.findall(qn(tag)):
            pPr.remove(el)
    bu_font = etree.SubElement(pPr, qn("a:buFont"))
    bu_font.set("typeface", "Arial")
    bu_char = etree.SubElement(pPr, qn("a:buChar"))
    bu_char.set("char", "•")


def _no_bullet(paragraph: Any) -> None:
    pPr = paragraph._p.get_or_add_pPr()
    pPr.set("marL", "0")
    pPr.set("indent", "0")
    for tag in ("a:buNone", "a:buChar", "a:buFont", "a:buAutoNum"):
        for el in pPr.findall(qn(tag)):
            pPr.remove(el)
    etree.SubElement(pPr, qn("a:buNone"))


def _spacing(paragraph: Any, before: float, after: float) -> None:
    paragraph.space_before = Pt(before)
    paragraph.space_after = Pt(after)
    paragraph.line_spacing = 1.0


def _frame_defaults(tf: Any) -> None:
    """Word wrap on, autofit off, top anchor, no internal margins (the frame is inset from its card instead)."""
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0


def _add_card(slide: Any, spec: CardSpec) -> None:
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(spec.x), Inches(spec.y), Inches(spec.w), Inches(spec.h))
    card.name = spec.card_name
    card.adjustments[0] = L.CARD_CORNER_ADJ / 100000.0
    card.fill.solid()
    card.fill.fore_color.rgb = WHITE
    card.line.color.rgb = BORDER
    card.line.width = Pt(L.CARD_OUTLINE_PT)
    card.shadow.inherit = False

    inset = L.CARD_INSET
    frame_h = 0.40 if spec.table is not None else spec.h - 2 * inset
    box = slide.shapes.add_textbox(Inches(spec.x + inset), Inches(spec.y + inset), Inches(spec.w - 2 * inset), Inches(frame_h))
    box.name = spec.text_name
    tf = box.text_frame
    _frame_defaults(tf)

    p = tf.paragraphs[0]
    _no_bullet(p)
    _spacing(p, 0.0, L.HEADING_SPACE_AFTER_PT)
    r = p.add_run()
    r.text = spec.heading
    _style_plain(r, FONT_HEAD, spec.heading_pt, True, NAVY)

    for ps in spec.paras:
        p = tf.add_paragraph()
        _write_card_para(p, ps, spec.body_pt)

    if spec.table is not None:
        _add_table(slide, spec.table, slide_no=None)


def _write_card_para(p: Any, ps: ParaSpec, body_pt: float) -> None:
    if ps.kind == SUBHEADING:
        _no_bullet(p)
        _spacing(p, L.SUBHEADING_SPACE_BEFORE_PT, L.SUBHEADING_SPACE_AFTER_PT)
        for run in ps.runs:
            r = p.add_run()
            r.text = run.text
            _style_plain(r, FONT_SEMIBOLD, L.CARD_SUBHEADING_PT, False, BLUE)
        return
    if ps.kind == BULLET:
        _set_bullet(p)
    else:
        _no_bullet(p)
    _spacing(p, 0.0, L.BODY_SPACE_AFTER_PT)
    for run in ps.runs:
        r = p.add_run()
        r.text = run.text
        _style_run(r, run, body_pt)


def _add_textbox(slide: Any, spec: TextBoxSpec) -> None:
    box = slide.shapes.add_textbox(Inches(spec.x), Inches(spec.y), Inches(spec.w), Inches(spec.h))
    box.name = spec.name
    tf = box.text_frame
    _frame_defaults(tf)
    for i, ps in enumerate(spec.paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        _no_bullet(p)
        _spacing(p, 0.0, L.BODY_SPACE_AFTER_PT)
        for run in ps.runs:
            r = p.add_run()
            r.text = run.text
            _style_run(r, run, spec.size_pt)


def _cell_border(cell: Any) -> None:
    """E2E8F0 borders on all four sides (the built-in table style is removed, so borders are explicit)."""
    tcPr = cell._tc.get_or_add_tcPr()
    for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        for el in tcPr.findall(qn(tag)):
            tcPr.remove(el)
    fills = [el for el in tcPr if el.tag in (qn("a:solidFill"), qn("a:noFill"))]
    for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        ln = etree.Element(qn(tag))
        ln.set("w", "12700")
        sf = etree.SubElement(ln, qn("a:solidFill"))
        clr = etree.SubElement(sf, qn("a:srgbClr"))
        clr.set("val", "E2E8F0")
        # borders precede the fill in a:tcPr
        if fills:
            fills[0].addprevious(ln)
        else:
            tcPr.append(ln)


def _fill_cell(cell: Any, color: RGBColor) -> None:
    cell.fill.solid()
    cell.fill.fore_color.rgb = color


def _cell_frame(cell: Any) -> None:
    cell.margin_left = cell.margin_right = Inches(L.CELL_MARGIN_LR)
    cell.margin_top = cell.margin_bottom = Inches(L.CELL_MARGIN_TB)
    cell.vertical_anchor = MSO_ANCHOR.TOP


def _write_cell(cell: Any, spec: CellSpec, size_pt: float, first_col: bool, header_like: bool = False) -> None:
    _cell_frame(cell)
    tf = cell.text_frame
    tf.word_wrap = True
    lines = spec.paras or [[]]
    for i, runs in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        _no_bullet(p)
        _spacing(p, 0.0, 0.0)
        p.alignment = PP_ALIGN.LEFT
        for run in runs:
            r = p.add_run()
            r.text = run.text
            _style_run(r, run, size_pt, force_bold_navy=first_col)
            if spec.text_color:
                r.font.color.rgb = _rgb(spec.text_color)
            if spec.bold:
                r.font.bold = True


def _add_table(slide: Any, spec: TableSpec, slide_no: Optional[int]) -> None:
    n_rows = len(spec.rows) + (1 if spec.header else 0)
    n_cols = len(spec.col_widths)
    shape = slide.shapes.add_table(n_rows, n_cols, Inches(spec.x), Inches(spec.y), Inches(spec.width), Inches(spec.height))
    shape.name = spec.name
    table = shape.table

    # the built-in table style is removed: no banding from PowerPoint's default style (DECK-21 (2))
    tblPr = table._tbl.tblPr
    for el in tblPr.findall(qn("a:tableStyleId")):
        tblPr.remove(el)
    table.first_row = spec.header is not None
    table.horz_banding = False

    for i, w in enumerate(spec.col_widths):
        table.columns[i].width = Inches(w)

    r0 = 0
    if spec.header:
        table.rows[0].height = Inches(spec.header_height)
        for c, text in enumerate(spec.header):
            cell = table.cell(0, c)
            _fill_cell(cell, BLUE)
            _cell_frame(cell)
            p = cell.text_frame.paragraphs[0]
            _no_bullet(p)
            _spacing(p, 0.0, 0.0)
            r = p.add_run()
            r.text = text
            _style_plain(r, FONT_HEAD, L.TABLE_HEADER_PT, True, WHITE)
            _cell_border(cell)
        r0 = 1

    sizes = [spec.body_pt] * n_cols
    if spec.deliverables_pt is not None:
        sizes[-1] = spec.deliverables_pt
    for ri, row in enumerate(spec.rows):
        table.rows[r0 + ri].height = Inches(row.height)
        band = BAND if ri % 2 == 0 else WHITE
        if row.overflow:
            origin = table.cell(r0 + ri, 0)
            origin.merge(table.cell(r0 + ri, n_cols - 1))
            _fill_cell(origin, band)
            _write_cell(origin, row.cells[0], sizes[0], first_col=False)
            _cell_border(origin)
            for c in range(1, n_cols):
                _fill_cell(table.cell(r0 + ri, c), band)
                _cell_border(table.cell(r0 + ri, c))
            continue
        for c, cell_spec in enumerate(row.cells):
            cell = table.cell(r0 + ri, c)
            if spec.key_value:
                label_col = c == 0
                _fill_cell(cell, BAND if label_col else WHITE)
                _cell_frame(cell)
                tf = cell.text_frame
                tf.word_wrap = True
                p = tf.paragraphs[0]
                _no_bullet(p)
                _spacing(p, 0.0, 0.0)
                for run in cell_spec.paras[0] if cell_spec.paras else []:
                    r = p.add_run()
                    r.text = run.text
                    if label_col:
                        _style_plain(r, FONT_HEAD, spec.body_pt, True, NAVY)
                    else:
                        _style_run(r, run, spec.body_pt)
            else:
                _fill_cell(cell, _rgb(cell_spec.fill) if cell_spec.fill else band)
                _write_cell(cell, cell_spec, sizes[c], first_col=(c == 0))
            _cell_border(cell)


def _style_title(slide: Any, title: str, kicker: str) -> None:
    """Title Proxima Nova bold 28 pt 0F172A; kicker Proxima Nova bold 11 pt 64748B (DECK-13)."""
    t = slide.placeholders[0]
    t.text_frame.text = ""
    p = t.text_frame.paragraphs[0]
    r = p.add_run()
    r.text = title
    _style_plain(r, FONT_HEAD, L.TITLE_PT, True, NAVY)
    k = slide.placeholders[1]
    k.text_frame.text = ""
    p = k.text_frame.paragraphs[0]
    r = p.add_run()
    r.text = kicker
    _style_plain(r, FONT_HEAD, L.KICKER_PT, True, MUTED_GRAY)


def write_onboarding_deck(
    model: DeckModel,
    target_path: Path,
    template_path: Optional[Path] = None,
) -> Path:
    """Write the deck and its trace manifest from the DeckModel (DECK-06, DECK-12, DECK-13)."""
    resolved_template = template_path or config.deck_template_path or DECK_TEMPLATE_PATH
    if not Path(resolved_template).exists():
        raise FileNotFoundError(f"Deck template missing: '{resolved_template}'")

    prs = pptx.Presentation(str(resolved_template))

    # Remove every template slide and its slide part (DECK-12)
    sld_id_lst = prs.slides._sldIdLst
    rids = [el.rId for el in list(sld_id_lst)]
    for el in list(sld_id_lst):
        sld_id_lst.remove(el)
    for rid in rids:
        if rid in prs.part.rels:
            prs.part.drop_rel(rid)

    layouts = {l.name: l for l in prs.slide_masters[0].slide_layouts}
    for needed in ("CUSTOM_1", "CUSTOM_16"):
        if needed not in layouts:
            raise ValueError(f"Required slide layout '{needed}' not found in template.")

    # Slide 1: cover, with the layout's own placeholder styling
    s1 = prs.slides.add_slide(layouts["CUSTOM_1"])
    s1.placeholders[0].text = model.cover.title.text
    s1.placeholders[1].text = "".join(r.text for r in model.cover.subtitle_runs)
    s1.placeholders[0].name = "Cover title"
    s1.placeholders[1].name = "Cover subtitle"
    s1.notes_slide.notes_text_frame.text = model.cover.notes

    for spec in model.slides:
        s = prs.slides.add_slide(layouts["CUSTOM_16"])
        _style_title(s, spec.title, spec.kicker)
        for card in spec.cards:
            _add_card(s, card)
        for table in spec.tables:
            _add_table(s, table, spec.number)
        for box in spec.boxes:
            _add_textbox(s, box)
        s.notes_slide.notes_text_frame.text = spec.notes

    target_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(target_path))
    model.manifest.write_json(target_path.with_name(f"{target_path.stem}.trace.json"))
    return target_path
