"""Tests for cross-run work item stability between runs 3, 4, and 5 (QA-07)."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model
from src.config import extract_sow_references


def test_story_phase_stability_across_runs_3_4_5(arc_run3, arc_run4, arc_run5):
    """Test that all 35 SOW stories land in the exact same milestones across runs 3, 4, and 5."""
    m3 = build_workbook_model(arc_run3, start_date=date(2026, 10, 5))
    m4 = build_workbook_model(arc_run4, start_date=date(2026, 10, 5))
    m5 = build_workbook_model(arc_run5, start_date=date(2026, 10, 5))

    # Map story ID -> milestone in run 3
    run3_story_to_ms = {}
    for s_row in m3.schedule_rows:
        if s_row.row_type == "Milestone" and s_row.sow_stories:
            for s_id in extract_sow_references(s_row.sow_stories):
                run3_story_to_ms[s_id] = s_row.milestone_id

    # Map story ID -> milestone in run 4
    run4_story_to_ms = {}
    for s_row in m4.schedule_rows:
        if s_row.row_type == "Milestone" and s_row.sow_stories:
            for s_id in extract_sow_references(s_row.sow_stories):
                run4_story_to_ms[s_id] = s_row.milestone_id

    # Map story ID -> milestone in run 5
    run5_story_to_ms = {}
    for s_row in m5.schedule_rows:
        if s_row.row_type == "Milestone" and s_row.sow_stories:
            for s_id in extract_sow_references(s_row.sow_stories):
                run5_story_to_ms[s_id] = s_row.milestone_id

    assert len(run3_story_to_ms) == 35, f"Expected 35 stories in run 3, got {len(run3_story_to_ms)}"
    assert len(run4_story_to_ms) == 35, f"Expected 35 stories in run 4, got {len(run4_story_to_ms)}"
    assert len(run5_story_to_ms) == 35, f"Expected 35 stories in run 5, got {len(run5_story_to_ms)}"

    # Compare each story
    mismatches = []
    for s_id, ms3 in run3_story_to_ms.items():
        ms4 = run4_story_to_ms.get(s_id)
        ms5 = run5_story_to_ms.get(s_id)
        if ms3 != ms4 or ms3 != ms5:
            mismatches.append(f"{s_id}: run3 in {ms3}, run4 in {ms4}, run5 in {ms5}")

    assert len(mismatches) == 0, f"Story milestone mismatches found: {mismatches}"
