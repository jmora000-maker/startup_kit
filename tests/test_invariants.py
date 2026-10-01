"""Invariant suite test cases (QA-04, INV-01 to INV-18)."""

import json
from pathlib import Path
import pytest
from src.core.models import StartupKitBaseline
from src.generators.docx_generator import DocxGenerator
from src.generators.pmo_workbook import export_pmo_workbook
from src.tools.check_artifacts import check_artifacts_directory
from src.llm.validation import validate_and_repair_baseline

FIXTURE_NAMES = ["arc_genomics", "mock_sow", "no_story_ids", "numbered_deliverables"]


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_invariants_on_fixtures(name, tmp_path):
    fixture_dir = Path("tests/fixtures/sow") / name
    baseline_file = fixture_dir / "baseline.json"
    assert baseline_file.exists(), f"Baseline file {baseline_file} missing."

    with open(baseline_file, "r", encoding="utf-8") as f:
        baseline_data = json.load(f)
    baseline = StartupKitBaseline.model_validate(baseline_data)
    validate_and_repair_baseline(baseline)

    writer = DocxGenerator()
    writer.write_kit_docx(baseline, tmp_path)
    writer.write_checklist_docx(baseline, tmp_path)
    export_pmo_workbook(baseline, tmp_path)

    violations = check_artifacts_directory(tmp_path)
    # Collect violations by invariant ID for structured reporting
    violation_ids = [v.inv_id for v in violations]
    
    # We assert no violations, or report the exact failures
    assert not violations, f"Invariant violations found for fixture '{name}': {[str(v) for v in violations]}"
