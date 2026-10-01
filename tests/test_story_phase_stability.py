"""Tests for cross-run work item stability between runs 3, 4, and 5 (QA-07)."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model
from src.config import extract_sow_references
from src.llm.validation import validate_and_repair_baseline


def test_story_phase_stability_across_runs_3_4_overextracted(arc_run3, arc_run4, arc_overextracted):
    """Test that all 35 SOW stories land in the exact same phases/workstreams across runs 3 and 4, and match catalogue phases in arc_overextracted (QA-07)."""
    validate_and_repair_baseline(arc_run3)
    validate_and_repair_baseline(arc_run4)
    validate_and_repair_baseline(arc_overextracted)
    m3 = build_workbook_model(arc_run3, start_date=date(2026, 10, 5))
    m4 = build_workbook_model(arc_run4, start_date=date(2026, 10, 5))
    moe = build_workbook_model(arc_overextracted, start_date=date(2026, 10, 5))

    # Map story ID -> workstream in run 3
    run3_story_to_ws = {}
    for s_row in m3.schedule_rows:
        if s_row.row_type == "Milestone" and s_row.sow_stories:
            for s_id in extract_sow_references(s_row.sow_stories):
                run3_story_to_ws[s_id] = s_row.workstream

    # Map story ID -> workstream in run 4
    run4_story_to_ws = {}
    for s_row in m4.schedule_rows:
        if s_row.row_type == "Milestone" and s_row.sow_stories:
            for s_id in extract_sow_references(s_row.sow_stories):
                run4_story_to_ws[s_id] = s_row.workstream

    # Map story ID -> workstream in arc_overextracted
    oe_story_to_ws = {}
    for s_row in moe.schedule_rows:
        if s_row.row_type == "Milestone" and s_row.sow_stories:
            for s_id in extract_sow_references(s_row.sow_stories):
                oe_story_to_ws[s_id] = s_row.workstream

    assert len(run3_story_to_ws) == 35, f"Expected 35 stories in run 3, got {len(run3_story_to_ws)}"
    assert len(run4_story_to_ws) == 35, f"Expected 35 stories in run 4, got {len(run4_story_to_ws)}"
    assert len(oe_story_to_ws) == 35, f"Expected 35 stories in arc_overextracted, got {len(oe_story_to_ws)}"

    # Compare run3 vs run4
    mismatches_3_4 = []
    for s_id, ws3 in run3_story_to_ws.items():
        ws4 = run4_story_to_ws.get(s_id)
        if ws3 != ws4:
            mismatches_3_4.append(f"{s_id}: run3 in {ws3}, run4 in {ws4}")
    assert len(mismatches_3_4) == 0, f"Story phase mismatches between run 3 and run 4: {mismatches_3_4}"

    # Verify arc_overextracted story workstream matches catalogue phase
    cat_map = {item.reference: item.phase for item in arc_overextracted.sow_stories_catalogue if item.reference}
    oe_mismatches = []
    for s_id, ws in oe_story_to_ws.items():
        expected_phase = cat_map.get(s_id)
        if expected_phase and not ws.startswith(expected_phase):
            oe_mismatches.append(f"{s_id}: expected phase {expected_phase}, got workstream {ws}")
    assert len(oe_mismatches) == 0, f"Story phase mismatches in arc_overextracted: {oe_mismatches}"
