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

    # Appendix B:
    # M1: DEL-01 (Scope match, WP-01) · DEL-02 (Scope match, WP-02) · DEL-03 (Scope match, WP-03) · DEL-04 (Phase code, WP-04)
    assert deliv_by_id["DEL-01"].milestone_id == "M1"
    assert deliv_by_id["DEL-01"].mapping_basis == "Scope match"
    assert deliv_by_id["DEL-02"].milestone_id == "M1"
    assert deliv_by_id["DEL-02"].mapping_basis == "Scope match"
    assert deliv_by_id["DEL-03"].milestone_id == "M1"
    assert deliv_by_id["DEL-03"].mapping_basis == "Scope match"
    assert deliv_by_id["DEL-04"].milestone_id == "M1"
    assert deliv_by_id["DEL-04"].mapping_basis == "Phase code"

    # M2: DEL-05 (Scope match, WP-05) · DEL-06 (Scope match, WP-06) · DEL-07 (Scope match, none) · DEL-08 (Scope match, WP-07) · DEL-09 (Phase code, WP-08)
    assert deliv_by_id["DEL-05"].milestone_id == "M2"
    assert deliv_by_id["DEL-05"].mapping_basis == "Scope match"
    assert deliv_by_id["DEL-06"].milestone_id == "M2"
    assert deliv_by_id["DEL-06"].mapping_basis == "Scope match"
    assert deliv_by_id["DEL-07"].milestone_id == "M2"
    assert deliv_by_id["DEL-07"].mapping_basis == "Scope match"
    assert deliv_by_id["DEL-08"].milestone_id == "M2"
    assert deliv_by_id["DEL-08"].mapping_basis == "Scope match"
    assert deliv_by_id["DEL-09"].milestone_id == "M2"
    assert deliv_by_id["DEL-09"].mapping_basis == "Phase code"

    # M3: DEL-10 (Scope match, WP-09) · DEL-11 (Scope match, none) · DEL-12 (Scope match, WP-10) · DEL-13 (Scope match, WP-11) · DEL-14 (Phase code, WP-12)
    assert deliv_by_id["DEL-10"].milestone_id == "M3"
    assert deliv_by_id["DEL-10"].mapping_basis == "Scope match"
    assert deliv_by_id["DEL-11"].milestone_id == "M3"
    assert deliv_by_id["DEL-11"].mapping_basis == "Scope match"
    assert deliv_by_id["DEL-12"].milestone_id == "M3"
    assert deliv_by_id["DEL-12"].mapping_basis == "Scope match"
    assert deliv_by_id["DEL-13"].milestone_id == "M3"
    assert deliv_by_id["DEL-13"].mapping_basis == "Scope match"
    assert deliv_by_id["DEL-14"].milestone_id == "M3"
    assert deliv_by_id["DEL-14"].mapping_basis == "Phase code"

    # M4: DEL-15 (Scope match, WP-13) · DEL-16 (Scope match, WP-14) · DEL-17 (Scope match, none) · DEL-18 (Scope match, none) · DEL-19 (Scope match, WP-15) · DEL-20 (Scope match, none)
    assert deliv_by_id["DEL-15"].milestone_id == "M4"
    assert deliv_by_id["DEL-15"].mapping_basis == "Scope match"
    assert deliv_by_id["DEL-16"].milestone_id == "M4"
    assert deliv_by_id["DEL-16"].mapping_basis == "Scope match"
    assert deliv_by_id["DEL-17"].milestone_id == "M4"
    assert deliv_by_id["DEL-17"].mapping_basis == "Scope match"
    assert deliv_by_id["DEL-18"].milestone_id == "M4"
    assert deliv_by_id["DEL-18"].mapping_basis == "Scope match"
    assert deliv_by_id["DEL-19"].milestone_id == "M4"
    assert deliv_by_id["DEL-19"].mapping_basis == "Scope match"
    assert deliv_by_id["DEL-20"].milestone_id == "M4"
    assert deliv_by_id["DEL-20"].mapping_basis == "Scope match"

    # Total task count: exactly 156 tasks
    task_rows = [w for w in model.wbs_rows if w.level == 4]
    assert len(task_rows) == 156
