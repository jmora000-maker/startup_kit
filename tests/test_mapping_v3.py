"""Test v3 A2: Deliverable and work package mapping against Appendix B."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model


def test_v3_deliverable_mapping_and_work_packages(arc_baseline):
    model = build_workbook_model(arc_baseline, start_date=date(2026, 10, 5))

    # Assert 0 unmapped deliverables
    assert model.unmapped_deliverables_count == 0

    deliv_rows = [w for w in model.wbs_rows if w.element_type == "Deliverable"]
    assert len(deliv_rows) == 20

    deliv_by_id = {w.deliverable_id: w for w in deliv_rows}

    # Appendix B Milestone Deliverable Mappings:
    # M1: DEL-01, DEL-02, DEL-03, DEL-04
    for d_id in ["DEL-01", "DEL-02", "DEL-03", "DEL-04"]:
        assert deliv_by_id[d_id].milestone_id == "M1"

    # M2: DEL-05, DEL-06, DEL-07, DEL-08, DEL-09
    for d_id in ["DEL-05", "DEL-06", "DEL-07", "DEL-08", "DEL-09"]:
        assert deliv_by_id[d_id].milestone_id == "M2"
    assert deliv_by_id["DEL-09"].mapping_basis == "Phase code"

    # M3: DEL-10, DEL-11, DEL-12, DEL-13, DEL-14
    for d_id in ["DEL-10", "DEL-11", "DEL-12", "DEL-13", "DEL-14"]:
        assert deliv_by_id[d_id].milestone_id == "M3"
    assert deliv_by_id["DEL-14"].mapping_basis == "Phase code"

    # M4: DEL-15, DEL-16, DEL-17, DEL-18, DEL-19, DEL-20
    for d_id in ["DEL-15", "DEL-16", "DEL-17", "DEL-18", "DEL-19", "DEL-20"]:
        assert deliv_by_id[d_id].milestone_id == "M4"

    # Total task count: exactly 156 tasks
    task_rows = [w for w in model.wbs_rows if w.level == 4]
    assert len(task_rows) == 156
