"""Snapshot testing for PMO Startup Kit generated artifacts (QA-03)."""

import json
from pathlib import Path
import pytest
from src.core.models import StartupKitBaseline
from src.generators.docx_generator import DocxGenerator
from src.generators.pmo_workbook import export_pmo_workbook
from src.tools.normalizers import normalize_artifacts
from src.llm.validation import validate_and_repair_baseline

FIXTURE_NAMES = ["arc_genomics", "mock_sow", "no_story_ids", "numbered_deliverables"]


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_artifact_snapshots(name, tmp_path, update_snapshots):
    fixture_dir = Path("tests/fixtures/sow") / name
    baseline_file = fixture_dir / "baseline.json"
    assert baseline_file.exists(), f"Baseline file {baseline_file} missing."

    with open(baseline_file, "r", encoding="utf-8") as f:
        baseline_data = json.load(f)
    baseline = StartupKitBaseline.model_validate(baseline_data)
    validate_and_repair_baseline(baseline)

    # Generate documents into tmp_path
    writer = DocxGenerator()
    kit_path = writer.write_kit_docx(baseline, tmp_path)
    chk_path = writer.write_checklist_docx(baseline, tmp_path)
    wb_res = export_pmo_workbook(baseline, tmp_path)
    wb_path = wb_res.file_path

    current_normalized = normalize_artifacts(kit_path, chk_path, wb_path)

    # QA-03 (Rev 2): Always write proposed snapshots to tests/snapshots_proposed/
    proposed_dir = Path("tests/snapshots_proposed") / name
    proposed_dir.mkdir(parents=True, exist_ok=True)
    proposed_file = proposed_dir / "snapshot.json"
    with open(proposed_file, "w", encoding="utf-8") as f:
        json.dump(current_normalized, f, indent=2, ensure_ascii=False)

    snapshot_dir = Path("tests/snapshots") / name
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_file = snapshot_dir / "snapshot.json"

    if update_snapshots or not snapshot_file.exists():
        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(current_normalized, f, indent=2, ensure_ascii=False)
        return

    with open(snapshot_file, "r", encoding="utf-8") as f:
        expected_normalized = json.load(f)

    assert current_normalized == expected_normalized, (
        f"Artifact snapshot mismatch for fixture '{name}'. "
        f"Proposed snapshot written to '{proposed_file}'. "
        "A human must review proposed snapshots and promote them with --update-snapshots."
    )
