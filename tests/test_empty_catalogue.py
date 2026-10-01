"""Tests for completely empty work item catalogue (v6 Section 1.1)."""

import copy
import logging
from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model
from src.scoring.cli_reporter import format_workbook_export_summary
from src.generators.pmo_workbook import PMOWorkbookResult
from pathlib import Path


def test_empty_catalogue_fallback_and_warning(arc_run3, caplog):
    """When baseline has no story IDs and no contracted scope items, fall back to deliverable-based behavior."""
    baseline = copy.deepcopy(arc_run3)

    # Clear all references and scope items
    for d in baseline.deliverables:
        d.sow_reference = None
        d.name = "Deliverable Name"
        d.description = "Deliverable Description"

    for wp in baseline.backlog_seed:
        wp.sow_reference = None
        wp.title = "Work Package Title"
        wp.description = "Work Package Description"

    baseline.sow_stories_catalogue = []
    if baseline.sow_interpretation:
        baseline.sow_interpretation.contracted_deliverables = []
    if baseline.charter:
        baseline.charter.high_level_scope = []

    with caplog.at_level(logging.WARNING):
        model = build_workbook_model(baseline, start_date=date(2026, 10, 5))

    # Verify WARNING logged
    assert any("No SOW work items identified in baseline" in record.message for record in caplog.records)

    # Verify traceability self-check
    assert "SOW References" in model.traceability
    trace = model.traceability["SOW References"]
    assert trace["empty"] is True

    # Test CLI output formatting
    res = PMOWorkbookResult(
        file_path=Path("dummy.xlsx"),
        workstreams_count=4,
        milestones_count=4,
        schedule_rows=4,
        wbs_rows=len(model.wbs_rows),
        task_rows=100,
        raid_rows=len(model.raid_rows),
        unmapped_deliverables=0,
        traceability=model.traceability
    )
    summary_text = format_workbook_export_summary(res, use_color=False)
    assert "No SOW work items identified" in summary_text
