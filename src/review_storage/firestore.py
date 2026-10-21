"""Firestore-backed ReviewStorage backend (HTL-14): the cloud backend for Google Cloud Run
and local development against the Firestore/GCS emulators.

Per schema design in docs/GCP_Firestore_CloudStorage_Setup.md Section 8.
Uses existing tested storage functions in src/storage/firestore_client.py and src/storage/gcs_client.py.
"""

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from google.cloud import firestore

from src.core.interfaces import ReviewStorage
from src.core.models import ReviewRun, ReviewRunSummary
from src.generators.formatting import sanitize_filename
from src.storage.firestore_client import (
    get_firestore_client,
    get_run as fs_get_run,
    query_runs_by_status as fs_query_runs_by_status,
    sync_milestones as fs_sync_milestones,
    write_run as fs_write_run,
)
from src.storage.gcs_client import (
    get_bucket_name,
    get_storage_client,
    upload_file as gcs_upload_file,
    download_file_bytes as gcs_download_file_bytes,
    list_run_files as gcs_list_run_files,
)

PENDING_REVIEW = "pending_review"
APPROVED = "approved"
REJECTED = "rejected"
GENERATED = "generated"

LEGAL_STATES = {PENDING_REVIEW, APPROVED, REJECTED, GENERATED}

_RUN_ID_TIMESTAMP_RE = re.compile(r"_(\d{8}_\d{6})$")


