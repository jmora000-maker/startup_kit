"""Test phase label parsing, week-range date calculation, delivery ordering, and predecessor links."""

from datetime import date
from src.generators.pmo_workbook.workstreams import parse_milestone_phase
from src.generators.pmo_workbook.builder import (
    build_workbook_model,
    parse_week_range,
    calculate_start_date,
)


def test_phase_label_parsing():
    desc1 = "P1 Foundation accepted: micro-frontend shell, Azure AD/MSAL authentication, E2E test harness (est. weeks 1–6)."
    p1 = parse_milestone_phase(desc1)
    assert p1.phase_code == "P1"
    assert p1.workstream_name == "P1 Foundation"
    assert p1.milestone_name == "P1 Foundation accepted"
    assert p1.has_phase_label is True
    assert "(est. weeks 1–6)" not in p1.milestone_scope_clean

    desc2 = "P2a Services and Data accepted: FastAPI search and async services (est. weeks 7–16)."
    p2 = parse_milestone_phase(desc2)
    assert p2.phase_code == "P2a"
    assert p2.workstream_name == "P2a Services and Data"
    assert p2.milestone_name == "P2a Services and Data accepted"

    desc3 = "P2b Application Surface accepted: ARC micro-frontend search and detail views (est. weeks 17–21)."
    p3 = parse_milestone_phase(desc3)
    assert p3.phase_code == "P2b"
    assert p3.workstream_name == "P2b Application Surface"

    desc4 = "P3 Launch accepted: integration, performance, security and cross-browser testing (est. weeks 22–26)."
    p4 = parse_milestone_phase(desc4)
    assert p4.phase_code == "P3"
    assert p4.workstream_name == "P3 Launch"


def test_week_range_parsing():
    assert parse_week_range("Running weeks 1–6 from Start Date") == (1, 6)
    assert parse_week_range("est. weeks 7—16") == (7, 16)
    assert parse_week_range("weeks 17-21") == (17, 21)
    assert parse_week_range("weeks 22 to 26") == (22, 26)
    assert parse_week_range("week 5 delivery") == (5, 5)
    assert parse_week_range("No dates mentioned") is None


def test_start_date_calculation(arc_baseline):
    # With award date 2026-09-29 (Tuesday) -> first Monday on or after is 2026-10-05
    calc_start, basis = calculate_start_date(arc_baseline, user_start_date=None)
    assert calc_start == date(2026, 10, 5)
    assert "Assumed" in basis

    # With user start date override
    user_start = date(2026, 11, 2)
    calc_start2, basis2 = calculate_start_date(arc_baseline, user_start_date=user_start)
    assert calc_start2 == user_start
    assert basis2 == "Provided"


def test_arc_baseline_phases_and_predecessors(arc_baseline):
    model = build_workbook_model(arc_baseline, start_date=date(2026, 10, 5))

    # Milestones in delivery order
    ms_rows = [s for s in model.schedule_rows if s.row_type == "Milestone"]
    assert len(ms_rows) == 4
    assert [m.milestone_id for m in ms_rows] == ["M1", "M2", "M3", "M4"]

    # Dates and Predecessors
    m1 = ms_rows[0]
    assert m1.workstream == "P1 Foundation"
    assert m1.planned_start == date(2026, 10, 5)
    assert m1.planned_finish == date(2026, 11, 13)
    assert m1.date_basis == "SOW estimate, weeks 1–6"
    assert m1.predecessor == ""

    m2 = ms_rows[1]
    assert m2.workstream == "P2a Services and Data"
    assert m2.planned_start == date(2026, 11, 16)
    assert m2.planned_finish == date(2027, 1, 22)
    assert m2.date_basis == "SOW estimate, weeks 7–16"
    assert m2.predecessor == ""  # HS-4781 is a client story, not a phase

    m3 = ms_rows[2]
    assert m3.workstream == "P2b Application Surface"
    assert m3.planned_start == date(2027, 1, 25)
    assert m3.planned_finish == date(2027, 2, 26)
    assert m3.date_basis == "SOW estimate, weeks 17–21"
    assert m3.predecessor == "M2"

    m4 = ms_rows[3]
    assert m4.workstream == "P3 Launch"
    assert m4.planned_start == date(2027, 3, 1)
    assert m4.planned_finish == date(2027, 4, 2)
    assert m4.date_basis == "SOW estimate, weeks 22–26"
    assert m4.predecessor == "M3"
