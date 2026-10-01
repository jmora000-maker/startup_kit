"""Tests for SOW Stories columns and self-check reporting (spec v5 A22)."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model


def test_sow_story_columns_in_schedule_and_wbs(arc_run3):
    """Test SOW Stories column counts in Schedule and WBS."""
    model = build_workbook_model(arc_run3, start_date=date(2026, 10, 5))

    # Schedule milestones SOW Stories counts
    sched_map = {s.milestone_id: s for s in model.schedule_rows if s.row_type == "Milestone"}
    assert "M1" in sched_map
    assert "M2" in sched_map
    assert "M3" in sched_map
    assert "M4" in sched_map

    m1_stories = [s.strip() for s in sched_map["M1"].sow_stories.split(",") if s.strip()]
    m2_stories = [s.strip() for s in sched_map["M2"].sow_stories.split(",") if s.strip()]
    m3_stories = [s.strip() for s in sched_map["M3"].sow_stories.split(",") if s.strip()]
    m4_stories = [s.strip() for s in sched_map["M4"].sow_stories.split(",") if s.strip()]

    assert len(m1_stories) == 7
    assert len(m2_stories) == 11
    assert len(m3_stories) == 10
    assert len(m4_stories) == 7

    # Traceability self-check reports 35 of 35 stories
    assert "SOW Stories" in model.traceability
    story_trace = model.traceability["SOW Stories"]
    assert story_trace["in_baseline"] == 35
    assert story_trace["in_workbook"] == 35
    assert len(story_trace["missing_ids"]) == 0
