"""HTL-06: the fact-review screen's content for the arc_application_implementation fixture (no Streamlit rendering)."""

import json
from pathlib import Path

import pytest

from src.review_ui import facts as review

ORACLE_PATH = Path(__file__).parent / "oracles" / "arc_application_implementation.json"


@pytest.fixture(scope="module")
def oracle():
    with open(ORACLE_PATH, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def categories():
    baseline = review.prepare_review_baseline(review.load_baseline(review.FIXTURE_BASELINE_PATH))
    return {c.key: c for c in review.build_fact_categories(baseline)}


@pytest.fixture(scope="module")
def values(categories):
    return review.extracted_values(list(categories.values()))


def test_fixture_file_is_not_modified_by_loading():
    before = review.FIXTURE_BASELINE_PATH.read_bytes()
    raw = review.load_baseline(review.FIXTURE_BASELINE_PATH)
    review.build_fact_categories(review.prepare_review_baseline(raw))
    assert raw.validation_report is None  # prepare_review_baseline validates a copy, never the input
    assert review.FIXTURE_BASELINE_PATH.read_bytes() == before


def test_category_list_is_exactly_htl06_in_order(categories):
    assert tuple(categories) == review.CATEGORY_KEYS
    assert len(categories) == 7


def test_project_identity_values(values):
    assert values["project_identity.project_name"] == "ARC Application Implementation"
    assert values["project_identity.client_name"] == "Syngenta Crop Protection, LLC"
    assert values["project_identity.client_sponsor"] == "Mike Magwire"
    assert values["project_identity.contract_type"] == "Fixed Bid"
    assert values["project_identity.governance_tier"] == "Partnered"


def test_award_date_matches_oracle(categories, values, oracle):
    assert values["award_date"] == oracle["award_date"]
    (field,) = categories["award_date"].fields
    assert oracle["award_date_stated_in_sow"] is True
    assert field.context == "Provenance (VAL-11): stated"


def test_named_roles_match_oracle(values, oracle):
    assert values["named_roles.delivery_manager"] == oracle["named_delivery_manager"]
    assert values["named_roles.client_contact"] == oracle["named_client_contact"]


def test_gate_count_phases_and_external_dates_match_oracle(categories, values, oracle):
    gate_ids = sorted({f.key.split(".")[1] for f in categories["milestones"].fields
                       if f.context and f.context.startswith("Gate")})
    assert len(gate_ids) == oracle["gate_count"]
    assert {g: values[f"milestones.{g}.external_date"] for g in gate_ids} == oracle["milestone_external_dates"]

    arc_oracle = json.loads((ORACLE_PATH.parent / f"{oracle['extends_reference_phase_map_from']}.json").read_text(encoding="utf-8"))
    assert [values[f"milestones.{g}.phase"] for g in gate_ids] == arc_oracle["phases"]


def test_checkpoint_phases_match_oracle(categories, values, oracle):
    cp_ids = sorted({f.key.split(".")[1] for f in categories["milestones"].fields
                     if f.context and f.context.startswith("Checkpoint")})
    assert {cp: values[f"milestones.{cp}.phase"].split()[0] for cp in cp_ids} == oracle["checkpoint_phases"]


def test_milestone_date_basis_is_the_generated_label(categories):
    basis = {f.key: f.basis_label for f in categories["milestones"].fields if f.key.endswith(".external_date")}
    assert basis == {
        "milestones.M1.external_date": "Contract date",
        "milestones.M2.external_date": "Contract date",
        "milestones.M3.external_date": "Contract date",
        "milestones.M4.external_date": "Contract date",
        "milestones.CP-01.external_date": "Within P1 Contract date",
    }


def test_deliverable_phase_assignment_and_mapping_basis(categories, oracle):
    fields = categories["deliverable_phase_assignment"].fields
    assert len(fields) == 20
    assert all(f.basis_label == "Catalogue phase" for f in fields)
    arc_oracle = json.loads((ORACLE_PATH.parent / "arc.json").read_text(encoding="utf-8"))
    assert {f.value for f in fields} == set(arc_oracle["phases"])
    by_id = {f.key.split(".")[1]: f.value for f in fields}
    assert by_id["DEL-01"] == "P1 Foundation"
    assert by_id["DEL-05"] == "P2a Services and Data"
    assert by_id["DEL-10"] == "P2b Application Surface"
    assert by_id["DEL-20"] == "P3 Launch"


def test_contract_wide_review_window_matches_oracle(values, oracle):
    assert values["contract_wide_review_window"] == oracle["contract_wide_review_window"]


def test_validation_findings_shown_in_full(categories):
    fields = categories["validation_findings"].fields
    assert [(f.label, f.value) for f in fields] == [
        ("repaired - INV-01", "Reconciled 4 primary gates and moved 1 interim items to Interim Checkpoints (CP)."),
        ("repaired - INV-07", "Rebuilt 35 work packages from SOW work item catalogue with verified parent deliverables and work item phases."),
    ]
    assert all(f.self_describing and f.source_text == review.SELF_DESCRIBING_LABEL for f in fields)


@pytest.mark.parametrize("category", [
    "project_identity", "award_date", "named_roles", "milestones",
    "deliverable_phase_assignment", "contract_wide_review_window",
])
def test_no_fabricated_source_quotes(categories, category):
    """Step 1 finding: the baseline stores no literal SOW sentence for these categories."""
    for f in categories[category].fields:
        assert f.source_quote is None
        assert f.source_text == review.NO_QUOTE_LABEL
        assert f.source_location is None or f.source_location != f.source_text


def test_source_locations_per_step1_table(categories):
    loc = {f.key: f.source_location for c in categories.values() for f in c.fields}
    assert loc["project_identity.project_name"].endswith("Page 1 Sections 1-2; Exhibit A Sections 1, 2, 4, 8, 9")
    assert loc["award_date"] is None
    assert loc["named_roles.delivery_manager"] is None
    assert loc["named_roles.client_contact"] is None
    assert loc["milestones.M1.external_date"].endswith("Section 2.B (Milestone 1); Exhibit A Sections 2.1 and 4")
    assert loc["deliverable_phase_assignment.DEL-01"].endswith("Exhibit A, Section 4 - Milestone 1 (HS-4762)")
