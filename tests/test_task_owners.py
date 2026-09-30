"""Test v3 A5: Role owners on tasks, never blank or placeholder."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model


def test_v3_task_owners(arc_baseline):
    model = build_workbook_model(arc_baseline, start_date=date(2026, 10, 5))

    task_rows = [w for w in model.wbs_rows if w.level == 4]
    assert len(task_rows) == 156

    for t in task_rows:
        assert t.owner != "", f"Task {t.wbs_code} ({t.name}) has empty owner"
        assert "[UNASSIGNED" not in t.owner, f"Task {t.wbs_code} ({t.name}) has placeholder owner: {t.owner}"
        assert t.owner in ("Talent PM", "Delivery Manager", "Toptal Delivery Team"), f"Unexpected owner {t.owner} for task {t.wbs_code}"
