"""Tests for acceptance merge and review window defaults (spec v5 B11, B12)."""

from datetime import date
from src.core.models import (
    Deliverable,
    AcceptanceProcessExtraction,
    SOWInterpretationExtraction,
    CharterExtraction,
    DeliverablesExtraction,
    MilestonesExtraction,
    RAIDExtraction,
    SourceReference,
)
from src.llm.aggregator import BaselineAggregator


def test_acceptance_merge_one_to_one_and_story_join():
    """Test one-to-one acceptance item merging using story IDs and Jaccard similarity."""
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="Sec 1", confidence_score=0.9)
    aggregator = BaselineAggregator()

    charter = CharterExtraction(project_name="Test Project", governance_tier="Partnered", contract_type="Time and Materials")
    deliverables_ext = DeliverablesExtraction(deliverables=[
        Deliverable(id="DEL-01", name="Auth Service", sow_reference="HS-101", source_reference=ref),
        Deliverable(id="DEL-02", name="Search Service", sow_reference="HS-102", source_reference=ref),
    ])
    milestones_ext = MilestonesExtraction(milestones=[])
    raid_ext = RAIDExtraction(items=[])

    # Acceptance items with story IDs
    acc_ext = AcceptanceProcessExtraction(acceptance_matrix_items=[
        Deliverable(id="ACC-01", name="Authentication module", sow_reference="HS-101", evidence_required="Auth logs", client_approver="Security Lead", source_reference=ref),
        Deliverable(id="ACC-02", name="Search API endpoints", sow_reference="HS-102", evidence_required="Search benchmarks", client_approver="Product Lead", source_reference=ref),
    ])

    sow_interp_ext = SOWInterpretationExtraction(
        approval_expectations="Written acceptance sign-off within 10 business days of delivery.",
        source_reference=ref
    )

    baseline = aggregator.aggregate(
        charter=charter,
        deliverables_ext=deliverables_ext,
        milestones_ext=milestones_ext,
        raid_ext=raid_ext,
        acceptance_ext=acc_ext,
        sow_interpretation_ext=sow_interp_ext,
    )

    deliv_map = {d.id: d for d in baseline.deliverables}
    assert deliv_map["DEL-01"].evidence_required == "Auth logs"
    assert deliv_map["DEL-01"].client_approver == "Security Lead"
    assert deliv_map["DEL-02"].evidence_required == "Search benchmarks"
    assert deliv_map["DEL-02"].client_approver == "Product Lead"


def test_unmatched_deliverable_review_window_from_sow():
    """Test that unmatched deliverables inherit review window from SOW and never default 5 business days."""
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="Sec 1", confidence_score=0.9)
    aggregator = BaselineAggregator()

    charter = CharterExtraction(project_name="Test Project", governance_tier="Partnered", contract_type="Time and Materials")
    deliverables_ext = DeliverablesExtraction(deliverables=[
        Deliverable(id="DEL-01", name="Unmatched Deliverable", source_reference=ref),
    ])
    milestones_ext = MilestonesExtraction(milestones=[])
    raid_ext = RAIDExtraction(items=[])

    sow_interp_ext = SOWInterpretationExtraction(
        approval_expectations="Client review completed within 14 calendar days.",
        source_reference=ref
    )

    baseline = aggregator.aggregate(
        charter=charter,
        deliverables_ext=deliverables_ext,
        milestones_ext=milestones_ext,
        raid_ext=raid_ext,
        sow_interpretation_ext=sow_interp_ext,
    )

    deliv = baseline.deliverables[0]
    assert deliv.review_window == "Client review completed within 14 calendar days."
    assert "5 business days" not in deliv.review_window
