"""Tests for degenerate backlog detection and mapping rules (spec v5 A24)."""

from datetime import date
from src.core.models import WorkPackageSeed, Milestone, Deliverable, SourceReference
from src.generators.pmo_workbook.mapping import detect_degenerate_work_packages, map_work_packages_to_milestones
from src.generators.pmo_workbook.builder import build_workbook_model


def test_degenerate_backlog_detection(arc_run3):
    """Test degenerate work package detection on arc_run3."""
    degen_ids = detect_degenerate_work_packages(arc_run3.backlog_seed, arc_run3.deliverables)
    assert len(degen_ids) == 19


def test_no_backlog_match_basis_under_degenerate_backlog(arc_run3):
    """Test that deliverables never receive 'Backlog match' mapping basis from degenerate work packages."""
    model = build_workbook_model(arc_run3, start_date=date(2026, 10, 5))

    deliv_rows = [w for w in model.wbs_rows if w.level == 3 and w.element_type == "Deliverable"]
    for d in deliv_rows:
        assert "backlog match" not in d.mapping_basis.lower(), f"Deliverable {d.deliverable_id} has Backlog match basis: {d.mapping_basis}"


def test_backlog_link_basis():
    """Test 'Backlog link' mapping basis for work packages with real parent and linked_milestones."""
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="Sec 1", confidence_score=0.9)
    ms = [Milestone(id="M1", description="Phase 1: Setup", source_reference=ref), Milestone(id="M2", description="Phase 2: Build", source_reference=ref)]
    delivs = [Deliverable(id="DEL-01", name="Core Service", source_reference=ref)]
    wps = [
        WorkPackageSeed(id="WP-01", title="Setup Environment", parent_deliverable_id="DEL-01", linked_milestones=["M1"], source_reference=ref),
        WorkPackageSeed(id="WP-02", title="Deploy Service", parent_deliverable_id="DEL-01", linked_milestones=["M2"], source_reference=ref),
    ]

    wp_to_ms, wp_to_basis, _ = map_work_packages_to_milestones(wps, ms, {}, None, delivs)
    assert wp_to_ms["WP-01"].id == "M1"
    assert wp_to_basis["WP-01"] == "Backlog link"
    assert wp_to_ms["WP-02"].id == "M2"
    assert wp_to_basis["WP-02"] == "Backlog link"
