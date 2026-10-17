"""Standalone Firestore client module for the Startup Kit app.

Per schema design in docs/GCP_Firestore_CloudStorage_Setup.md Section 8.
Connects via google-cloud-firestore, respecting FIRESTORE_EMULATOR_HOST when set.
"""

import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter


def get_firestore_client(project: Optional[str] = None) -> firestore.Client:
    """Initialize and return a Firestore client.
    
    If FIRESTORE_EMULATOR_HOST is set in environment, the client connects to the
    emulator without requiring real cloud credentials.
    """
    proj = (
        project
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCP_PROJECT")
        or "toptal-delivery-apps"
    )
    return firestore.Client(project=proj)


def _format_date(val: Any) -> Optional[str]:
    """Format date/datetime/string into ISO YYYY-MM-DD string or None."""
    if val is None or val == "":
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str:
            return None
        # If full timestamp string, extract date part if matches ISO pattern
        if "T" in val_str:
            return val_str.split("T")[0]
        return val_str
    return str(val)


def _sanitize_for_firestore(data: Any) -> Any:
    """Recursively convert Pydantic models, dates, Paths, etc. to Firestore-safe types."""
    if data is None:
        return None
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")
    elif hasattr(data, "dict"):
        data = data.dict()

    if isinstance(data, dict):
        return {str(k): _sanitize_for_firestore(v) for k, v in data.items()}
    elif isinstance(data, (list, tuple, set)):
        return [_sanitize_for_firestore(item) for item in data]
    elif isinstance(data, date) and not isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, datetime):
        if data.tzinfo is None:
            return data.replace(tzinfo=timezone.utc)
        return data
    elif isinstance(data, Path):
        return str(data)
    return data


def write_run(
    run_id: str,
    status: str,
    project_name: str,
    contract_type: str,
    delivery_manager: str,
    talent_pm: str,
    sow_awarded_date: Any,
    baseline: Any,
    validation_report: Any,
    client: Optional[firestore.Client] = None,
) -> Dict[str, Any]:
    """Create or overwrite the runs/{run_id} document.
    
    Timestamps: created_at is only set on the first write, updated_at is updated on every write.
    """
    db = client or get_firestore_client()
    doc_ref = db.collection("runs").document(run_id)

    # Check if document already exists to preserve created_at
    existing_snapshot = doc_ref.get()
    existing_data = existing_snapshot.to_dict() if existing_snapshot.exists else None

    sanitized_baseline = _sanitize_for_firestore(baseline) or {}
    sanitized_validation = _sanitize_for_firestore(validation_report) or {}
    formatted_award_date = _format_date(sow_awarded_date)

    run_data: Dict[str, Any] = {
        "status": status,
        "project_name": project_name or "",
        "contract_type": contract_type or "",
        "delivery_manager": delivery_manager or "",
        "talent_pm": talent_pm or "",
        "sow_awarded_date": formatted_award_date,
        "baseline": sanitized_baseline,
        "validation_report": sanitized_validation,
        "updated_at": firestore.SERVER_TIMESTAMP,
    }

    if existing_data and "created_at" in existing_data:
        run_data["created_at"] = existing_data["created_at"]
    else:
        run_data["created_at"] = firestore.SERVER_TIMESTAMP

    doc_ref.set(run_data)
    return run_data


def get_run(
    run_id: str,
    client: Optional[firestore.Client] = None,
) -> Optional[Dict[str, Any]]:
    """Fetch and return the full runs/{run_id} document, or None if not found."""
    db = client or get_firestore_client()
    doc_ref = db.collection("runs").document(run_id)
    snapshot = doc_ref.get()
    if not snapshot.exists:
        return None
    data = snapshot.to_dict() or {}
    data["run_id"] = run_id
    return data


def query_runs_by_status(
    status: str,
    client: Optional[firestore.Client] = None,
) -> List[Dict[str, Any]]:
    """Query and return all runs/{run_id} documents where status matches."""
    db = client or get_firestore_client()
    query = db.collection("runs").where(filter=FieldFilter("status", "==", status))
    results: List[Dict[str, Any]] = []
    for doc in query.stream():
        data = doc.to_dict() or {}
        data["run_id"] = doc.id
        results.append(data)
    return results


def sync_milestones(
    run_id: str,
    milestones: List[Any],
    client: Optional[firestore.Client] = None,
) -> List[Dict[str, Any]]:
    """Rewrite the runs/{run_id}/milestones subcollection to match given milestone list.
    
    Replaces whatever was previously in the subcollection for this run.
    """
    db = client or get_firestore_client()
    run_ref = db.collection("runs").document(run_id)
    milestones_coll = run_ref.collection("milestones")

    # 1. Delete all existing milestones in the subcollection
    existing_docs = list(milestones_coll.stream())
    if existing_docs:
        batch = db.batch()
        for doc in existing_docs:
            batch.delete(doc.reference)
        batch.commit()

    # 2. Write new milestones
    synced: List[Dict[str, Any]] = []
    if not milestones:
        return synced

    batch = db.batch()
    for idx, m in enumerate(milestones):
        m_dict: Dict[str, Any]
        if hasattr(m, "model_dump"):
            m_dict = m.model_dump(mode="json")
        elif hasattr(m, "dict"):
            m_dict = m.dict()
        elif isinstance(m, dict):
            m_dict = dict(m)
        else:
            m_dict = vars(m)

        m_sanitized = _sanitize_for_firestore(m_dict)
        # Ensure external_date and internal_buffer_date are normalized strings
        if "external_date" in m_sanitized:
            m_sanitized["external_date"] = _format_date(m_sanitized["external_date"])
        if "internal_buffer_date" in m_sanitized:
            m_sanitized["internal_buffer_date"] = _format_date(m_sanitized["internal_buffer_date"])

        m_id = str(m_sanitized.get("id") or f"MS-{idx + 1:02d}")
        m_sanitized["id"] = m_id
        m_sanitized["run_id"] = run_id

        doc_ref = milestones_coll.document(m_id)
        batch.set(doc_ref, m_sanitized)
        synced.append(m_sanitized)

    batch.commit()
    return synced


def query_milestones_by_date_range(
    start_date: Any,
    end_date: Any,
    client: Optional[firestore.Client] = None,
) -> List[Dict[str, Any]]:
    """Query across every run's milestones subcollection via collection group query.
    
    Returns milestones with external_date in the range [start_date, end_date], across ALL runs.
    """
    db = client or get_firestore_client()
    start_str = _format_date(start_date)
    end_str = _format_date(end_date)

    if start_str is None or end_str is None:
        raise ValueError(f"Invalid date range: start_date={start_date!r}, end_date={end_date!r}")

    query = (
        db.collection_group("milestones")
        .where(filter=FieldFilter("external_date", ">=", start_str))
        .where(filter=FieldFilter("external_date", "<=", end_str))
    )

    results: List[Dict[str, Any]] = []
    for doc in query.stream():
        data = doc.to_dict() or {}
        if "id" not in data:
            data["id"] = doc.id
        if "run_id" not in data and doc.reference.parent and doc.reference.parent.parent:
            data["run_id"] = doc.reference.parent.parent.id
        results.append(data)
    return results
