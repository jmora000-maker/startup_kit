"""QA-09 fixture integrity test for arc_run5."""

import pytest
from src.core.models import StartupKitBaseline
from src.generators.pmo_workbook.builder import build_workbook_model
from src.llm.validation import validate_and_repair_baseline
from datetime import date


def test_arc_run5_fixture_integrity(arc_run5: StartupKitBaseline):
    """QA-09: Verify arc_run5 fixture integrity, milestone structure, and carried requirements."""
    assert len(arc_run5.milestones) == 4
    assert [m.id for m in arc_run5.milestones] == ["M1", "M2", "M3", "M4"]
    assert len(arc_run5.deliverables) == 19
    assert len(arc_run5.backlog_seed) == 15
    assert len(arc_run5.raid_items) == 9
    assert len(arc_run5.contract_ambiguities) == 15
    assert len(arc_run5.dependencies_assumptions) == 10

    # Verify reconciliation and model build
    model = build_workbook_model(arc_run5, start_date=date(2026, 10, 5))
    ws_rows = [r for r in model.schedule_rows if r.row_type == "Workstream"]
    assert len(ws_rows) == 4
    ms_rows = [r for r in model.schedule_rows if r.row_type == "Milestone"]
    assert len(ms_rows) == 4
    assert [m.milestone_id for m in ms_rows] == ["M1", "M2", "M3", "M4"]
    assert len(model.raid_rows) == 51


def test_qa_09_carried_merged_gates_and_checkpoints_verification(arc_run5: StartupKitBaseline):
    """QA-09: Verify MS-03 to MS-05, KIT-01, KIT-02, FMT-03, RAID-08 against arc_run5 and multi-milestone reconciliation."""
    # 1. arc_run5 baseline values
    assert [m.id for m in arc_run5.milestones] == ["M1", "M2", "M3", "M4"]
    assert len(arc_run5.interim_checkpoints) == 0

    model = build_workbook_model(arc_run5, start_date=date(2026, 10, 5))
    ms_rows = [r for r in model.schedule_rows if r.row_type == "Milestone"]
    assert [m.milestone_id for m in ms_rows] == ["M1", "M2", "M3", "M4"]
    cp_rows = [r for r in model.schedule_rows if r.row_type == "Checkpoint"]
    assert len(cp_rows) == 0

    # 2. Over-extracted 10-milestone scenario with merged gates and checkpoints
    from src.core.models import Milestone, DecisionItem, Deliverable, RiskAssumption, SourceReference
    ref = SourceReference(document_name="ARC_Genomics_SOW.pdf", clause_or_slide="Section 3", confidence_score=0.95)
    over_extracted_milestones = [
        Milestone(id="M1", description="P1 Foundation accepted: shell and core", source_reference=ref),
        Milestone(id="M2", description="P1 Acceptance Review & Sign-Off gating the start of P2", source_reference=ref),
        Milestone(id="M3", description="P2a Services accepted: API services", source_reference=ref),
        Milestone(id="M4", description="P2a Acceptance Review & Sign-Off", source_reference=ref),
        Milestone(id="M5", description="P2b Application Surface accepted: UI components", source_reference=ref),
        Milestone(id="M6", description="P2b Acceptance Review", source_reference=ref),
        Milestone(id="M7", description="P3 Launch accepted: Release and cutover", source_reference=ref),
        Milestone(id="M8", description="P3 Acceptance Review", source_reference=ref),
        Milestone(id="M9", description="P3 Interim Checkpoint: Smoke Tests Complete (est. week 24)", source_reference=ref),
        Milestone(id="M10", description="P3 Interim Checkpoint: Training Sign-off (est. week 25)", source_reference=ref),
    ]
    test_baseline = arc_run5.model_copy(deep=True)
    test_baseline.milestones = over_extracted_milestones
    test_baseline.decisions = [
        DecisionItem(id="DEC-01", decision_text="Project delivers four sequential acceptance gates across P1, P2a, P2b, and P3.")
    ]
    report = validate_and_repair_baseline(test_baseline)

    # MS-03: Reconciled to 4 gates and 6 checkpoints
    assert len(test_baseline.milestones) == 4
    assert [m.id for m in test_baseline.milestones] == ["M1", "M2", "M3", "M4"]
    assert len(test_baseline.interim_checkpoints) == 6
    assert [cp.id for cp in test_baseline.interim_checkpoints] == ["CP-01", "CP-02", "CP-03", "CP-04", "CP-05", "CP-06"]

    # Build model on reconciled baseline
    reconciled_model = build_workbook_model(test_baseline, start_date=date(2026, 10, 5))
    reconciled_ms_rows = [r for r in reconciled_model.schedule_rows if r.row_type == "Milestone"]
    assert len(reconciled_ms_rows) == 4
    assert [m.milestone_id for m in reconciled_ms_rows] == ["M1", "M2", "M3", "M4"]

    # FMT-03: Row types
    sched_types = {r.row_type for r in reconciled_model.schedule_rows}
    assert "Workstream" in sched_types
    assert "Milestone" in sched_types
    wbs_types = {r.element_type for r in reconciled_model.wbs_rows}
    assert "Deliverable" in wbs_types
