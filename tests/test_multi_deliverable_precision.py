"""Tests for MAP-07 multi-deliverable note precision."""

import pytest
from datetime import date
from src.core.models import (
    StartupKitBaseline,
    Milestone,
    Deliverable,
    WorkPackageSeed,
)
from src.generators.pmo_workbook.builder import build_workbook_model


def test_map_07_same_gate_only():
    """Verify multi-deliverable notes only apply within the same gate and score >= 0.45."""
    milestones = [
        Milestone(id="M1", description="P1 Foundation accepted: shell and core"),
        Milestone(id="M2", description="P2 Services accepted: API services"),
    ]
    deliverables = [
        Deliverable(id="DEL-01", name="Foundation Shell Architecture", sow_reference="HS-01"),
        Deliverable(id="DEL-02", name="Foundation Shell Implementation", sow_reference="HS-02"),
        Deliverable(id="DEL-03", name="Services Shell API", sow_reference="HS-03"),  # In M2!
    ]
    backlog = [
        WorkPackageSeed(
            id="WP-01",
            parent_deliverable_id="DEL-01",
            title="Foundation Shell Architecture and Implementation Component",
            owner="Talent PM"
        )
    ]
    baseline = StartupKitBaseline(
        project_name="MAP-07 Precision Test",
        milestones=milestones,
        deliverables=deliverables,
        backlog_seed=backlog,
    )

    model = build_workbook_model(baseline, start_date=date(2026, 10, 5))

    deliv_rows = {r.deliverable_id: r for r in model.wbs_rows if r.level == 3 and r.deliverable_id}
    # DEL-01 and DEL-02 are both in M1, so DEL-01 may also cover DEL-02
    # But DEL-03 is in M2, so it must NEVER be covered across gates
    assert "DEL-03" not in (deliv_rows.get("DEL-01").notes or "")
