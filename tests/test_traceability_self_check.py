"""Test v3 A13: Traceability self-check across milestones, deliverables, work packages, and RAID items."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model
from src.generators.pmo_workbook import export_pmo_workbook
from src.scoring.cli_reporter import format_workbook_export_summary


def test_v3_traceability_self_check_clean(arc_baseline, tmp_path):
    model = build_workbook_model(arc_baseline, start_date=date(2026, 10, 5))

    trace = model.traceability
    assert "Milestones" in trace
    assert "Deliverables" in trace
    assert "Work packages" in trace
    assert "RAID items" in trace

    # Check zero missing IDs
    assert trace["Milestones"]["missing_ids"] == []
    assert trace["Deliverables"]["missing_ids"] == []
    assert trace["Work packages"]["missing_ids"] == []
    assert trace["RAID items"]["missing_ids"] == []

    # Check counts
    assert trace["Milestones"]["in_baseline"] == 4
    assert trace["Milestones"]["in_workbook"] == 4

    assert trace["Deliverables"]["in_baseline"] == 20
    assert trace["Deliverables"]["in_workbook"] == 20

    assert trace["Work packages"]["in_baseline"] == 15
    assert trace["Work packages"]["in_workbook"] == 15

    # RAID items in workbook = 52
    assert trace["RAID items"]["in_workbook"] == 52

    # Verify export and CLI summary
    res = export_pmo_workbook(arc_baseline, tmp_path, start_date=date(2026, 10, 5))
    summary_text = format_workbook_export_summary(res)
    assert "TRACEABILITY SELF-CHECK" in summary_text
    assert "Missing: None" in summary_text
    assert "Evidence flags       : 12 deliverable(s)" in summary_text
