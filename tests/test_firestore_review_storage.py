"""Integration tests for FirestoreReviewStorage against real local Firestore & GCS emulators."""

import os
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
import pytest

from src.core.models import (
    Milestone,
    ProjectStartupCharter,
    Stakeholder,
    StartupKitBaseline,
)
from src.review_storage.firestore import (
    FirestoreReviewStorage,
    PENDING_REVIEW,
    APPROVED,
    REJECTED,
    GENERATED,
)
from src.review_ui import facts as review
from src.storage.firestore_client import get_firestore_client
from src.storage.gcs_client import download_file, list_run_files

FIRESTORE_HOST = os.environ.get("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080")
GCS_EMULATOR_HOST = os.environ.get("STORAGE_EMULATOR_HOST", "http://localhost:4443")


@pytest.fixture(scope="session", autouse=True)
def ensure_emulators():
    """Verify both Firestore and Cloud Storage emulators are reachable before tests."""
    os.environ["FIRESTORE_EMULATOR_HOST"] = FIRESTORE_HOST
    os.environ["STORAGE_EMULATOR_HOST"] = GCS_EMULATOR_HOST

    fs_url = f"http://{FIRESTORE_HOST}/"
    try:
        with urllib.request.urlopen(fs_url, timeout=2.0) as resp:
            if resp.status != 200:
                pytest.fail(f"Firestore emulator returned status {resp.status} at {fs_url}")
    except Exception as exc:
        pytest.fail(f"Firestore emulator not reachable at {fs_url} ({exc})")

    gcs_url = f"{GCS_EMULATOR_HOST.rstrip('/')}/storage/v1/b"
    try:
        with urllib.request.urlopen(gcs_url, timeout=2.0) as resp:
            if resp.status != 200:
                pytest.fail(f"GCS emulator returned status {resp.status} at {gcs_url}")
    except Exception as exc:
        pytest.fail(f"GCS emulator not reachable at {gcs_url} ({exc})")


@pytest.fixture
def storage():
    return FirestoreReviewStorage()


def _create_sample_baseline(
    project_name: str = "Firestore Storage Test Project",
    delivery_manager: str = "Alice Johnson",
) -> StartupKitBaseline:
    return StartupKitBaseline(
        project_name=project_name,
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 11, 15),
        award_date_source="stated",
        charter=ProjectStartupCharter(
            project_name=project_name,
            client_name="Test Client Corp",
            governance_tier="Elevated",
            contract_type="Fixed Bid",
            delivery_manager=delivery_manager,
            talent_pm="Bob PM",
        ),
        milestones=[
            Milestone(id="MS-01", description="Phase 1 Architecture", external_date=date(2026, 11, 20)),
            Milestone(id="MS-02", description="Phase 2 Delivery", external_date=date(2026, 12, 15)),
        ],
        stakeholders=[
            Stakeholder(name="Executive Sponsor", role="Executive Sponsor", organization="Test Client Corp"),
            Stakeholder(name=delivery_manager, role="Delivery Manager", organization="Toptal"),
        ],
    )


def test_create_run_then_get_run_roundtrip(storage):
    """Verify create_run creates document in Firestore and get_run retrieves matching ReviewRun."""
    ts = int(datetime.now(timezone.utc).timestamp())
    project_name = f"Roundtrip Project {ts}"
    baseline = _create_sample_baseline(project_name).model_dump(mode="json")
    validation_report = {"findings": [{"code": "VAL-01", "severity": "info", "message": "All clear"}]}
    outputs = {"kit": True, "checklist": True, "workbook": True, "slides": True}

    run_id = storage.create_run(
        project_name=project_name,
        baseline=baseline,
        validation_report=validation_report,
        outputs=outputs,
    )

    run = storage.get_run(run_id)
    assert run.run_id == run_id
    assert run.project_name == project_name
    assert run.state == PENDING_REVIEW
    assert run.baseline["project_name"] == project_name
    assert run.validation_report == validation_report
    assert run.outputs == outputs
    assert isinstance(run.created_at, datetime)


