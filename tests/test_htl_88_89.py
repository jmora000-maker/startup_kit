"""Regression tests for HTL-88 and HTL-89: Slide Header Formatting Consistency & Slide 15 Table Styling."""

from pathlib import Path
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
import pytest

from tests.deck_bundle import load_baseline
from tests.test_htl_62 import _build_pge_baseline
from src.generators.client_deck import export_client_deck
from src.generators.governance_deck import export_governance_deck
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
    assert tp.runs[0].font.color.rgb == RGBColor(0x0F, 0x25, 0x6E)

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
    assert sp.runs[0].font.color.rgb == RGBColor(0x0F, 0x25, 0x6E)


def test_htl_88_client_kickoff_deck_all_slides_header_standardization(tmp_path):
    """HTL-88: Verify all content slides in the generated Client Kickoff Deck adhere to canonical header standards."""
    baseline = _build_pge_baseline()

    res = export_client_deck(baseline, tmp_path)
    prs = pptx.Presentation(str(res.file_path))

    # All content slides with kicker + title (and optional subtitle)
    # 1-indexed: Slides 2, 3, 5, 6, 8, 9, 10, 11, 12, 13, 15
    standard_3_element_slides = [5, 6, 8, 9, 10, 11, 12, 13, 15]
    kicker_title_only_slides = [2, 3]

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
        assert tp.runs[0].font.color.rgb == RGBColor(0x0F, 0x25, 0x6E)

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
        assert tp.runs[0].font.color.rgb == RGBColor(0x0F, 0x25, 0x6E)

        # Subtitle invariants
        assert abs(s.left - SUBTITLE_LEFT) < 1000, f"Slide {s_num} subtitle left mismatch"
        assert abs(s.top - SUBTITLE_TOP) < 1000, f"Slide {s_num} subtitle top mismatch"
        expected_sub_w = 5240000 if s_num == 6 else SUBTITLE_WIDTH
        assert abs(s.width - expected_sub_w) < 1000, f"Slide {s_num} subtitle width mismatch"
        assert abs(s.height - SUBTITLE_HEIGHT) < 1000, f"Slide {s_num} subtitle height mismatch"
        sp = s.text_frame.paragraphs[0]
        assert sp.runs[0].font.name == "Proxima Nova"
        assert sp.runs[0].font.size == Pt(9.0)
        assert sp.runs[0].font.bold is False
        assert sp.runs[0].font.color.rgb == RGBColor(0x0F, 0x25, 0x6E)


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


