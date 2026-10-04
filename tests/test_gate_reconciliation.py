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


def test_milestone_phase_display_preservation():
    """Verify phase preserves uppercase code while phase_display captures raw casing or None."""
    # Case 1: Real stated phase code with mixed case (e.g. "P2a")
    ms_stated = Milestone(id="M1", description="P2a Services accepted: core API")
    baseline_stated = StartupKitBaseline(
        project_name="Stated Phase Test",
        milestones=[ms_stated],
        decisions=[],
        deliverables=[],
    )
    validate_and_repair_baseline(baseline_stated)

    assert len(baseline_stated.milestones) == 1
    m1 = baseline_stated.milestones[0]
    assert m1.phase == "P2A"
    assert m1.phase_display == "P2a"

    # Case 2: Milestone with no stated phase code (synthetic G_N gate)
    ms_synthetic = Milestone(id="M1", description="Initial Kickoff and Discovery")
    baseline_synthetic = StartupKitBaseline(
        project_name="Synthetic Phase Test",
        milestones=[ms_synthetic],
        decisions=[],
        deliverables=[],
    )
    validate_and_repair_baseline(baseline_synthetic)

    assert len(baseline_synthetic.milestones) == 1
    m_synth = baseline_synthetic.milestones[0]
    assert m_synth.phase == "G_1"
    assert m_synth.phase_display is None


def test_checkpoint_phase_fallback_preservation():
    """Verify checkpoints extracted during gate reconciliation preserve phase and phase_display."""
    # Case 1: Checkpoint with explicit mixed-case phase code (e.g. "P2a")
    ms_gate1 = Milestone(id="M1", description="P2a Services accepted: core API")
    ms_cp1 = Milestone(id="M2", description="P2a Identity and RBAC checkpoint (est. week 3)")
    baseline_stated = StartupKitBaseline(
        project_name="Stated Checkpoint Test",
        milestones=[ms_gate1, ms_cp1],
        decisions=[],
        deliverables=[],
    )
    validate_and_repair_baseline(baseline_stated)

    assert len(baseline_stated.milestones) == 1
    assert len(baseline_stated.interim_checkpoints) == 1
    cp1 = baseline_stated.interim_checkpoints[0]
    assert cp1.id == "CP-01"
    assert cp1.phase == "P2A"
    assert cp1.phase_display == "P2a"

    # Case 2: Checkpoint inheriting phase from preceding gate in the same phase group
    ms_gate2 = Milestone(id="M1", description="P2b Services accepted: backend services")
    ms_cp2 = Milestone(id="M2", description="General architecture review checkpoint")
    baseline_inherited = StartupKitBaseline(
        project_name="Inherited Checkpoint Test",
        milestones=[ms_gate2, ms_cp2],
        decisions=[],
        deliverables=[],
    )
    validate_and_repair_baseline(baseline_inherited)

    assert len(baseline_inherited.milestones) == 1
    assert len(baseline_inherited.interim_checkpoints) == 1
    cp2 = baseline_inherited.interim_checkpoints[0]
    assert cp2.id == "CP-01"
    assert cp2.phase == "P2B"
    assert cp2.phase_display == "P2b"
