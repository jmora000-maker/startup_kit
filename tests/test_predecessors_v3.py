"""Test v3 A3: Milestone predecessors and exclusion of acceptance links from Client Prerequisites."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model


def test_v3_milestone_predecessors(arc_baseline):
    model = build_workbook_model(arc_baseline, start_date=date(2026, 10, 5))

    ms_rows = [s for s in model.schedule_rows if s.row_type == "Milestone"]
    assert len(ms_rows) == 4

    m1, m2, m3, m4 = ms_rows

    assert m1.milestone_id == "M1"
    assert m1.predecessor == ""

    assert m2.milestone_id == "M2"
    assert m2.predecessor == "M1"

    assert m3.milestone_id == "M3"
    assert m3.predecessor == "M2"

    assert m4.milestone_id == "M4"
    assert m4.predecessor == "M3"

    # None of the "... accepted" entries appear in Client Prerequisites
    for s in ms_rows:
        assert "accepted" not in s.client_prerequisites.lower()
        assert "p1 foundation accepted" not in s.client_prerequisites.lower()
        assert "p2a services and data accepted" not in s.client_prerequisites.lower()
        assert "p2b application surface accepted" not in s.client_prerequisites.lower()

    # Check WBS Client Prerequisites tasks
    prereq_tasks = [w for w in model.wbs_rows if w.level == 4 and w.name.startswith("Confirm:")]
    assert len(prereq_tasks) == 12  # M1: 3, M2: 4, M3: 2, M4: 3
    for t in prereq_tasks:
        assert "accepted" not in t.name.lower()
