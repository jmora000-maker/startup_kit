"""Tests for orchestrator export options and --slides output selection (DECK-02, OUT-01, OUT-02)."""

import logging
from pathlib import Path
import pytest

from src.core.models import OutputSelection, StartupKitBaseline
from src.orchestrator import StartupKitController
from src.generators.docx_generator import DocxGenerator
from src.llm.client import MockLLMClient
from src.llm.validation import validate_and_repair_baseline
import json


def test_output_selection_flags():
    """Verify OutputSelection.from_flags for slides and all combinations (DECK-02)."""
    # Default: workbook only
    sel_default = OutputSelection.from_flags(all_=False, kit=False, checklist=False, export_tools=False, slides=False)
    assert not sel_default.kit
    assert not sel_default.checklist
    assert sel_default.workbook
    assert not sel_default.slides

    # --slides implies kit, workbook, and slides
    sel_slides = OutputSelection.from_flags(all_=False, kit=False, checklist=False, export_tools=False, slides=True)
    assert sel_slides.kit
    assert not sel_slides.checklist
    assert sel_slides.workbook
    assert sel_slides.slides

    # --all implies kit, checklist, workbook, slides
    sel_all = OutputSelection.from_flags(all_=True, kit=False, checklist=False, export_tools=False, slides=False)
    assert sel_all.kit
    assert sel_all.checklist
    assert sel_all.workbook
    assert sel_all.slides


def test_orchestrator_run_with_slides(tmp_path, caplog):
    """Verify orchestrator run with --slides writes Kit, Workbook, and Deck (DECK-02)."""
    fixture_dir = Path("tests/fixtures/sow/arc_genomics")
    with open(fixture_dir / "baseline.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    baseline = StartupKitBaseline.model_validate(data)
    validate_and_repair_baseline(baseline)

    controller = StartupKitController(
        doc_writer=DocxGenerator(),
    )

    outputs = OutputSelection(kit=True, checklist=False, workbook=True, slides=True)

    with caplog.at_level(logging.INFO):
        run_result = controller.run_reingest(
            docx_path=DocxGenerator().write_kit_docx(baseline, tmp_path),
            output_dir=tmp_path / "out",
            outputs=outputs,
        )

    assert run_result.workbook is not None
    assert run_result.slides is not None
    assert run_result.slides_path is not None
    assert run_result.slides_path.exists()
    assert run_result.slides.manifest_path.exists()
    assert "Deck sources: Startup Kit and Project Delivery Workbook also written" in caplog.text or "Exporting Talent Onboarding Deck" in caplog.text
