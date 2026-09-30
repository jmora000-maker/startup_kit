"""Test v3 A1: Removal of Project Management workstream, recurring rows, and kickoff package."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model
from src.generators.pmo_workbook import export_pmo_workbook
import openpyxl


def test_no_project_management_workstream_or_branch(arc_baseline, tmp_path):
    model = build_workbook_model(arc_baseline, start_date=date(2026, 10, 5))

    # 1. WBS has exactly 4 level 1 rows (one per SOW phase)
    l1_rows = [w for w in model.wbs_rows if w.level == 1]
    assert len(l1_rows) == 4
    for w in l1_rows:
        assert "Project Management" not in w.name
        assert "Kickoff" not in w.name
        assert "Reporting and Control" not in w.name
        assert "Ongoing" not in w.name

    # 2. No level 1 or level 2 row has Source "PM Best Practice"
    for w in model.wbs_rows:
        if w.level in (1, 2):
            assert w.source != "PM Best Practice", f"Row {w.wbs_code} ({w.name}) has source PM Best Practice"

    # 3. Schedule has exactly 4 workstream rows and 4 milestone rows
    ws_rows = [s for s in model.schedule_rows if s.row_type == "Workstream"]
    assert len(ws_rows) == 4
    for s in ws_rows:
        assert "Project Management" not in s.workstream
        assert s.source == "Baseline - Milestone Plan"

    # 4. Check workbook file contents and dropdowns
    res = export_pmo_workbook(arc_baseline, tmp_path, start_date=date(2026, 10, 5))
    wb = openpyxl.load_workbook(str(res.file_path))
    ws_lists = wb["_Lists"]

    # Verify List_Workstreams dropdown values in column 1 of _Lists
    ws_values = [cell.value for cell in ws_lists["A"] if cell.value]
    assert "Project Management (ongoing)" not in ws_values
    assert "P1 Foundation" in ws_values
    assert "P2a Services and Data" in ws_values
    assert "P2b Application Surface" in ws_values
    assert "P3 Launch" in ws_values
    assert "Multiple phases" in ws_values
    assert "Cross-phase" in ws_values
