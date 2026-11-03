"""Unit tests for HTL-95, HTL-96, and HTL-97 formatting fixes.

- HTL-95: "Why we're here" card body text bumped from 8pt to 10pt on Client Deck (Slide 5)
  and Governance Deck (Slide 13), with no overflow across dense SOW content.
- HTL-96: "What we will deliver" (Client Slide 6 / Governance Slide 14) combines Solution Overview
  into one text box, uses real PPTX bullets (buChar/buAutoNum) for Out of Scope, and sets 5pt space-after on header.
- HTL-97: Governance Deck Slide 16 3 deep-dive cards body text box heights are dynamic,
  sized to fit each card's actual content rather than a fixed uniform height across all cards.
"""

from datetime import date
from pathlib import Path
import pptx
from pptx.util import Pt
from pptx.dml.color import RGBColor

from src.core.models import (
    Deliverable,
    Milestone,
    ProjectStartupCharter,
    SOWInterpretationSummary,
    StartupKitBaseline,
)
from src.generators.client_deck import export_client_deck
from src.generators.client_deck.builder import build_client_deck_model
from src.generators.client_deck.writer import write_client_deck
from src.generators.governance_deck import export_governance_deck
from src.generators.governance_deck.builder import build_governance_deck_model
from src.generators.governance_deck.writer import write_governance_deck
from tests.deck_bundle import load_baseline
from tests.test_htl_62 import _build_pge_baseline


def test_htl_95_slide5_and_slide13_font_size_10pt(tmp_path):
    """HTL-95: Verify 'Why we're here' card body text is 10pt on Client Deck Slide 5 and Governance Deck Slide 13."""
    baseline = _build_pge_baseline()

    # 1. Client Kickoff Deck (Slide 5)
    c_model = build_client_deck_model(baseline)
    c_out = tmp_path / "client_deck_s5_10pt.pptx"
    write_client_deck(c_model, c_out)

    c_prs = pptx.Presentation(str(c_out))
    slide5 = c_prs.slides[4]

    s5_shapes = [s for s in slide5.shapes if s.has_text_frame]
    card1 = next(s for s in s5_shapes if s.shape_id == 176 or "Assess PGE's cloud application" in s.text_frame.text)
    card2 = next(s for s in s5_shapes if s.shape_id == 180 or "Fragmented on-premise infrastructure" in s.text_frame.text)
    card3 = next(s for s in s5_shapes if s.shape_id == 184 or "Formal client sign-off" in s.text_frame.text)

    sz1 = card1.text_frame.paragraphs[0].runs[0].font.size.pt
    sz2 = card2.text_frame.paragraphs[0].runs[0].font.size.pt
    sz3 = card3.text_frame.paragraphs[0].runs[0].font.size.pt

    assert sz1 == 10.0, f"Expected 10.0pt for Card 1, got {sz1}pt"
    assert sz2 == 10.0, f"Expected 10.0pt for Card 2, got {sz2}pt"
    assert sz3 == 10.0, f"Expected 10.0pt for Card 3, got {sz3}pt"

    # 2. PS Governance Kickoff Deck (Slide 13)
    g_model = build_governance_deck_model(baseline)
    g_out = tmp_path / "gov_deck_s13_10pt.pptx"
    write_governance_deck(g_model, g_out)

    g_prs = pptx.Presentation(str(g_out))
    slide13 = g_prs.slides[12]

    s13_shapes = [s for s in slide13.shapes if s.has_text_frame]
    g_card1 = next(s for s in s13_shapes if s.shape_id == 176 or "Assess PGE's cloud application" in s.text_frame.text)
    g_card2 = next(s for s in s13_shapes if s.shape_id == 180 or "Fragmented on-premise infrastructure" in s.text_frame.text)
    g_card3 = next(s for s in s13_shapes if s.shape_id == 184 or "Formal client sign-off" in s.text_frame.text)

    g_sz1 = g_card1.text_frame.paragraphs[0].runs[0].font.size.pt
    g_sz2 = g_card2.text_frame.paragraphs[0].runs[0].font.size.pt
    g_sz3 = g_card3.text_frame.paragraphs[0].runs[0].font.size.pt

    assert g_sz1 == 10.0, f"Expected 10.0pt for Governance Card 1, got {g_sz1}pt"
    assert g_sz2 == 10.0, f"Expected 10.0pt for Governance Card 2, got {g_sz2}pt"
    assert g_sz3 == 10.0, f"Expected 10.0pt for Governance Card 3, got {g_sz3}pt"


