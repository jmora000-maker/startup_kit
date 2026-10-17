"""Integration tests for standalone Firestore client against local Firestore emulator."""

import os
import urllib.request
import urllib.error
from datetime import date, datetime, timezone
import pytest

from src.core.models import Milestone
from src.storage.firestore_client import (
    get_firestore_client,
    write_run,
    get_run,
    query_runs_by_status,
    sync_milestones,
    query_milestones_by_date_range,
)

FIRESTORE_HOST = os.environ.get("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080")


@pytest.fixture(scope="session", autouse=True)
def ensure_firestore_emulator():
    """Verify Firestore emulator is reachable before executing tests."""
    os.environ["FIRESTORE_EMULATOR_HOST"] = FIRESTORE_HOST
    url = f"http://{FIRESTORE_HOST}/"
    try:
        with urllib.request.urlopen(url, timeout=2.0) as resp:
            if resp.status != 200:
                pytest.fail(
                    f"Firestore emulator returned status {resp.status} at {url}. "
                    "Start it with: firebase emulators:start --only firestore"
                )
    except Exception as exc:
        pytest.fail(
            f"Firestore emulator is not reachable at {url} ({exc}). "
            "Start it with: firebase emulators:start --only firestore"
        )


def test_write_and_get_run_roundtrip():
    """Verify write_run and get_run properly store and retrieve run documents."""
    run_id = f"test_run_roundtrip_{int(datetime.now(timezone.utc).timestamp())}"
    baseline_payload = {
        "project_name": "Phoenix Migration",
        "contract_type": "Fixed Bid",
        "charter": {"delivery_manager": "Sarah Connor", "talent_pm": "Kyle Reese"},
        "milestones": [{"id": "MS-01", "description": "Architecture Review"}],
    }
    validation_payload = {"summary": "Valid baseline", "issues": []}

    res_write = write_run(
        run_id=run_id,
        status="pending_review",
        project_name="Phoenix Migration",
        contract_type="Fixed Bid",
        delivery_manager="Sarah Connor",
        talent_pm="Kyle Reese",
        sow_awarded_date=date(2026, 11, 1),
        baseline=baseline_payload,
        validation_report=validation_payload,
    )
    assert res_write is not None

    fetched = get_run(run_id)
    assert fetched is not None
    assert fetched["run_id"] == run_id
    assert fetched["status"] == "pending_review"
    assert fetched["project_name"] == "Phoenix Migration"
    assert fetched["contract_type"] == "Fixed Bid"
    assert fetched["delivery_manager"] == "Sarah Connor"
    assert fetched["talent_pm"] == "Kyle Reese"
    assert fetched["sow_awarded_date"] == "2026-11-01"
    assert fetched["baseline"]["project_name"] == "Phoenix Migration"
    assert fetched["validation_report"]["summary"] == "Valid baseline"
    assert "created_at" in fetched
    assert "updated_at" in fetched


def test_write_run_preserves_created_at_on_update():
    """Verify that overwriting a run document preserves created_at and refreshes updated_at."""
    run_id = f"test_run_timestamps_{int(datetime.now(timezone.utc).timestamp())}"
    
    # 1. Initial write
    write_run(
        run_id=run_id,
        status="pending_review",
        project_name="Timestamp Test",
        contract_type="T&M",
        delivery_manager="DM One",
        talent_pm="PM One",
        sow_awarded_date="2026-10-15",
        baseline={"version": 1},
        validation_report={},
    )
    run_v1 = get_run(run_id)
    assert run_v1 is not None
    created_at_v1 = run_v1["created_at"]
    updated_at_v1 = run_v1["updated_at"]

    # 2. Overwrite / update
    write_run(
        run_id=run_id,
        status="approved",
        project_name="Timestamp Test",
        contract_type="T&M",
        delivery_manager="DM One",
        talent_pm="PM One",
        sow_awarded_date="2026-10-15",
        baseline={"version": 2},
        validation_report={},
    )
    run_v2 = get_run(run_id)
    assert run_v2 is not None
    assert run_v2["status"] == "approved"
    assert run_v2["baseline"]["version"] == 2
    assert run_v2["created_at"] == created_at_v1
    assert run_v2["updated_at"] >= updated_at_v1


def test_get_run_nonexistent_returns_none():
    """Verify get_run returns None for a non-existent run ID."""
    assert get_run("non_existent_run_id_xyz_99999") is None


