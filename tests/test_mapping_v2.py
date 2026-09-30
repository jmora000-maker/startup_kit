"""Test deliverable-to-milestone and work-package mapping according to v2 spec and Appendix B."""

from datetime import date
from src.generators.pmo_workbook.mapping import (
    tokenize_v2,
    compute_idf,
    compute_score,
)
from src.generators.pmo_workbook.builder import build_workbook_model


def test_tokenizer_rules():
    tokens = tokenize_v2("Micro-frontend shell/services with Azure AD authentication & tests")
    assert "micro" in tokens
    assert "frontend" in tokens
    assert "micro-frontend" not in tokens  # v3 A2: split into parts only
    assert "shell" in tokens
    assert "service" in tokens  # plural stripped
    assert "azure" in tokens
    assert "authentication" in tokens
    assert "test" in tokens  # plural stripped
    # Stop words dropped
    assert "with" not in tokens
    assert "and" not in tokens


def test_arc_baseline_mapping_against_appendix_b(arc_baseline):
    model = build_workbook_model(arc_baseline, start_date=date(2026, 10, 5))

    # Assert 0 unmapped deliverables
    assert model.unmapped_deliverables_count == 0

    # Deliverables Level 3 in WBS (20 deliverables in v3)
    deliv_rows = [w for w in model.wbs_rows if w.element_type == "Deliverable"]
    assert len(deliv_rows) == 20

    deliv_by_id = {w.deliverable_id: w for w in deliv_rows}

    # Appendix B Milestone Deliverable Mappings:
    # M1: DEL-01, DEL-02, DEL-03, DEL-04
    for d_id in ["DEL-01", "DEL-02", "DEL-03", "DEL-04"]:
        assert deliv_by_id[d_id].milestone_id == "M1", f"{d_id} expected under M1, got {deliv_by_id[d_id].milestone_id}"

    # M2: DEL-05, DEL-06, DEL-07, DEL-08, DEL-09
    for d_id in ["DEL-05", "DEL-06", "DEL-07", "DEL-08", "DEL-09"]:
        assert deliv_by_id[d_id].milestone_id == "M2", f"{d_id} expected under M2, got {deliv_by_id[d_id].milestone_id}"

    # M3: DEL-10, DEL-11, DEL-12, DEL-13, DEL-14
    for d_id in ["DEL-10", "DEL-11", "DEL-12", "DEL-13", "DEL-14"]:
        assert deliv_by_id[d_id].milestone_id == "M3", f"{d_id} expected under M3, got {deliv_by_id[d_id].milestone_id}"

    # M4: DEL-15, DEL-16, DEL-17, DEL-18, DEL-19, DEL-20
    for d_id in ["DEL-15", "DEL-16", "DEL-17", "DEL-18", "DEL-19", "DEL-20"]:
        assert deliv_by_id[d_id].milestone_id == "M4", f"{d_id} expected under M4, got {deliv_by_id[d_id].milestone_id}"

    # Check work types in deliverable notes
    assert "Work type: Build" in deliv_by_id["DEL-01"].notes
    assert "Work type: Integration" in deliv_by_id["DEL-02"].notes
    assert "Work type: Test" in deliv_by_id["DEL-03"].notes
    assert "Work type: Test" in deliv_by_id["DEL-04"].notes
    assert "Work type: Build" in deliv_by_id["DEL-05"].notes
    assert "Work type: Integration" in deliv_by_id["DEL-06"].notes
    assert "Work type: Analysis" in deliv_by_id["DEL-07"].notes
    assert "Work type: Integration" in deliv_by_id["DEL-08"].notes
    assert "Work type: Test" in deliv_by_id["DEL-09"].notes
    assert "Work type: Build" in deliv_by_id["DEL-10"].notes
    assert "Work type: Integration" in deliv_by_id["DEL-11"].notes
    assert "Work type: Test" in deliv_by_id["DEL-12"].notes
    assert "Work type: Test" in deliv_by_id["DEL-13"].notes
    assert "Work type: Integration" in deliv_by_id["DEL-14"].notes
    assert "Work type: Test" in deliv_by_id["DEL-15"].notes
    assert "Work type: Test" in deliv_by_id["DEL-16"].notes
    assert "Work type: Test" in deliv_by_id["DEL-17"].notes
    assert "Work type: Test" in deliv_by_id["DEL-18"].notes
    assert "Work type: Analysis" in deliv_by_id["DEL-19"].notes
    assert "Work type: Documentation" in deliv_by_id["DEL-20"].notes

    # Check Other-work packages (0 in v3)
    other_pkgs = [w for w in model.wbs_rows if w.element_type == "Work Package" and w.name.startswith("Other ")]
    assert len(other_pkgs) == 0

    # Check task counts and WP task placement
    wp_tasks = [w for w in model.wbs_rows if w.source == "Baseline - Backlog" and w.level == 4]
    assert len(wp_tasks) == 15

    # Check note when work package parent differed in baseline
    wp_05_task = next(w for w in wp_tasks if w.source_id == "WP-05")
    assert wp_05_task.deliverable_id == "DEL-05"
    assert "Baseline backlog lists parent DEL-02" in wp_05_task.notes

    # Total task count: 156 tasks (v3 Appendix B)
    task_rows = [w for w in model.wbs_rows if w.level == 4]
    assert len(task_rows) == 156