def test_htl_96_slide6_combined_textbox_and_real_bullets(tmp_path):
    """HTL-96: Verify Slide 6 combines Solution Overview into 1 shape, uses 14pt headers / 10pt body, real PPTX bullets, 5pt space-after, and fixed box bounds with truncation."""
    for name, baseline in [("PGE", _build_pge_baseline()), ("ARC", load_baseline("arc_application_implementation"))]:
        c_model = build_client_deck_model(baseline)
        c_out = tmp_path / f"client_deck_s6_htl96_{name}.pptx"
        write_client_deck(c_model, c_out)

        prs = pptx.Presentation(str(c_out))
        slide6 = prs.slides[5]

        # 1. Solution Overview: Combined single text box (Shape 193)
        so_shapes = [s for s in slide6.shapes if s.shape_id == 193 or (s.has_text_frame and "Solution Overview" in s.text_frame.text)]
        assert len(so_shapes) == 1, f"Expected exactly 1 Solution Overview shape for {name}"
        so_box = so_shapes[0]

        # Shape 194 should be removed
        old_body_shapes = [s for s in slide6.shapes if s.shape_id == 194]
        assert len(old_body_shapes) == 0, f"Shape 194 should be removed for {name}"

        # Fixed coordinates and dimensions
        assert so_box.top == 580000
        assert so_box.left == 6347125
        assert so_box.width == 2600000
        assert so_box.height == 2150000

        tf_so = so_box.text_frame
        assert len(tf_so.paragraphs) == 2
        # Header: 14pt bold
        assert tf_so.paragraphs[0].text == "Solution Overview"
        assert tf_so.paragraphs[0].runs[0].font.bold is True
        assert tf_so.paragraphs[0].runs[0].font.size == Pt(14)
        assert tf_so.paragraphs[0].runs[0].font.color.rgb == RGBColor(255, 255, 255)
        assert tf_so.paragraphs[0].space_after == Pt(5) or tf_so.paragraphs[0].space_after == 63500

        # Body: 10pt Proxima Nova
        assert len(tf_so.paragraphs[1].text) > 0
        assert tf_so.paragraphs[1].runs[0].font.size == Pt(10)
        assert tf_so.paragraphs[1].runs[0].font.bold is False
        assert tf_so.paragraphs[1].runs[0].font.color.rgb == RGBColor(255, 255, 255)

        # 2. Out of Scope: Real PPTX bullets, 14pt header, 10pt body, and 5pt space-after
        oos_shapes = [s for s in slide6.shapes if s.shape_id == 202 or (s.has_text_frame and "Out of Scope:" in s.text_frame.text)]
        assert len(oos_shapes) == 1, f"Expected exactly 1 Out of Scope shape for {name}"
        oos_box = oos_shapes[0]
        assert oos_box.top == 2850000
        assert oos_box.left == 6347125
        assert oos_box.width == 2600000
        assert oos_box.height == 1850000
        tf_oos = oos_box.text_frame

        # Header paragraph: 14pt bold & 5pt space-after
        p0 = tf_oos.paragraphs[0]
        assert p0.text == "Out of Scope:"
        assert p0.runs[0].font.bold is True
        assert p0.runs[0].font.size == Pt(14)
        assert p0.runs[0].font.color.rgb == RGBColor(255, 255, 255)
        assert p0.space_after == Pt(5) or p0.space_after == 63500

        # Bullet paragraphs: XML buChar / buClr formatting and 10pt size
        assert len(tf_oos.paragraphs) > 1
        for p in tf_oos.paragraphs[1:]:
            pPr = p._p.xpath("./a:pPr")
            assert len(pPr) > 0, "Missing pPr on Out of Scope item"
            buChar = pPr[0].xpath("./a:buChar")
            assert len(buChar) > 0, "Missing real bullet buChar in Out of Scope item"
            assert not p.text.startswith("•"), "Found raw typed bullet character in text"
            assert not p.text.startswith("●"), "Found raw typed bullet character in text"
            buSzPts = pPr[0].xpath("./a:buSzPts")
            if buSzPts:
                assert buSzPts[0].attrib.get("val") == "1000", "Bullet size should be 10pt (1000)"

        # 3. Position check: Out of Scope is positioned below Solution Overview
        assert oos_box.top >= so_box.top + so_box.height, f"OOS ({oos_box.top}) must start below SO ({so_box.top + so_box.height})"

        # 4. No overflow past bottom slide boundary (5143500 EMU)
        slide_height = prs.slide_height or 5143500
        total_bottom = oos_box.top + oos_box.height
        assert total_bottom <= slide_height, f"{name} Out of Scope overflows bottom: {total_bottom} > {slide_height}"


def test_htl_105_slide16_uniform_card_geometry_and_font_size(tmp_path):
    """HTL-105 (overriding HTL-97): Verify Slide 16 cards have uniform text box heights and uniform 7.5pt font size across all 3 cards."""
    # Build baseline with different step counts across cards
    from tests.test_htl_74 import ARC_12_STEP_NARRATIVE
    baseline = load_baseline("arc_application_implementation")
    baseline.sow_interpretation.acceptance_process_narrative = ARC_12_STEP_NARRATIVE

    g_model = build_governance_deck_model(baseline)
    g_out = tmp_path / "gov_deck_s16_htl105.pptx"
    write_governance_deck(g_model, g_out)

    prs = pptx.Presentation(str(g_out))
    slide16 = next(s for s in prs.slides if any(shape.has_text_frame and ("How milestone acceptance works" in shape.text_frame.text or "Acceptance Workflow" in shape.text_frame.text) for shape in s.shapes))

    # Find the 3 body text boxes
    c1_box = next(s for s in slide16.shapes if s.has_text_frame and "Inputs ready:" in s.text_frame.text)
    c2_box = next(s for s in slide16.shapes if s.has_text_frame and "Triage:" in s.text_frame.text)
    c3_box = next(s for s in slide16.shapes if s.has_text_frame and "Deemed accepted:" in s.text_frame.text)

    # All 3 text boxes must share the exact same uniform height and top position (HTL-105)
    h1 = c1_box.height
    h2 = c2_box.height
    h3 = c3_box.height

    assert h1 == h2 == h3, f"Expected uniform height across all cards: Card 1 ({h1}), Card 2 ({h2}), Card 3 ({h3})"

    # All 3 cards must share the exact same uniform 7.5pt body font size
    sz1 = c1_box.text_frame.paragraphs[0].runs[0].font.size.pt
    sz2 = c2_box.text_frame.paragraphs[0].runs[0].font.size.pt
    sz3 = c3_box.text_frame.paragraphs[0].runs[0].font.size.pt

    assert sz1 == sz2 == sz3 == 7.5, f"Expected uniform 7.5pt font size, got {sz1}, {sz2}, {sz3}"
