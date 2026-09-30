"""Tests for RAID owner normalization (spec v4 A18)."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model


def test_raid_owner_normalization(arc_run2):
    """Test RAID-01, RAID-02, and RAID-06 owners are normalized to [UNASSIGNED - TO BE CONFIRMED]."""
    model = build_workbook_model(arc_run2, start_date=date(2026, 10, 5))
    
    raid_map = {r.raid_id: r for r in model.raid_rows}
    assert "RAID-01" in raid_map
    assert "RAID-02" in raid_map
    assert "RAID-06" in raid_map

    assert raid_map["RAID-01"].owner == "[UNASSIGNED - TO BE CONFIRMED]"
    assert "Owner unassigned" in raid_map["RAID-01"].notes

    assert raid_map["RAID-02"].owner == "[UNASSIGNED - TO BE CONFIRMED]"
    assert "Owner unassigned" in raid_map["RAID-02"].notes

    assert raid_map["RAID-06"].owner == "[UNASSIGNED - TO BE CONFIRMED]"
    assert "Owner unassigned" in raid_map["RAID-06"].notes

    # Verify standard owners are not marked as unassigned
    assert raid_map["RAID-03"].owner == "Talent PM"
    assert "Owner unassigned" not in raid_map["RAID-03"].notes
