"""Tests for SOW story catalogue and backlog generation (spec v5 B13)."""

from datetime import date
from src.core.models import (
    Deliverable,
    CharterExtraction,
    DeliverablesExtraction,
    MilestonesExtraction,
    RAIDExtraction,
    SourceReference,
)
from src.llm.aggregator import BaselineAggregator


def test_story_catalogue_and_backlog_generation():
    """Test that SOW stories generate work packages parented to the deliverable without 'Work Package:' prefix."""
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="Sec 1", confidence_score=0.9)
    aggregator = BaselineAggregator()

    charter = CharterExtraction(project_name="Test Project", governance_tier="Partnered", contract_type="Time and Materials")
    deliverables_ext = DeliverablesExtraction(deliverables=[
        Deliverable(id="DEL-01", name="Auth Service", sow_reference="HS-4762, HS-4764", source_reference=ref),
        Deliverable(id="DEL-02", name="Search Service", sow_reference="HS-4771", source_reference=ref),
    ])
    milestones_ext = MilestonesExtraction(milestones=[])
    raid_ext = RAIDExtraction(items=[])

    baseline = aggregator.aggregate(
        charter=charter,
        deliverables_ext=deliverables_ext,
        milestones_ext=milestones_ext,
        raid_ext=raid_ext,
    )

    # Check SOW story catalogue populated
    assert len(baseline.sow_stories_catalogue) == 3
    story_ids = {s.id for s in baseline.sow_stories_catalogue}
    assert story_ids == {"HS-4762", "HS-4764", "HS-4771"}

    # Check backlog seeds
    assert len(baseline.backlog_seed) == 3
    for wp in baseline.backlog_seed:
        assert not wp.title.startswith("Work Package:")
        assert wp.sow_reference is not None

    wp_map = {wp.sow_reference: wp for wp in baseline.backlog_seed}
    assert wp_map["HS-4762"].parent_deliverable_id == "DEL-01"
    assert wp_map["HS-4764"].parent_deliverable_id == "DEL-01"
    assert wp_map["HS-4771"].parent_deliverable_id == "DEL-02"
