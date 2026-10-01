"""Tests for VAL-02 backlog validation and catalogue reconstruction against recorded ARC output."""

import json
from pathlib import Path
import pytest
from src.core.models import StartupKitBaseline
from src.config import SOW_REFERENCE_PATTERNS, detect_sow_reference_kind, extract_sow_references
from src.llm.validation import validate_and_repair_baseline


def test_raw_recorded_arc_backlog_has_defects():
    """Verify that raw recorded ARC LLM extraction has backlog defects before validation."""
    baseline_file = Path("tests/fixtures/sow/arc_genomics/baseline.json")
    with open(baseline_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    baseline = StartupKitBaseline.model_validate(data)

    deliv_ids = {d.id for d in baseline.deliverables}
    
    # Check if raw backlog has missing parents or placeholder owners or phase references
    has_blank_parent = any(not wp.parent_deliverable_id or wp.parent_deliverable_id not in deliv_ids for wp in baseline.backlog_seed)
    has_placeholder_owner = any(
        not wp.owner or "UNASSIGNED" in wp.owner.upper() or "[ACT-" in wp.owner or "CONFIRM" in wp.owner.upper()
        for wp in baseline.backlog_seed
    )
    
    # At least one defect exists in raw extraction
    assert has_blank_parent or has_placeholder_owner, "Expected raw LLM backlog to exhibit defects."


def test_rebuilt_backlog_from_catalogue():
    """Verify that validate_and_repair_baseline reconstructs valid backlog seed from catalogue (VAL-02)."""
    baseline_file = Path("tests/fixtures/sow/arc_genomics/baseline.json")
    with open(baseline_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    baseline = StartupKitBaseline.model_validate(data)

    report = validate_and_repair_baseline(baseline)

    deliv_ids = {d.id for d in baseline.deliverables}
    assert len(baseline.backlog_seed) > 0, "Backlog seed should not be empty."

    for wp in baseline.backlog_seed:
        # Every work package has an existing parent deliverable
        assert wp.parent_deliverable_id in deliv_ids, f"WP {wp.id} parent {wp.parent_deliverable_id} not in deliverables."
        # Owner is non-placeholder
        assert wp.owner and "UNASSIGNED" not in wp.owner.upper() and "[ACT-" not in wp.owner, f"WP {wp.id} has invalid owner: {wp.owner}"
        # SOW references do not contain phase names (e.g. 'Phase 1', 'P2a')
        if wp.sow_reference:
            for ref in extract_sow_references(wp.sow_reference):
                assert detect_sow_reference_kind(ref) != "Section", f"WP {wp.id} reference {ref} is invalid section/phase."
        # linked_milestones is set
        assert wp.linked_milestones, f"WP {wp.id} missing linked_milestones."
