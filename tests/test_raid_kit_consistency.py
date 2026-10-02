"""RAID-09 / INV-30: the Workbook RAID rows carry the Kit RAID Log fields."""

import pytest

from src.tools import deck_checks
from tests.deck_fixtures import KIT_RAID_ROW, make_kit, make_workbook


def _inv30(tmp_path, kit_row=None, wb_overrides=None):
    kit = make_kit(tmp_path / "kit.docx", kit_row)
    wb = make_workbook(tmp_path / "wb.xlsx", wb_overrides)
    return [str(v) for v in deck_checks.check_inv30(kit, wb) if v.inv_id == "INV-30"]


def test_inv30_passes_when_workbook_matches_kit(tmp_path):
    assert _inv30(tmp_path) == []


@pytest.mark.parametrize("field, value", [
    ("Mitigation / Response", ""),
    ("Mitigation / Response", "Active monitoring by PMO and Delivery Manager"),
    ("Probability", "Low"),
    ("Impact", "Low"),
    ("Owner", "Client"),
    ("Status", "Closed"),
])
def test_inv30_fails_when_a_field_differs(tmp_path, field, value):
    msgs = _inv30(tmp_path, wb_overrides={field: value})
    assert any(field in m and "RSK-01" in m for m in msgs), msgs


def test_inv30_compares_after_raid06_normalization(tmp_path):
    row = list(KIT_RAID_ROW)
    row[4], row[6], row[8] = "Moderate", "[ACT-03: Assign risk owner (+2.3% Recovery)]", "resolved"
    assert _inv30(tmp_path, kit_row=row, wb_overrides={"Probability": "Medium", "Owner": "[UNASSIGNED - TO BE CONFIRMED]", "Status": "Closed"}) == []


def test_inv30_ignores_rows_not_sourced_from_kit_risks_and_issues(tmp_path):
    assert _inv30(tmp_path, wb_overrides={"Source ID": "DEP-01", "Mitigation / Response": ""}) == []
