"""Tests for MAP-05 work package matching order (parent link before text scoring)."""

import pytest
from src.core.models import Deliverable, WorkPackageSeed, SourceReference
from src.generators.pmo_workbook.mapping import map_work_packages_to_deliverables


def test_map_05_parent_link_wins_over_text_scoring():
    """MAP-05: When parent link and text scoring disagree, parent link wins."""
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="Sec 1", confidence_score=1.0)
    
    delivs = [
        Deliverable(id="DEL-01", name="Authentication and IAM", source_reference=ref),
        Deliverable(id="DEL-02", name="Database Migration and Cleansing", source_reference=ref),
    ]

    # WP has title that matches DEL-02 on text, but parent link points to DEL-01
    wps = [
        WorkPackageSeed(
            id="WP-01",
            title="Database Migration execution script",
            parent_deliverable_id="DEL-01",
            source_reference=ref
        )
    ]

    matched, other = map_work_packages_to_deliverables(wps, delivs)
    
    # Assert parent link won: mapped to DEL-01, not DEL-02
    assert len(matched["DEL-01"]) == 1
    assert matched["DEL-01"][0].id == "WP-01"
    assert len(matched["DEL-02"]) == 0
    assert len(other) == 0