def test_get_run_nonexistent_raises_file_not_found(storage):
    """Verify get_run raises FileNotFoundError for non-existent run ID."""
    with pytest.raises(FileNotFoundError):
        storage.get_run("non_existent_run_fs_99999")


def test_list_runs_and_list_pending_runs(storage):
    """Verify list_runs returns all runs and filtered subsets, matching LocalReviewStorage behavior."""
    ts = int(datetime.now(timezone.utc).timestamp())
    p1 = f"List Pending 1 {ts}"
    p2 = f"List Pending 2 {ts}"
    p3 = f"List Approved 3 {ts}"

    b1 = _create_sample_baseline(p1).model_dump(mode="json")
    b2 = _create_sample_baseline(p2).model_dump(mode="json")
    b3 = _create_sample_baseline(p3).model_dump(mode="json")

    id1 = storage.create_run(p1, b1, {})
    id2 = storage.create_run(p2, b2, {})
    id3 = storage.create_run(p3, b3, {})

    storage.update_status(id3, APPROVED, if_state=PENDING_REVIEW)

    all_runs = storage.list_runs()
    all_ids = {r.run_id for r in all_runs}
    assert {id1, id2, id3}.issubset(all_ids)

    pending_runs = storage.list_pending_runs()
    pending_ids = {r.run_id for r in pending_runs}
    assert id1 in pending_ids
    assert id2 in pending_ids
    assert id3 not in pending_ids

    approved_runs = storage.list_runs(state=APPROVED)
    approved_ids = {r.run_id for r in approved_runs}
    assert id3 in approved_ids
    assert id1 not in approved_ids


def test_update_status_guard_logic_and_state_transitions(storage):
    """Verify update_status atomic guard checks: valid state, matching if_state, terminal rejected guard."""
    ts = int(datetime.now(timezone.utc).timestamp())
    project = f"Guard Test {ts}"
    b = _create_sample_baseline(project).model_dump(mode="json")
    run_id = storage.create_run(project, b, {})

    # 1. Invalid new_state raises ValueError
    with pytest.raises(ValueError, match="invalid new_state"):
        storage.update_status(run_id, "unknown_state", if_state=PENDING_REVIEW)

    # 2. Wrong if_state raises ValueError and state remains pending_review
    with pytest.raises(ValueError, match="guard failed"):
        storage.update_status(run_id, APPROVED, if_state=APPROVED)
    assert storage.get_run(run_id).state == PENDING_REVIEW

    # 3. Correct transition succeeds: pending_review -> approved
    storage.update_status(run_id, APPROVED, if_state=PENDING_REVIEW)
    assert storage.get_run(run_id).state == APPROVED

    # 4. Stale transition raises ValueError
    with pytest.raises(ValueError, match="guard failed"):
        storage.update_status(run_id, APPROVED, if_state=PENDING_REVIEW)
    assert storage.get_run(run_id).state == APPROVED

    # 5. Non-existent run raises FileNotFoundError
    with pytest.raises(FileNotFoundError):
        storage.update_status("non_existent_run_fs_00000", APPROVED)

    # 6. Terminal rejected state cannot be resumed
    run_rej = storage.create_run(f"Reject Test {ts}", b, {})
    storage.update_status(run_rej, REJECTED, if_state=PENDING_REVIEW)
    assert storage.get_run(run_rej).state == REJECTED

    with pytest.raises(ValueError, match="rejected"):
        storage.update_status(run_rej, APPROVED, if_state=REJECTED)

    with pytest.raises(ValueError, match="rejected"):
        storage.update_status(run_rej, APPROVED)

    assert storage.get_run(run_rej).state == REJECTED


def test_outputs_persistence_htl36(storage):
    """HTL-36: Output selection dictionary is stored, retrievable, and preserved across state updates."""
    ts = int(datetime.now(timezone.utc).timestamp())
    project = f"Outputs HTL36 {ts}"
    b = _create_sample_baseline(project).model_dump(mode="json")
    outputs_selected = {"kit": False, "checklist": False, "workbook": True, "slides": True}

    run_id = storage.create_run(
        project_name=project,
        baseline=b,
        validation_report={},
        outputs=outputs_selected,
    )

    run = storage.get_run(run_id)
    assert run.outputs == outputs_selected

    # Transition to approved and confirm outputs remain intact
    storage.update_status(run_id, APPROVED, if_state=PENDING_REVIEW)
    run_approved = storage.get_run(run_id)
    assert run_approved.state == APPROVED
    assert run_approved.outputs == outputs_selected


