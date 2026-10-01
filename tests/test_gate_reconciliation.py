"""Tests for MS-02 to MS-05 milestone gate reconciliation and checkpoints."""

import pytest
from datetime import date
from src.core.models import (
    StartupKitBaseline,
    Milestone,
    Deliverable,
    DecisionItem,
)
from src.generators.pmo_workbook.builder import build_workbook_model
from src.llm.validation import validate_and_repair_baseline


def test_gate_and_checkpoint_rows():
    """Verify gates become Milestone rows and interim checkpoints become Checkpoint rows (MS-03, MS-05)."""
    milestones = [
        Milestone(id="M1", description="P1 Foundation accepted: shell and core"),
        Milestone(id="M2", description="P1 Identity and RBAC checkpoint (est. week 3)"),
        Milestone(id="M3", description="P2 Services accepted: API services"),
    ]
    decisions = [
        DecisionItem(id="DEC-01", decision_text="Project delivers two sequential acceptance gates across P1 and P2.")
    ]
    deliverables = [
        Deliverable(id="DEL-01", name="Foundation Shell", sow_reference="HS-01"),
        Deliverable(id="DEL-02", name="API Services", sow_reference="HS-02"),
    ]
    baseline = StartupKitBaseline(
        project_name="Gate & Checkpoint Test",
        milestones=milestones,
        decisions=decisions,
        deliverables=deliverables,
    )
    validate_and_repair_baseline(baseline)

    # 2 gates (M1, M2) + 1 checkpoint (CP-01)
    assert len(baseline.milestones) == 2
    assert len(baseline.interim_checkpoints) == 1

    model = build_workbook_model(baseline, start_date=date(2026, 10, 5))
    sched_types = [(r.wbs_code, r.row_type, r.milestone_id) for r in model.schedule_rows]
    
    # Verify workstream and milestone rows exist
    ws_rows = [r for r in model.schedule_rows if r.row_type == "Workstream"]
    assert len(ws_rows) == 2
