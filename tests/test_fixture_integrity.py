"""QA-09 fixture integrity and Revision 6 expected results tests."""

import pytest
from datetime import date
from src.core.models import StartupKitBaseline
from src.generators.pmo_workbook.builder import build_workbook_model
from src.llm.validation import validate_and_repair_baseline


def test_arc_overextracted_pre_validation_structure(arc_overextracted: StartupKitBaseline):
    """Step 1.4: Assert arc_overextracted has exactly milestone IDs M1 to M10 before validation."""
    assert len(arc_overextracted.milestones) == 10
    assert [m.id for m in arc_overextracted.milestones] == [
        "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10"
    ]
    assert len(arc_overextracted.interim_checkpoints) == 0


def test_arc_overextracted_validation_and_workbook_expectations(arc_overextracted: StartupKitBaseline):
    """Step 1.5: Validate arc_overextracted through validation layer and workbook builder against spec expected results."""
    baseline = arc_overextracted.model_copy(deep=True)

    # 1. Validation Layer (VAL-01, KIT-01, KIT-02)
    report = validate_and_repair_baseline(baseline)

    # VAL-01: 4 gates; M2 merged into M1, M4 into M3, and M6 into M5; exactly 3 checkpoints, CP-01 to CP-03 (from M7, M8, and M9).
    assert len(baseline.milestones) == 4
    gate_ids = [m.id for m in baseline.milestones]
    assert gate_ids == ["M1", "M3", "M5", "M10"]

    # Check merged milestone tracking on gates
    m1 = next(m for m in baseline.milestones if m.id == "M1")
    m3 = next(m for m in baseline.milestones if m.id == "M3")
    m5 = next(m for m in baseline.milestones if m.id == "M5")
    m10 = next(m for m in baseline.milestones if m.id == "M10")

    assert m1.merged_milestone_ids == ["M2"]
    assert m3.merged_milestone_ids == ["M4"]
    assert m5.merged_milestone_ids == ["M6"]
    assert m10.merged_milestone_ids == []

    # KIT-01, KIT-02: Interim Checkpoints table holds CP-01 to CP-03
    assert len(baseline.interim_checkpoints) == 3
    cp_ids = [cp.id for cp in baseline.interim_checkpoints]
    assert cp_ids == ["CP-01", "CP-02", "CP-03"]
    assert "M7" in baseline.interim_checkpoints[0].description or "integration" in baseline.interim_checkpoints[0].description.lower()
    assert "M8" in baseline.interim_checkpoints[1].description or "uat" in baseline.interim_checkpoints[1].description.lower()
    assert "M9" in baseline.interim_checkpoints[2].description or "smoke" in baseline.interim_checkpoints[2].description.lower()

    # 2. PMO Workbook Builder (MS-04, MS-05, FMT-03, RAID-08)
    model = build_workbook_model(baseline, start_date=date(2026, 10, 5))

    # MS-04: The gate Milestone ID cells read "M1 (+M2)", "M3 (+M4)", "M5 (+M6)", and "M10"
    ms_schedule_rows = [r for r in model.schedule_rows if r.row_type == "Milestone"]
    assert len(ms_schedule_rows) == 4
    actual_gate_ids = [r.milestone_id for r in ms_schedule_rows]
    assert actual_gate_ids == ["M1 (+M2)", "M3 (+M4)", "M5 (+M6)", "M10"]

    # MS-05 and FMT-03: 3 Checkpoint rows in P3, before the P3 gate
    cp_schedule_rows = [r for r in model.schedule_rows if r.row_type == "Checkpoint"]
    assert len(cp_schedule_rows) == 3
    assert [r.milestone_id for r in cp_schedule_rows] == ["CP-01", "CP-02", "CP-03"]
    assert all(r.workstream == "P3 Launch" for r in cp_schedule_rows)

    # Verify WBS codes and ordering in P3
    p3_rows = [r for r in model.schedule_rows if r.workstream == "P3 Launch"]
    p3_cp_wbs = [r.wbs_code for r in p3_rows if r.row_type == "Checkpoint"]
    p3_gate_wbs = [r.wbs_code for r in p3_rows if r.row_type == "Milestone"]
    assert p3_cp_wbs == ["4.1", "4.2", "4.3"]
    assert p3_gate_wbs == ["4.4"]

    # RAID-08: RAID rows naming M2, M4, M6, M7, M8, or M9 link to their gate, with the merge or checkpoint note
    # Create test items referencing merged and checkpoint milestones
    from src.core.models import RiskAssumption
    test_baseline = baseline.model_copy(deep=True)
    test_baseline.raid_items.extend([
        RiskAssumption(id="RAID-TEST-01", description="Risk regarding M2 sign-off turnaround", category="Governance", type="Risk"),
        RiskAssumption(id="RAID-TEST-02", description="Dependency on M4 client approval", category="Technical", type="Dependency"),
        RiskAssumption(id="RAID-TEST-03", description="Issue with M6 acceptance review", category="Delivery", type="Issue"),
        RiskAssumption(id="RAID-TEST-04", description="Risk during M7 cross-browser testing", category="Quality", type="Risk"),
        RiskAssumption(id="RAID-TEST-05", description="Dependency on M8 UAT scientist group", category="Delivery", type="Dependency"),
        RiskAssumption(id="RAID-TEST-06", description="Issue during M9 production smoke test", category="Technical", type="Issue"),
    ])
    test_model = build_workbook_model(test_baseline, start_date=date(2026, 10, 5))

    raid_dict = {r.description: r for r in test_model.raid_rows}
    r1 = raid_dict["Risk regarding M2 sign-off turnaround"]
    assert r1.linked_milestone == "M1"
    assert "Refers to M2 (merged into M1)" in r1.notes

    r2 = raid_dict["Dependency on M4 client approval"]
    assert r2.linked_milestone == "M3"
    assert "Refers to M4 (merged into M3)" in r2.notes

    r3 = raid_dict["Issue with M6 acceptance review"]
    assert r3.linked_milestone == "M5"
    assert "Refers to M6 (merged into M5)" in r3.notes

    r4 = raid_dict["Risk during M7 cross-browser testing"]
    assert r4.linked_milestone == "M10"
    assert "Refers to M7 (checkpoint of M10)" in r4.notes

    r5 = raid_dict["Dependency on M8 UAT scientist group"]
    assert r5.linked_milestone == "M10"
    assert "Refers to M8 (checkpoint of M10)" in r5.notes

    r6 = raid_dict["Issue during M9 production smoke test"]
    assert r6.linked_milestone == "M10"
    assert "Refers to M9 (checkpoint of M10)" in r6.notes