def test_htl_88_governance_kickoff_deck_all_slides_header_standardization(tmp_path):
    """HTL-88: Verify all content slides in PS Governance Kickoff Deck adhere to canonical header standards."""
    baseline = _build_pge_baseline()

    res = export_governance_deck(baseline, tmp_path / "gov_deck")
    prs = pptx.Presentation(str(res.file_path))

    # In PS Governance Kickoff Deck:
    # Slide 2: Kicker only
    # Slides 4, 5, 6, 7, 8, 9, 10, 12: Kicker + Title only
    # Slides 13, 14, 15, 16, 17, 18, 19: Kicker + Title + Subtitle

    # Slide 2: Kicker only
    slide2 = prs.slides[1]
    k2, t2, s2 = identify_header_shapes(slide2)
    assert k2 is not None, "Gov Slide 2 missing kicker shape"
    assert t2 is None, "Gov Slide 2 should not have title shape"
    assert s2 is None, "Gov Slide 2 should not have subtitle shape"
    assert abs(k2.left - KICKER_LEFT) < 1000
    assert abs(k2.top - KICKER_TOP) < 1000
    assert k2.text_frame.paragraphs[0].text.isupper()
    assert k2.text_frame.paragraphs[0].runs[0].font.size == Pt(9.0)
    assert k2.text_frame.paragraphs[0].runs[0].font.bold is True
    assert k2.text_frame.paragraphs[0].runs[0].font.color.rgb == RGBColor(0x2E, 0x5A, 0xAC)

    kicker_title_only_slides = [4, 5, 6, 7, 8, 9, 10, 12]

    for s_num in kicker_title_only_slides:
        slide = prs.slides[s_num - 1]
        k, t, s = identify_header_shapes(slide)
        assert k is not None, f"Gov Slide {s_num} missing kicker shape"
        assert t is not None, f"Gov Slide {s_num} missing title shape"
        assert s is None, f"Gov Slide {s_num} should not have a subtitle shape"

        # Kicker invariants
        assert abs(k.left - KICKER_LEFT) < 1000, f"Gov Slide {s_num} kicker left mismatch"
        assert abs(k.top - KICKER_TOP) < 1000, f"Gov Slide {s_num} kicker top mismatch"
        assert abs(k.width - KICKER_WIDTH) < 1000, f"Gov Slide {s_num} kicker width mismatch"
        assert abs(k.height - KICKER_HEIGHT) < 1000, f"Gov Slide {s_num} kicker height mismatch"
        kp = k.text_frame.paragraphs[0]
        assert kp.text.isupper(), f"Gov Slide {s_num} kicker must be uppercase: {kp.text}"
        assert kp.runs[0].font.name == "Proxima Nova"
        assert kp.runs[0].font.size == Pt(9.0)
        assert kp.runs[0].font.bold is True
        assert kp.runs[0].font.color.rgb == RGBColor(0x2E, 0x5A, 0xAC)

        # Title invariants
        assert abs(t.left - TITLE_LEFT) < 1000, f"Gov Slide {s_num} title left mismatch"
        assert abs(t.top - TITLE_TOP) < 1000, f"Gov Slide {s_num} title top mismatch"
        assert abs(t.width - TITLE_WIDTH) < 1000, f"Gov Slide {s_num} title width mismatch"
        assert abs(t.height - TITLE_HEIGHT) < 1000, f"Gov Slide {s_num} title height mismatch"
        tp = t.text_frame.paragraphs[0]
        assert tp.runs[0].font.name == "Proxima Nova"
        assert tp.runs[0].font.size == Pt(24.0)
        assert tp.runs[0].font.bold is True
        assert tp.runs[0].font.color.rgb == RGBColor(0x0F, 0x25, 0x6E)
        if s_num == 6:
            assert tp.text == "The PM owns the plan and the day-to-day work"

    # Content slides with Subtitle: Slide 13 (Why we're here), Slide 14 pages (What we deliver), Slide 15 pages (Acceptance Criteria),
    # Slide 16 (How Acceptance Works), Slide 17 (Approach), Slide 18 (Risk Register), Slide 19 (Next Steps)
    total_slides = len(prs.slides)
    standard_3_element_indices = [12, 13, 14, 15, 16, 17, 18]
    for s_idx in standard_3_element_indices:
        slide = prs.slides[s_idx]
        s_num = s_idx + 1
        k, t, s = identify_header_shapes(slide)
        assert k is not None, f"Gov Slide {s_num} missing kicker shape"
        assert t is not None, f"Gov Slide {s_num} missing title shape"
        assert s is not None, f"Gov Slide {s_num} missing subtitle shape"

        # Kicker invariants
        assert abs(k.left - KICKER_LEFT) < 1000, f"Gov Slide {s_num} kicker left mismatch"
        assert abs(k.top - KICKER_TOP) < 1000, f"Gov Slide {s_num} kicker top mismatch"
        kp = k.text_frame.paragraphs[0]
        assert kp.text.isupper(), f"Gov Slide {s_num} kicker must be uppercase: {kp.text}"
        assert kp.runs[0].font.name == "Proxima Nova"
        assert kp.runs[0].font.size == Pt(9.0)
        assert kp.runs[0].font.bold is True
        assert kp.runs[0].font.color.rgb == RGBColor(0x2E, 0x5A, 0xAC)

        # Title invariants
        assert abs(t.left - TITLE_LEFT) < 1000, f"Gov Slide {s_num} title left mismatch"
        assert abs(t.top - TITLE_TOP) < 1000, f"Gov Slide {s_num} title top mismatch"
        tp = t.text_frame.paragraphs[0]
        assert tp.runs[0].font.name == "Proxima Nova"
        assert tp.runs[0].font.size == Pt(24.0)
        assert tp.runs[0].font.bold is True
        assert tp.runs[0].font.color.rgb == RGBColor(0x0F, 0x25, 0x6E)

        # Subtitle invariants
        assert abs(s.left - SUBTITLE_LEFT) < 1000, f"Gov Slide {s_num} subtitle left mismatch"
        assert abs(s.top - SUBTITLE_TOP) < 1000, f"Gov Slide {s_num} subtitle top mismatch"
        sp = s.text_frame.paragraphs[0]
        assert sp.runs[0].font.name == "Proxima Nova"
        assert sp.runs[0].font.size == Pt(9.0)
        assert sp.runs[0].font.bold is False
        assert sp.runs[0].font.color.rgb == RGBColor(0x0F, 0x25, 0x6E)