def test_milestone_sync_on_create_and_corrected_baseline(storage):
    """Verify milestones in baseline are synced to runs/{run_id}/milestones subcollection."""
    ts = int(datetime.now(timezone.utc).timestamp())
    project = f"Milestone Sync {ts}"
    baseline_obj = _create_sample_baseline(project)
    run_id = storage.create_run(
        project_name=project,
        baseline=baseline_obj.model_dump(mode="json"),
        validation_report={},
    )

    client = get_firestore_client()
    subcoll = client.collection("runs").document(run_id).collection("milestones")
    docs1 = list(subcoll.stream())
    doc_ids1 = {d.id for d in docs1}
    assert doc_ids1 == {"MS-01", "MS-02"}

    # Update baseline with a replacement set of milestones
    corrected_baseline = baseline_obj.model_dump(mode="json")
    corrected_baseline["milestones"] = [
        {"id": "MS-99", "description": "Single Final Milestone", "external_date": "2026-12-31"}
    ]
    audit_data = {"run_id": run_id, "facts": {"milestones": "human_corrected"}}

    storage.save_corrected_baseline(run_id, corrected_baseline, audit_data)

    docs2 = list(subcoll.stream())
    doc_ids2 = {d.id for d in docs2}
    assert doc_ids2 == {"MS-99"}
    assert "MS-01" not in doc_ids2

    # Verify Firestore run doc has updated baseline
    run = storage.get_run(run_id)
    assert len(run.baseline["milestones"]) == 1
    assert run.baseline["milestones"][0]["id"] == "MS-99"


def test_put_generated_files_uploads_to_gcs(storage, tmp_path):
    """Verify put_generated_files uploads files to GCS under runs/{run_id}/ and returns references."""
    ts = int(datetime.now(timezone.utc).timestamp())
    run_id = f"test_put_files_{ts}"

    doc1 = tmp_path / "Project_Startup_Kit.docx"
    doc1.write_bytes(b"Simulated DOCX content")
    doc2 = tmp_path / "Project_Delivery_Workbook.xlsx"
    doc2.write_bytes(b"Simulated XLSX content")

    references = storage.put_generated_files(run_id, [doc1, doc2])

    assert "Project_Startup_Kit.docx" in references
    assert "Project_Delivery_Workbook.xlsx" in references
    assert references["Project_Startup_Kit.docx"] == f"runs/{run_id}/Project_Startup_Kit.docx"

    # Confirm files exist in GCS emulator bucket and can be downloaded
    gcs_files = list_run_files(run_id)
    assert f"runs/{run_id}/Project_Startup_Kit.docx" in gcs_files
    assert f"runs/{run_id}/Project_Delivery_Workbook.xlsx" in gcs_files

    dl_dir = tmp_path / "downloaded"
    dest1 = dl_dir / "dl_kit.docx"
    download_file(run_id, "Project_Startup_Kit.docx", dest1)
    assert dest1.read_bytes() == b"Simulated DOCX content"

    # Test get_file_bytes and list_generated_files (HTL-38)
    bytes_kit = storage.get_file_bytes(run_id, "Project_Startup_Kit.docx")
    assert bytes_kit == b"Simulated DOCX content"

    bytes_wb = storage.get_file_bytes(run_id, f"runs/{run_id}/Project_Delivery_Workbook.xlsx")
    assert bytes_wb == b"Simulated XLSX content"

    gen_files = storage.list_generated_files(run_id)
    assert "Project_Startup_Kit.docx" in gen_files
    assert "Project_Delivery_Workbook.xlsx" in gen_files
    assert gen_files["Project_Startup_Kit.docx"] == f"runs/{run_id}/Project_Startup_Kit.docx"


