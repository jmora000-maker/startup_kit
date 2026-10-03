"""Unit test for CHK-07: Checklist G01-04 gate counting matches the Kit (excluding checkpoints)."""

import pytest
from datetime import date
from src.core.models import (
    StartupKitBaseline,
    Milestone,
    DecisionItem,
    ReadinessChecklistItem,
)
from src.llm.validation import validate_and_repair_baseline


def test_checklist_g01_04_counts_gates_only():
    """CHK-07: G01-04 evidence counts gates only, never interim checkpoints."""
    milestones = [
        Milestone(id="M1", description="P1 Foundation accepted: shell and IAM", external_date=date(2026, 11, 17), owner="Delivery Manager"),
        Milestone(id="M2", description="P1 Project Kickoff Call", external_date=date(2026, 10, 14), owner="Delivery Manager"),  # Checkpoint
        Milestone(id="M3", description="P2 Services accepted: API and data", external_date=date(2027, 1, 26), owner="Delivery Manager"),
        Milestone(id="M4", description="P3 Launch accepted: rollout and testing", external_date=date(2027, 4, 6), owner="Delivery Manager"),
    ]
    decisions = [
        DecisionItem(id="DEC-01", decision_text="Project delivers sequential acceptance gates across P1 to P3.")
    ]
    checklist = [
        ReadinessChecklistItem(
            item_id="G01-04",
            gate_criterion="Milestone delivery plan with external dates and internal buffers committed",
            related_section4_artifact="Milestone Delivery Plan",
            owner="Delivery Manager",
            status="Complete",
            evidence=f"{len(milestones)} milestones mapped with external dates and internal buffer calculations.",
            approval_status="Approved",
        )
    ]
    baseline = StartupKitBaseline(
        project_name="Gate Counting Test",
        milestones=milestones,
        decisions=decisions,
        readiness_checklist=checklist,
    )
    validate_and_repair_baseline(baseline)

    assert len(baseline.milestones) == 3
    assert len(baseline.interim_checkpoints) == 1

    # G01-04 evidence must match gates count (3), not total raw milestones (4)
    g01_04 = next(item for item in baseline.readiness_checklist if item.item_id == "G01-04")
    assert "3 milestones" in g01_04.evidence
    assert "4 milestones" not in g01_04.evidence
