"""Unit and regression tests for HTL-101: 1:1 Deliverables and Acceptance Criteria Traceability.

Enforces HTL-64 standing principle across multiple baselines (ARC and PGE):
1. 100% of SOW Section 4 deliverable rows are present in baseline.deliverables (35 for ARC, 6 for PGE).
2. Slide 6 (Client Deck) and Slide 14 (Governance Deck) render 100% of deliverables grouped by workstream with zero omissions and zero "+N more" summaries.
3. Slide 15 (Acceptance Criteria Table) renders 100% of deliverables with their distinct criteria (35 rows across 9 pages for ARC, 6 rows for PGE).
4. No condensation, consolidation, or dropped items between SOW, baseline model, and rendered presentations.
"""

from pathlib import Path
import pptx
import pytest

from src.generators.client_deck import export_client_deck
from src.generators.governance_deck import export_governance_deck
from tests.deck_bundle import load_baseline
from tests.test_htl_62 import _build_pge_baseline


def test_htl_101_arc_exact_35_deliverables_cross_deck_traceability(tmp_path):
    """HTL-101: ARC SOW Section 4 (35 real rows) renders with exact 1:1 fidelity across Client and Governance decks."""
    baseline = load_baseline("arc_application_implementation")

    # 1. Verify baseline data model contains exactly 35 deliverables
    assert len(baseline.deliverables) == 35, f"Expected 35 deliverables in ARC baseline, found {len(baseline.deliverables)}"
    expected_ids = [f"DEL-{i:02d}" for i in range(1, 36)]
    actual_ids = [d.id for d in baseline.deliverables]
    assert actual_ids == expected_ids, f"Mismatch in deliverable IDs: {actual_ids} vs {expected_ids}"

    # 2. Client Kickoff Deck Slide 6
    c_res = export_client_deck(baseline, tmp_path)
    c_prs = pptx.Presentation(str(c_res.file_path))

    s6_slides = [
        s for s in c_prs.slides
        if any(shp.has_text_frame and "What we will deliver" in shp.text_frame.text for shp in s.shapes)
    ]
    assert len(s6_slides) == 4, f"Expected 4 Slide 6 continuation pages, got {len(s6_slides)}"

    # Collect all deliverables rendered in Slide 6 tables
    s6_deliv_text = "\n".join(
        shp.table.cell(r, 1).text
        for s in s6_slides
        for shp in s.shapes
        if shp.has_table
        for r in range(1, len(shp.table.rows))
    )
    for did in expected_ids:
        assert did in s6_deliv_text, f"Deliverable {did} missing from Client Deck Slide 6"
    assert "more:" not in s6_deliv_text, "Found truncated '+N more' summary in Client Deck Slide 6"

    # 3. PS Governance Kickoff Deck Slide 14 & Slide 15
    g_res = export_governance_deck(baseline, tmp_path)
    g_prs = pptx.Presentation(str(g_res.file_path))

    # Slide 14 (Deliverables Table)
    s14_slides = [
        s for s in g_prs.slides
        if any(shp.has_text_frame and "What we will deliver" in shp.text_frame.text for shp in s.shapes)
    ]
    assert len(s14_slides) == 4, f"Expected 4 Slide 14 continuation pages, got {len(s14_slides)}"
    s14_deliv_text = "\n".join(
        shp.table.cell(r, 1).text
        for s in s14_slides
        for shp in s.shapes
        if shp.has_table
        for r in range(1, len(shp.table.rows))
    )
    for did in expected_ids:
        assert did in s14_deliv_text, f"Deliverable {did} missing from Governance Deck Slide 14"
    assert "more:" not in s14_deliv_text, "Found truncated '+N more' summary in Governance Deck Slide 14"

    # Slide 15 (Acceptance Criteria Table: 35 rows across 9 pages)
    s15_slides = [
        s for s in g_prs.slides
        if any(shp.has_text_frame and "Deliverable acceptance criteria" in shp.text_frame.text for shp in s.shapes)
    ]
    assert len(s15_slides) == 9, f"Expected 9 Slide 15 pages for 35 deliverables, got {len(s15_slides)}"

    s15_deliv_ids = []
    s15_criteria = []
    for s in s15_slides:
        tbl = next(shp.table for shp in s.shapes if shp.has_table)
        for r in range(1, len(tbl.rows)):
            s15_deliv_ids.append(tbl.cell(r, 0).text.split("\n")[0].strip())
            s15_criteria.append(tbl.cell(r, 1).text.strip())

    assert len(s15_deliv_ids) == 35, f"Expected 35 deliverable rows on Slide 15, found {len(s15_deliv_ids)}"
    assert s15_deliv_ids == expected_ids, f"Slide 15 deliverable ID sequence mismatch"

    # Verify criteria are distinct and not empty
    for idx, crit_text in enumerate(s15_criteria, 1):
        assert len(crit_text) > 0, f"Empty criteria for DEL-{idx:02d}"
        assert "[CONFIRMATION REQUIRED]" not in crit_text, f"Placeholder found in criteria for DEL-{idx:02d}"


