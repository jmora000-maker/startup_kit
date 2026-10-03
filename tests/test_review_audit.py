"""HTL-07: provenance tags and review_audit.json (Appendix Q.2 shape) written by the review screen's save logic."""

import json
from datetime import date, datetime

import pytest

from src.core.models import StartupKitBaseline
from src.review_ui import facts as review

WHEN = datetime(2026, 10, 3, 14, 35, 10)


@pytest.fixture(scope="module")
def reviewed():
    baseline = review.prepare_review_baseline(review.load_baseline(review.FIXTURE_BASELINE_PATH))
    return baseline, review.build_fact_categories(baseline)


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_one_edit_tags_only_that_category(reviewed, tmp_path):
    baseline, categories = reviewed
    submitted = review.extracted_values(categories)
    submitted["award_date"] = "2026-10-01"  # intentionally wrong
    notes = {"award_date": "Forced wrong value for test."}

    audit, baseline_path, audit_path = review.review_and_save(
        baseline, categories, submitted, notes, out_dir=tmp_path, when=WHEN)

    on_disk = _read(audit_path)
    assert on_disk == audit
    assert list(on_disk) == ["run_id", "reviewed_by", "reviewed_at", "facts", "corrections"]
    assert on_disk["run_id"] == "ARC_Application_Implementation_20261003_143510"
    assert on_disk["reviewed_at"] == "2026-10-03T14:35:10"
    assert list(on_disk["facts"]) == list(review.CATEGORY_KEYS)
    assert on_disk["facts"]["award_date"] == review.HUMAN_CORRECTED
    others = {k: v for k, v in on_disk["facts"].items() if k != "award_date"}
    assert len(others) == 6
    assert set(others.values()) == {review.MACHINE_EXTRACTED_UNCONFIRMED}
    assert on_disk["corrections"] == [{
        "field": "award_date",
        "extracted": "2026-10-07",
        "corrected_to": "2026-10-01",
        "reviewer_note": "Forced wrong value for test.",
    }]

    corrected = StartupKitBaseline.model_validate(_read(baseline_path))
    assert corrected.sow_awarded_date in (date(2026, 10, 1), "2026-10-01")
    assert corrected.milestones[0].external_date == baseline.milestones[0].external_date
    assert baseline.sow_awarded_date != corrected.sow_awarded_date  # the reviewed baseline itself is untouched


def test_zero_edits_all_unconfirmed(reviewed, tmp_path):
    baseline, categories = reviewed
    audit, baseline_path, audit_path = review.review_and_save(
        baseline, categories, review.extracted_values(categories), out_dir=tmp_path, when=WHEN)

    on_disk = _read(audit_path)
    assert on_disk["facts"] == {k: review.MACHINE_EXTRACTED_UNCONFIRMED for k in review.CATEGORY_KEYS}
    assert on_disk["corrections"] == []
    assert _read(baseline_path) == json.loads(json.dumps(baseline.model_dump(mode="json")))


def test_whitespace_only_change_is_not_a_correction(reviewed):
    _, categories = reviewed
    submitted = review.extracted_values(categories)
    submitted["named_roles.delivery_manager"] = "  Saadia Iqbal  "
    facts, corrections = review.compute_review(categories, submitted)
    assert facts["named_roles"] == review.MACHINE_EXTRACTED_UNCONFIRMED
    assert corrections == []


def test_multi_field_category_edit_records_each_field(reviewed):
    baseline, categories = reviewed
    submitted = review.extracted_values(categories)
    submitted["milestones.M2.external_date"] = "2027-02-02"
    submitted["milestones.CP-01.phase"] = "P2a Services and Data"
    facts, corrections = review.compute_review(categories, submitted)
    assert facts["milestones"] == review.HUMAN_CORRECTED
    assert [c["field"] for c in corrections] == ["milestones.M2.external_date", "milestones.CP-01.phase"]

    corrected = review.apply_corrections(baseline, corrections)
    assert corrected.milestones[1].external_date == date(2027, 2, 2)
    assert corrected.interim_checkpoints[0].phase == "P2a"


def test_invalid_date_is_rejected(reviewed):
    baseline, categories = reviewed
    submitted = review.extracted_values(categories)
    submitted["award_date"] = "07/10/2026"
    _, corrections = review.compute_review(categories, submitted)
    with pytest.raises(ValueError, match="award_date"):
        review.apply_corrections(baseline, corrections)


def test_audit_rejects_incomplete_or_unknown_tags():
    facts = {k: review.MACHINE_EXTRACTED_UNCONFIRMED for k in review.CATEGORY_KEYS}
    with pytest.raises(ValueError):
        review.build_review_audit("r", {k: v for k, v in facts.items() if k != "milestones"}, [], WHEN)
    with pytest.raises(ValueError):
        review.build_review_audit("r", {**facts, "award_date": "confirmed"}, [], WHEN)


@pytest.mark.parametrize("protected", [
    review.REPO_ROOT / "tests" / "fixtures" / "sow" / review.FIXTURE_NAME,
    review.REPO_ROOT / "tests" / "oracles",
])
def test_save_refuses_protected_directories(reviewed, protected):
    baseline, _ = reviewed
    facts = {k: review.MACHINE_EXTRACTED_UNCONFIRMED for k in review.CATEGORY_KEYS}
    audit = review.build_review_audit("r", facts, [], WHEN)
    with pytest.raises(ValueError, match="protected"):
        review.save_review(baseline, audit, protected)


def test_default_save_location_is_scratch():
    assert review.SCRATCH_ROOT == review.REPO_ROOT / "review_ui_scratch"
    assert not review._is_protected(review.SCRATCH_ROOT / review.FIXTURE_NAME)
