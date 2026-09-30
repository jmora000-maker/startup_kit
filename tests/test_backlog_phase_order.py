"""Tests for backlog phase-order detection (spec v4 A14)."""

from datetime import date
from src.core.models import WorkPackageSeed, Milestone, Deliverable, SourceReference
from src.generators.pmo_workbook.mapping import detect_backlog_phase_order, map_deliverables_to_milestones_v2
from src.generators.pmo_workbook.builder import build_workbook_model


def test_backlog_phase_order_detection_on(arc_run2):
    """Test backlog phase-order detection is ON for arc_run2."""
    is_detected, parents = detect_backlog_phase_order(arc_run2.backlog_seed, arc_run2.milestones, arc_run2.deliverables)
    assert is_detected is True
    assert parents == ["DEL-01", "DEL-02", "DEL-03", "DEL-04"]


def test_backlog_phase_order_detection_off_when_mismatched(arc_run2):
    """Test backlog phase-order detection is OFF when parent IDs are mixed/unordered."""
    wps = [
        WorkPackageSeed(id="WP-01", title="Setup", parent_deliverable_id="DEL-02", preliminary_sequence=1),
        WorkPackageSeed(id="WP-02", title="Auth", parent_deliverable_id="DEL-01", preliminary_sequence=2),
    ]
    is_detected, _ = detect_backlog_phase_order(wps, arc_run2.milestones, arc_run2.deliverables)
    assert is_detected is False


def test_backlog_phase_order_work_package_placement(arc_run2):
    """Test WP-06, WP-08, WP-09, and WP-12 placements and notes suppression."""
    model = build_workbook_model(arc_run2, start_date=date(2026, 10, 5))
    
    # Check that no task has the 'Baseline backlog lists parent' note
    for w in model.wbs_rows:
        if w.level == 4 and w.source == "Baseline - Backlog":
            assert "Baseline backlog lists parent" not in w.notes, f"Note found on task {w.wbs_code}: {w.notes}"

    # Check placement of key work packages
    wp_wbs_map = {w.source_id: w for w in model.wbs_rows if w.level == 4 and w.source == "Baseline - Backlog"}
    assert wp_wbs_map["WP-06"].milestone_id == "M2"
    assert wp_wbs_map["WP-06"].deliverable_id == "DEL-07"
    assert wp_wbs_map["WP-08"].milestone_id == "M2"
    assert wp_wbs_map["WP-08"].deliverable_id == "DEL-10"
    assert wp_wbs_map["WP-09"].milestone_id == "M3"
    assert wp_wbs_map["WP-09"].deliverable_id == "DEL-11"
    assert wp_wbs_map["WP-12"].milestone_id == "M3"
    assert wp_wbs_map["WP-12"].deliverable_id == "DEL-14"
