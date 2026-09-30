"""Test v3 A6: Milestone acceptance review task from communications plan."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model


def test_v3_acceptance_review_comm_routing(arc_baseline):
    model = build_workbook_model(arc_baseline, start_date=date(2026, 10, 5))

    # All 4 Milestone Acceptance packages should use COM-06 Milestone Acceptance Review
    accept_pkgs = [w for w in model.wbs_rows if w.element_type == "Work Package" and "Milestone Acceptance" in w.name]
    assert len(accept_pkgs) == 4

    for pkg in accept_pkgs:
        ms_id = pkg.milestone_id
        tasks = [w for w in model.wbs_rows if w.level == 4 and w.wbs_code.startswith(pkg.wbs_code + ".")]
        assert len(tasks) == 6

        # Task 3 should be Milestone Acceptance Review with source COM-06
        review_task = tasks[2]
        assert "Milestone Acceptance Review" in review_task.name
        assert review_task.source == "Baseline - Communications Plan"
        assert review_task.source_id == "COM-06"
        assert review_task.owner == "Delivery Manager"
