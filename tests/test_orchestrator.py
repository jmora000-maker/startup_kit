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


def test_startup_kit_controller_e2e(populated_inputs_dir, tmp_path):
    output_dir = tmp_path / "output"
    mock_llm = create_mock_llm_client()

    controller = StartupKitController(
        ingestion_service=IngestionService(),
        llm_client=mock_llm,
        aggregator=BaselineAggregator(),
        doc_writer=DocxGenerator()
    )

    generated_file = controller.run(
        inputs_dir=populated_inputs_dir,
        output_dir=output_dir,
        tier_override="Elevated",
        contract_type_override="Fixed Bid"
    )

    assert generated_file.exists()
    assert generated_file.parent == output_dir
    assert generated_file.suffix == ".docx"

    # Verify content in generated document
    doc = docx.Document(str(generated_file))
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
        "--export-tools"
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    exit_code = main()
    assert exit_code == 0

    created_docx = list(output_dir.glob("*.docx"))
    assert len(created_docx) == 1

    created_csv = list(output_dir.glob("*.csv"))
    assert len(created_csv) == 2  # RAID and Decision Log

    created_json = list(output_dir.glob("*.json"))
    assert len(created_json) == 3  # Milestone Plan, PSA Seed, Budget Burndown Seed


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

    generated_file = controller.run(
        inputs_dir=populated_inputs_dir,
        output_dir=output_dir,
        pmo_lead="Sarah Connor",
        delivery_lead="John Connor",
        talent_pm="Kyle Reese",
    )

    assert generated_file.exists()
    doc = docx.Document(str(generated_file))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Sarah Connor" in full_text
    assert "John Connor" in full_text
    assert "Kyle Reese" in full_text
