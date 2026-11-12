import re
from pathlib import Path
import pptx
from pptx.util import Pt
from pptx.dml.color import RGBColor
from lxml import etree

from src.core.models import StartupKitBaseline
from src.generators.client_deck import export_client_deck
from src.generators.governance_deck import export_governance_deck
from src.generators.governance_deck.builder import _sanitize_no_names, build_slide16_model
from src.generators.deck_header import TITLE_COLOR, SUBTITLE_COLOR
from tests.deck_bundle import load_baseline
from tests.test_htl_62 import _build_pge_baseline


def test_htl_103_parenthetical_name_sanitization():
    """HTL-103: Verify _sanitize_no_names catches 'Role (Name)' and 'Role Name' patterns cleanly."""
    arc = load_baseline("arc_application_implementation")

    trigger_phrase = "Delivery Manager Saadia Iqbal notifies the Client Contact (Mike Magwire)"
    cleaned = _sanitize_no_names(trigger_phrase, baseline=arc)
    assert "Saadia" not in cleaned
    assert "Iqbal" not in cleaned
    assert "Mike" not in cleaned
    assert "Magwire" not in cleaned
    assert cleaned == "Delivery Manager notifies the Client Contact"

    case2 = "Delivery Manager (Saadia Iqbal) sends formal notice to Client Approver (Mike Magwire)"
    cleaned2 = _sanitize_no_names(case2, baseline=arc)
    assert cleaned2 == "Delivery Manager sends formal notice to Client Approver"


def test_htl_103_deck_header_colors():
    """HTL-103: Verify global deck header title and subtitle constants are canonical navy #0F256E."""
    assert TITLE_COLOR == RGBColor(0x0F, 0x25, 0x6E)
    assert SUBTITLE_COLOR == RGBColor(0x0F, 0x25, 0x6E)


def test_htl_103_governance_slide4_zero_041133():
    """HTL-103: Verify Slide 4 of the Governance Deck template has zero #041133 occurrences."""
    tpl_path = Path("templates/PS_Governance Kickoff_TEMPLATE.pptx")
    prs = pptx.Presentation(str(tpl_path))
    slide4 = prs.slides[3]

    for shp in slide4.shapes:
        xml = etree.tostring(shp._element).decode()
        assert "041133" not in xml.lower(), f"Shape {shp.shape_id} on Slide 4 contains #041133"


