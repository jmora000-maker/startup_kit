"""Tests for Contract Reference consistency across RAID rows (spec v5 A25)."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model


def test_contract_reference_consistency(arc_run3):
    """Test every Contract Clarification and Open Question has Contract Reference populated or 'Not cited'."""
    model = build_workbook_model(arc_run3, start_date=date(2026, 10, 5))

    for r in model.raid_rows:
        if r.category in ("Contract Clarification", "Open Question"):
            assert r.contract_reference != "", f"RAID row {r.raid_id} ({r.category}) has blank Contract Reference"
            assert "SOW refs:" in r.contract_reference or "Sections:" in r.contract_reference or r.contract_reference == "Not cited"
        else:
            assert r.contract_reference == "", f"RAID row {r.raid_id} ({r.category}) has non-blank Contract Reference: {r.contract_reference}"