class FirestoreReviewStorage(ReviewStorage):
    """Firestore + Cloud Storage backed ReviewStorage backend (HTL-14)."""

    def __init__(
        self,
        firestore_client: Optional[firestore.Client] = None,
        bucket_name: Optional[str] = None,
    ):
        self.client = firestore_client or get_firestore_client()
        self.bucket_name = get_bucket_name(bucket_name)

    @staticmethod
    def _created_at(run_id: str, raw_created_at: Any = None) -> datetime:
        """Parse or recover creation timestamp."""
        if isinstance(raw_created_at, datetime):
            return raw_created_at.replace(tzinfo=None) if raw_created_at.tzinfo else raw_created_at
        if isinstance(raw_created_at, str):
            try:
                iso_clean = raw_created_at.replace("Z", "+00:00")
                dt = datetime.fromisoformat(iso_clean)
                return dt.replace(tzinfo=None) if dt.tzinfo else dt
            except ValueError:
                pass
        m = _RUN_ID_TIMESTAMP_RE.search(run_id)
        if m:
            return datetime.strptime(m.group(1), "%Y%m%d_%H%M%S")
        return datetime.now()

    def create_run(
        self,
        project_name: str,
        baseline: dict,
        validation_report: dict,
        outputs: Optional[dict] = None,
    ) -> str:
        when = datetime.now()
        run_id = f"{sanitize_filename(project_name)}_{when.strftime('%Y%m%d_%H%M%S')}"

        charter = baseline.get("charter", {}) if isinstance(baseline, dict) else {}
        delivery_manager = charter.get("delivery_manager", "") if isinstance(charter, dict) else ""
        talent_pm = charter.get("talent_pm", "") if isinstance(charter, dict) else ""
        contract_type = baseline.get("contract_type", "") if isinstance(baseline, dict) else ""
        sow_awarded_date = baseline.get("sow_awarded_date") if isinstance(baseline, dict) else None

        fs_write_run(
            run_id=run_id,
            status=PENDING_REVIEW,
            project_name=project_name,
            contract_type=contract_type,
            delivery_manager=delivery_manager,
            talent_pm=talent_pm,
            sow_awarded_date=sow_awarded_date,
            baseline=baseline,
            validation_report=validation_report,
            outputs=outputs,
            client=self.client,
        )

        milestones = baseline.get("milestones", []) if isinstance(baseline, dict) else []
        fs_sync_milestones(run_id, milestones, client=self.client)

        return run_id

    @staticmethod
    def _parse_timestamp(raw_val: Any) -> Optional[datetime]:
        """Parse or recover a timestamp from datetime or ISO string in UTC."""
        if raw_val is None:
            return None
        if isinstance(raw_val, datetime):
            if raw_val.tzinfo is not None:
                return raw_val.astimezone(timezone.utc).replace(tzinfo=None)
            return raw_val
        if isinstance(raw_val, str):
            try:
                iso_clean = raw_val.replace("Z", "+00:00")
                dt = datetime.fromisoformat(iso_clean)
                if dt.tzinfo is not None:
                    return dt.astimezone(timezone.utc).replace(tzinfo=None)
                return dt
            except ValueError:
                pass
        return None

    def mark_generation_started(self, run_id: str, when: Optional[datetime] = None) -> None:
        """HTL-39: Record when document generation began to detect interrupted runs."""
        doc_ref = self.client.collection("runs").document(run_id)
        ts = when if when is not None else firestore.SERVER_TIMESTAMP
        doc_ref.update({
            "generation_started_at": ts,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })

    def get_run(self, run_id: str) -> ReviewRun:
        doc = fs_get_run(run_id, client=self.client)
        if doc is None:
            raise FileNotFoundError(f"Run {run_id!r} not found in Firestore.")

        baseline = doc.get("baseline") or {}
        validation_report = doc.get("validation_report") or {}
        state = doc.get("status") or doc.get("state") or PENDING_REVIEW
        project_name = doc.get("project_name") or baseline.get("project_name", "")
        created_at = self._created_at(run_id, doc.get("created_at"))
        generation_started_at = self._parse_timestamp(doc.get("generation_started_at"))
        outputs = doc.get("outputs")

        return ReviewRun(
            run_id=run_id,
            project_name=project_name,
            state=state,
            created_at=created_at,
            generation_started_at=generation_started_at,
            baseline=baseline,
            validation_report=validation_report,
            outputs=outputs,
        )

    def list_runs(self, state: Optional[str] = None) -> List[ReviewRunSummary]:
        if state is not None:
            docs = fs_query_runs_by_status(status=state, client=self.client)
        else:
            docs = []
            coll_ref = self.client.collection("runs")
            for d in coll_ref.stream():
                data = d.to_dict() or {}
                data["run_id"] = d.id
                docs.append(data)

        summaries: List[ReviewRunSummary] = []
        for doc in docs:
            run_id = doc.get("run_id", "")
            baseline = doc.get("baseline") or {}
            project_name = doc.get("project_name") or baseline.get("project_name", "")
            run_state = doc.get("status") or doc.get("state") or PENDING_REVIEW
            created_at = self._created_at(run_id, doc.get("created_at"))
            generation_started_at = self._parse_timestamp(doc.get("generation_started_at"))
            summaries.append(
                ReviewRunSummary(
                    run_id=run_id,
                    project_name=project_name,
                    state=run_state,
                    created_at=created_at,
                    generation_started_at=generation_started_at,
                )
            )
        return summaries

    def list_pending_runs(self) -> List[ReviewRunSummary]:
        return self.list_runs(state=PENDING_REVIEW)

    def update_status(self, run_id: str, new_state: str, if_state: Optional[str] = None) -> None:
        if new_state not in LEGAL_STATES:
            raise ValueError(
                f"update_status guard failed for {run_id!r}: invalid new_state {new_state!r}, "
                f"expected one of {sorted(LEGAL_STATES)!r} (no update applied)."
            )

        doc_ref = self.client.collection("runs").document(run_id)

        @firestore.transactional
        def _update_in_transaction(transaction: firestore.Transaction) -> None:
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                raise FileNotFoundError(f"Run {run_id!r} not found in Firestore (no update applied).")
            data = snapshot.to_dict() or {}
            current_state = data.get("status") or data.get("state")
            if current_state == REJECTED:
                raise ValueError(
                    f"update_status guard failed for {run_id!r}: run is in terminal 'rejected' state "
                    f"and cannot be resumed (no update applied)."
                )
            if if_state is not None and current_state != if_state:
                raise ValueError(
                    f"update_status guard failed for {run_id!r}: expected state {if_state!r}, "
                    f"found {current_state!r} (no update applied)."
                )
            transaction.update(
                doc_ref,
                {
                    "status": new_state,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                },
            )

        transaction = self.client.transaction()
        _update_in_transaction(transaction)

    def save_corrected_baseline(self, run_id: str, baseline: dict, audit: dict) -> None:
        doc = fs_get_run(run_id, client=self.client)
        if doc is None:
            raise FileNotFoundError(f"Run {run_id!r} not found in Firestore.")

        charter = baseline.get("charter", {}) if isinstance(baseline, dict) else {}
        delivery_manager = charter.get("delivery_manager", "") if isinstance(charter, dict) else ""
        talent_pm = charter.get("talent_pm", "") if isinstance(charter, dict) else ""
        contract_type = baseline.get("contract_type", "") if isinstance(baseline, dict) else ""
        sow_awarded_date = baseline.get("sow_awarded_date") if isinstance(baseline, dict) else None
        project_name = baseline.get("project_name", "") if isinstance(baseline, dict) else doc.get("project_name", "")

        fs_write_run(
            run_id=run_id,
            status=doc.get("status") or doc.get("state") or PENDING_REVIEW,
            project_name=project_name,
            contract_type=contract_type,
            delivery_manager=delivery_manager,
            talent_pm=talent_pm,
            sow_awarded_date=sow_awarded_date,
            baseline=baseline,
            validation_report=doc.get("validation_report", {}),
            outputs=doc.get("outputs"),
            review_audit=audit,
            client=self.client,
        )

        milestones = baseline.get("milestones", []) if isinstance(baseline, dict) else []
        fs_sync_milestones(run_id, milestones, client=self.client)

    def put_generated_files(self, run_id: str, file_paths: List[Path]) -> Dict[str, str]:
        references: Dict[str, str] = {}
        for src_path in file_paths:
            src_path = Path(src_path)
            blob_path = gcs_upload_file(
                run_id=run_id,
                local_file_path=src_path,
                document_name=src_path.name,
                client=get_storage_client(),
                bucket_name=self.bucket_name,
            )
            references[src_path.name] = blob_path
        return references

    def get_file_bytes(self, run_id: str, reference: str) -> bytes:
        return gcs_download_file_bytes(
            run_id=run_id,
            document_name=reference,
            client=get_storage_client(),
            bucket_name=self.bucket_name,
        )

    def list_generated_files(self, run_id: str) -> Dict[str, str]:
        blob_names = gcs_list_run_files(
            run_id=run_id,
            client=get_storage_client(),
            bucket_name=self.bucket_name,
        )
        return {Path(b).name: b for b in blob_names}