def test_full_round_trip_resume_generation_with_firestore_storage(storage, tmp_path):
    """End-to-end lifecycle test against FirestoreReviewStorage: create -> correct -> approve -> generate."""
    ts = int(datetime.now(timezone.utc).timestamp())
    project = f"E2E Lifecycle {ts}"
    initial_baseline = _create_sample_baseline(
        project_name=project,
        delivery_manager="Original Delivery Manager",
    )

    run_id = storage.create_run(
        project_name=project,
        baseline=initial_baseline.model_dump(mode="json"),
        validation_report={"summary": "Valid baseline"},
    )

    # 1. Human reviewer loads run and corrects Delivery Manager & Award Date
    loaded_baseline = review.load_run_baseline(run_id, storage=storage)
    categories = review.build_fact_categories(loaded_baseline)
    submitted = review.extracted_values(categories)
    submitted["named_roles.delivery_manager"] = "Elena Rostova (Corrected DM)"
    submitted["award_date"] = "2026-11-25"

    audit, corrected = review.save_run_review(
        run_id=run_id,
        baseline=loaded_baseline,
        categories=categories,
        submitted=submitted,
        notes={"named_roles": "Corrected in review"},
        storage=storage,
    )
    assert audit["run_id"] == run_id

    # 2. Approve run
    storage.update_status(run_id, APPROVED, if_state=PENDING_REVIEW)
    assert storage.get_run(run_id).state == APPROVED

    # 3. Generate approved run
    references, result = review.generate_approved_run(run_id, storage=storage)

    # Confirm storage state updated to generated
    run_after = storage.get_run(run_id)
    assert run_after.state == GENERATED

    # Confirm generated outputs were uploaded to GCS
    gcs_blobs = list_run_files(run_id)
    assert len(gcs_blobs) >= 3
    for ref_key, ref_blob in references.items():
        assert ref_blob in gcs_blobs


def test_firestore_mark_generation_started_persists_timestamp(storage):
    """HTL-39: mark_generation_started sets generation_started_at in Firestore doc."""
    ts = int(datetime.now(timezone.utc).timestamp())
    project = f"Interrupted Test {ts}"
    initial_baseline = _create_sample_baseline(project_name=project)

    run_id = storage.create_run(
        project_name=project,
        baseline=initial_baseline.model_dump(mode="json"),
        validation_report={"summary": "Valid baseline"},
    )
    storage.update_status(run_id, APPROVED, if_state=PENDING_REVIEW)

    run_before = storage.get_run(run_id)
    assert run_before.generation_started_at is None

    test_time = datetime(2026, 10, 21, 10, 30, 0)
    storage.mark_generation_started(run_id, when=test_time)

    run_after = storage.get_run(run_id)
    assert run_after.generation_started_at is not None
    assert run_after.generation_started_at.year == 2026
    assert run_after.generation_started_at.month == 10
    assert run_after.generation_started_at.day == 21

    summaries = storage.list_runs()
    matching_summary = next(s for s in summaries if s.run_id == run_id)
    assert matching_summary.generation_started_at is not None


def test_firestore_mark_generation_started_default_records_utc_timestamp(storage):
    """HTL-39: mark_generation_started without when arg uses firestore.SERVER_TIMESTAMP in UTC."""
    from datetime import timedelta
    ts = int(datetime.now(timezone.utc).timestamp())
    project = f"Interrupted Default {ts}"
    initial_baseline = _create_sample_baseline(project_name=project)

    run_id = storage.create_run(
        project_name=project,
        baseline=initial_baseline.model_dump(mode="json"),
        validation_report={"summary": "Valid baseline"},
    )
    storage.update_status(run_id, APPROVED, if_state=PENDING_REVIEW)

    before = datetime.now(timezone.utc).replace(tzinfo=None)
    storage.mark_generation_started(run_id)
    after = datetime.now(timezone.utc).replace(tzinfo=None)

    run = storage.get_run(run_id)
    assert run.generation_started_at is not None
    assert before - timedelta(seconds=5) <= run.generation_started_at <= after + timedelta(seconds=5)
