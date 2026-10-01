"""Test that work packages match to deliverables by parent link or work item ID, not shared section references."""

import pytest
from src.core.models import Milestone, Deliverable, WorkPackageSeed
from src.generators.pmo_workbook.mapping import map_work_packages_to_deliverables


def test_shared_section_reference_does_not_misassign_work_packages():
    """Two deliverables share 'Section 3.1'. Work packages with distinct parent links remain with their parent."""
    m1 = Milestone(id="M1", name="Milestone 1", sow_phase="P1")
    
    d1 = Deliverable(
        id="DEL-01",
        name="Architecture Design",
        sow_reference="Section 2.1",
        linked_milestone="M1"
    )
    d2 = Deliverable(
        id="DEL-02",
        name="System Implementation",
        sow_reference="Section 3.1",
        linked_milestone="M1"
    )
    d3 = Deliverable(
        id="DEL-03",
        name="Validation and Compliance Documentation",
        sow_reference="Section 3.1",
        linked_milestone="M1"
    )
    
    wp1 = WorkPackageSeed(
        id="WP-01",
        title="Design architecture components",
        parent_deliverable_id="DEL-01",
        sow_reference="Section 2.1"
    )
    wp2 = WorkPackageSeed(
        id="WP-02",
        title="Implement core services",
        parent_deliverable_id="DEL-02",
        sow_reference="Section 3.1"
    )
    wp3 = WorkPackageSeed(
        id="WP-03",
        title="Prepare compliance documentation",
        parent_deliverable_id="DEL-03",
        sow_reference="Section 3.1"
    )
    
    deliverables = [d1, d2, d3]
    work_packages = [wp1, wp2, wp3]
    
    matched_by_deliv, other_wps = map_work_packages_to_deliverables(work_packages, deliverables)
    
    assert other_wps == []
    assert len(matched_by_deliv["DEL-01"]) == 1
    assert matched_by_deliv["DEL-01"][0].id == "WP-01"
    
    assert len(matched_by_deliv["DEL-02"]) == 1
    assert matched_by_deliv["DEL-02"][0].id == "WP-02"
    
    assert len(matched_by_deliv["DEL-03"]) == 1
    assert matched_by_deliv["DEL-03"][0].id == "WP-03"
