"""Shared slide header formatting and positioning helper for PPTX presentations (HTL-88).

Enforces canonical kicker, title, and subtitle typography, color, and vertical spacing
across all content slides in both Client Kickoff and PS Governance Kickoff decks.
"""

from typing import Optional, Tuple
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

# Canonical Constants (matching Slide 5 baseline)
KICKER_COLOR = RGBColor(0x2E, 0x5A, 0xAC)   # #2E5AAC
TITLE_COLOR = RGBColor(0x0F, 0x25, 0x6E)    # #0F256E (HTL-103)
SUBTITLE_COLOR = RGBColor(0x0F, 0x25, 0x6E) # #0F256E (HTL-88 / HTL-103)

# Positions and Dimensions in EMU (and Inches)
KICKER_LEFT = Inches(0.525)    # 480073 EMU (0.525 in)
KICKER_TOP = Inches(0.465)     # 425196 EMU (0.465 in)
KICKER_WIDTH = Inches(7.500)   # 6858300 EMU (7.500 in)
KICKER_HEIGHT = Inches(0.225)  # 205800 EMU (0.225 in)

TITLE_LEFT = Inches(0.525)     # 480076 EMU (0.525 in)
TITLE_TOP = Inches(0.804)      # 734900 EMU (0.804 in)
TITLE_WIDTH = Inches(8.775)    # 8023800 EMU (8.775 in)
TITLE_HEIGHT = Inches(0.364)   # 332400 EMU (0.364 in)

SUBTITLE_LEFT = Inches(0.525)  # 480073 EMU (0.525 in)
SUBTITLE_TOP = Inches(1.350)   # 1234440 EMU (1.350 in)
SUBTITLE_WIDTH = Inches(7.500) # 6858300 EMU (7.500 in)
SUBTITLE_HEIGHT = Inches(0.300)# 274200 EMU (0.300 in)


def _format_textbox_properties(shape) -> None:
    """Ensure top-anchoring, word wrap, and zero text frame margins."""
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.margin_left = 0
    tf.margin_right = 0
    for bpr in shape._element.xpath(".//a:bodyPr"):
        bpr.set("anchor", "t")
        for autofit in list(bpr.xpath("./a:normAutofit")):
            bpr.remove(autofit)


def format_kicker_shape(shape, kicker_text: Optional[str] = None) -> None:
    """Format and position a kicker shape to canonical standards."""
    shape.left = KICKER_LEFT
    shape.top = KICKER_TOP
    shape.width = KICKER_WIDTH
    shape.height = KICKER_HEIGHT
    _format_textbox_properties(shape)

    tf = shape.text_frame
    if kicker_text is not None:
        text = kicker_text.upper()
    else:
        text = tf.text.strip().upper() if tf.text else ""

    # Clear extra paragraphs
    for p in list(tf.paragraphs[1:]):
        tf._txBody.remove(p._p)

    if not tf.paragraphs:
        p = tf.add_paragraph()
    else:
        p = tf.paragraphs[0]

    p.text = text
    p.space_before = Pt(0)
    p.space_after = Pt(0)
    for end_rpr in p._p.xpath(".//a:endParaRPr"):
        for solid_fill in end_rpr.xpath(".//a:solidFill"):
            end_rpr.remove(solid_fill)
    for r in p.runs:
        r.font.name = "Proxima Nova"
        r.font.size = Pt(9.0)
        r.font.bold = True
        r.font.color.rgb = KICKER_COLOR


def format_title_shape(shape, title_text: Optional[str] = None, title_sz: float = 24.0) -> None:
    """Format and position a title shape to canonical standards."""
    shape.left = TITLE_LEFT
    shape.top = TITLE_TOP
    shape.width = TITLE_WIDTH
    shape.height = TITLE_HEIGHT
    _format_textbox_properties(shape)

    tf = shape.text_frame
    if title_text is not None:
        text = title_text
    else:
        text = tf.text.strip() if tf.text else ""

    # Clear extra paragraphs
    for p in list(tf.paragraphs[1:]):
        tf._txBody.remove(p._p)

    if not tf.paragraphs:
        p = tf.add_paragraph()
    else:
        p = tf.paragraphs[0]

    p.text = text
    p.space_before = Pt(0)
    p.space_after = Pt(0)
    for end_rpr in p._p.xpath(".//a:endParaRPr"):
        for solid_fill in end_rpr.xpath(".//a:solidFill"):
            end_rpr.remove(solid_fill)
    for r in p.runs:
        r.font.name = "Proxima Nova"
        r.font.size = Pt(title_sz)
        r.font.bold = True
        r.font.color.rgb = TITLE_COLOR


