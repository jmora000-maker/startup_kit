"""Test v3 A9: Evidence consistency flags detection and warning formatting."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model
from src.generators.pmo_workbook import export_pmo_workbook
import openpyxl


def test_v3_evidence_consistency_flags(arc_baseline, tmp_path):
    model = build_workbook_model(arc_baseline, start_date=date(2026, 10, 5))

    # Exactly 12 flags in Appendix B
    assert model.evidence_flags_count == 12

    expected_flagged = [
        "DEL-02", "DEL-03", "DEL-04", "DEL-05", "DEL-07", "DEL-08",
        "DEL-10", "DEL-11", "DEL-12", "DEL-13", "DEL-14", "DEL-15"
    ]
    assert sorted(model.evidence_flags) == expected_flagged

    # Unflagged: DEL-01, DEL-06, DEL-09, DEL-16..DEL-20
    for unflagged_id in ["DEL-01", "DEL-06", "DEL-09", "DEL-16", "DEL-17", "DEL-18", "DEL-19", "DEL-20"]:
        assert unflagged_id not in model.flagged_evidence_deliverables

    # Check notes and cell fill in exported workbook
    res = export_pmo_workbook(arc_baseline, tmp_path, start_date=date(2026, 10, 5))
    assert res.evidence_flags == 12

    wb = openpyxl.load_workbook(str(res.file_path))
    ws_wbs = wb["WBS"]

    deliv_rows = [row for row in ws_wbs.iter_rows(min_row=6, values_only=False) if row[1].value == 3 and row[2].value == "Deliverable"]
    assert len(deliv_rows) == 20

    for row in deliv_rows:
        deliv_id = row[6].value
        crit_cell = row[17]
        notes_val = str(row[21].value or "")
        if deliv_id in expected_flagged:
            assert "Evidence may belong to" in notes_val
            # Warning fill applied
            assert crit_cell.fill.fill_type is not None
        else:
            assert "Evidence may belong to" not in notes_val
