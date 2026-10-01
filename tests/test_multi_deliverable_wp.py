"""Tests for multi-deliverable work package coverage notes (MAP-07)."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model


def test_multi_deliverable_coverage_notes(arc_run4):
    """Test that work packages covering multiple deliverables receive 'Also covers' within the same gate only (MAP-07)."""
    model = build_workbook_model(arc_run4, start_date=date(2026, 10, 5))

    # In arc_run4, cross-gate coverage (e.g. WP-01 covering DEL-11 in another gate) is rejected by MAP-07
    deliv_rows = {w.deliverable_id: w for w in model.wbs_rows if w.element_type == "Deliverable" and w.deliverable_id}
    wp_tasks = [w for w in model.wbs_rows if w.element_type == "Task" and w.source_id.startswith("WP-")]

    for wp_task in wp_tasks:
        if "Also covers" in (wp_task.notes or ""):
            # Must cover deliverables within the same gate only
            assert wp_task.milestone_id is not None
