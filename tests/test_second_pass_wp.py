"""Tests for second-pass work package assignment (v6 A29)."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model


def test_second_pass_wp10_attachment(arc_run4):
    """Test that WP-10 attaches to DEL-12 via second pass and eliminates Other work in M3."""
    model = build_workbook_model(arc_run4, start_date=date(2026, 10, 5))

    # Check DEL-12 package in WBS
    deliv_12_tasks = [w for w in model.wbs_rows if w.deliverable_id == "DEL-12" and w.level == 4]
    
    # WP-10 is the core task under DEL-12
    wp10_task = next((t for t in deliv_12_tasks if t.source_id == "WP-10"), None)
    assert wp10_task is not None
    assert wp10_task.name == "Haplotype Search, Visualization and API features"

    # Verify no Other-work package exists in M3
    other_work_tasks = [w for w in model.wbs_rows if "Other" in w.workstream and "work" in w.name.lower()]
    assert len(other_work_tasks) == 0

    # Total tasks = 150
    tasks = [w for w in model.wbs_rows if w.level == 4]
    assert len(tasks) == 150


def test_runs_1_to_3_unchanged(arc_run1, arc_run2, arc_run3):
    """Test that runs 1, 2, and 3 task counts and mappings remain unchanged."""
    m1 = build_workbook_model(arc_run1, start_date=date(2026, 10, 5))
    tasks1 = [w for w in m1.wbs_rows if w.level == 4]
    assert len(tasks1) == 156

    m2 = build_workbook_model(arc_run2, start_date=date(2026, 10, 5))
    tasks2 = [w for w in m2.wbs_rows if w.level == 4]
    assert len(tasks2) == 153

    m3 = build_workbook_model(arc_run3, start_date=date(2026, 10, 5))
    tasks3 = [w for w in m3.wbs_rows if w.level == 4]
    assert len(tasks3) == 165
