"""HTL-06 / HTL-07 / HTL-13: Tests for generalized Fact Review loading and saving against review storage."""

from datetime import date, datetime
from pathlib import Path
import pytest

from src.core.models import ProjectStartupCharter, GovernanceTier, Stakeholder, StartupKitBaseline
from src.review_storage.local import LocalReviewStorage
from src.review_ui import facts as review


def _create_sample_baseline(project_name: str = "Omega Migration") -> StartupKitBaseline:
    return StartupKitBaseline(
        project_name=project_name,
        contract_type="Fixed Bid",
        governance_tier="Partnered",
        sow_awarded_date=date(2026, 11, 15),
        award_date_source="stated",
        charter=ProjectStartupCharter(
            project_name=project_name,
            client_name="Omega Corp",
            governance_tier="Partnered",
            contract_type="Fixed Bid",
            delivery_manager="Alice Johnson",
        ),
        stakeholders=[
            Stakeholder(name="Bob Smith", role="Executive Sponsor", organization="Omega Corp"),
            Stakeholder(name="Charlie Brown", role="Client Contact", organization="Omega Corp"),
            Stakeholder(name="Alice Johnson", role="Delivery Manager", organization="Toptal"),
        ],
    )


def test_load_run_baseline_from_storage(tmp_path):
    """HTL-06: load_run_baseline loads a real run from review storage and builds fact categories from it."""
    storage = LocalReviewStorage(base_dir=tmp_path / "review_queue")
    sample_baseline = _create_sample_baseline("Omega Migration")
    run_id = storage.create_run(
        project_name="Omega Migration",
        baseline=sample_baseline.model_dump(mode="json"),
        validation_report={},
    )

    loaded_baseline = review.load_run_baseline(run_id, storage=storage)
    assert loaded_baseline.project_name == "Omega Migration"
    assert loaded_baseline.charter.client_name == "Omega Corp"

    categories = {c.key: c for c in review.build_fact_categories(loaded_baseline)}
    values = review.extracted_values(list(categories.values()))

    assert values["project_identity.project_name"] == "Omega Migration"
    assert values["project_identity.client_name"] == "Omega Corp"
    assert values["project_identity.client_sponsor"] == "Bob Smith"
    assert values["named_roles.delivery_manager"] == "Alice Johnson"
    assert values["named_roles.client_contact"] == "Charlie Brown"
    assert values["award_date"] == "2026-11-15"


def test_save_run_review_writes_to_storage_and_updates_baseline(tmp_path):
    """HTL-07 / HTL-06: save_run_review persists corrected baseline and review_audit.json to the run's storage."""
    storage = LocalReviewStorage(base_dir=tmp_path / "review_queue")
    sample_baseline = _create_sample_baseline("Omega Migration")
    run_id = storage.create_run(
        project_name="Omega Migration",
        baseline=sample_baseline.model_dump(mode="json"),
        validation_report={},
    )

    baseline = review.load_run_baseline(run_id, storage=storage)
    categories = review.build_fact_categories(baseline)

    submitted = review.extracted_values(categories)
    submitted["named_roles.delivery_manager"] = "Danielle Vance"
    submitted["award_date"] = "2026-11-20"
    notes = {"named_roles": "Assigned new DM", "award_date": "Updated per addendum"}

    when = datetime(2026, 10, 8, 11, 0, 0)
    audit, corrected = review.save_run_review(
        run_id=run_id,
        baseline=baseline,
        categories=categories,
        submitted=submitted,
        notes=notes,
        storage=storage,
        when=when,
    )

    # 1. Audit assertions
    assert audit["run_id"] == run_id
    assert audit["facts"]["named_roles"] == review.HUMAN_CORRECTED
    assert audit["facts"]["award_date"] == review.HUMAN_CORRECTED
    assert audit["facts"]["project_identity"] == review.MACHINE_EXTRACTED_UNCONFIRMED

    # 2. Storage assertions
    stored_run = storage.get_run(run_id)
    assert stored_run.baseline["charter"]["delivery_manager"] == "Danielle Vance"
    assert stored_run.baseline["sow_awarded_date"] == "2026-11-20"

    # Confirm audit was written to disk
    audit_file = tmp_path / "review_queue" / run_id / "review_audit.json"
    assert audit_file.exists()


def test_load_demo_fixture_option_remains_intact():
    """HTL-06: Selecting the demo fixture loads the arc_application_implementation fixture baseline."""
    baseline = review.load_run_baseline(review.DEMO_FIXTURE_OPTION)
    assert baseline.project_name == "ARC Application Implementation"
    assert baseline.charter.client_name == "Syngenta Crop Protection, LLC"
