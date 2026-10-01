"""Tests for VAL-05, DT-01, and KIT-09 award date provenance and start date calculations."""

import pytest
from datetime import date
from src.core.models import (
    StartupKitBaseline,
    ProjectStartupCharter,
    Milestone,
)
from src.llm.validation import validate_and_repair_baseline
from src.generators.pmo_workbook.builder import calculate_start_date


def test_val_05_and_dt_01_award_date_fallback():
    """Verify that absent award date does not use today - 1 day, and start date falls back to generation date (VAL-05, DT-01)."""
    baseline = StartupKitBaseline(
        project_name="Award Date Test",
        sow_awarded_date=None,
        open_questions=[]
    )
    report = validate_and_repair_baseline(baseline)

    # Invariant INV-18: warning on absent award date
    assert any(f.invariant_id == "INV-18" for f in report.warnings)
    assert any("award" in q.lower() for q in baseline.open_questions)

    # Start date calculation with today=2026-10-01 (Thursday)
    today = date(2026, 10, 1)
    calc_start, basis = calculate_start_date(baseline, user_start_date=None, today=today)
    assert calc_start == date(2026, 10, 5)  # First Monday on or after generation date
    assert "generation" in basis.lower()
