"""Tests for RAID milestones derived from linked deliverables (spec v5 A23)."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model


def test_raid_21_multiphase_linking(arc_run3):
    """Test RAID-21 (AMB-02) links M2, M3, M4 with workstream 'Multiple phases'."""
    model = build_workbook_model(arc_run3, start_date=date(2026, 10, 5))

    raid_map = {r.source_id: r for r in model.raid_rows}
    assert "AMB-02" in raid_map
    r21 = raid_map["AMB-02"]

    assert r21.workstream == "Multiple phases"
    linked_ms = [m.strip() for m in r21.linked_milestone.split(",") if m.strip()]
    assert linked_ms == ["M2", "M3", "M4"]

    # Check linked deliverables
    linked_delivs = [d.strip() for d in r21.linked_deliverables.split(",") if d.strip()]
    assert "DEL-04" in linked_delivs or "DEL-05" in linked_delivs or "DEL-07" in linked_delivs
    assert "DEL-11" in linked_delivs or "DEL-13" in linked_delivs
    assert "DEL-14" in linked_delivs
