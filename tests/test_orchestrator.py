"""End-to-end integration tests for StartupKitController and CLI."""

import pytest
from pathlib import Path
import docx
import pymupdf as fitz
from pptx import Presentation

from src.orchestrator import StartupKitController
from src.extractors.service import IngestionService
from src.llm.client import MockLLMClient
from src.llm.aggregator import BaselineAggregator
from src.generators.docx_generator import DocxGenerator
from main import create_mock_llm_client, main
import sys


from src.core.models import OutputSelection, RunResult


def test_startup_kit_controller_e2e(populated_inputs_dir, tmp_path):
    output_dir = tmp_path / "output"
    mock_llm = create_mock_llm_client()

    controller = StartupKitController(
        ingestion_service=IngestionService(),
        llm_client=mock_llm,
        aggregator=BaselineAggregator(),
        doc_writer=DocxGenerator()
    )

    result = controller.run(
        inputs_dir=populated_inputs_dir,
        output_dir=output_dir,
        tier_override="Elevated",
        contract_type_override="Fixed Bid",
        outputs=OutputSelection(kit=True, checklist=True, workbook=True)
    )

    assert isinstance(result, RunResult)
    assert result.kit_path.exists()
    assert result.kit_path.parent == output_dir
    assert result.kit_path.suffix == ".docx"
    assert result.workbook is not None
    assert result.workbook.file_path.exists()

    # Verify content in generated document
    doc = docx.Document(str(result.kit_path))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "TOPTAL PMO STARTUP KIT" in full_text
    assert "Pfizer Analytics & Cloud Modernization" in full_text


def test_controller_empty_inputs_error(tmp_path):
    empty_inputs = tmp_path / "empty_inputs"
    empty_inputs.mkdir()
    output_dir = tmp_path / "output"

    controller = StartupKitController(
        llm_client=create_mock_llm_client()
    )

    with pytest.raises(FileNotFoundError):
        controller.run(inputs_dir=empty_inputs, output_dir=output_dir)


def test_cli_main_execution_with_export_tools(populated_inputs_dir, tmp_path, monkeypatch):
    output_dir = tmp_path / "cli_tools_output"

    test_args = [
        "main.py",
        "--mock",
        "--inputs-dir", str(populated_inputs_dir),
        "--output-dir", str(output_dir),
        "--tier", "Elevated",
        "--contract-type", "Fixed Bid",
        "--all"
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    exit_code = main()
    assert exit_code == 0

    created_docx = list(output_dir.glob("*_Startup_Kit.docx"))
    assert len(created_docx) == 1
    assert len(list(output_dir.glob("*.docx"))) == 2

    created_xlsx = list(output_dir.glob("*.xlsx"))
    assert len(created_xlsx) == 1


def test_concurrent_extraction_all_domain_passes(populated_inputs_dir, tmp_path):
    """Verify that concurrent multi-pass extraction properly executes all domain extractors."""
    output_dir = tmp_path / "concurrent_output"
    mock_llm = create_mock_llm_client()

    controller = StartupKitController(
        ingestion_service=IngestionService(),
        llm_client=mock_llm,
        aggregator=BaselineAggregator(),
        doc_writer=DocxGenerator()
    )

    result = controller.run(
        inputs_dir=populated_inputs_dir,
        output_dir=output_dir,
        pmo_lead="Sarah Connor",
        delivery_lead="John Connor",
        talent_pm="Kyle Reese",
        outputs=OutputSelection(kit=True)
    )

    assert result.kit_path.exists()
    doc = docx.Document(str(result.kit_path))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Sarah Connor" in full_text
    assert "John Connor" in full_text
    assert "Kyle Reese" in full_text


def test_controller_default_mock_inputs_dir(tmp_path, monkeypatch):
    """Verify that StartupKitController defaults to config.mock_inputs_dir when inputs_dir is None and MockLLMClient is used."""
    output_dir = tmp_path / "mock_dir_output"
    mock_llm = create_mock_llm_client()

    captured_inputs = {}

    class DummyIngestionService(IngestionService):
        def ingest_directory(self, directory_path):
            captured_inputs["dir"] = Path(directory_path)
            return super().ingest_directory(directory_path)

    controller = StartupKitController(
        ingestion_service=DummyIngestionService(),
        llm_client=mock_llm,
        aggregator=BaselineAggregator(),
        doc_writer=DocxGenerator()
    )

    from src.config import config
    # Run using the tracked mock inputs dir (tests/fixtures/sow/mock_sow/inputs)
    if config.mock_inputs_dir.exists():
        result = controller.run(
            inputs_dir=None,
            output_dir=output_dir,
            outputs=OutputSelection(kit=True)
        )
        assert captured_inputs["dir"] == config.mock_inputs_dir
        assert result.kit_path.exists()


def test_controller_default_mock_output_dir(tmp_path, monkeypatch):
    """Verify that StartupKitController defaults to config.mock_output_dir when output_dir is None and MockLLMClient is used."""
    mock_llm = create_mock_llm_client()

    captured_paths = {}

    class DummyDocWriter:
        def write_kit_docx(self, baseline, output_path):
            captured_paths["out"] = Path(output_path)
            return Path(output_path) / "test.docx"

        def write_docx(self, baseline, output_path):
            captured_paths["out"] = Path(output_path)
            return Path(output_path) / "test.docx"

    controller = StartupKitController(
        ingestion_service=IngestionService(),
        llm_client=mock_llm,
        aggregator=BaselineAggregator(),
        doc_writer=DummyDocWriter()
    )

    from src.config import config
    if config.mock_inputs_dir.exists():
        controller.run(
            inputs_dir=config.mock_inputs_dir,
            output_dir=None,
            outputs=OutputSelection(kit=True)
        )
        assert captured_paths["out"] == config.mock_output_dir
