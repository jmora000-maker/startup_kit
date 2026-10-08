"""HTL-02 / HTL-29: tests for the review pipeline split point in StartupKitController.run()."""

from pathlib import Path
import pytest

from src.core.models import OutputSelection, RunResult
from src.extractors.service import IngestionService
from src.generators.docx_generator import DocxGenerator
from src.llm.aggregator import BaselineAggregator
from src.llm.mock_responses import create_mock_llm_client
from src.orchestrator import StartupKitController
from src.review_storage.local import LocalReviewStorage


def test_pause_for_review_true_creates_stored_run_and_writes_no_documents(populated_inputs_dir, tmp_path, monkeypatch):
    """HTL-02 / HTL-29: With pause_for_review=True, execution stops after extraction/validation,
    persists a pending_review run in storage with the extracted baseline and validation report,
    and generates NO document files."""
    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    output_dir = tmp_path / "output"
    mock_llm = create_mock_llm_client()
    controller = StartupKitController(
        ingestion_service=IngestionService(),
        llm_client=mock_llm,
        aggregator=BaselineAggregator(),
        doc_writer=DocxGenerator(),
    )

    result = controller.run(
        inputs_dir=populated_inputs_dir,
        output_dir=output_dir,
        tier_override="Elevated",
        contract_type_override="Fixed Bid",
        outputs=OutputSelection(kit=True, checklist=True, workbook=True, slides=True),
        pause_for_review=True,
    )

    # 1. Confirm result indicates run was paused with a valid run_id
    assert isinstance(result, RunResult)
    assert result.paused is True
    assert result.run_id is not None
    assert result.kit_path is None
    assert result.checklist_path is None
    assert result.workbook is None
    assert result.slides is None

    # 2. Confirm NO document files are written to output_dir
    if output_dir.exists():
        assert list(output_dir.iterdir()) == []

    # 3. Confirm a real run now exists in storage with state == "pending_review"
    stored_run = storage.get_run(result.run_id)
    assert stored_run.state == "pending_review"
    assert stored_run.run_id == result.run_id

    # 4. Confirm stored baseline and validation report match what was actually extracted
    assert result.baseline is not None
    assert result.validation_report is not None
    assert stored_run.baseline == result.baseline.model_dump(mode="json")
    assert stored_run.validation_report == result.validation_report.model_dump(mode="json")


def test_pause_for_review_false_generates_documents_and_creates_no_stored_run(populated_inputs_dir, tmp_path, monkeypatch):
    """HTL-02: With pause_for_review=False, straight-through execution writes document outputs
    and creates no run in review storage."""
    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    output_dir = tmp_path / "output"
    mock_llm = create_mock_llm_client()
    controller = StartupKitController(
        ingestion_service=IngestionService(),
        llm_client=mock_llm,
        aggregator=BaselineAggregator(),
        doc_writer=DocxGenerator(),
    )

    result = controller.run(
        inputs_dir=populated_inputs_dir,
        output_dir=output_dir,
        tier_override="Elevated",
        contract_type_override="Fixed Bid",
        outputs=OutputSelection(kit=True, checklist=True, workbook=True),
        pause_for_review=False,
    )

    # 1. Confirm result indicates straight-through generation
    assert result.paused is False
    assert result.run_id is None
    assert result.kit_path is not None
    assert result.kit_path.exists()
    assert result.checklist_path is not None
    assert result.checklist_path.exists()
    assert result.workbook is not None
    assert result.workbook.file_path.exists()

    # 2. Confirm no run was created in storage
    assert storage.list_runs() == []


def test_pause_for_review_omitted_defaults_to_false(populated_inputs_dir, tmp_path, monkeypatch):
    """HTL-29: Default value of pause_for_review is False, leaving existing callers untouched."""
    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)
    monkeypatch.setattr("src.review_storage.get_review_storage", lambda: storage)

    output_dir = tmp_path / "output"
    mock_llm = create_mock_llm_client()
    controller = StartupKitController(
        ingestion_service=IngestionService(),
        llm_client=mock_llm,
        aggregator=BaselineAggregator(),
        doc_writer=DocxGenerator(),
    )

    result = controller.run(
        inputs_dir=populated_inputs_dir,
        output_dir=output_dir,
        outputs=OutputSelection(kit=True, checklist=False, workbook=False),
    )

    assert result.paused is False
    assert result.run_id is None
    assert result.kit_path is not None
    assert result.kit_path.exists()
    assert storage.list_runs() == []
