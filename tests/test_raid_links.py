"""Test RAID default-fill detection, multi-milestone linking, and phase workstream assignment (v3 spec)."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model
from src.generators.pmo_workbook.mapping import detect_default_filled_milestone, detect_default_filled_deliverable


def test_default_fill_detection(arc_baseline):
    all_raw = list(arc_baseline.raid_items) + list(arc_baseline.dependencies_assumptions)
    val_ms = detect_default_filled_milestone(all_raw)
    assert val_ms == "M1"
    val_deliv = detect_default_filled_deliverable(all_raw)
    assert val_deliv == "DEL-01"


def test_arc_raid_linking(arc_baseline):
    model = build_workbook_model(arc_baseline, start_date=date(2026, 10, 5))

    # Total 52 RAID rows in v3 Appendix B
    assert len(model.raid_rows) == 52

    raid_by_id = {r.raid_id: r for r in model.raid_rows}

    # RAID-01 (Design system in P1) -> P1 Foundation (M1)
    r1 = raid_by_id["RAID-01"]
    assert r1.workstream == "P1 Foundation"
    assert r1.linked_milestone == "M1"

    # DEP-02 (HS-4781 before P2a) -> RAID-10 -> P2a Services and Data (M2)
    r10 = raid_by_id["RAID-10"]
    assert r10.source_id == "DEP-02"
    assert r10.workstream == "P2a Services and Data"
    assert r10.linked_milestone == "M2"

    # DEP-03 (Sequential gates P1, P2a, P2b, P3) -> RAID-11 -> Multiple phases
    r11 = raid_by_id["RAID-11"]
    assert r11.source_id == "DEP-03"
    assert r11.workstream == "Multiple phases"
    assert "M1" in r11.linked_milestone and "M2" in r11.linked_milestone and "M3" in r11.linked_milestone and "M4" in r11.linked_milestone

    # ASM-01 (week ranges for all phases) -> RAID-17 -> Multiple phases
    r17 = raid_by_id["RAID-17"]
    assert r17.source_id == "ASM-01"
    assert r17.workstream == "Multiple phases"
    assert "M1" in r17.linked_milestone and "M2" in r17.linked_milestone and "M3" in r17.linked_milestone and "M4" in r17.linked_milestone

    # AMB-02 (P1 delivery timeline) -> RAID-21 -> P1 Foundation (M1)
    r21 = raid_by_id["RAID-21"]
    assert r21.source_id == "AMB-02"
    assert r21.workstream == "P1 Foundation"
    assert r21.linked_milestone == "M1"
    assert r21.contract_reference != ""

    # AMB-08 (P3 launch window) -> RAID-27 -> P3 Launch (M4)
    r27 = raid_by_id["RAID-27"]
    assert r27.source_id == "AMB-08"
    assert r27.workstream == "P3 Launch"
    assert r27.linked_milestone == "M4"

    # Q-01 (Start Date for P1) -> RAID-35 -> P1 Foundation (M1)
    r35 = raid_by_id["RAID-35"]
    assert r35.source_id == "Q-01"
    assert r35.workstream == "P1 Foundation"
    assert r35.linked_milestone == "M1"

    # Check evidence consistency flags count in model: exactly 12 (v3 A9)
    assert model.evidence_flags_count == 12
