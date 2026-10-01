"""Tests for missing evidence notes on deliverable and evidence assembly tasks (spec v5 A26)."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model


def test_missing_evidence_notes(arc_run3):
    """Test all 10 deliverables with placeholder evidence gain the missing evidence note."""
    model = build_workbook_model(arc_run3, start_date=date(2026, 10, 5))

    expected_missing_deliv_ids = {
        "DEL-03", "DEL-06", "DEL-09", "DEL-10", "DEL-11",
        "DEL-13", "DEL-15", "DEL-17", "DEL-18", "DEL-19"
    }

    deliv_rows = [w for w in model.wbs_rows if w.level == 3 and w.element_type == "Deliverable"]
    for d in deliv_rows:
        if d.deliverable_id in expected_missing_deliv_ids:
            assert "Evidence not defined in baseline - agree with the client" in d.notes, f"Note missing on deliverable {d.deliverable_id}"
        else:
            assert "Evidence not defined in baseline - agree with the client" not in d.notes, f"Note unexpectedly present on deliverable {d.deliverable_id}"

    # Check 'Assemble acceptance evidence' tasks under these deliverables
    ev_tasks = [w for w in model.wbs_rows if w.level == 4 and w.name == "Assemble acceptance evidence"]
    assert len(ev_tasks) == 19
    for t in ev_tasks:
        if t.deliverable_id in expected_missing_deliv_ids:
            assert "Evidence not defined in baseline - agree with the client" in t.notes, f"Note missing on task under {t.deliverable_id}"
        else:
            assert "Evidence not defined in baseline - agree with the client" not in t.notes, f"Note unexpectedly present on task under {t.deliverable_id}"
