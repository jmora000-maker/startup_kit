"""Tests for deliverable granularity and story count threshold (spec v5 B16)."""

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
import logging


def test_deliverable_granularity_warning(caplog):
    """Test that deliverables carrying > 5 stories trigger a granularity check warning."""
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="Sec 1", confidence_score=0.9)
    aggregator = BaselineAggregator()

    charter = CharterExtraction(project_name="Test Project", governance_tier="Partnered", contract_type="Time and Materials")
    # Deliverable with 6 stories
    deliverables_ext = DeliverablesExtraction(deliverables=[
        Deliverable(
            id="DEL-01",
            name="Super Deliverable",
            sow_reference="HS-4761, HS-4762, HS-4763, HS-4764, HS-4765, HS-4766",
            source_reference=ref
        ),
    ])
    milestones_ext = MilestonesExtraction(milestones=[])
    raid_ext = RAIDExtraction(items=[])

    with caplog.at_level(logging.WARNING):
        baseline = aggregator.aggregate(
            charter=charter,
            deliverables_ext=deliverables_ext,
            milestones_ext=milestones_ext,
            raid_ext=raid_ext,
        )

    assert any("carries 6 stories (> 5 stories threshold)" in record.message for record in caplog.records)
