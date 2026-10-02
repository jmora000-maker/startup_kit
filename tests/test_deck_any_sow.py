"""Tests verifying that the Onboarding Deck builds without error for all fixtures (DECK-15)."""

import json
from pathlib import Path
import pytest
import docx
import openpyxl

from src.core.models import StartupKitBaseline
from src.generators.docx_generator import DocxGenerator
from src.generators.pmo_workbook import export_pmo_workbook
from src.generators.onboarding_deck import export_onboarding_deck
from src.tools.check_artifacts import check_deck_invariants
from src.llm.validation import validate_and_repair_baseline

FIXTURE_PATHS = [
    Path("tests/fixtures/sow/arc_genomics/baseline.json"),
    Path("tests/fixtures/sow/arc_overextracted/baseline.json"),
    Path("tests/fixtures/sow/mock_sow/baseline.json"),
    Path("tests/fixtures/sow/no_story_ids/baseline.json"),
    Path("tests/fixtures/sow/numbered_deliverables/baseline.json"),
]


@pytest.mark.parametrize("baseline_file", FIXTURE_PATHS)
def test_deck_builds_and_passes_invariants_for_all_fixtures(baseline_file, tmp_path):
    """DECK-15: Deck builds and passes invariant checks across all five fixtures."""
    with open(baseline_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    baseline = StartupKitBaseline.model_validate(data)
    validate_and_repair_baseline(baseline)

    kit_path = DocxGenerator().write_kit_docx(baseline, tmp_path)
    wb_res = export_pmo_workbook(baseline, tmp_path)
    deck_res = export_onboarding_deck(baseline, tmp_path)

    assert deck_res.file_path.exists()
    assert deck_res.manifest_path.exists()
    assert deck_res.slides_count == 6

    kit_doc = docx.Document(str(kit_path))
    wb = openpyxl.load_workbook(str(wb_res.file_path), data_only=False)

    violations = check_deck_invariants(
        deck_res.file_path,
        deck_res.manifest_path,
        kit_doc,
        wb,
    )
    # Check that there are no invariant violations
    assert len(violations) == 0, f"Invariant violations on {baseline_file.parent.name}: {violations}"
