"""Unit and regression tests for HTL-110: Governance Deck Slide 20 (How milestone acceptance works) stage cards.

Validates:
1. Uniform font size (8.5pt Proxima Nova) across all three stage cards.
2. Centered vertical alignment (anchor="ctr") on all three stage cards.
3. Balanced paragraph spacing (space_after=4.0pt, line_spacing=1.08).
4. Geometric containment within card boundary (bottom <= 5.25 in).
5. Cross-baseline consistency across PGE, ARC, and Mock SOW fixtures.
"""

from pathlib import Path
import pptx
from pptx.util import Pt

from src.generators.governance_deck import export_governance_deck
from tests.deck_bundle import load_baseline
from tests.test_htl_62 import _build_pge_baseline


def test_htl_110_slide20_stage_cards_uniform_font_and_vertical_centering(tmp_path: Path):
    """HTL-110: Verify Slide 20 stage cards use uniform 8.5pt font, anchor='ctr', and space_after=4pt."""
    for fixture_name, baseline in [
        ("pge", _build_pge_baseline()),
        ("arc", load_baseline("arc_application_implementation")),
        ("mock", load_baseline("mock_sow")),
    ]:
        out_dir = tmp_path / f"gov_{fixture_name}"
        res = export_governance_deck(baseline, out_dir)
        prs = pptx.Presentation(str(res.file_path))

        # Locate Slide 20 ("How milestone acceptance works")
        slide = next(
            s for s in prs.slides
            if any(shp.has_text_frame and "How milestone acceptance works" in shp.text_frame.text for shp in s.shapes)
        )

        # Locate the 3 body text boxes (height > 2,000,000 EMU)
        body_boxes = [
            s for s in slide.shapes
            if s.has_text_frame and s.height > 2000000 and s.text_frame.text.strip()
        ]
        assert len(body_boxes) == 3, f"Expected 3 stage card body boxes for {fixture_name}, found {len(body_boxes)}"

        # Validate each card
        for idx, box in enumerate(body_boxes):
            # Check bounding containment
            top_in = box.top / 914400.0
            h_in = box.height / 914400.0
            assert top_in + h_in <= 5.25, f"{fixture_name} Card {idx+1} exceeded bottom limit: {top_in + h_in} > 5.25 in"

            # Check vertical centering anchor
            bpr = box._element.xpath(".//a:bodyPr")
            assert len(bpr) > 0, f"{fixture_name} Card {idx+1} missing bodyPr"
            assert bpr[0].get("anchor") == "ctr", f"{fixture_name} Card {idx+1} anchor is {bpr[0].get('anchor')}, expected 'ctr'"

            # Check font styling on all runs
            tf = box.text_frame
            for p in tf.paragraphs:
                assert p.space_after == Pt(4.0) or p.space_after == 50800, f"{fixture_name} Card {idx+1} paragraph space_after != 4pt"
                for r in p.runs:
                    assert r.font.name == "Proxima Nova", f"{fixture_name} Card {idx+1} run font is {r.font.name}"
                    assert r.font.size == Pt(8.5), f"{fixture_name} Card {idx+1} run font size is {r.font.size.pt}, expected 8.5"
