"""Test v3 A10: Task timing and date separation for prerequisites, deliverables, and acceptance."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model


def test_v3_task_timing_table(arc_baseline):
    model = build_workbook_model(arc_baseline, start_date=date(2026, 10, 5))

    # Test M1
    # Prerequisites: 2026-10-05 to 2026-10-05
    m1_prereqs = [w for w in model.wbs_rows if w.milestone_id == "M1" and w.name == "Client Prerequisites"]
    assert len(m1_prereqs) == 1
    assert m1_prereqs[0].planned_start == date(2026, 10, 5)
    assert m1_prereqs[0].planned_finish == date(2026, 10, 5)

    # Deliverables: 2026-10-05 to 2026-11-06 (one week before finish)
    m1_delivs = [w for w in model.wbs_rows if w.milestone_id == "M1" and w.element_type == "Deliverable"]
    for d in m1_delivs:
        assert d.planned_start == date(2026, 10, 5)
        assert d.planned_finish == date(2026, 11, 6)

    # Acceptance: 2026-11-09 to 2026-11-13
    m1_accept = [w for w in model.wbs_rows if w.milestone_id == "M1" and w.level == 3 and "Milestone Acceptance" in w.name]
    assert len(m1_accept) == 1
    assert m1_accept[0].planned_start == date(2026, 11, 9)
    assert m1_accept[0].planned_finish == date(2026, 11, 13)

    # Test M2
    # Prerequisites: 2026-10-05 to 2026-11-13 (last working day before M2)
    m2_prereqs = [w for w in model.wbs_rows if w.milestone_id == "M2" and w.name == "Client Prerequisites"]
    assert len(m2_prereqs) == 1
    assert m2_prereqs[0].planned_start == date(2026, 10, 5)
    assert m2_prereqs[0].planned_finish == date(2026, 11, 13)

    # Deliverables: 2026-11-16 to 2027-01-15
    m2_delivs = [w for w in model.wbs_rows if w.milestone_id == "M2" and w.element_type == "Deliverable"]
    for d in m2_delivs:
        assert d.planned_start == date(2026, 11, 16)
        assert d.planned_finish == date(2027, 1, 15)

    # Acceptance: 2027-01-18 to 2027-01-22
    m2_accept = [w for w in model.wbs_rows if w.milestone_id == "M2" and w.level == 3 and "Milestone Acceptance" in w.name]
    assert len(m2_accept) == 1
    assert m2_accept[0].planned_start == date(2027, 1, 18)
    assert m2_accept[0].planned_finish == date(2027, 1, 22)

    # Test M3
    # Prerequisites: 2026-10-05 to 2027-01-22
    m3_prereqs = [w for w in model.wbs_rows if w.milestone_id == "M3" and w.name == "Client Prerequisites"]
    assert len(m3_prereqs) == 1
    assert m3_prereqs[0].planned_start == date(2026, 10, 5)
    assert m3_prereqs[0].planned_finish == date(2027, 1, 22)

    # Deliverables: 2027-01-25 to 2027-02-19
    m3_delivs = [w for w in model.wbs_rows if w.milestone_id == "M3" and w.element_type == "Deliverable"]
    for d in m3_delivs:
        assert d.planned_start == date(2027, 1, 25)
        assert d.planned_finish == date(2027, 2, 19)

    # Acceptance: 2027-02-22 to 2027-02-26
    m3_accept = [w for w in model.wbs_rows if w.milestone_id == "M3" and w.level == 3 and "Milestone Acceptance" in w.name]
    assert len(m3_accept) == 1
    assert m3_accept[0].planned_start == date(2027, 2, 22)
    assert m3_accept[0].planned_finish == date(2027, 2, 26)

    # Test M4
    # Prerequisites: 2026-10-05 to 2027-02-26
    m4_prereqs = [w for w in model.wbs_rows if w.milestone_id == "M4" and w.name == "Client Prerequisites"]
    assert len(m4_prereqs) == 1
    assert m4_prereqs[0].planned_start == date(2026, 10, 5)
    assert m4_prereqs[0].planned_finish == date(2027, 2, 26)

    # Deliverables: 2027-03-01 to 2027-03-26
    m4_delivs = [w for w in model.wbs_rows if w.milestone_id == "M4" and w.element_type == "Deliverable"]
    for d in m4_delivs:
        assert d.planned_start == date(2027, 3, 1)
        assert d.planned_finish == date(2027, 3, 26)

    # Acceptance: 2027-03-29 to 2027-04-02
    m4_accept = [w for w in model.wbs_rows if w.milestone_id == "M4" and w.level == 3 and "Milestone Acceptance" in w.name]
    assert len(m4_accept) == 1
    assert m4_accept[0].planned_start == date(2027, 3, 29)
    assert m4_accept[0].planned_finish == date(2027, 4, 2)
