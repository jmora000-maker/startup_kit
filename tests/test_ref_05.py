"""Tests for REF-05: SOW work item titles captured in catalogue, Kit, and WBS."""

import json
import re
from datetime import date
from pathlib import Path
import pytest
from src.core.models import StartupKitBaseline
from src.llm.validation import validate_and_repair_baseline
from src.generators.pmo_workbook.builder import build_workbook_model
from src.tools.check_artifacts import check_artifacts_directory


def test_ref_05_oracle_sample_titles():
    """REF-05: Kit work packages and WBS task names contain SOW descriptive titles."""
    oracle_path = Path("tests/oracles/arc.json")
    with open(oracle_path, "r", encoding="utf-8") as f:
        oracle = json.load(f)

    baseline_path = Path("tests/fixtures/sow/arc_genomics/baseline.json")
    with open(baseline_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    baseline = StartupKitBaseline.model_validate(data)
    validate_and_repair_baseline(baseline)

    # 1. Check Kit work packages
    sample_titles = oracle["sample_work_item_titles"]

    def _norm(s: str) -> str:
        cleaned = s.replace("<", "").replace(">", "")
        cleaned = re.sub(r'-\s*\n\s*', '-', cleaned)
        return " ".join(cleaned.lower().split())

    for s_id, sample in sample_titles.items():
        norm_sample = _norm(sample)
        sample_words = norm_sample.split()
        sample_prefix = " ".join(sample_words[:min(4, len(sample_words))])

        matching_wp = next((wp for wp in baseline.backlog_seed if s_id in (wp.sow_reference or "") or s_id in wp.title), None)
        assert matching_wp is not None, f"No matching work package for {s_id}"

        norm_wp_title = _norm(matching_wp.title)
        assert sample_prefix in norm_wp_title, f"Work package title '{matching_wp.title}' does not contain sample title '{sample}'"

    # 2. Check WBS tasks
    model = build_workbook_model(baseline, start_date=date(2026, 10, 5))
    for s_id, sample in sample_titles.items():
        norm_sample = _norm(sample)
        sample_words = norm_sample.split()
        sample_prefix = " ".join(sample_words[:min(4, len(sample_words))])

        matching_wbs = next(
            (t for t in model.wbs_rows if t.element_type == "Task" and (t.source_id == s_id or s_id in t.sow_stories or s_id in t.name or (t.notes and s_id in t.notes))),
            None
        )
        assert matching_wbs is not None, f"No matching WBS task for {s_id}"
        norm_t_name = _norm(matching_wbs.name)
        assert sample_prefix in norm_t_name, f"WBS task name '{matching_wbs.name}' does not contain sample title '{sample}'"
