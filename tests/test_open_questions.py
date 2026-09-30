"""Test v3 A8: Open questions routing to RAID Log with Q-01 to Q-18 IDs."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model


def test_v3_open_questions_in_raid(arc_baseline):
    model = build_workbook_model(arc_baseline, start_date=date(2026, 10, 5))

    q_rows = [r for r in model.raid_rows if r.category == "Open Question"]
    # 21 in baseline, 3 unassigned-role questions dropped -> exactly 18 rows
    assert len(q_rows) == 18

    # Source IDs match Q-01 to Q-18
    expected_ids = [f"Q-{i:02d}" for i in range(1, 19)]
    actual_ids = [r.source_id for r in q_rows]
    assert actual_ids == expected_ids

    for r in q_rows:
        assert r.type == "Issue"
        assert r.category == "Open Question"
        assert r.owner == "Talent PM"
        assert r.status == "Open"
        assert r.source == "Baseline - Open Questions"
        assert "role is unassigned" not in r.description.lower()