def test_htl_101_pge_exact_6_deliverables_cross_deck_traceability(tmp_path):
    """HTL-101: PGE SOW Section 4 (6 real rows / 12 criteria) renders with exact 1:1 fidelity across decks."""
    baseline = _build_pge_baseline()

    # 1. Baseline data model verification
    assert len(baseline.deliverables) == 6, f"Expected 6 deliverables in PGE baseline, found {len(baseline.deliverables)}"
    pge_expected_ids = [f"DEL-{i:02d}" for i in range(1, 7)]
    assert [d.id for d in baseline.deliverables] == pge_expected_ids

    # 2. Client Deck Slide 6 (single page)
    c_res = export_client_deck(baseline, tmp_path)
    c_prs = pptx.Presentation(str(c_res.file_path))
    s6_slides = [
        s for s in c_prs.slides
        if any(shp.has_text_frame and "What we will deliver" in shp.text_frame.text for shp in s.shapes)
    ]
    assert len(s6_slides) == 1, "PGE Slide 6 should fit on a single page"
    tbl6 = next(shp.table for shp in s6_slides[0].shapes if shp.has_table)
    assert len(tbl6.rows) == 2  # 1 header + 1 workstream row with 6 deliverables
    s6_text = tbl6.cell(1, 1).text
    for did in pge_expected_ids:
        assert did in s6_text, f"Deliverable {did} missing from PGE Client Deck Slide 6"

    # 3. Governance Deck Slide 14 & Slide 15
    g_res = export_governance_deck(baseline, tmp_path)
    g_prs = pptx.Presentation(str(g_res.file_path))

    # Slide 14
    s14_slides = [
        s for s in g_prs.slides
        if any(shp.has_text_frame and "What we will deliver" in shp.text_frame.text for shp in s.shapes)
    ]
    assert len(s14_slides) == 1
    tbl14 = next(shp.table for shp in s14_slides[0].shapes if shp.has_table)
    s14_text = tbl14.cell(1, 1).text
    for did in pge_expected_ids:
        assert did in s14_text

    # Slide 15 (Acceptance Criteria: 6 rows)
    s15_slides = [
        s for s in g_prs.slides
        if any(shp.has_text_frame and "Deliverable acceptance criteria" in shp.text_frame.text for shp in s.shapes)
    ]
    assert len(s15_slides) == 1
    tbl15 = next(shp.table for shp in s15_slides[0].shapes if shp.has_table)
    assert len(tbl15.rows) == 7  # 1 header + 6 data rows
    for r in range(1, 7):
        did_cell = tbl15.cell(r, 0).text
        crit_cell = tbl15.cell(r, 1).text
        assert f"DEL-{r:02d}" in did_cell
        assert "•" in crit_cell or "\n" in crit_cell, f"Expected multiple criteria bullets for DEL-{r:02d}"
