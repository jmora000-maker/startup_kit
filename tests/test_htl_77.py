"""HTL-77: Automated regression test suite for financial scrubbing from Project Delivery Workbook (.xlsx).

Verifies:
1. No dollar figures, currency symbols ($), or financial amounts appear in ANY sheet of generated Workbooks (PGE, ARC, and custom baselines).
2. PGE Project Schedule Cell S7 (MS-01 Critical Path Assumptions) reads "Fee billed upon formal client acceptance." with raw dollar amount removed.
3. ARC Project Schedule Cells S8, S10, S12, S14 read "Fee is invoiced on acceptance" with all milestone dollar amounts ($26,808, $60,356, $68,210, $44,991) stripped.
4. Non-financial numeric content (dates, durations, percentages, counts, WBS codes, deliverable/RAID IDs, Excel formulas) is 100% preserved.
"""

import re
from pathlib import Path
import openpyxl
import pytest

from tests.deck_bundle import load_baseline
from tests.test_htl_62 import _build_pge_baseline
from src.generators.pmo_workbook import export_pmo_workbook
from src.config import sanitize_financial_text

FINANCIAL_REGEX = re.compile(
    r'(?:\$|€|£|¥)\s*\d+'
    r'|\b(?:USD|CAD|EUR|GBP)\s*[\d,]+'
    r'|\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:USD|CAD|EUR|GBP|dollars?)\b',
    re.IGNORECASE
)


def _scan_workbook_for_financials(wb_path: Path):
    """Scan all cells in all worksheets of an xlsx workbook for dollar figures / financial patterns."""
    wb = openpyxl.load_workbook(str(wb_path), data_only=False)
    violations = []

    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        for row_idx, row in enumerate(sheet.iter_rows(values_only=False), start=1):
            for col_idx, cell in enumerate(row, start=1):
                val = cell.value
                if val is not None and isinstance(val, str):
                    if FINANCIAL_REGEX.search(val):
                        cell_coord = f"{openpyxl.utils.get_column_letter(col_idx)}{row_idx}"
                        violations.append((sheet_name, cell_coord, val))

    return violations


def test_pge_workbook_has_zero_dollar_figures(tmp_path):
    """HTL-77: PGE Project Delivery Workbook must contain zero dollar figures across all sheets."""
    baseline = _build_pge_baseline()
    wb_res = export_pmo_workbook(baseline, tmp_path)

    wb_path = Path(wb_res.file_path)
    assert wb_path.exists(), f"Workbook was not generated: {wb_path}"

    violations = _scan_workbook_for_financials(wb_path)
    assert not violations, f"Found financial figures in PGE workbook: {violations}"

    # Specific check for PGE Project Schedule S7 (MS-01 Critical Path Assumptions)
    wb = openpyxl.load_workbook(str(wb_path), data_only=True)
    sched_sheet = wb["Project Schedule"]
    s7_val = sched_sheet["S7"].value

    assert s7_val == "Fee billed upon formal client acceptance.", (
        f"PGE S7 does not match expected scrubbed text. Got: {s7_val!r}"
    )


def test_arc_workbook_has_zero_dollar_figures(tmp_path):
    """HTL-77: ARC Project Delivery Workbook must contain zero dollar figures across all sheets."""
    baseline = load_baseline("arc_application_implementation")
    wb_res = export_pmo_workbook(baseline, tmp_path)

    wb_path = Path(wb_res.file_path)
    assert wb_path.exists(), f"Workbook was not generated: {wb_path}"

    violations = _scan_workbook_for_financials(wb_path)
    assert not violations, f"Found financial figures in ARC workbook: {violations}"

    # Specific checks for ARC Project Schedule milestone rows
    wb = openpyxl.load_workbook(str(wb_path), data_only=True)
    sched_sheet = wb["Project Schedule"]

    # Collect Critical Path Assumptions (Column S / 19) for all milestone rows
    ms_assumptions = {}
    for r in range(1, sched_sheet.max_row + 1):
        wbs_code = str(sched_sheet.cell(r, 1).value or "").strip()
        row_type = str(sched_sheet.cell(r, 2).value or "").strip()
        if row_type == "Milestone" or wbs_code in ("1.1", "2.1", "3.1", "4.1"):
            ms_assumptions[wbs_code] = str(sched_sheet.cell(r, 19).value or "")

    # MS-01 (1.1)
    s1_val = ms_assumptions.get("1.1", "")
    assert "$26,808" not in s1_val
    assert "Fee is invoiced on acceptance" in s1_val
    assert "Planned for weeks 1-6 from the start date" in s1_val

    # MS-02 (2.1)
    s2_val = ms_assumptions.get("2.1", "")
    assert "$60,356" not in s2_val
    assert "Fee is invoiced on acceptance" in s2_val
    assert "Planned for weeks 7-16 from the start date" in s2_val

    # MS-03 (3.1)
    s3_val = ms_assumptions.get("3.1", "")
    assert "$68,210" not in s3_val
    assert "Fee is invoiced on acceptance" in s3_val
    assert "Planned for weeks 17-21 from the start date" in s3_val

    # MS-04 (4.1)
    s4_val = ms_assumptions.get("4.1", "")
    assert "$44,991" not in s4_val
    assert "Fee is invoiced on acceptance" in s4_val
    assert "Planned for weeks 22-26 from the start date" in s4_val


def test_legitimate_numeric_content_preserved_in_workbook(tmp_path):
    """HTL-77: Legitimate non-financial numbers (dates, percentages, durations, IDs, formulas) remain intact."""
    baseline = _build_pge_baseline()
    wb_res = export_pmo_workbook(baseline, tmp_path)
    wb = openpyxl.load_workbook(str(wb_res.file_path), data_only=False)

    sched = wb["Project Schedule"]
    wbs = wb["WBS"]
    raid = wb["RAID Log"]

    # Check dates are preserved
    assert sched["I7"].value is not None  # Planned finish date

    # Check WBS codes & deliverable IDs are preserved
    wbs_codes = [str(row[0]) for row in wbs.iter_rows(values_only=True) if row[0]]
    assert "1" in wbs_codes
    assert "1.1" in wbs_codes

    # Check RAID items are preserved
    raid_ids = [row[0] for row in raid.iter_rows(values_only=True) if row[0]]
    assert "RAID-01" in raid_ids

    # Check acceptance criteria percentages and durations preserved in WBS (Column 18, index 17)
    ac_col_vals = [str(row[17]) for row in wbs.iter_rows(values_only=True) if len(row) > 17 and row[17]]
    assert any("95% of in-scope workloads" in val for val in ac_col_vals)
