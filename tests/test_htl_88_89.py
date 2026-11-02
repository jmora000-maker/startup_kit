"""Regression tests for HTL-88 and HTL-89: Slide Header Formatting Consistency & Slide 15 Table Styling."""

from pathlib import Path
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
import pytest

from tests.deck_bundle import load_baseline
from tests.test_htl_62 import _build_pge_baseline
from src.generators.client_deck import export_client_deck
from src.generators.deck_header import (
    apply_slide_header_formatting,
    identify_header_shapes,
    format_kicker_shape,
    format_title_shape,
    format_subtitle_shape,
    KICKER_COLOR,
    TITLE_COLOR,
    SUBTITLE_COLOR,
    KICKER_LEFT,
    KICKER_TOP,
    KICKER_WIDTH,
    KICKER_HEIGHT,
    TITLE_LEFT,
    TITLE_TOP,
    TITLE_WIDTH,
    TITLE_HEIGHT,
    SUBTITLE_LEFT,
    SUBTITLE_TOP,
    SUBTITLE_WIDTH,
    SUBTITLE_HEIGHT,
)


def test_htl_88_deck_header_helper_unit_formatting():
    """HTL-88: Test apply_slide_header_formatting creates and formats canonical shapes on an empty slide."""
    prs = pptx.Presentation()
    blank_slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_slide_layout)

    k, t, s = apply_slide_header_formatting(
        slide,
        kicker_text="TEST KICKER",
        title_text="Test Main Title",
        subtitle_text="Test subtitle description.",
    )

    # 1. Kicker
    assert k is not None
    assert k.left == KICKER_LEFT
    assert k.top == KICKER_TOP
    assert k.width == KICKER_WIDTH
    assert k.height == KICKER_HEIGHT
    kp = k.text_frame.paragraphs[0]
    assert kp.text == "TEST KICKER"
    assert kp.runs[0].font.name == "Proxima Nova"
    assert kp.runs[0].font.size == Pt(9.0)
    assert kp.runs[0].font.bold is True
    assert kp.runs[0].font.color.rgb == RGBColor(0x2E, 0x5A, 0xAC)

    # 2. Title
    assert t is not None
    assert t.left == TITLE_LEFT
    assert t.top == TITLE_TOP
    assert t.width == TITLE_WIDTH
    assert t.height == TITLE_HEIGHT
    tp = t.text_frame.paragraphs[0]
    assert tp.text == "Test Main Title"
    assert tp.runs[0].font.name == "Proxima Nova"
    assert tp.runs[0].font.size == Pt(24.0)
    assert tp.runs[0].font.bold is True
    assert tp.runs[0].font.color.rgb == RGBColor(0x04, 0x11, 0x33)

    # 3. Subtitle
    assert s is not None
    assert s.left == SUBTITLE_LEFT
    assert s.top == SUBTITLE_TOP
    assert s.width == SUBTITLE_WIDTH
    assert s.height == SUBTITLE_HEIGHT
    sp = s.text_frame.paragraphs[0]
    assert sp.text == "Test subtitle description."
    assert sp.runs[0].font.name == "Proxima Nova"
    assert sp.runs[0].font.size == Pt(9.0)
    assert sp.runs[0].font.bold is False
    assert sp.runs[0].font.color.rgb == RGBColor(0x04, 0x11, 0x33)


