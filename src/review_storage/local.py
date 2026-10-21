"""Local filesystem ReviewStorage backend (HTL-03): the default everywhere except a deployed
Cloud Run instance (HTL-14).

Each paused run gets one folder, review_queue/{run_id}/, where run_id is
{sanitize_filename(project_name)}_{YYYYMMDD_HHMMSS} (OUT-11's shared sanitize_filename helper;
one run per invocation). The folder holds baseline.json, validation_report.json, and status.json
({"state": "pending_review"} initially).
"""

import json
import re
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from src.core.interfaces import ReviewStorage
from src.core.models import ReviewRun, ReviewRunSummary
from src.generators.formatting import sanitize_filename

PENDING_REVIEW = "pending_review"
APPROVED = "approved"
REJECTED = "rejected"
GENERATED = "generated"

LEGAL_STATES = {PENDING_REVIEW, APPROVED, REJECTED, GENERATED}

_RUN_ID_TIMESTAMP_RE = re.compile(r"_(\d{8}_\d{6})$")

# Guards update_status's read-current-state-then-write so the if_state check and the write that
# follows it are never interleaved with another update_status call in this process (HTL-09).
_UPDATE_LOCK = threading.Lock()


class LocalReviewStorage(ReviewStorage):
    """HTL-03's local filesystem backend."""

    def __init__(self, base_dir: Path = Path("review_queue")):
        self.base_dir = Path(base_dir)

    def _run_dir(self, run_id: str) -> Path:
        return self.base_dir / run_id

    def _baseline_path(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "baseline.json"

    def _validation_report_path(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "validation_report.json"

    def _status_path(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "status.json"

    @staticmethod
    def _write_json(path: Path, data: dict) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _read_json(path: Path) -> dict:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)

    @staticmethod
    def _created_at(run_id: str) -> datetime:
        """Recover the run's creation timestamp from HTL-03's own run_id shape, rather than
        storing it again in status.json (which HTL-03 defines as holding only {"state": ...})."""
        m = _RUN_ID_TIMESTAMP_RE.search(run_id)
        if not m:
            raise ValueError(f"run_id does not match HTL-03's shape: {run_id!r}")
        return datetime.strptime(m.group(1), "%Y%m%d_%H%M%S")

    def create_run(
        self,
        project_name: str,
        baseline: dict,
        validation_report: dict,
        outputs: Optional[dict] = None,
    ) -> str:
        when = datetime.now()
        run_id = f"{sanitize_filename(project_name)}_{when.strftime('%Y%m%d_%H%M%S')}"
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(self._baseline_path(run_id), baseline)
        self._write_json(self._validation_report_path(run_id), validation_report)
        status_data: dict = {"state": PENDING_REVIEW}
        if outputs is not None:
            status_data["outputs"] = outputs
        self._write_json(self._status_path(run_id), status_data)
        return run_id

    @staticmethod
    def _parse_timestamp(raw_val: Optional[str]) -> Optional[datetime]:
        if not raw_val:
            return None
        try:
            iso_clean = raw_val.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_clean)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except (ValueError, TypeError):
            return None

    def mark_generation_started(self, run_id: str, when: Optional[datetime] = None) -> None:
        """HTL-39: Record when document generation began to detect interrupted runs."""
        status_path = self._status_path(run_id)
        if when is None:
            ts = datetime.now(timezone.utc)
        elif when.tzinfo is not None:
            ts = when.astimezone(timezone.utc)
        else:
            ts = when
        with _UPDATE_LOCK:
            status_data = self._read_json(status_path)
            status_data["generation_started_at"] = ts.isoformat()
            self._write_json(status_path, status_data)

    def get_run(self, run_id: str) -> ReviewRun:
        baseline = self._read_json(self._baseline_path(run_id))
        validation_report = self._read_json(self._validation_report_path(run_id))
        status = self._read_json(self._status_path(run_id))
        return ReviewRun(
            run_id=run_id,
            project_name=baseline.get("project_name", ""),
            state=status["state"],
            created_at=self._created_at(run_id),
            generation_started_at=self._parse_timestamp(status.get("generation_started_at")),
            baseline=baseline,
            validation_report=validation_report,
            outputs=status.get("outputs"),
        )

    def list_runs(self, state: Optional[str] = None) -> List[ReviewRunSummary]:
        if not self.base_dir.exists():
            return []
        summaries: List[ReviewRunSummary] = []
        for run_dir in self.base_dir.iterdir():
            if not run_dir.is_dir():
                continue
            run_id = run_dir.name
            status_path = self._status_path(run_id)
            baseline_path = self._baseline_path(run_id)
            if not status_path.exists() or not baseline_path.exists():
                continue
            status_dict = self._read_json(status_path)
            run_state = status_dict["state"]
            if state is not None and run_state != state:
                continue
            project_name = self._read_json(baseline_path).get("project_name", "")
            summaries.append(
                ReviewRunSummary(
                    run_id=run_id,
                    project_name=project_name,
                    state=run_state,
                    created_at=self._created_at(run_id),
                    generation_started_at=self._parse_timestamp(status_dict.get("generation_started_at")),
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
        status_path = self._status_path(run_id)
        with _UPDATE_LOCK:
            status_data = self._read_json(status_path)
            current_state = status_data["state"]
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
            status_data["state"] = new_state
            self._write_json(status_path, status_data)

    def save_corrected_baseline(self, run_id: str, baseline: dict, audit: dict) -> None:
        self._write_json(self._baseline_path(run_id), baseline)
        self._write_json(self._run_dir(run_id) / "review_audit.json", audit)

    def put_generated_files(self, run_id: str, file_paths: List[Path]) -> Dict[str, str]:
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        references: Dict[str, str] = {}
        for src_path in file_paths:
            src_path = Path(src_path)
            dest_path = run_dir / src_path.name
            if src_path.resolve() != dest_path.resolve():
                shutil.copyfile(src_path, dest_path)
            references[src_path.name] = str(dest_path)
        return references

    def get_file_bytes(self, run_id: str, reference: str) -> bytes:
        ref_path = Path(reference)
        if not ref_path.is_absolute() or not ref_path.exists():
            ref_path = self._run_dir(run_id) / ref_path.name
        if not ref_path.exists():
            raise FileNotFoundError(f"File {reference!r} not found for run {run_id!r} in {self._run_dir(run_id)}")
        return ref_path.read_bytes()

    def list_generated_files(self, run_id: str) -> Dict[str, str]:
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            return {}
        ignored = {"baseline.json", "status.json", "validation_report.json", "review_audit.json"}
        return {p.name: str(p) for p in run_dir.iterdir() if p.is_file() and p.name not in ignored}
