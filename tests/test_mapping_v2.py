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
    assert "micro-frontend" in tokens
    assert "micro" in tokens
    assert "frontend" in tokens
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

    # Deliverables Level 3 in WBS
    deliv_rows = [w for w in model.wbs_rows if w.element_type == "Deliverable"]
    assert len(deliv_rows) == 19

    deliv_by_id = {w.deliverable_id: w for w in deliv_rows}

    # Appendix B Milestone Deliverable Mappings:
    # M1: DEL-01 (Scope match, Build), DEL-02 (Scope match, Integration), DEL-03 (Scope match, Test),
    #     DEL-04 (Scope match, Test), DEL-05 (Scope match, Test), DEL-09 (Scope match, Test)
    for d_id in ["DEL-01", "DEL-02", "DEL-03", "DEL-04", "DEL-05", "DEL-09"]:
        assert deliv_by_id[d_id].milestone_id == "M1", f"{d_id} expected under M1, got {deliv_by_id[d_id].milestone_id}"

    # M2: DEL-06 (Scope match, Build), DEL-07 (Scope match, Analysis), DEL-08 (Scope match, Integration)
    for d_id in ["DEL-06", "DEL-07", "DEL-08"]:
        assert deliv_by_id[d_id].milestone_id == "M2", f"{d_id} expected under M2, got {deliv_by_id[d_id].milestone_id}"

    # M3: DEL-10 (Scope match, Build), DEL-11 (Scope match, Integration), DEL-12 (Scope match, Test), DEL-13 (Phase code, Test)
    for d_id in ["DEL-10", "DEL-11", "DEL-12", "DEL-13"]:
        assert deliv_by_id[d_id].milestone_id == "M3", f"{d_id} expected under M3, got {deliv_by_id[d_id].milestone_id}"
    assert deliv_by_id["DEL-13"].mapping_basis == "Phase code"

    # M4: DEL-14 (Scope match, Test), DEL-15 (Scope match, Test), DEL-16 (Scope match, Test),
    #     DEL-17 (Scope match, Test), DEL-18 (Backlog match, Analysis), DEL-19 (Scope match, Documentation)
    for d_id in ["DEL-14", "DEL-15", "DEL-16", "DEL-17", "DEL-18", "DEL-19"]:
        assert deliv_by_id[d_id].milestone_id == "M4", f"{d_id} expected under M4, got {deliv_by_id[d_id].milestone_id}"
    assert deliv_by_id["DEL-18"].mapping_basis == "Backlog match"

    # Check work types in deliverable notes
    assert "Work type: Build" in deliv_by_id["DEL-01"].notes
    assert "Work type: Integration" in deliv_by_id["DEL-02"].notes
    assert "Work type: Test" in deliv_by_id["DEL-03"].notes
    assert "Work type: Analysis" in deliv_by_id["DEL-07"].notes
    assert "Work type: Integration" in deliv_by_id["DEL-08"].notes
    assert "Work type: Test" in deliv_by_id["DEL-09"].notes
    assert "Work type: Build" in deliv_by_id["DEL-10"].notes
    assert "Work type: Integration" in deliv_by_id["DEL-11"].notes
    assert "Work type: Test" in deliv_by_id["DEL-12"].notes
    assert "Work type: Test" in deliv_by_id["DEL-13"].notes
    assert "Work type: Test" in deliv_by_id["DEL-14"].notes
    assert "Work type: Test" in deliv_by_id["DEL-15"].notes
    assert "Work type: Test" in deliv_by_id["DEL-16"].notes
    assert "Work type: Test" in deliv_by_id["DEL-17"].notes
    assert "Work type: Analysis" in deliv_by_id["DEL-18"].notes
    assert "Work type: Documentation" in deliv_by_id["DEL-19"].notes

    # Check Other-work packages
    other_pkgs = [w for w in model.wbs_rows if w.element_type == "Work Package" and w.name.startswith("Other ")]
    assert len(other_pkgs) == 2
    assert other_pkgs[0].name == "Other P1 Foundation work"
    assert other_pkgs[1].name == "Other P2a Services and Data work"

    # Check task counts and WP task placement
    wp_tasks = [w for w in model.wbs_rows if w.source == "Baseline - Backlog" and w.level == 4]
    assert len(wp_tasks) == 15

    # Check note when work package parent differed in baseline
    wp_04_task = next(w for w in wp_tasks if w.source_id == "WP-04")
    assert wp_04_task.deliverable_id == "DEL-06"
    assert "Baseline backlog lists parent DEL-02" in wp_04_task.notes

    # Total task count: 166 tasks
    task_rows = [w for w in model.wbs_rows if w.level == 4]
    assert len(task_rows) == 166
