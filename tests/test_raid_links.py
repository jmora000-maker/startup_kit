"""Test RAID default-fill detection, multi-milestone linking, and phase workstream assignment."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model
from src.generators.pmo_workbook.mapping import detect_default_filled_milestone


def test_default_fill_detection(arc_baseline):
    all_raw = list(arc_baseline.raid_items) + list(arc_baseline.dependencies_assumptions)
    val = detect_default_filled_milestone(all_raw)
    assert val == "M1"


def test_arc_raid_linking(arc_baseline):
    model = build_workbook_model(arc_baseline, start_date=date(2026, 10, 5))

    raid_by_id = {r.raid_id: r for r in model.raid_rows}

    # RAID-01 (Cogen API) -> Cross-phase
    r1 = raid_by_id["RAID-01"]
    assert r1.workstream == "Cross-phase"
    assert r1.linked_milestone == ""

    # RAID-02 is the second item (RAID-09 in source fixture: HS-4781 before P2a)
    r2 = raid_by_id["RAID-02"]
    assert r2.workstream == "P2a Services and Data"
    assert r2.linked_milestone == "M2"
    assert r2.linked_wbs_code == "2.1"

    # RAID-03 (RAID-10 in source: Cross-phase across P1, P2a, P2b, P3)
    r3 = raid_by_id["RAID-03"]
    assert r3.workstream == "Multiple phases"
    assert "M1" in r3.linked_milestone and "M2" in r3.linked_milestone and "M3" in r3.linked_milestone and "M4" in r3.linked_milestone

    # RAID-04 (RAID-16 in source)
    r4 = raid_by_id["RAID-04"]
    assert r4.workstream == "Multiple phases"
    assert "M1" in r4.linked_milestone and "M2" in r4.linked_milestone and "M3" in r4.linked_milestone and "M4" in r4.linked_milestone

    # Dependencies (DEP-01 to DEP-12): since M1 was default fill and description has no phase, they fall back to Cross-phase
    for i in range(5, 17):
        r_dep = raid_by_id[f"RAID-{i:02d}"]
        assert r_dep.workstream == "Cross-phase"
        assert r_dep.linked_milestone == ""
