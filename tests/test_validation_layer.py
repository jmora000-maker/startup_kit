"""Unit tests for extraction validation layer (VAL-01 to VAL-07)."""

import pytest
from datetime import date
from src.core.models import (
    StartupKitBaseline,
    ProjectStartupCharter,
    Deliverable,
    Milestone,
    WorkPackageSeed,
    DecisionItem,
    DependencyAssumptionItem,
    SOWWorkItem,
    SOWInterpretationSummary,
)
from src.llm.validation import validate_and_repair_baseline


def test_val_01_gate_reconciliation():
    """VAL-01: Reconcile milestones to SOW gates and move restatements/checkpoints."""
    milestones = [
        Milestone(id="M1", description="P1 Foundation accepted: shell and IAM"),
        Milestone(id="M2", description="P1 Shell and auth acceptance sign-off"),  # Restatement
        Milestone(id="M3", description="P2a Services accepted: API and ingestion"),
        Milestone(id="M4", description="P2b Application Surface accepted: frontend"),
        Milestone(id="M5", description="P3 Launch accepted: rollout and testing"),
    ]
    decisions = [
        DecisionItem(id="DEC-01", decision_text="Project delivers four sequential acceptance gates across P1 to P3.")
    ]
    baseline = StartupKitBaseline(
        project_name="Gate Reconciliation Test",
        milestones=milestones,
        decisions=decisions,
    )
    report = validate_and_repair_baseline(baseline)

    assert len(baseline.milestones) == 4
    assert [m.id for m in baseline.milestones] == ["M1", "M2", "M3", "M4"]
    assert len(baseline.interim_checkpoints) == 1
    assert baseline.interim_checkpoints[0].id == "CP-01"


def test_val_02_work_packages_from_catalogue():
    """VAL-02: Work packages are rebuilt from the SOW work item catalogue."""
    deliverables = [
        Deliverable(id="DEL-01", name="Core Microservices", sow_reference="HS-101, HS-102")
    ]
    catalogue = [
        SOWWorkItem(reference="HS-101", title="User Service", phase="P1", deliverable_id="DEL-01"),
        SOWWorkItem(reference="HS-102", title="Auth Service", phase="P1", deliverable_id="DEL-01"),
    ]
    # Broken LLM backlog seed
    backlog = [
        WorkPackageSeed(id="WP-99", parent_deliverable_id="NON_EXISTENT", title="Bad WP", owner="[UNASSIGNED - TO BE CONFIRMED]")
    ]
    baseline = StartupKitBaseline(
        project_name="Backlog Rebuild Test",
        deliverables=deliverables,
        sow_stories_catalogue=catalogue,
        backlog_seed=backlog,
        milestones=[Milestone(id="M1", description="P1 Foundation accepted")]
    )
    validate_and_repair_baseline(baseline)

    assert len(baseline.backlog_seed) == 2
    assert baseline.backlog_seed[0].parent_deliverable_id == "DEL-01"
    assert baseline.backlog_seed[0].owner == "Toptal Delivery Team"
    assert baseline.backlog_seed[0].sow_reference == "HS-101"


def test_val_03_id_uniqueness():
    """VAL-03: Duplicate or non-standard IDs are renumbered sequentially."""
    deliverables = [
        Deliverable(id="DEL-01", name="D1"),
        Deliverable(id="DEL-01", name="D2 (duplicate)"),
        Deliverable(id="CUSTOM", name="D3"),
    ]
    baseline = StartupKitBaseline(
        project_name="Unique ID Test",
        deliverables=deliverables,
    )
    validate_and_repair_baseline(baseline)

    assert [d.id for d in baseline.deliverables] == ["DEL-01", "DEL-02", "DEL-03"]


def test_val_05_award_date_provenance():
    """VAL-05: When sow_awarded_date is absent, record warning and add open question."""
    baseline = StartupKitBaseline(
        project_name="Award Date Test",
        sow_awarded_date=None,
        open_questions=[]
    )
    report = validate_and_repair_baseline(baseline)

    warnings = [f for f in report.findings if f.invariant_id == "INV-18"]
    assert len(warnings) == 1
    assert any("award" in q.lower() for q in baseline.open_questions)


def test_val_06_one_numbering_system():
    """VAL-06: SOW references hold references only, stripping phase labels."""
    deliverables = [
        Deliverable(id="DEL-01", name="Data Pipeline", sow_reference="Phase 1: HS-4762, Milestone 2: HS-4764")
    ]
    baseline = StartupKitBaseline(
        project_name="Numbering System Test",
        deliverables=deliverables,
    )
    validate_and_repair_baseline(baseline)

    assert baseline.deliverables[0].sow_reference == "HS-4762, HS-4764"