def test_htl_88_client_kickoff_deck_all_slides_header_standardization(tmp_path):
    """HTL-88: Verify all content slides in the generated Client Kickoff Deck adhere to canonical header standards."""
    baseline = load_baseline("arc_genomics")
    baseline.project_name = "ARC Application Implementation"
    if baseline.charter:
        baseline.charter.project_name = "ARC Application Implementation"

    res = export_client_deck(baseline, tmp_path)
    prs = pptx.Presentation(str(res.file_path))

    # All content slides with kicker + title (and optional subtitle)
    # 1-indexed: Slides 2, 3, 5, 6, 8, 9, 10, 11, 12, 13, 15
    standard_3_element_slides = [5, 8, 9, 10, 11, 12, 13, 15]
    kicker_title_only_slides = [2, 3, 6]

    for s_num in kicker_title_only_slides:
        slide = prs.slides[s_num - 1]
        k, t, s = identify_header_shapes(slide)
        assert k is not None, f"Slide {s_num} missing kicker shape"
        assert t is not None, f"Slide {s_num} missing title shape"
        assert s is None, f"Slide {s_num} should not have a subtitle shape"

        # Kicker invariants
        assert abs(k.left - KICKER_LEFT) < 1000, f"Slide {s_num} kicker left mismatch"
        assert abs(k.top - KICKER_TOP) < 1000, f"Slide {s_num} kicker top mismatch"
        assert abs(k.width - KICKER_WIDTH) < 1000, f"Slide {s_num} kicker width mismatch"
        assert abs(k.height - KICKER_HEIGHT) < 1000, f"Slide {s_num} kicker height mismatch"
        kp = k.text_frame.paragraphs[0]
        assert kp.text.isupper(), f"Slide {s_num} kicker must be uppercase: {kp.text}"
        assert kp.runs[0].font.name == "Proxima Nova"
        assert kp.runs[0].font.size == Pt(9.0)
        assert kp.runs[0].font.bold is True
        assert kp.runs[0].font.color.rgb == RGBColor(0x2E, 0x5A, 0xAC)

        # Title invariants
        assert abs(t.left - TITLE_LEFT) < 1000, f"Slide {s_num} title left mismatch"
        assert abs(t.top - TITLE_TOP) < 1000, f"Slide {s_num} title top mismatch"
        assert abs(t.width - TITLE_WIDTH) < 1000, f"Slide {s_num} title width mismatch"
        assert abs(t.height - TITLE_HEIGHT) < 1000, f"Slide {s_num} title height mismatch"
        tp = t.text_frame.paragraphs[0]
        assert tp.runs[0].font.name == "Proxima Nova"
        assert tp.runs[0].font.size == Pt(24.0)
        assert tp.runs[0].font.bold is True
        assert tp.runs[0].font.color.rgb == RGBColor(0x04, 0x11, 0x33)

    for s_num in standard_3_element_slides:
        slide = prs.slides[s_num - 1]
        k, t, s = identify_header_shapes(slide)
        assert k is not None, f"Slide {s_num} missing kicker shape"
        assert t is not None, f"Slide {s_num} missing title shape"
        assert s is not None, f"Slide {s_num} missing subtitle shape"

        # Kicker invariants
        assert abs(k.left - KICKER_LEFT) < 1000, f"Slide {s_num} kicker left mismatch"
        assert abs(k.top - KICKER_TOP) < 1000, f"Slide {s_num} kicker top mismatch"
        assert abs(k.width - KICKER_WIDTH) < 1000, f"Slide {s_num} kicker width mismatch"
        assert abs(k.height - KICKER_HEIGHT) < 1000, f"Slide {s_num} kicker height mismatch"
        kp = k.text_frame.paragraphs[0]
        assert kp.text.isupper(), f"Slide {s_num} kicker must be uppercase: {kp.text}"
        assert kp.runs[0].font.name == "Proxima Nova"
        assert kp.runs[0].font.size == Pt(9.0)
        assert kp.runs[0].font.bold is True
        assert kp.runs[0].font.color.rgb == RGBColor(0x2E, 0x5A, 0xAC)

        # Title invariants
        assert abs(t.left - TITLE_LEFT) < 1000, f"Slide {s_num} title left mismatch"
        assert abs(t.top - TITLE_TOP) < 1000, f"Slide {s_num} title top mismatch"
        assert abs(t.width - TITLE_WIDTH) < 1000, f"Slide {s_num} title width mismatch"
        assert abs(t.height - TITLE_HEIGHT) < 1000, f"Slide {s_num} title height mismatch"
        tp = t.text_frame.paragraphs[0]
        assert tp.runs[0].font.name == "Proxima Nova"
        assert tp.runs[0].font.size == Pt(24.0)
        assert tp.runs[0].font.bold is True
        assert tp.runs[0].font.color.rgb == RGBColor(0x04, 0x11, 0x33)

        # Subtitle invariants
        assert abs(s.left - SUBTITLE_LEFT) < 1000, f"Slide {s_num} subtitle left mismatch"
        assert abs(s.top - SUBTITLE_TOP) < 1000, f"Slide {s_num} subtitle top mismatch"
        assert abs(s.width - SUBTITLE_WIDTH) < 1000, f"Slide {s_num} subtitle width mismatch"
        assert abs(s.height - SUBTITLE_HEIGHT) < 1000, f"Slide {s_num} subtitle height mismatch"
        sp = s.text_frame.paragraphs[0]
        assert sp.runs[0].font.name == "Proxima Nova"
        assert sp.runs[0].font.size == Pt(9.0)
        assert sp.runs[0].font.bold is False
        assert sp.runs[0].font.color.rgb == RGBColor(0x04, 0x11, 0x33)


def test_htl_88_pge_client_kickoff_deck_all_slides_header_standardization(tmp_path):
    """HTL-88: Verify all content slides in PGE Client Kickoff Deck adhere to canonical header standards."""
    pge_baseline = _build_pge_baseline()
    res = export_client_deck(pge_baseline, tmp_path)
    prs = pptx.Presentation(str(res.file_path))

    for s_num in [5, 8, 9, 10, 11, 12, 13, 15]:
        slide = prs.slides[s_num - 1]
        k, t, s = identify_header_shapes(slide)
        assert k is not None and t is not None and s is not None
        assert k.text_frame.paragraphs[0].runs[0].font.size == Pt(9.0)
        assert t.text_frame.paragraphs[0].runs[0].font.size == Pt(24.0)
        assert s.text_frame.paragraphs[0].runs[0].font.size == Pt(9.0)
