"""Tests for multi-deliverable work package coverage notes (v6 A30)."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model


def test_multi_deliverable_coverage_notes(arc_run4):
    """Test that work packages covering multiple deliverables receive 'Also covers' and deliverable rows get 'Covered by'."""
    model = build_workbook_model(arc_run4, start_date=date(2026, 10, 5))

    # Find WP-01 task (covers DEL-03 and DEL-11 with score >= 0.30)
    wp01_task = next((w for w in model.wbs_rows if w.source_id == "WP-01"), None)
    assert wp01_task is not None
    assert "Also covers" in wp01_task.notes
    assert "DEL-03" in wp01_task.notes or "DEL-11" in wp01_task.notes

    # Find DEL-03 deliverable row
    del03_row = next((w for w in model.wbs_rows if w.element_type == "Deliverable" and w.deliverable_id == "DEL-03"), None)
    assert del03_row is not None
    assert "Covered by" in del03_row.notes
    assert "WP-01" in del03_row.notes
