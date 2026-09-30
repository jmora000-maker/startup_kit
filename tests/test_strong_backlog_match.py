"""Tests for strong backlog deliverable matching (spec v4 A14)."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model


def test_strong_backlog_match_del_07(arc_run2):
    """Test DEL-07 maps to M2 with basis Backlog match (WP-06)."""
    model = build_workbook_model(arc_run2, start_date=date(2026, 10, 5))
    
    deliv_rows = {w.deliverable_id: w for w in model.wbs_rows if w.element_type == "Deliverable"}
    assert "DEL-07" in deliv_rows
    deliv_07 = deliv_rows["DEL-07"]
    assert deliv_07.milestone_id == "M2"
    assert deliv_07.mapping_basis == "Backlog match (WP-06)"


def test_strong_backlog_match_threshold_low_score(arc_run2):
    """Test that deliverables with lower backlog match scores retain their primary mapping basis."""
    model = build_workbook_model(arc_run2, start_date=date(2026, 10, 5))
    
    deliv_rows = {w.deliverable_id: w for w in model.wbs_rows if w.element_type == "Deliverable"}
    # DEL-05 is mapped via Phase code
    assert deliv_rows["DEL-05"].milestone_id == "M1"
    assert deliv_rows["DEL-05"].mapping_basis == "Phase code"
    
    # DEL-08 has no matching work package and is mapped via Scope match
    assert deliv_rows["DEL-08"].milestone_id == "M2"
    assert deliv_rows["DEL-08"].mapping_basis == "Scope match"
