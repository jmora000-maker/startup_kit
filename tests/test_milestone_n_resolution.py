"""Tests for RAID-05 Milestone N resolution."""

import pytest
from src.core.models import (
    Milestone,
    Deliverable,
    RiskAssumption,
)
from src.generators.pmo_workbook.mapping import link_raid_item_v2, parse_milestone_phase


def test_milestone_n_resolution():
    """Verify that 'Milestone 2' in RAID description resolves to the 2nd gate (RAID-05)."""
    m1 = Milestone(id="M1", description="P1 Foundation accepted: shell")
    m2 = Milestone(id="M2", description="P2 Services accepted: API")
    milestones = [m1, m2]
    parsed_phases = {m.id: parse_milestone_phase(m.description) for m in milestones}
    wbs_map = {"M1": "1.1", "M2": "2.1"}

    risk = RiskAssumption(
        type="Risk",
        description="Dependency on third-party payment gateway sandbox during Milestone 2 testing."
    )

    ws, linked_ms, linked_wbs, note = link_raid_item_v2(
        risk, milestones, {}, parsed_phases, wbs_map
    )

    assert linked_ms == "M2"
    assert "P2" in ws
