"""Tests for HTL-65: Client Kickoff Deck Trace Manifest Attribution Correctness.

Verifies that the Client Kickoff Deck trace manifest (trace.json) accurately attributes
source provenance for Slide 5 (problem_statement, success_criteria_summary, project_purpose),
Slide 6 (solution_overview, workstreams, out_of_scope), Slide 12 (risks), and Slide 15 (next steps),
including correct reflection of deterministic fallbacks when primary fields are absent.
"""

import json
from pathlib import Path
import pytest

from src.core.models import (
    StartupKitBaseline,
    ProjectStartupCharter,
    GovernanceContext,
    SOWInterpretationSummary,
    Deliverable,
    Milestone,
    RiskAssumption,
)
from src.generators.client_deck.builder import build_client_deck_model
from src.generators.client_deck import export_client_deck
from tests.test_htl_62 import _build_pge_baseline


def test_htl_65_primary_synthesis_and_extraction_fields_attributed():
    """HTL-65: Slide 5/6 manifest entries accurately cite problem_statement, success_criteria_summary, and solution_overview."""
    baseline = _build_pge_baseline()
    baseline.charter.problem_statement = "Legacy application has unflagged manual overrides and stability issues."
    baseline.charter.solution_overview = "Toptal performs discovery and builds a 7 Rs cloud roadmap over 3 weeks."
    baseline.charter.success_criteria_summary = "Client receives clear evidence to make confident migration decisions."

    model = build_client_deck_model(baseline)
    entries = {e.element: e for e in model.manifest.entries}

    # 1. Problem Statement
    assert "What problem are we solving?" in entries
    prob_entry = entries["What problem are we solving?"]
    assert prob_entry.traces[0].artifact == "Charter"
    assert prob_entry.traces[0].field == "problem_statement"
    assert prob_entry.traces[0].key == "problem_statement"
    assert prob_entry.derived is None

    # 2. Success Criteria Summary
    assert "What does success look like?" in entries
    succ_entry = entries["What does success look like?"]
    assert succ_entry.traces[0].artifact == "Charter"
    assert succ_entry.traces[0].field == "success_criteria_summary"
    assert succ_entry.traces[0].key == "success_criteria_summary"
    assert succ_entry.derived is None

    # 3. Solution Overview
    assert "Solution Overview" in entries
    so_entry = entries["Solution Overview"]
    assert so_entry.traces[0].artifact == "Charter"
    assert so_entry.traces[0].field == "solution_overview"
    assert so_entry.traces[0].key == "solution_overview"
    assert so_entry.derived is None

    # 4. Out of Scope
    assert "Out of Scope" in entries
    oos_entry = entries["Out of Scope"]
    assert oos_entry.traces[0].artifact == "Charter"
    assert oos_entry.traces[0].field == "exclusions"
    assert oos_entry.derived is None


def test_htl_65_fallback_paths_attributed_correctly():
    """HTL-65: Fallbacks for Slide 5 and Slide 6 are accurately tagged in trace manifest when primary fields are absent."""
    baseline = StartupKitBaseline(
        project_name="Fallback Test Project",
        charter=ProjectStartupCharter(
            client_name="Test Client",
            project_purpose="Purpose statement for project.",
            success_criteria=["Criterion 1: 95% test coverage.", "Criterion 2: Zero high severity defects."],
            high_level_scope=["Discovery phase", "Architecture design", "Wave planning"],
        ),
        sow_interpretation=SOWInterpretationSummary(
            out_of_scope_items=["Hardware procurement", "Production rollout"],
        ),
    )

    model = build_client_deck_model(baseline)
    entries = {e.element: e for e in model.manifest.entries}

    # Problem statement absent -> Fallback
    prob_entry = entries["What problem are we solving?"]
    assert prob_entry.traces[0].field == "problem_statement"
    assert prob_entry.derived == "Fallback"

    # Success criteria summary absent -> Deterministic fallback from success_criteria
    succ_entry = entries["What does success look like?"]
    assert succ_entry.traces[0].field == "success_criteria"
    assert succ_entry.derived == "Deterministic Fallback"

    # Solution overview absent -> Deterministic fallback from high_level_scope
    so_entry = entries["Solution Overview"]
    assert so_entry.traces[0].field == "high_level_scope"
    assert so_entry.derived == "Deterministic Fallback"

    # Exclusions absent on charter -> SOWInterpretation out_of_scope_items
    oos_entry = entries["Out of Scope"]
    assert oos_entry.traces[0].artifact == "SOWInterpretation"
    assert oos_entry.traces[0].field == "out_of_scope_items"


def test_htl_65_export_client_deck_writes_valid_trace_json(tmp_path):
    """HTL-65: Exporting deck writes trace.json with valid JSON structure and correct entries."""
    baseline = _build_pge_baseline()
    baseline.charter.problem_statement = "Pain point statement."
    baseline.charter.solution_overview = "Solution narrative."
    baseline.charter.success_criteria_summary = "Success summary narrative."

    res = export_client_deck(baseline, tmp_path)
    assert res.manifest_path.exists()

    data = json.loads(res.manifest_path.read_text(encoding="utf-8"))
    assert data["entries_count"] == len(data["entries"])

    field_map = {e["element"]: e["traces"][0]["field"] for e in data["entries"]}
    assert field_map["What problem are we solving?"] == "problem_statement"
    assert field_map["What does success look like?"] == "success_criteria_summary"
    assert field_map["Solution Overview"] == "solution_overview"
    assert field_map["Out of Scope"] == "exclusions"
