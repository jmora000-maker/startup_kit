"""Tests for Deck structure, layouts, template removal, INV-28/INV-29, and the Your Project Kit slide (DECK-01, DECK-12, DECK-22)."""

import zipfile

import pytest

from src.tools.check_artifacts import check_deck_invariants
from tests.deck_bundle import notes_points, slide_text

KIT_FILE = "ARC_Genomics_Platform_Startup_Kit.docx"
WB_FILE = "ARC_Genomics_Platform_Project_Delivery_Workbook.xlsx"

TITLES = [
    "Project Charter",
    "Workstreams, Milestones, Deliverables and Dates",
    "Acceptance Criteria",
    "High-Risk Items",
    "Client Collaboration",
    "Your Project Kit",
]


def _violations(bundle, deck_path=None, inv=None):
    out = check_deck_invariants(deck_path or bundle["deck_path"], bundle["manifest_path"], bundle["kit"], bundle["wb"])
    return [v for v in out if inv is None or v.inv_id == inv]


def test_deck_has_seven_slide_parts_and_no_template_leftovers(arc_bundle):
    with zipfile.ZipFile(arc_bundle["deck_path"], "r") as z:
        slide_parts = [n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
        assert len(slide_parts) == 7
        for n in z.namelist():
            if n.startswith("ppt/slides/"):
                assert "DELIVERY GOVERNANCE" not in z.read(n).decode("utf-8", errors="ignore")


def test_slide_order_titles_and_layouts(arc_bundle):
    slides = list(arc_bundle["prs"].slides)
    assert len(slides) == 7
    assert slides[0].slide_layout.name == "CUSTOM_1"
    assert [s.slide_layout.name for s in slides[1:]] == ["CUSTOM_16"] * 6
    assert [s.placeholders[0].text for s in slides[1:]] == TITLES


def test_inv28_and_inv29_pass_on_the_ARC_deck(arc_bundle):
    assert [str(v) for v in _violations(arc_bundle) if v.inv_id in ("INV-28", "INV-29")] == []


def test_inv29_fails_when_template_text_is_present(arc_bundle, tmp_path):
    broken = tmp_path / "broken_deck.pptx"
    with zipfile.ZipFile(arc_bundle["deck_path"], "r") as zin, zipfile.ZipFile(broken, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "ppt/slides/slide1.xml":
                data = data.replace(b"</p:spTree>", b"<a:p><a:r><a:t>DELIVERY GOVERNANCE</a:t></a:r></a:p></p:spTree>")
            zout.writestr(item, data)
    msgs = [str(v) for v in _violations(arc_bundle, broken, "INV-29")]
    assert msgs and "DELIVERY GOVERNANCE" in msgs[0]


def test_inv29_fails_when_a_slide_part_is_missing(arc_bundle, tmp_path):
    from pptx import Presentation

    prs = Presentation(str(arc_bundle["deck_path"]))
    sld_id = prs.slides._sldIdLst[-1]
    prs.part.drop_rel(sld_id.rId)
    prs.slides._sldIdLst.remove(sld_id)
    broken = tmp_path / "six_slides.pptx"
    prs.save(str(broken))
    msgs = [str(v) for v in _violations(arc_bundle, broken)]
    assert any("INV-29" in m and "expected exactly 7" in m for m in msgs)
    assert any("INV-28" in m and "expected exactly 7" in m for m in msgs)


# --- DECK-22: Your Project Kit ------------------------------------------------------------------
def test_slide_7_names_files_exactly_as_in_the_output_folder(arc_bundle):
    text = slide_text(arc_bundle["prs"].slides[6])
    folder = {p.name for p in arc_bundle["dir"].iterdir()}
    for name in (KIT_FILE, WB_FILE):
        assert name in folder and name in text


def test_slide_7_lists_real_kit_headings_and_workbook_sheets(arc_bundle):
    slide = arc_bundle["prs"].slides[6]
    text = slide_text(slide)
    kit_headings = {p.text for p in arc_bundle["kit"].paragraphs if p.style.name.startswith("Heading")}
    notes_sources = " ".join(
        s.notes_slide.notes_text_frame.text.split("SOURCES:")[1] for s in list(arc_bundle["prs"].slides)[:6]
    )
    used = [h for h in kit_headings if h in notes_sources]
    assert used, "slides 1 to 6 name Kit sections in their SOURCES lines"
    for heading in used:
        assert heading in text
    assert "header table" not in text.lower()
    for sheet in arc_bundle["wb"].sheetnames:
        if not sheet.startswith("_"):
            assert sheet in text
    assert "Project Schedule: gates, dates, and client prerequisites" in text
    assert "WBS: deliverables and tasks, with acceptance steps" in text
    assert "RAID Log: risks, issues, dependencies, and open questions" in text


def test_slide_7_fixed_lines_and_trace_statement(arc_bundle):
    text = slide_text(arc_bundle["prs"].slides[6])
    assert "The approved project baseline: scope, deliverables and acceptance, governance, and RAID." in text
    assert "The working delivery plan: schedule by phase, tasks, and the RAID Log." in text
    assert "Every fact in this deck traces to these two documents. Each slide's notes list its sources." in text
    assert "Sections used in this deck" in text and "Sheets" in text


def test_slide_7_talking_points_and_no_readiness_content(arc_bundle):
    slide = arc_bundle["prs"].slides[6]
    assert 2 <= len(notes_points(slide)) <= 4
    assert "SOURCES:" in slide.notes_slide.notes_text_frame.text
    full = slide_text(slide) + slide.notes_slide.notes_text_frame.text
    assert "checklist" not in full.lower() and "readiness" not in full.lower()
