"""Comprehensive unit and regression tests for HTL-100: Exhaustive Deliverables Table.

HTL-100 Requirements:
- Replaces summarized left-column workstream boxes on Slide 6 (Client Deck) and Slide 14 (Governance Deck)
  with an exhaustive 2-column table ("Workstream / Feature Set" and "Outcomes / Deliverables").
- Visual table styling matches Slide 15 Acceptance Criteria (navy #041133 header, white bordered body cells #D0D5DD, Proxima Nova font hierarchy).
- Multi-page pagination when deliverable count exceeds single-slide capacity (e.g. ARC with 20 deliverables).
- 100% of deliverables appear without truncation or '+N more' summaries.
- Right dark panel (Solution Overview & Out of Scope) is preserved intact in fixed positions.
- Downstream slide re-indexing verified across single-page (PGE) and multi-page (ARC) baselines.
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
    StartupKitBaseline,
)
from src.generators.client_deck import export_client_deck
from src.generators.client_deck.builder import build_client_deck_model
from src.generators.client_deck.writer import (
    chunk_workstreams_for_deliverables_table,
    write_client_deck,
)
from src.generators.governance_deck import export_governance_deck
from src.generators.governance_deck.builder import build_governance_deck_model
from src.generators.governance_deck.writer import write_governance_deck
from tests.deck_bundle import load_baseline
from tests.test_htl_62 import _build_pge_baseline


def test_htl_100_pge_single_page_deliverables_table(tmp_path):
    """HTL-100: PGE baseline (6 deliverables) renders as a single-page 2-column table on Client Slide 6 and Gov Slide 14."""
    baseline = _build_pge_baseline()

    # 1. Client Deck
    c_out = tmp_path / "pge_client.pptx"
    c_res = export_client_deck(baseline, tmp_path)
    c_prs = pptx.Presentation(str(c_res.file_path))

    # Single page on Slide 6 -> total slides = 16
    assert c_res.slides_count == 16
    slide6 = c_prs.slides[5]

    # Check 2-column table exists
    tbl_shape = next(s for s in slide6.shapes if s.has_table)
    table = tbl_shape.table
    assert len(table.columns) == 2
    assert table.cell(0, 0).text == "Workstream / Feature Set"
    assert table.cell(0, 1).text == "Outcomes / Deliverables"
    assert tbl_shape.width == 5240000
    assert table.columns[0].width == 2150000
    assert table.columns[1].width == 3090000

    # Verify no stray lines or old shapes remain on Client Slide 6
    assert not any(s.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.LINE for s in slide6.shapes)
    all_s6_text = " ".join([s.text_frame.text for s in slide6.shapes if s.has_text_frame])
    assert "Rimage" not in all_s6_text
    assert "EnterpriseOne" not in all_s6_text
    assert "JD Edwards" not in all_s6_text

    # Verify header formatting
    h_tf = table.cell(0, 0).text_frame
    assert h_tf.paragraphs[0].runs[0].font.bold is True
    assert h_tf.paragraphs[0].runs[0].font.name == "Proxima Nova"

    # All 6 deliverables DEL-01 to DEL-06 present in table
    table_text = "\n".join(c.text for r in table.rows for c in r.cells)
    assert "DEL-01" in table_text
    assert "DEL-02" in table_text
    assert "DEL-03" in table_text
    assert "DEL-04" in table_text
    assert "DEL-05" in table_text
    assert "DEL-06" in table_text
    assert "more:" not in table_text

    # Right dark panel preserved without overlap
    s193 = next(s for s in slide6.shapes if s.shape_id == 193 or (s.has_text_frame and "Solution Overview" in s.text_frame.text))
    s202 = next(s for s in slide6.shapes if s.shape_id == 202 or (s.has_text_frame and "Out of Scope:" in s.text_frame.text))
    assert s193.left == 6347125
    assert s202.left == 6347125
    assert s193.left - (tbl_shape.left + tbl_shape.width) > 600000

    # 2. Governance Deck
    g_res = export_governance_deck(baseline, tmp_path)
    g_prs = pptx.Presentation(str(g_res.file_path))

    # PGE: Slide 15 is single page, Slide 16 is single page -> total slides = 20 (HTL-109)
    assert g_res.slides_count == 20
    gov_s14 = g_prs.slides[14]

    g_tbl_shape = next(s for s in gov_s14.shapes if s.has_table)
    g_table = g_tbl_shape.table
    assert len(g_table.columns) == 2
    assert g_tbl_shape.width == 5240000
    assert g_table.columns[0].width == 2150000
    assert g_table.columns[1].width == 3090000

    # Verify no stray lines or contaminating template text on Gov Slide 14
    for shp in gov_s14.shapes:
        assert shp.shape_id not in (401, 402, 403, 404, 405)
    all_g14_text = " ".join([s.text_frame.text for s in gov_s14.shapes if s.has_text_frame])
    assert "Rimage" not in all_g14_text, "Found contaminating Rimage template text on Gov Slide 14"
    assert "EnterpriseOne" not in all_g14_text, "Found contaminating EnterpriseOne template text on Gov Slide 14"
    assert "JD Edwards" not in all_g14_text, "Found contaminating JD Edwards template text on Gov Slide 14"
    assert "landing zone" not in all_g14_text, "Found contaminating landing zone text on Gov Slide 14"

    # Verify clearance between table right edge and right dark panel
    g_so = next(s for s in gov_s14.shapes if s.shape_id == 395 or (s.has_text_frame and "Solution Overview" in s.text_frame.text))
    assert g_so.left == 6347125
    assert g_so.left - (g_tbl_shape.left + g_tbl_shape.width) > 600000

    g_table_text = "\n".join(c.text for r in g_table.rows for c in r.cells)
    assert "DEL-01" in g_table_text
    assert "DEL-06" in g_table_text
    assert "more:" not in g_table_text


def test_htl_100_arc_multi_page_deliverables_table(tmp_path):
    """HTL-100: ARC baseline (35 deliverables) paginates across multiple pages with 100% deliverable coverage."""
    baseline = load_baseline("arc_application_implementation")

    # 1. Client Deck
    c_res = export_client_deck(baseline, tmp_path)
    c_prs = pptx.Presentation(str(c_res.file_path))

    # Find all Slide 6 deliverable pages
    s6_slides = [
        s for s in c_prs.slides
        if any(shp.has_text_frame and "What we will deliver" in shp.text_frame.text for shp in s.shapes)
    ]
    assert len(s6_slides) == 4

    # Check continuation headers
    subtitles = []
    for s in s6_slides:
        for shp in s.shapes:
            if shp.has_text_frame and "Contracted project deliverables" in shp.text_frame.text:
                subtitles.append(shp.text_frame.text)
    assert any("Part 1 of 4" in st for st in subtitles)
    assert any("Part 2 of 4" in st for st in subtitles)
    assert any("Part 3 of 4" in st for st in subtitles)
    assert any("Part 4 of 4" in st for st in subtitles)

    # 100% of deliverables DEL-01 to DEL-35 present across all table pages
    all_table_text = "\n".join(
        c.text
        for s in s6_slides
        for shp in s.shapes
        if shp.has_table
        for r in shp.table.rows
        for c in r.cells
    )
    for i in range(1, 36):
        assert f"DEL-{i:02d}" in all_table_text, f"Missing deliverable DEL-{i:02d}"
    assert "more:" not in all_table_text

    # Every page preserves the right dark panel
    for s in s6_slides:
        assert any(shp.shape_id == 193 or (shp.has_text_frame and "Solution Overview" in shp.text_frame.text) for shp in s.shapes)
        assert any(shp.shape_id == 202 or (shp.has_text_frame and "Out of Scope:" in shp.text_frame.text) for shp in s.shapes)

    # 2. Governance Deck
    g_res = export_governance_deck(baseline, tmp_path)
    g_prs = pptx.Presentation(str(g_res.file_path))

    # Total slides = 31 (HTL-109)
    assert g_res.slides_count == 31
    gov_s14_slides = [
        s for s in g_prs.slides
        if any(shp.has_text_frame and "What we will deliver" in shp.text_frame.text for shp in s.shapes)
    ]
    assert len(gov_s14_slides) == 4

    all_gov_table_text = "\n".join(
        c.text
        for s in gov_s14_slides
        for shp in s.shapes
        if shp.has_table
        for r in shp.table.rows
        for c in r.cells
    )
    for i in range(1, 36):
        assert f"DEL-{i:02d}" in all_gov_table_text, f"Missing Governance DEL-{i:02d}"
    assert "more:" not in all_gov_table_text


def test_htl_100_downstream_slide_reindexing_integrity(tmp_path):
    """HTL-100: Validates downstream slide contents (Risk Register, Next Steps, Acceptance Narrative) write to correct shifted positions."""
    baseline = load_baseline("arc_application_implementation")

    # 1. Client Deck
    c_res = export_client_deck(baseline, tmp_path)
    c_prs = pptx.Presentation(str(c_res.file_path))

    # Total 4 pages on Slide 6:
    # Indices 5, 6, 7, 8: Slide 6 pages
    # Index 10 + 4 = 14: Slide 12 (Risk Register)
    # Index 13 + 4 = 17: Slide 15 (Next Steps)
    slide12 = c_prs.slides[14]
    tbl12 = next(s.table for s in slide12.shapes if s.has_table)
    assert "Risk" in tbl12.cell(0, 0).text

    slide15 = c_prs.slides[17]
    tbl15 = next(s.table for s in slide15.shapes if s.has_table)
    assert "Action" in tbl15.cell(0, 1).text

    # 2. Governance Deck
    g_res = export_governance_deck(baseline, tmp_path)
    g_prs = pptx.Presentation(str(g_res.file_path))

    # Total 4 pages on Slide 15 + 9 pages on Slide 16:
    # Indices 14..17: Slide 15 pages (What We Deliver)
    # Indices 18..26: Slide 16 pages (Acceptance Criteria)
    # Index 27: Slide 17 (How Milestone Acceptance Works)
    # Index 28: Slide 18 (Approach)
    # Index 29: Slide 19 (Initial Risk Register)
    # Index 30: Slide 20 (Next Steps)
    slide16 = g_prs.slides[27]
    assert any("How milestone acceptance works" in shp.text_frame.text for shp in slide16.shapes if shp.has_text_frame)

    slide17 = g_prs.slides[28]
    assert any("Approach" in shp.text_frame.text for shp in slide17.shapes if shp.has_text_frame)

    slide18 = g_prs.slides[29]
    tbl18 = next(s.table for s in slide18.shapes if s.has_table)
    assert "Risk" in tbl18.cell(0, 0).text

    slide19 = g_prs.slides[30]
    tbl19 = next(s.table for s in slide19.shapes if s.has_table)
    assert "Action" in tbl19.cell(0, 1).text


def test_htl_100_table_formatting_and_slide15_clean_canvas(tmp_path):
    """HTL-100: Validates uniform header row heights, aligned cell margins, and clean Slide 15 canvas without dark panel."""
    baseline = load_baseline("arc_application_implementation")

    # 1. Governance Deck: Slide 14 and Slide 15 verification
    g_res = export_governance_deck(baseline, tmp_path)
    g_prs = pptx.Presentation(str(g_res.file_path))

    # Slide 14 pages (Deliverables Table)
    s14_slides = [
        s for s in g_prs.slides
        if any(shp.has_text_frame and "What we will deliver" in shp.text_frame.text for shp in s.shapes)
    ]
    assert len(s14_slides) == 4
    for s in s14_slides:
        tbl = next(shp.table for shp in s.shapes if shp.has_table)
        assert tbl.rows[0].height == Pt(22)
        # Check header cell margins match data cell margins
        for c_idx in range(len(tbl.columns)):
            tcPr = tbl.cell(0, c_idx)._tc.xpath(".//a:tcPr")[0]
            assert tcPr.get("marL") == "36576"
            assert tcPr.get("marR") == "36576"
            assert tcPr.get("marT") == "18288"
            assert tcPr.get("marB") == "18288"

    # Slide 15 pages (Acceptance Criteria Table: 9 continuation pages)
    s15_slides = [
        s for s in g_prs.slides
        if any(shp.has_text_frame and "Deliverable acceptance criteria" in shp.text_frame.text for shp in s.shapes)
    ]
    assert len(s15_slides) == 9
    for page_idx, s in enumerate(s15_slides, 1):
        # Must use clean DEFAULT layout with zero layout background shapes
        assert s.slide_layout.name == "DEFAULT", f"Slide 15 Part {page_idx} using non-clean layout: {s.slide_layout.name}"
        assert len(s.slide_layout.shapes) == 0, f"Slide 15 Part {page_idx} has {len(s.slide_layout.shapes)} layout shapes"

        # Must have no Solution Overview or Out of Scope shapes
        assert not any(
            shp.has_text_frame and ("Solution Overview" in shp.text_frame.text or "Out of Scope" in shp.text_frame.text)
            for shp in s.shapes
        ), f"Slide 15 Part {page_idx} contains unexpected dark panel text"

        tbl = next(shp.table for shp in s.shapes if shp.has_table)
        assert tbl.rows[0].height == Pt(22), f"Slide 15 Part {page_idx} header height is {tbl.rows[0].height}, expected Pt(22)"

        # Check cell margins
        for c_idx in range(len(tbl.columns)):
            tcPr = tbl.cell(0, c_idx)._tc.xpath(".//a:tcPr")[0]
            assert tcPr.get("marL") == "36576"
            assert tcPr.get("marR") == "36576"
            assert tcPr.get("marT") == "18288"
            assert tcPr.get("marB") == "18288"
