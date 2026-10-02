"""Tests for Deck completeness, table capacities, and INV-27 (DECK-07, INV-27)."""

import copy
import json
from pathlib import Path
import pytest
import pptx
import docx
import openpyxl

from src.core.models import StartupKitBaseline
from src.generators.docx_generator import DocxGenerator
from src.generators.pmo_workbook import export_pmo_workbook
from src.generators.onboarding_deck import export_onboarding_deck, build_deck_model, write_onboarding_deck
from src.tools.check_artifacts import check_deck_invariants
from src.llm.validation import validate_and_repair_baseline


@pytest.fixture
def arc_baseline():
    fixture_dir = Path("tests/fixtures/sow/arc_genomics")
    with open(fixture_dir / "baseline.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    baseline = StartupKitBaseline.model_validate(data)
    validate_and_repair_baseline(baseline)
    return baseline


def test_inv27_passes_on_arc_deck(arc_baseline, tmp_path):
    """INV-27 passes on valid deck and verifies all milestones/deliverables are captured."""
    kit_path = DocxGenerator().write_kit_docx(arc_baseline, tmp_path)
    wb_res = export_pmo_workbook(arc_baseline, tmp_path)
    deck_res = export_onboarding_deck(arc_baseline, tmp_path)

    kit_doc = docx.Document(str(kit_path))
    wb = openpyxl.load_workbook(str(wb_res.file_path), data_only=False)

    violations = check_deck_invariants(
        deck_res.file_path,
        deck_res.manifest_path,
        kit_doc,
        wb,
    )
    inv27_violations = [v for v in violations if v.inv_id == "INV-27"]
    assert len(inv27_violations) == 0


def test_inv27_fails_when_table_exceeds_capacity(arc_baseline, tmp_path):
    """INV-27 fails when a slide table exceeds its specified capacity."""
    model = build_deck_model(arc_baseline)
    # Force acceptance slide to have 18 rows without overflow truncation
    from src.generators.onboarding_deck.builder import TableRowData
    extra_rows = [
        TableRowData(cells=[f"DEL-{i:02d}", "Criteria", "M1"], is_placeholder=[False, False, False])
        for i in range(1, 18)
    ]
    model.acceptance_slide.rows = extra_rows

    broken_deck_path = tmp_path / "broken_capacity.pptx"
    write_onboarding_deck(model, broken_deck_path)

    kit_path = DocxGenerator().write_kit_docx(arc_baseline, tmp_path)
    wb_res = export_pmo_workbook(arc_baseline, tmp_path)
    kit_doc = docx.Document(str(kit_path))
    wb = openpyxl.load_workbook(str(wb_res.file_path), data_only=False)

    violations = check_deck_invariants(
        broken_deck_path,
        tmp_path / "broken_capacity.trace.json",
        kit_doc,
        wb,
    )
    inv27_violations = [v for v in violations if v.inv_id == "INV-27"]
    assert len(inv27_violations) > 0
    assert "exceeding capacity" in str(inv27_violations[0])
