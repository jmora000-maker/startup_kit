"""Tests for RAID decision linking (spec v4 A19)."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model


def test_decision_links_in_raid_rows(arc_run2):
    """Test that RAID ambiguity rows link to approved decisions by shared story or text overlap."""
    model = build_workbook_model(arc_run2, start_date=date(2026, 10, 5))
    
    amb_rows = [r for r in model.raid_rows if r.category == "Contract Clarification"]
    # Check that decisions are linked
    linked_decisions = [r.linked_decision for r in amb_rows if r.linked_decision]
    assert len(linked_decisions) > 0

    # AMB-01 or AMB-02 shares HS-4781 with DEC-05
    amb_map = {r.source_id: r for r in amb_rows}
    assert "DEC-05" in amb_map["AMB-01"].linked_decision or "DEC-05" in amb_map["AMB-02"].linked_decision