def format_subtitle_shape(shape, subtitle_text: Optional[str] = None) -> None:
    """Format and position a subtitle shape to canonical standards."""
    shape.left = SUBTITLE_LEFT
    shape.top = SUBTITLE_TOP
    shape.width = SUBTITLE_WIDTH
    shape.height = SUBTITLE_HEIGHT
    _format_textbox_properties(shape)

    tf = shape.text_frame
    if subtitle_text is not None:
        text = subtitle_text
    else:
        text = tf.text.strip() if tf.text else ""

    # Clear extra paragraphs
    for p in list(tf.paragraphs[1:]):
        tf._txBody.remove(p._p)

    if not tf.paragraphs:
        p = tf.add_paragraph()
    else:
        p = tf.paragraphs[0]

    p.text = text
    p.space_before = Pt(0)
    p.space_after = Pt(0)
    for end_rpr in p._p.xpath(".//a:endParaRPr"):
        for solid_fill in end_rpr.xpath(".//a:solidFill"):
            end_rpr.remove(solid_fill)
    for r in p.runs:
        r.font.name = "Proxima Nova"
        r.font.size = Pt(9.0)
        r.font.bold = False
        r.font.color.rgb = SUBTITLE_COLOR


def identify_header_shapes(slide) -> Tuple[Optional[pptx.shapes.base.BaseShape], Optional[pptx.shapes.base.BaseShape], Optional[pptx.shapes.base.BaseShape]]:
    """Identify existing (kicker, title, subtitle) header shapes in a slide based on vertical position and text properties."""
    kicker_shape = None
    title_shape = None
    subtitle_shape = None

    for sh in slide.shapes:
        if not sh.has_text_frame:
            continue
        top_in = sh.top / 914400.0
        left_in = sh.left / 914400.0
        h_in = sh.height / 914400.0
        w_in = sh.width / 914400.0

        # Header shapes are located in the upper portion of the slide (top < 1.70 in, left < 1.5 in, height < 1.0 in)
        if top_in < 1.70 and left_in < 1.5 and h_in < 1.0:
            text = sh.text_frame.text.strip()
            # Check font size or vertical band
            first_run = None
            if sh.text_frame.paragraphs and sh.text_frame.paragraphs[0].runs:
                first_run = sh.text_frame.paragraphs[0].runs[0]
            run_sz = first_run.font.size.pt if first_run and first_run.font.size else None

            # 1. Kicker: top < 0.65 in, or ALL CAPS short text, or size ~9pt
            if top_in < 0.65 or (run_sz and run_sz <= 11.0 and text.isupper()):
                if kicker_shape is None or top_in < kicker_shape.top / 914400.0:
                    kicker_shape = sh
            # 2. Main Title: top between 0.65 in and 1.25 in, or large size (>=18pt)
            elif (0.65 <= top_in < 1.25) or (run_sz and run_sz >= 18.0):
                if title_shape is None:
                    title_shape = sh
            # 3. Subtitle: top between 1.20 in and 1.65 in, width >= 4.0 in, and has text
            elif 1.20 <= top_in < 1.65 and w_in >= 4.0 and len(text) > 0:
                if subtitle_shape is None:
                    subtitle_shape = sh

    return kicker_shape, title_shape, subtitle_shape


def apply_slide_header_formatting(
    slide,
    kicker_text: Optional[str] = None,
    title_text: Optional[str] = None,
    subtitle_text: Optional[str] = None,
    title_sz: float = 24.0,
    has_kicker: bool = True,
    has_subtitle: bool = True,
) -> Tuple[Optional[pptx.shapes.base.BaseShape], Optional[pptx.shapes.base.BaseShape], Optional[pptx.shapes.base.BaseShape]]:
    """Format slide header elements to canonical kicker, title, and subtitle standards (HTL-88).

    If shapes already exist on the slide, they are reformatted and repositioned in place.
    If shapes do not exist (e.g. dynamically rebuilt slides), new textboxes are created.
    """
    k_shape, t_shape, s_shape = identify_header_shapes(slide)

    # 1. Kicker
    if has_kicker:
        if k_shape is None and kicker_text is not None:
            k_shape = slide.shapes.add_textbox(KICKER_LEFT, KICKER_TOP, KICKER_WIDTH, KICKER_HEIGHT)
        if k_shape is not None:
            format_kicker_shape(k_shape, kicker_text)

    # 2. Main Title
    if t_shape is None and title_text is not None:
        t_shape = slide.shapes.add_textbox(TITLE_LEFT, TITLE_TOP, TITLE_WIDTH, TITLE_HEIGHT)
    if t_shape is not None:
        format_title_shape(t_shape, title_text, title_sz=title_sz)

    # 3. Subtitle
    if has_subtitle:
        if s_shape is None and subtitle_text is not None:
            s_shape = slide.shapes.add_textbox(SUBTITLE_LEFT, SUBTITLE_TOP, SUBTITLE_WIDTH, SUBTITLE_HEIGHT)
        if s_shape is not None:
            format_subtitle_shape(s_shape, subtitle_text)

    return k_shape, t_shape, s_shape