def test_htl_89_governance_deck_tables_literal_navy_header_styling(tmp_path):
    """HTL-89 / HTL-103: Verify Slides 15, 18, and 19 tables in Governance Kickoff Deck all use literal RGB #0F256E for header fills (not schemeClr)."""
    for baseline_name, baseline in [
        ("arc_genomics", load_baseline("arc_genomics")),
        ("pge_ocp", _build_pge_baseline()),
    ]:
        if baseline_name == "arc_genomics":
            baseline.project_name = "ARC Application Implementation"
            if baseline.charter:
                baseline.charter.project_name = "ARC Application Implementation"

        res = export_governance_deck(baseline, tmp_path / f"gov_{baseline_name}")
        prs = pptx.Presentation(str(res.file_path))

        # Collect all tables across the deck
        tables_with_titles = []
        for s_idx, slide in enumerate(prs.slides):
            for shape in slide.shapes:
                if shape.has_table:
                    headers = [shape.table.cell(0, c).text.strip() for c in range(len(shape.table.columns))]
                    if any(h in ["Deliverable", "Risk Description", "Owner"] for h in headers):
                        tables_with_titles.append((s_idx + 1, shape.table, headers))

        assert len(tables_with_titles) >= 3, f"Expected at least 3 tables in {baseline_name}, found {len(tables_with_titles)}"

        for s_num, tbl, headers in tables_with_titles:
            # 1. Header Row (Row 0): Check literal RGB #0F256E fill on every header cell
            for col_idx in range(len(tbl.columns)):
                cell = tbl.cell(0, col_idx)
                tcPr = cell._tc.xpath(".//a:tcPr")[0]

                # Assert literal srgbClr="0F256E" is present
                solid_fill = tcPr.xpath("./a:solidFill/a:srgbClr")
                assert solid_fill, f"{baseline_name} Slide {s_num} header cell (0, {col_idx}) missing literal srgbClr solidFill"
                assert solid_fill[0].get("val") == "0F256E", (
                    f"{baseline_name} Slide {s_num} header cell (0, {col_idx}) fill is {solid_fill[0].get('val')}, expected literal 0F256E"
                )

                # Assert NO theme color reference (schemeClr) exists
                scheme_fill = tcPr.xpath("./a:solidFill/a:schemeClr")
                assert not scheme_fill, (
                    f"{baseline_name} Slide {s_num} header cell (0, {col_idx}) must not use schemeClr: {scheme_fill[0].get('val') if scheme_fill else ''}"
                )

                # White bold Proxima Nova text
                p = cell.text_frame.paragraphs[0]
                assert p.runs[0].font.name == "Proxima Nova"
                assert p.runs[0].font.bold is True
                assert p.runs[0].font.color.rgb == RGBColor(0xFF, 0xFF, 0xFF)


def test_htl_89_client_deck_tables_literal_navy_header_styling(tmp_path):
    """HTL-89 / HTL-103: Verify Slides 6, 12, and 15 tables in Client Kickoff Deck use literal RGB #0F256E for header fills."""
    baseline = load_baseline("arc_genomics")
    baseline.project_name = "ARC Application Implementation"
    if baseline.charter:
        baseline.charter.project_name = "ARC Application Implementation"

    res = export_client_deck(baseline, tmp_path / "client_deck")
    prs = pptx.Presentation(str(res.file_path))

    table_slides = [s for s in prs.slides if any(shp.has_table for shp in s.shapes)]
    assert len(table_slides) >= 3

    for slide in table_slides:
        tbl_shape = next(s for s in slide.shapes if s.has_table)
        tbl = tbl_shape.table

        for col_idx in range(len(tbl.columns)):
            cell = tbl.cell(0, col_idx)
            tcPr = cell._tc.xpath(".//a:tcPr")[0]
            solid_fill = tcPr.xpath("./a:solidFill/a:srgbClr")
            assert solid_fill, f"Client table header cell (0, {col_idx}) missing literal solidFill"
            assert solid_fill[0].get("val") == "0F256E"
            assert not tcPr.xpath("./a:solidFill/a:schemeClr")
