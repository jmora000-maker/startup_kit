"""Tests for the ReviewStorage interface and its local filesystem backend (HTL-13, HTL-03)."""

import json
import os

import pytest

from src.config import config
from src.review_storage import get_review_storage
from src.review_storage.local import LocalReviewStorage

BASELINE = {"project_name": "Acme Project", "governance_tier": "Elevated"}
VALIDATION_REPORT = {"findings": [{"code": "VAL-01", "severity": "warning", "message": "example"}]}


@pytest.fixture
def storage(tmp_path):
    return LocalReviewStorage(base_dir=tmp_path / "review_queue")


def test_create_run_then_get_run_roundtrips_exact_content(storage):
    run_id = storage.create_run("Acme Project", BASELINE, VALIDATION_REPORT)

    run = storage.get_run(run_id)

    assert run.run_id == run_id
    assert run.state == "pending_review"
    assert run.baseline == BASELINE
    assert run.validation_report == VALIDATION_REPORT


def test_create_run_writes_htl03_file_layout(storage):
    run_id = storage.create_run("Acme Project", BASELINE, VALIDATION_REPORT)

    run_dir = storage.base_dir / run_id
    assert (run_dir / "baseline.json").exists()
    assert (run_dir / "validation_report.json").exists()
    status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
    assert status == {"state": "pending_review"}


def test_list_runs_with_no_filter_returns_all(storage):
    id1 = storage.create_run("Project One", BASELINE, VALIDATION_REPORT)
    id2 = storage.create_run("Project Two", BASELINE, VALIDATION_REPORT)

    summaries = storage.list_runs()

    assert {s.run_id for s in summaries} == {id1, id2}


def test_list_runs_filtered_by_state_returns_only_matching(storage):
    id1 = storage.create_run("Project One", BASELINE, VALIDATION_REPORT)
    id2 = storage.create_run("Project Two", BASELINE, VALIDATION_REPORT)
    storage.update_status(id2, "approved", if_state="pending_review")

    pending = storage.list_runs(state="pending_review")
    approved = storage.list_runs(state="approved")

    assert [s.run_id for s in pending] == [id1]
    assert [s.run_id for s in approved] == [id2]


def test_update_status_with_correct_if_state_succeeds(storage):
    run_id = storage.create_run("Acme Project", BASELINE, VALIDATION_REPORT)

    storage.update_status(run_id, "approved", if_state="pending_review")

    assert storage.get_run(run_id).state == "approved"


def test_update_status_with_wrong_if_state_raises_and_state_unchanged_on_disk(storage):
    run_id = storage.create_run("Acme Project", BASELINE, VALIDATION_REPORT)

    with pytest.raises(ValueError):
        storage.update_status(run_id, "approved", if_state="approved")

    # Read the on-disk state back directly (a fresh LocalReviewStorage instance, not the same
    # in-memory call) to prove the guard's failure genuinely left no write behind.
    reread = LocalReviewStorage(base_dir=storage.base_dir)
    assert reread.get_run(run_id).state == "pending_review"


def test_save_corrected_baseline_updates_stored_baseline(storage):
    run_id = storage.create_run("Acme Project", BASELINE, VALIDATION_REPORT)
    corrected = {**BASELINE, "governance_tier": "Guided"}
    audit = {"run_id": run_id, "facts": {}, "corrections": []}

    storage.save_corrected_baseline(run_id, corrected, audit)

    assert storage.get_run(run_id).baseline == corrected


def test_put_generated_files_returns_local_path_reference_and_files_exist(storage, tmp_path):
    run_id = storage.create_run("Acme Project", BASELINE, VALIDATION_REPORT)
    source_file = tmp_path / "Acme_Startup_Kit.docx"
    source_file.write_bytes(b"fake docx bytes")

    references = storage.put_generated_files(run_id, [source_file])

    assert set(references) == {"Acme_Startup_Kit.docx"}
    stored_path = references["Acme_Startup_Kit.docx"]
    assert os.path.exists(stored_path)
    assert open(stored_path, "rb").read() == b"fake docx bytes"


def test_review_storage_backend_defaults_to_local():
    assert config.review_storage_backend == "local"


def test_get_review_storage_returns_local_backend_instance():
    assert isinstance(get_review_storage(), LocalReviewStorage)


def test_pytest_uses_local_backend_even_when_review_storage_backend_env_is_gcp(monkeypatch):
    """HTL-13's safety rule: a shell's REVIEW_STORAGE_BACKEND must never make a test run touch
    the (unimplemented) cloud backend. config.review_storage_backend was fixed to "local" when
    src.config was first imported (tests/conftest.py forces REVIEW_STORAGE_BACKEND=local before
    any import happens), so setting the env var afterward, as this test does, must not change
    get_review_storage()'s behavior."""
    monkeypatch.setenv("REVIEW_STORAGE_BACKEND", "gcp")

    assert os.environ["REVIEW_STORAGE_BACKEND"] == "gcp"
    assert config.review_storage_backend == "local"
    assert isinstance(get_review_storage(), LocalReviewStorage)


def test_gcp_backend_raises_not_implemented(monkeypatch):
    monkeypatch.setattr(config, "review_storage_backend", "gcp")
    with pytest.raises(NotImplementedError):
        get_review_storage()


def test_unknown_backend_raises_value_error(monkeypatch):
    monkeypatch.setattr(config, "review_storage_backend", "bogus")
    with pytest.raises(ValueError):
        get_review_storage()
