"""HTL-08 / HTL-09: Tests for Fact Review screen Approve action and error gating."""

from datetime import date
from pathlib import Path
import pytest

from src.core.models import (
    ProjectStartupCharter,
    Stakeholder,
    StartupKitBaseline,
    ValidationFinding,
    ValidationReport,
)
from src.review_storage.local import LocalReviewStorage
from src.review_ui import facts as review


def _create_sample_baseline(project_name: str = "Gamma Migration") -> StartupKitBaseline:
    return StartupKitBaseline(
        project_name=project_name,
        contract_type="Fixed Bid",
        governance_tier="Partnered",
        sow_awarded_date=date(2026, 11, 15),
        award_date_source="stated",
        charter=ProjectStartupCharter(
            project_name=project_name,
            client_name="Gamma Corp",
            governance_tier="Partnered",
            contract_type="Fixed Bid",
            delivery_manager="Alice Johnson",
        ),
        stakeholders=[
            Stakeholder(name="Bob Smith", role="Executive Sponsor", organization="Gamma Corp"),
            Stakeholder(name="Alice Johnson", role="Delivery Manager", organization="Toptal"),
        ],
    )


def test_get_blocking_validation_errors_isolates_only_error_severity():
    """HTL-08: Only 'error'-severity validation findings block approval.
    'warning' and 'repaired' findings never block approval."""
    # 1. Report with error, warning, and repaired findings
    report_dict = {
        "findings": [
            {"invariant_id": "VAL-01", "severity": "error", "message": "Phase missing descriptive title"},
            {"invariant_id": "VAL-05", "severity": "warning", "message": "Award date not found"},
            {"invariant_id": "VAL-09", "severity": "repaired", "message": "Rebuilt 3 work packages"},
        ]
    }
    errors = review.get_blocking_validation_errors(report_dict)
    assert len(errors) == 1
    assert "VAL-01" in errors[0]
    assert "Phase missing descriptive title" in errors[0]

    # 2. Report with only warning and repaired findings
    non_blocking_report = {
        "findings": [
            {"invariant_id": "VAL-05", "severity": "warning", "message": "Award date not found"},
            {"invariant_id": "VAL-09", "severity": "repaired", "message": "Rebuilt 3 work packages"},
        ]
    }
    assert review.get_blocking_validation_errors(non_blocking_report) == []

    # 3. ValidationReport object instance
    vr_obj = ValidationReport(
        findings=[
            ValidationFinding(invariant_id="VAL-03", severity="error", message="Missing critical dependency"),
            ValidationFinding(invariant_id="VAL-07", severity="warning", message="Ambiguous milestone date"),
        ]
    )
    errors_obj = review.get_blocking_validation_errors(vr_obj)
    assert len(errors_obj) == 1
    assert "VAL-03" in errors_obj[0]
    assert "Missing critical dependency" in errors_obj[0]


def test_run_with_warning_and_repaired_findings_approves_and_updates_state_on_disk(tmp_path):
    """HTL-08 / HTL-09: A run with only warning and repaired findings (no error) can be approved,
    transitioning status.json to 'approved' via atomic if_state guard, verified on disk via a fresh storage instance."""
    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)

    baseline = _create_sample_baseline("Clean Project")
    validation_report = {
        "findings": [
            {"invariant_id": "VAL-05", "severity": "warning", "message": "SOW award date inferred"},
            {"invariant_id": "VAL-09", "severity": "repaired", "message": "Schedule rebuilt from stories"},
        ]
    }
    run_id = storage.create_run(
        project_name="Clean Project",
        baseline=baseline.model_dump(mode="json"),
        validation_report=validation_report,
    )

    # Confirm no blocking validation errors exist
    stored_run = storage.get_run(run_id)
    assert stored_run.state == "pending_review"
    assert review.get_blocking_validation_errors(stored_run.validation_report) == []

    # Execute HTL-09 atomic approval transition
    storage.update_status(run_id, "approved", if_state="pending_review")

    # Verify state genuinely 'approved' via a FRESH LocalReviewStorage instance reading from disk
    fresh_storage = LocalReviewStorage(base_dir=storage_dir)
    fresh_run = fresh_storage.get_run(run_id)
    assert fresh_run.state == "approved"

    # Confirm status.json content directly
    status_file = storage_dir / run_id / "status.json"
    assert '"state": "approved"' in status_file.read_text(encoding="utf-8")


def test_approve_run_not_in_pending_review_fails_via_if_state_guard(tmp_path):
    """HTL-09: Approving a run that is not in pending_review fails via the existing if_state guard."""
    storage_dir = tmp_path / "review_queue"
    storage = LocalReviewStorage(base_dir=storage_dir)

    baseline = _create_sample_baseline("Already Approved Project")
    run_id = storage.create_run(
        project_name="Already Approved Project",
        baseline=baseline.model_dump(mode="json"),
        validation_report={},
    )

    # First approval moves pending_review -> approved
    storage.update_status(run_id, "approved", if_state="pending_review")
    assert storage.get_run(run_id).state == "approved"

    # Second approval attempt with if_state='pending_review' must raise ValueError via if_state guard
    with pytest.raises(ValueError, match=r"expected state 'pending_review', found 'approved'"):
        storage.update_status(run_id, "approved", if_state="pending_review")

    # Verify state remains 'approved' on disk
    fresh_storage = LocalReviewStorage(base_dir=storage_dir)
    assert fresh_storage.get_run(run_id).state == "approved"
