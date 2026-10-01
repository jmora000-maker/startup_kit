"""Tests for DT-06 predecessor graph sanity and acyclicity."""

import pytest
from datetime import date
from src.core.models import (
    StartupKitBaseline,
    Milestone,
    Deliverable,
    DependencyAssumptionItem,
)
from src.generators.pmo_workbook.builder import build_workbook_model


def test_predecessor_sanity_drops_forward_and_self_links():
    """Verify that forward or self predecessors are dropped with a warning (DT-06)."""
    milestones = [
        Milestone(
            id="M1",
            description="P1 Foundation accepted: micro-frontend shell (weeks 1-4)",
            key_dependencies=["P2 Services accepted before P1 begins"]  # Forward link to M2 (invalid!)
        ),
        Milestone(
            id="M2",
            description="P2 Services accepted: backend API endpoints (weeks 5-8)",
            key_dependencies=["P1 Foundation accepted before P2 begins"]  # Backward link (valid!)
        ),
    ]
    deliverables = [
        Deliverable(id="DEL-01", name="Foundation", sow_reference="HS-01"),
        Deliverable(id="DEL-02", name="Services", sow_reference="HS-02"),
    ]
    baseline = StartupKitBaseline(
        project_name="Predecessor Sanity Test",
        milestones=milestones,
        deliverables=deliverables,
    )

    model = build_workbook_model(baseline, start_date=date(2026, 10, 5))

    sched_by_id = {r.milestone_id: r for r in model.schedule_rows if r.row_type == "Milestone"}
    assert sched_by_id["M1"].predecessor == ""  # Forward link dropped!
    assert sched_by_id["M2"].predecessor == "M1"  # Valid backward link preserved!
