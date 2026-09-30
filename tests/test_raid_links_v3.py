"""Test v3 A4: RAID default-fill detection and linking order."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model
from src.generators.pmo_workbook.mapping import detect_default_filled_milestone, detect_default_filled_deliverable


def test_v3_default_fill_detection_and_raid_links(arc_baseline):
    all_raw = list(arc_baseline.raid_items) + list(arc_baseline.dependencies_assumptions)
    assert detect_default_filled_milestone(all_raw) == "M1"
    assert detect_default_filled_deliverable(all_raw) == "DEL-01"

    model = build_workbook_model(arc_baseline, start_date=date(2026, 10, 5))
    assert len(model.raid_rows) == 52

    # Map by source_id
    raid_by_source = {r.source_id: r for r in model.raid_rows if r.source_id}

    # DEP-02 (HS-4781 before P2a) -> M2
    assert raid_by_source["DEP-02"].linked_milestone == "M2"
    assert raid_by_source["DEP-02"].workstream == "P2a Services and Data"

    # DEP-03 (P1, P2a, P2b, P3) -> Multiple phases
    assert raid_by_source["DEP-03"].workstream == "Multiple phases"
    assert "M1" in raid_by_source["DEP-03"].linked_milestone
    assert "M2" in raid_by_source["DEP-03"].linked_milestone
    assert "M3" in raid_by_source["DEP-03"].linked_milestone
    assert "M4" in raid_by_source["DEP-03"].linked_milestone

    # Cross-phase items (default fill ignored, no phase code in text)
    assert raid_by_source["DEP-01"].workstream == "Cross-phase"
    assert raid_by_source["DEP-04"].workstream == "Cross-phase"
    assert raid_by_source["DEP-06"].workstream == "Cross-phase"
    assert raid_by_source["DEP-07"].workstream == "Cross-phase"
    assert raid_by_source["DEP-08"].workstream == "Cross-phase"
    assert raid_by_source["ASM-02"].workstream == "Cross-phase"
    assert raid_by_source["ASM-03"].workstream == "Cross-phase"

    # No dependency row is linked to M1 by default
    for dep_id in ["DEP-01", "DEP-04", "DEP-06", "DEP-07", "DEP-08", "ASM-02", "ASM-03"]:
        assert raid_by_source[dep_id].linked_milestone == ""
        assert "Linked via deliverable" not in raid_by_source[dep_id].notes
