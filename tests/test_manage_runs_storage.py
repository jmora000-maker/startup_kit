"""HTL-75 / HTL-76: Automated regression test suite for Manage Runs storage backend operations.

Covers both LocalReviewStorage and FirestoreReviewStorage / firestore_client:
1. New runs default to archived == False.
2. archive_run() marks archived == True; unarchive_run() marks archived == False.
3. list_runs(include_archived=False) excludes archived runs; list_runs(include_archived=True) includes both.
4. purge_run() on an active (non-archived) run raises ValueError and leaves all files and records intact.
5. purge_run() on an archived run permanently removes all files, subcollections, and records.
6. Firestore subcollection chunked batch deletion commits discrete batches for collections exceeding batch size.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, call, patch
import pytest

from src.core.models import ReviewRun, ReviewRunSummary
from src.review_storage.local import LocalReviewStorage
from src.review_storage.firestore import FirestoreReviewStorage
from src.storage.firestore_client import (
    write_run as fs_write_run,
    get_run as fs_get_run,
    set_run_archived as fs_set_run_archived,
    delete_run as fs_delete_run,
)


BASELINE_SAMPLE = {
    "project_name": "Cloud Migration Alpha",
    "contract_type": "Fixed Bid",
    "charter": {"delivery_manager": "Sarah Connor", "talent_pm": "Kyle Reese"},
}
VALIDATION_SAMPLE = {"findings": []}


# =========================================================================
# 1. Local Filesystem Backend Tests (LocalReviewStorage)
# =========================================================================

@pytest.fixture
def local_storage(tmp_path):
    return LocalReviewStorage(base_dir=tmp_path / "review_queue")


def test_local_storage_new_run_defaults_to_not_archived(local_storage):
    """Verify newly created run has archived == False in both get_run and list_runs."""
    run_id = local_storage.create_run("Cloud Migration Alpha", BASELINE_SAMPLE, VALIDATION_SAMPLE)

    run = local_storage.get_run(run_id)
    assert run.archived is False
    assert run.state == "pending_review"

    summaries = local_storage.list_runs(include_archived=True)
    assert len(summaries) == 1
    assert summaries[0].run_id == run_id
    assert summaries[0].archived is False

    active_summaries = local_storage.list_runs(include_archived=False)
    assert len(active_summaries) == 1
    assert active_summaries[0].run_id == run_id


def test_local_storage_archive_and_unarchive_toggles(local_storage):
    """Verify archive_run sets archived=True and unarchive_run sets archived=False."""
    run_id = local_storage.create_run("Cloud Migration Alpha", BASELINE_SAMPLE, VALIDATION_SAMPLE)

    # 1. Archive run
    local_storage.archive_run(run_id)
    run_archived = local_storage.get_run(run_id)
    assert run_archived.archived is True

    # Excluded when include_archived=False
    assert local_storage.list_runs(include_archived=False) == []

    # Included when include_archived=True
    all_runs = local_storage.list_runs(include_archived=True)
    assert len(all_runs) == 1
    assert all_runs[0].archived is True

    # 2. Unarchive run
    local_storage.unarchive_run(run_id)
    run_unarchived = local_storage.get_run(run_id)
    assert run_unarchived.archived is False

    # Included again in active runs
    active_runs = local_storage.list_runs(include_archived=False)
    assert len(active_runs) == 1
    assert active_runs[0].archived is False


def test_local_storage_purge_active_run_raises_value_error_and_preserves_files(local_storage, tmp_path):
    """Verify purge_run raises ValueError on active run and leaves all files intact."""
    run_id = local_storage.create_run("Cloud Migration Alpha", BASELINE_SAMPLE, VALIDATION_SAMPLE)

    # Put a generated file
    test_file = tmp_path / "Cloud_Migration_Alpha_Startup_Kit.docx"
    test_file.write_text("dummy deliverable content", encoding="utf-8")
    local_storage.put_generated_files(run_id, [test_file])

    run_dir = local_storage._run_dir(run_id)
    assert (run_dir / "Cloud_Migration_Alpha_Startup_Kit.docx").exists()
    assert (run_dir / "baseline.json").exists()

    # Attempt purge without archiving first
    with pytest.raises(ValueError, match="run is not archived"):
        local_storage.purge_run(run_id)

    # Confirm all files and records remain completely untouched
    assert run_dir.exists()
    assert (run_dir / "Cloud_Migration_Alpha_Startup_Kit.docx").exists()
    assert (run_dir / "baseline.json").exists()
    assert local_storage.get_run(run_id).run_id == run_id


def test_local_storage_purge_archived_run_deletes_all_files_and_record(local_storage, tmp_path):
    """Verify purge_run on archived run deletes the entire run folder and record."""
    run_id = local_storage.create_run("Cloud Migration Alpha", BASELINE_SAMPLE, VALIDATION_SAMPLE)

    # Put a generated file
    test_file = tmp_path / "Cloud_Migration_Alpha_Startup_Kit.docx"
    test_file.write_text("dummy deliverable content", encoding="utf-8")
    local_storage.put_generated_files(run_id, [test_file])

    run_dir = local_storage._run_dir(run_id)
    assert run_dir.exists()

    # Archive then purge
    local_storage.archive_run(run_id)
    local_storage.purge_run(run_id)

    # Confirm folder is deleted
    assert not run_dir.exists()

    # Confirm get_run raises FileNotFoundError
    with pytest.raises(FileNotFoundError):
        local_storage.get_run(run_id)

    # Confirm list_runs returns empty
    assert local_storage.list_runs(include_archived=True) == []


def test_local_storage_operations_on_nonexistent_run_raise_file_not_found(local_storage):
    """Verify archive, unarchive, and purge raise FileNotFoundError for nonexistent run_id."""
    with pytest.raises(FileNotFoundError):
        local_storage.get_run("nonexistent_run_123")
    with pytest.raises(FileNotFoundError):
        local_storage.archive_run("nonexistent_run_123")
    with pytest.raises(FileNotFoundError):
        local_storage.unarchive_run("nonexistent_run_123")
    with pytest.raises(FileNotFoundError):
        local_storage.purge_run("nonexistent_run_123")


# =========================================================================
# 2. Firestore Client & Storage Backend Tests (FirestoreReviewStorage)
# =========================================================================

def _build_mock_firestore_client(existing_docs: dict = None):
    """Build a mock firestore Client backed by an in-memory dictionary of docs and subcollections."""
    store = existing_docs or {}
    # Structure: store[coll_name][doc_id] = {"data": dict, "subcollections": {subcoll_name: {doc_id: dict}}}

    client = MagicMock()

    def mock_collection(coll_name):
        coll_mock = MagicMock()

        def mock_document(doc_id):
            doc_ref = MagicMock()
            doc_ref.id = doc_id

            def mock_get(transaction=None):
                snap = MagicMock()
                coll_data = store.get(coll_name, {})
                if doc_id in coll_data:
                    snap.exists = True
                    snap.to_dict.return_value = dict(coll_data[doc_id]["data"])
                else:
                    snap.exists = False
                    snap.to_dict.return_value = None
                return snap

            def mock_set(data, merge=False):
                coll_data = store.setdefault(coll_name, {})
                if doc_id not in coll_data:
                    coll_data[doc_id] = {"data": {}, "subcollections": {}}
                coll_data[doc_id]["data"] = dict(data)

            def mock_update(fields):
                coll_data = store.get(coll_name, {})
                if doc_id not in coll_data:
                    raise FileNotFoundError(f"Doc {doc_id} not found")
                coll_data[doc_id]["data"].update(fields)

            def mock_delete():
                coll_data = store.get(coll_name, {})
                if doc_id in coll_data:
                    del coll_data[doc_id]

            def mock_subcollection(sub_name):
                subcoll_mock = MagicMock()

                def mock_sub_stream():
                    coll_data = store.get(coll_name, {})
                    doc_entry = coll_data.get(doc_id, {})
                    sub_dict = doc_entry.get("subcollections", {}).get(sub_name, {})
                    snaps = []
                    for sid, sdata in list(sub_dict.items()):
                        ssnap = MagicMock()
                        ssnap.id = sid
                        ssnap.to_dict.return_value = dict(sdata)
                        sref = MagicMock()
                        sref.id = sid
                        
                        def make_delete_fn(sub_id_to_del):
                            def del_fn():
                                if sub_id_to_del in sub_dict:
                                    del sub_dict[sub_id_to_del]
                            return del_fn

                        sref.delete.side_effect = make_delete_fn(sid)
                        ssnap.reference = sref
                        snaps.append(ssnap)
                    return iter(snaps)

                subcoll_mock.stream.side_effect = mock_sub_stream
                return subcoll_mock

            doc_ref.get.side_effect = mock_get
            doc_ref.set.side_effect = mock_set
            doc_ref.update.side_effect = mock_update
            doc_ref.delete.side_effect = mock_delete
            doc_ref.collection.side_effect = mock_subcollection
            return doc_ref

        def mock_stream():
            coll_data = store.get(coll_name, {})
            snaps = []
            for did, dentry in list(coll_data.items()):
                snap = MagicMock()
                snap.id = did
                snap.to_dict.return_value = dict(dentry["data"])
                snap.reference = mock_document(did)
                snaps.append(snap)
            return iter(snaps)

        def mock_where(filter=None):
            q_mock = MagicMock()
            q_mock.stream.side_effect = mock_stream
            return q_mock

        coll_mock.document.side_effect = mock_document
        coll_mock.stream.side_effect = mock_stream
        coll_mock.where.side_effect = mock_where
        return coll_mock

    client.collection.side_effect = mock_collection

    # Batch implementation
    def mock_batch():
        b = MagicMock()
        deletes = []
        sets = []

        def batch_delete(ref):
            deletes.append(ref)

        def batch_set(ref, data):
            sets.append((ref, data))

        def batch_commit():
            for ref in deletes:
                ref.delete()
            for ref, data in sets:
                ref.set(data)

        b.delete.side_effect = batch_delete
        b.set.side_effect = batch_set
        b.commit.side_effect = batch_commit
        return b

    client.batch.side_effect = mock_batch
    return client, store


def test_firestore_client_write_run_and_defaults_archived_false():
    """Verify write_run defaults archived to False on new documents."""
    client, store = _build_mock_firestore_client()
    run_id = "test_fs_run_01"

    fs_write_run(
        run_id=run_id,
        status="pending_review",
        project_name="Cloud Migration Beta",
        contract_type="Fixed Bid",
        delivery_manager="Sarah Connor",
        talent_pm="Kyle Reese",
        sow_awarded_date="2026-11-01",
        baseline=BASELINE_SAMPLE,
        validation_report=VALIDATION_SAMPLE,
        client=client,
    )

    doc = fs_get_run(run_id, client=client)
    assert doc is not None
    assert doc["archived"] is False


def test_firestore_client_set_run_archived_and_delete_run_guards():
    """Verify set_run_archived updates flag and delete_run enforces archived status."""
    client, store = _build_mock_firestore_client({
        "runs": {
            "test_fs_run_02": {
                "data": {"project_name": "Project Beta", "status": "pending_review", "archived": False},
                "subcollections": {
                    "milestones": {
                        "MS-01": {"id": "MS-01", "description": "Phase 1"},
                        "MS-02": {"id": "MS-02", "description": "Phase 2"},
                    }
                }
            }
        }
    })

    # 1. Attempt delete on active run -> raises ValueError
    with pytest.raises(ValueError, match="run is not archived"):
        fs_delete_run("test_fs_run_02", client=client)

    # Verify run and subcollection remain intact
    assert "test_fs_run_02" in store["runs"]
    assert len(store["runs"]["test_fs_run_02"]["subcollections"]["milestones"]) == 2

    # 2. Set archived=True
    fs_set_run_archived("test_fs_run_02", True, client=client)
    assert store["runs"]["test_fs_run_02"]["data"]["archived"] is True

    # 3. Delete run -> succeeds and removes document and milestones
    fs_delete_run("test_fs_run_02", client=client)
    assert "test_fs_run_02" not in store.get("runs", {})


def test_firestore_client_chunked_batch_deletion_executes_multiple_batches():
    """Verify delete_run chunks milestone deletes into batches <= max_batch_size and commits each."""
    # Build 7 milestones with max_batch_size=3 -> requires ceil(7/3) = 3 batches
    milestones_dict = {f"MS-{i:02d}": {"id": f"MS-{i:02d}"} for i in range(1, 8)}
    client, store = _build_mock_firestore_client({
        "runs": {
            "test_chunk_run": {
                "data": {"project_name": "Large Milestone Run", "archived": True},
                "subcollections": {"milestones": milestones_dict}
            }
        }
    })

    batch_instances = []

    def mock_batch_tracked():
        b = MagicMock()
        deletes = []

        def batch_delete(ref):
            deletes.append(ref)

        def batch_commit():
            for ref in deletes:
                ref.delete()

        b.delete.side_effect = batch_delete
        b.commit.side_effect = batch_commit
        batch_instances.append(b)
        return b

    client.batch.side_effect = mock_batch_tracked

    fs_delete_run("test_chunk_run", client=client, max_batch_size=3)

    # 7 items chunked at max_batch_size=3 -> 3 discrete batches created and committed
    assert len(batch_instances) == 3
    for b in batch_instances:
        assert b.commit.call_count == 1

    # Confirm all milestones and parent document were deleted
    assert "test_chunk_run" not in store.get("runs", {})


def test_firestore_review_storage_e2e_archive_unarchive_and_purge():
    """Verify FirestoreReviewStorage integrates archive, unarchive, list filtering, and GCS + Firestore purge."""
    client, store = _build_mock_firestore_client()
    storage = FirestoreReviewStorage(firestore_client=client, bucket_name="test-bucket")

    # 1. Create run
    run_id = storage.create_run(
        project_name="GCP Migration Project",
        baseline=BASELINE_SAMPLE,
        validation_report=VALIDATION_SAMPLE,
    )

    # Initial state
    run = storage.get_run(run_id)
    assert run.archived is False
    assert len(storage.list_runs(include_archived=False)) == 1

    # 2. Archive run
    storage.archive_run(run_id)
    assert storage.get_run(run_id).archived is True
    assert len(storage.list_runs(include_archived=False)) == 0
    assert len(storage.list_runs(include_archived=True)) == 1

    # 3. Unarchive run
    storage.unarchive_run(run_id)
    assert storage.get_run(run_id).archived is False
    assert len(storage.list_runs(include_archived=False)) == 1

    # 4. Purge without archive -> raises ValueError
    with patch("src.review_storage.firestore.gcs_delete_run_files") as mock_gcs_del, \
         patch("src.review_storage.firestore.get_storage_client") as mock_get_sc:
        with pytest.raises(ValueError, match="run is not archived"):
            storage.purge_run(run_id)
        mock_gcs_del.assert_not_called()

    # 5. Archive and purge -> deletes GCS blobs and Firestore docs
    storage.archive_run(run_id)
    mock_sc = MagicMock()
    with patch("src.review_storage.firestore.gcs_delete_run_files") as mock_gcs_del, \
         patch("src.review_storage.firestore.get_storage_client", return_value=mock_sc) as mock_get_sc:
        storage.purge_run(run_id)
        mock_gcs_del.assert_called_once_with(run_id, client=mock_sc, bucket_name="test-bucket")

    # Confirm get_run raises FileNotFoundError and list_runs is empty
    with pytest.raises(FileNotFoundError):
        storage.get_run(run_id)
    assert storage.list_runs(include_archived=True) == []