def test_query_runs_by_status():
    """Verify query_runs_by_status performs a real Firestore query and returns matching runs."""
    ts = int(datetime.now(timezone.utc).timestamp())
    run_p1 = f"test_status_p1_{ts}"
    run_p2 = f"test_status_p2_{ts}"
    run_a1 = f"test_status_a1_{ts}"

    write_run(
        run_id=run_p1,
        status="pending_review",
        project_name="Alpha",
        contract_type="Fixed Bid",
        delivery_manager="DM A",
        talent_pm="PM A",
        sow_awarded_date=None,
        baseline={},
        validation_report={},
    )
    write_run(
        run_id=run_p2,
        status="pending_review",
        project_name="Beta",
        contract_type="Fixed Bid",
        delivery_manager="DM B",
        talent_pm="PM B",
        sow_awarded_date=None,
        baseline={},
        validation_report={},
    )
    write_run(
        run_id=run_a1,
        status="approved",
        project_name="Gamma",
        contract_type="Fixed Bid",
        delivery_manager="DM C",
        talent_pm="PM C",
        sow_awarded_date=None,
        baseline={},
        validation_report={},
    )

    pending_runs = query_runs_by_status("pending_review")
    pending_ids = [r["run_id"] for r in pending_runs]
    assert run_p1 in pending_ids
    assert run_p2 in pending_ids
    assert run_a1 not in pending_ids

    approved_runs = query_runs_by_status("approved")
    approved_ids = [r["run_id"] for r in approved_runs]
    assert run_a1 in approved_ids
    assert run_p1 not in approved_ids


def test_sync_milestones_replaces_prior_content():
    """Verify sync_milestones completely rewrites subcollection to match new milestone list."""
    run_id = f"test_run_ms_sync_{int(datetime.now(timezone.utc).timestamp())}"
    write_run(
        run_id=run_id,
        status="pending_review",
        project_name="Sync Project",
        contract_type="Fixed Bid",
        delivery_manager="DM",
        talent_pm="PM",
        sow_awarded_date=None,
        baseline={},
        validation_report={},
    )

    # Initial set of milestones (3 milestones)
    initial_milestones = [
        {"id": "MS-01", "description": "Kickoff", "external_date": "2026-11-01"},
        {"id": "MS-02", "description": "Design Approval", "external_date": "2026-11-15"},
        {"id": "MS-03", "description": "Prototype Complete", "external_date": "2026-12-01"},
    ]
    synced_1 = sync_milestones(run_id, initial_milestones)
    assert len(synced_1) == 3

    client = get_firestore_client()
    docs_1 = list(client.collection("runs").document(run_id).collection("milestones").stream())
    doc_ids_1 = {d.id for d in docs_1}
    assert doc_ids_1 == {"MS-01", "MS-02", "MS-03"}

    # Replace with a different set of milestones (using Pydantic models)
    updated_milestones = [
        Milestone(id="MS-10", description="Revised Kickoff", external_date=date(2026, 11, 5)),
        Milestone(id="MS-20", description="Final Signoff", external_date=date(2026, 12, 20)),
    ]
    synced_2 = sync_milestones(run_id, updated_milestones)
    assert len(synced_2) == 2

    docs_2 = list(client.collection("runs").document(run_id).collection("milestones").stream())
    doc_ids_2 = {d.id for d in docs_2}
    # Old milestones (MS-01, MS-02, MS-03) must be deleted
    assert doc_ids_2 == {"MS-10", "MS-20"}
    assert "MS-01" not in doc_ids_2
    assert "MS-02" not in doc_ids_2
    assert "MS-03" not in doc_ids_2


def test_query_milestones_by_date_range_cross_run_collection_group():
    """Verify collection group query returns milestones from multiple runs in date range."""
    ts = int(datetime.now(timezone.utc).timestamp())
    run_a = f"test_cg_run_a_{ts}"
    run_b = f"test_cg_run_b_{ts}"
    ms_a1 = f"MS_A1_{ts}"
    ms_a2 = f"MS_A2_{ts}"
    ms_b1 = f"MS_B1_{ts}"
    ms_b2 = f"MS_B2_{ts}"

    write_run(
        run_id=run_a,
        status="pending_review",
        project_name="Run A",
        contract_type="Fixed Bid",
        delivery_manager="DM A",
        talent_pm="PM A",
        sow_awarded_date=None,
        baseline={},
        validation_report={},
    )
    write_run(
        run_id=run_b,
        status="pending_review",
        project_name="Run B",
        contract_type="Fixed Bid",
        delivery_manager="DM B",
        talent_pm="PM B",
        sow_awarded_date=None,
        baseline={},
        validation_report={},
    )

    sync_milestones(
        run_a,
        [
            {"id": ms_a1, "description": "A In Range", "external_date": "2026-11-10"},
            {"id": ms_a2, "description": "A Out of Range Late", "external_date": "2026-12-25"},
        ],
    )
    sync_milestones(
        run_b,
        [
            {"id": ms_b1, "description": "B Out of Range Early", "external_date": "2026-10-15"},
            {"id": ms_b2, "description": "B In Range", "external_date": "2026-11-20"},
        ],
    )

    # Query range [2026-11-01, 2026-11-30]
    matched = query_milestones_by_date_range(date(2026, 11, 1), date(2026, 11, 30))
    matched_ids = {m["id"] for m in matched}

    assert ms_a1 in matched_ids
    assert ms_b2 in matched_ids
    assert ms_a2 not in matched_ids
    assert ms_b1 not in matched_ids

    # Confirm run_id provenance is preserved
    a1_item = next(m for m in matched if m["id"] == ms_a1)
    b2_item = next(m for m in matched if m["id"] == ms_b2)
    assert a1_item["run_id"] == run_a
    assert b2_item["run_id"] == run_b