def test_htl_103_table_headers_and_expanded_elements_color_verification(tmp_path):
    """HTL-103: Verify all table headers, stage chevrons, badges, titles, and IDs use #0F256E."""
    arc = load_baseline("arc_application_implementation")

    # 1. Export both decks for ARC
    gov_res = export_governance_deck(arc, tmp_path / "gov_arc")
    client_res = export_client_deck(arc, tmp_path / "client_arc")

    prs_gov = pptx.Presentation(str(gov_res.file_path))
    prs_client = pptx.Presentation(str(client_res.file_path))

    # 2. Check Governance Deck Deliverables Acceptance Criteria Table Header (Slide 15)
    slide15 = next(s for s in prs_gov.slides if any(shp.has_text_frame and "Deliverable acceptance criteria" in shp.text_frame.text for shp in s.shapes))
    tbl_s15 = next(s.table for s in slide15.shapes if s.has_table)
    for c_idx in range(len(tbl_s15.columns)):
        cell = tbl_s15.cell(0, c_idx)
        tcPr = cell._tc.xpath(".//a:tcPr")[0]
        sfill = tcPr.xpath("./a:solidFill/a:srgbClr")
        assert sfill and sfill[0].get("val") == "0F256E"

    # 3. Check Governance Deck How Milestone Acceptance Works (Slide 16) Stage Chevrons & Pill Badges
    slide16 = next(s for s in prs_gov.slides if any(shp.has_text_frame and "How milestone acceptance works" in shp.text_frame.text for shp in s.shapes))
    found_0f256e_badges = 0
    flow_node_titles = ["1. Formal Submission", "2. Client Review & SLAs", "3. Decision / Defect Check", "4. Sign-Off & Deemed Accepted"]
    for shp in slide16.shapes:
        xml = etree.tostring(shp._element).decode()
        if "0f256e" in xml.lower():
            found_0f256e_badges += 1
        if shp.has_text_frame and shp.text_frame.text.strip() in flow_node_titles:
            # Confirm all 4 upper flowchart pills use solid fill #0F256E
            assert "0f256e" in xml.lower(), f"Flow node '{shp.text_frame.text.strip()}' is missing #0F256E solid fill"
    assert found_0f256e_badges >= 7, f"Expected at least 7 #0F256E elements on Gov Slide 16, found {found_0f256e_badges}"

    # 4. Check Governance Deck Approach Cards Title Color (Slide 17)
    slide17 = next(s for s in prs_gov.slides if any(shp.has_text_frame and "Approach" in shp.text_frame.text for shp in s.shapes))
    card_titles_0f256e = 0
    for shp in slide17.shapes:
        if shp.has_text_frame:
            for p in shp.text_frame.paragraphs:
                for r in p.runs:
                    if r.font.size == Pt(13) and r.font.color and r.font.color.rgb == RGBColor(0x0F, 0x25, 0x6E):
                        card_titles_0f256e += 1
    assert card_titles_0f256e == 3, f"Expected 3 #0F256E approach card titles, found {card_titles_0f256e}"

    # 5. Check Client Deck Deliverables Table Header (Slide 6)
    slide6 = next(s for s in prs_client.slides if any(shp.has_text_frame and "What we will deliver" in shp.text_frame.text for shp in s.shapes))
    tbl_s6 = next(s.table for s in slide6.shapes if s.has_table)
    for c_idx in range(len(tbl_s6.columns)):
        cell = tbl_s6.cell(0, c_idx)
        tcPr = cell._tc.xpath(".//a:tcPr")[0]
        sfill = tcPr.xpath("./a:solidFill/a:srgbClr")
        assert sfill and sfill[0].get("val") == "0F256E"

    # 6. Check Client Deck Risk Table Header (Slide 12) & Next Steps Table Header (Slide 15)
    tbl_slides = [s for s in prs_client.slides if any(shp.has_table for shp in s.shapes)]
    assert len(tbl_slides) >= 3

    for slide in tbl_slides:
        tbl = next(shp.table for shp in slide.shapes if shp.has_table)
        for c_idx in range(len(tbl.columns)):
            cell = tbl.cell(0, c_idx)
            tcPr = cell._tc.xpath(".//a:tcPr")[0]
            sfill = tcPr.xpath("./a:solidFill/a:srgbClr")
            assert sfill and sfill[0].get("val") == "0F256E"


def test_htl_103_zero_remaining_041133_across_both_generated_decks(tmp_path):
    """HTL-103: Full sweep across all shapes and slides of both generated decks ensuring zero #041133 instances."""
    for baseline_name, baseline in [
        ("arc_application_implementation", load_baseline("arc_application_implementation")),
        ("pge_ocp", _build_pge_baseline()),
    ]:
        gov_res = export_governance_deck(baseline, tmp_path / f"gov_{baseline_name}")
        client_res = export_client_deck(baseline, tmp_path / f"client_{baseline_name}")

        prs_gov = pptx.Presentation(str(gov_res.file_path))
        prs_client = pptx.Presentation(str(client_res.file_path))

        for deck_name, prs in [("Governance", prs_gov), ("Client", prs_client)]:
            for s_idx, slide in enumerate(prs.slides):
                for shp in slide.shapes:
                    xml = etree.tostring(shp._element).decode()
                    assert "041133" not in xml.lower(), (
                        f"{deck_name} Deck ({baseline_name}) Slide {s_idx+1} Shape {shp.shape_id} ({shp.name}) contains stale #041133!"
                    )


def test_htl_103_slide16_card_geometry_and_font_uniformity(tmp_path):
    """HTL-103 / HTL-110: Verify Slide 16 cards all maintain uniform 9.0pt font, top-anchoring, and uniform card height."""
    arc = load_baseline("arc_application_implementation")
    gov_res = export_governance_deck(arc, tmp_path / "gov_arc")
    prs = pptx.Presentation(str(gov_res.file_path))

    slide16 = next(s for s in prs.slides if any(shp.has_text_frame and "How milestone acceptance works" in shp.text_frame.text for shp in s.shapes))
    body_text_boxes = [s for s in slide16.shapes if s.has_text_frame and s.height > 1800000 and s.text_frame.text.strip()]
    assert len(body_text_boxes) == 3

    # Check text box body runs are all exactly 9.0pt and top-anchored
    for tb in body_text_boxes:
        bpr = tb._element.xpath(".//a:bodyPr")
        assert len(bpr) > 0
        assert bpr[0].get("anchor") == "t"
        for p in tb.text_frame.paragraphs:
            for r in p.runs:
                assert r.font.size == Pt(9.0)
