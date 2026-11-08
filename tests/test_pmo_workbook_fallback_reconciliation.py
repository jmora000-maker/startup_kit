"""Tests for milestone phase reconciliation, gate fallback, and RAID provenance in PMO workbook (HTL-93)."""

from datetime import date
from typing import Dict, List
import pytest

from src.core.models import (
    Milestone,
    Deliverable,
    WorkPackageSeed,
    SOWWorkItem,
    RiskAssumption,
    DependencyAssumptionItem,
)
from src.generators.pmo_workbook.workstreams import (
    parse_milestone_phase,
    classify_milestone,
    ParsedMilestonePhase,
)
from src.generators.pmo_workbook.mapping import (
    map_deliverables_to_milestones_v2,
    map_work_packages_to_milestones,
    link_raid_item_v2,
    detect_default_filled_milestone,
    detect_default_filled_deliverable,
)


# ==============================================================================
# Group A: Deliverable & Work Package Milestone Fallbacks
# ==============================================================================

def test_deliverable_mapping_with_empty_milestones():
    """When milestones list is empty, map_deliverables_to_milestones_v2 produces MS-TBC placeholder."""
    deliverables = [
        Deliverable(id="DEL-01", name="Architecture Blueprint"),
        Deliverable(id="DEL-02", name="API Gateway Service"),
    ]
    deliv_mapping, wp_to_ms, deliv_to_matched_wp = map_deliverables_to_milestones_v2(
        deliverables=deliverables,
        milestones=[],
        work_packages=[],
        parsed_phases={},
    )

    assert len(deliv_mapping) == 2
    for d_id in ("DEL-01", "DEL-02"):
        ms, basis, is_unmapped = deliv_mapping[d_id]
        assert ms.id == "MS-TBC"
        assert ms.description == "Delivery milestones to be confirmed"
        assert basis == "Fallback - MS-TBC"
        assert is_unmapped is True


def test_work_package_mapping_with_empty_milestones():
    """When milestones list is empty, map_work_packages_to_milestones safely returns empty dicts."""
    work_packages = [
        WorkPackageSeed(id="WP-01", title="Initialize Repo", parent_deliverable_id="DEL-01"),
    ]
    wp_to_ms, wp_to_basis, is_phase_order = map_work_packages_to_milestones(
        work_packages=work_packages,
        milestones=[],
        parsed_phases={},
    )
    assert wp_to_ms == {}
    assert wp_to_basis == {}
    assert is_phase_order is False


def test_backlog_phase_order_orphan_work_package_fallback():
    """When backlog phase order is detected, an orphan WP with unmapped parent falls back to final milestone."""
    milestones = [
        Milestone(id="M1", description="Phase 1: Discovery accepted"),
        Milestone(id="M2", description="Phase 2: Build accepted"),
        Milestone(id="M3", description="Phase 3: Deploy accepted"),
    ]
    # Backlog parents encode phases (DEL-01, DEL-02, DEL-03), plus an orphan WP with parent_deliverable_id=""
    work_packages = [
        WorkPackageSeed(id="WP-01", title="Discovery 1", parent_deliverable_id="DEL-01"),
        WorkPackageSeed(id="WP-02", title="Build 1", parent_deliverable_id="DEL-02"),
        WorkPackageSeed(id="WP-03", title="Deploy 1", parent_deliverable_id="DEL-03"),
        WorkPackageSeed(id="WP-04", title="Orphan Task", parent_deliverable_id=""),
    ]
    parsed_phases = {m.id: parse_milestone_phase(m) for m in milestones}

    wp_to_ms, wp_to_basis, is_phase_order = map_work_packages_to_milestones(
        work_packages=work_packages,
        milestones=milestones,
        parsed_phases=parsed_phases,
    )

    assert is_phase_order is True
    assert wp_to_ms["WP-01"].id == "M1"
    assert wp_to_basis["WP-01"] == "Backlog phase order"
    assert wp_to_ms["WP-02"].id == "M2"
    assert wp_to_ms["WP-03"].id == "M3"
    # Orphan WP-04 falls back to milestones[-1] (M3)
    assert wp_to_ms["WP-04"].id == "M3"
    assert wp_to_basis["WP-04"] == "Fallback"


def test_deliverable_unmapped_fallback_to_last_milestone():
    """A deliverable with zero matches across all rules falls back to last milestone with is_unmapped=True."""
    milestones = [
        Milestone(id="M1", description="Phase 1: Discovery & Requirements accepted"),
        Milestone(id="M2", description="Phase 2: Deployment & Release accepted"),
    ]
    parsed_phases = {m.id: parse_milestone_phase(m) for m in milestones}
    deliverables = [
        Deliverable(id="DEL-ZZZ", name="Xylophone Quartz Vibrations", description="Completely unrelated jargon"),
    ]

    deliv_mapping, _, _ = map_deliverables_to_milestones_v2(
        deliverables=deliverables,
        milestones=milestones,
        work_packages=[],
        parsed_phases=parsed_phases,
    )

    ms, basis, is_unmapped = deliv_mapping["DEL-ZZZ"]
    assert ms.id == "M2"
    assert basis == "Unmapped - confirm milestone"
    assert is_unmapped is True


# ==============================================================================
# Group B: Deliverable Precedence Tiers (Rules 1, 2, 3, 6, 7)
# ==============================================================================

def test_deliverable_catalogue_phase_mapping():
    """Rule 1: Deliverable whose SOW references all belong to one catalogue phase maps to that phase."""
    milestones = [
        Milestone(id="M1", description="Phase 1 Discovery: Scope"),
        Milestone(id="M2", description="Phase 2 Integration: Scope"),
    ]
    parsed_phases = {m.id: parse_milestone_phase(m) for m in milestones}
    catalogue = [
        SOWWorkItem(reference="SOW-P2-01", title="API Endpoint", phase="P2"),
    ]
    deliverables = [
        Deliverable(id="DEL-01", name="Custom Microservice", sow_reference="SOW-P2-01"),
    ]

    deliv_mapping, _, _ = map_deliverables_to_milestones_v2(
        deliverables=deliverables,
        milestones=milestones,
        work_packages=[],
        parsed_phases=parsed_phases,
        sow_catalogue=catalogue,
    )

    ms, basis, is_unmapped = deliv_mapping["DEL-01"]
    assert ms.id == "M2"
    assert basis == "Catalogue phase"
    assert is_unmapped is False


def test_deliverable_milestone_n_title_mapping():
    """Rule 2: Deliverable mentioning 'Milestone N' in title maps directly to MN."""
    milestones = [
        Milestone(id="M1", description="Phase 1: Inception"),
        Milestone(id="M2", description="Phase 2: Construction"),
    ]
    parsed_phases = {m.id: parse_milestone_phase(m) for m in milestones}
    deliverables = [
        Deliverable(id="DEL-02", name="Acceptance Checklist for Milestone 2"),
    ]

    deliv_mapping, _, _ = map_deliverables_to_milestones_v2(
        deliverables=deliverables,
        milestones=milestones,
        work_packages=[],
        parsed_phases=parsed_phases,
    )

    ms, basis, is_unmapped = deliv_mapping["DEL-02"]
    assert ms.id == "M2"
    assert basis == "Phase code"
    assert is_unmapped is False


def test_deliverable_referenced_in_milestone_text():
    """Rule 3: Deliverable ID cited in milestone dependencies or assumptions maps to that milestone."""
    milestones = [
        Milestone(id="M1", description="Phase 1: Discovery", key_dependencies=["Requires DEL-04 signoff"]),
        Milestone(id="M2", description="Phase 2: Build"),
    ]
    parsed_phases = {m.id: parse_milestone_phase(m) for m in milestones}
    deliverables = [
        Deliverable(id="DEL-04", name="Requirements Traceability Matrix"),
    ]

    deliv_mapping, _, _ = map_deliverables_to_milestones_v2(
        deliverables=deliverables,
        milestones=milestones,
        work_packages=[],
        parsed_phases=parsed_phases,
    )

    ms, basis, is_unmapped = deliv_mapping["DEL-04"]
    assert ms.id == "M1"
    assert basis == "Referenced by milestone"
    assert is_unmapped is False


def test_deliverable_backlog_text_match():
    """Rule 6: Deliverable with text overlap (score >= 0.30) against a work package title maps via that work package."""
    milestones = [
        Milestone(id="M1", description="Phase 1 Discovery: Scoping"),
        Milestone(id="M2", description="Phase 2 Deployment: Signoff"),
    ]
    parsed_phases = {m.id: parse_milestone_phase(m) for m in milestones}
    work_packages = [
        WorkPackageSeed(id="WP-01", title="Kubernetes Cluster Provisioning Script Automation", parent_deliverable_id="DEL-01", linked_milestones=["M2"]),
    ]
    deliverables = [
        Deliverable(id="DEL-01", name="Target Deliverable"),
        Deliverable(id="DEL-05", name="Cluster Provisioning Automation Guidebook"),
    ]

    deliv_mapping, _, deliv_to_matched_wp = map_deliverables_to_milestones_v2(
        deliverables=deliverables,
        milestones=milestones,
        work_packages=work_packages,
        parsed_phases=parsed_phases,
    )

    ms, basis, is_unmapped = deliv_mapping["DEL-05"]
    assert ms.id == "M2"
    assert "Backlog match" in basis
    assert is_unmapped is False
    assert deliv_to_matched_wp["DEL-05"] == "WP-01"


def test_deliverable_submission_target_date_mapping():
    """Rule 7: Deliverable target date maps to earliest milestone >= date, or latest milestone if exceeding all."""
    milestones = [
        Milestone(id="M1", description="Phase 1 Gate", external_date=date(2026, 11, 1)),
        Milestone(id="M2", description="Phase 2 Gate", external_date=date(2026, 11, 30)),
    ]
    parsed_phases = {m.id: parse_milestone_phase(m) for m in milestones}
    deliverables = [
        Deliverable(id="DEL-10", name="Early Deliverable", submission_target_date=date(2026, 11, 15)),
        Deliverable(id="DEL-11", name="Late Deliverable", submission_target_date=date(2026, 12, 15)),
    ]

    deliv_mapping, _, _ = map_deliverables_to_milestones_v2(
        deliverables=deliverables,
        milestones=milestones,
        work_packages=[],
        parsed_phases=parsed_phases,
    )

    # DEL-10 (Nov 15) <= M2 (Nov 30) -> M2
    ms10, basis10, is_unmapped10 = deliv_mapping["DEL-10"]
    assert ms10.id == "M2"
    assert basis10 == "Submission date"
    assert is_unmapped10 is False

    # DEL-11 (Dec 15) > all milestones -> maps to latest dated milestone (M2)
    ms11, basis11, is_unmapped11 = deliv_mapping["DEL-11"]
    assert ms11.id == "M2"
    assert basis11 == "Submission date"
    assert is_unmapped11 is False


# ==============================================================================
# Group C: Work Package Precedence Tiers (Rules 1, 2, 4)
# ==============================================================================

def test_work_package_catalogue_reference_phase_mapping():
    """Rule 1: Work package SOW reference resolving to catalogue phase maps to that milestone phase."""
    milestones = [
        Milestone(id="M1", description="Phase 1: Requirements"),
        Milestone(id="M2", description="Phase 2: Integration"),
    ]
    parsed_phases = {m.id: parse_milestone_phase(m) for m in milestones}
    catalogue = [
        SOWWorkItem(reference="SOW-P2-01", title="Payment Gateway Connector", phase="P2"),
    ]
    work_packages = [
        WorkPackageSeed(id="WP-10", title="Build Connector", sow_reference="SOW-P2-01"),
    ]

    wp_to_ms, wp_to_basis, _ = map_work_packages_to_milestones(
        work_packages=work_packages,
        milestones=milestones,
        parsed_phases=parsed_phases,
        sow_catalogue=catalogue,
    )

    assert wp_to_ms["WP-10"].id == "M2"
    assert wp_to_basis["WP-10"] == "Work item phase"


def test_work_package_parent_deliverable_backlog_link_mapping():
    """Rule 2: Work package with linked_milestones on parent deliverable maps to that milestone."""
    milestones = [
        Milestone(id="M1", description="Phase 1: Setup"),
        Milestone(id="M2", description="Phase 2: Implementation"),
    ]
    parsed_phases = {m.id: parse_milestone_phase(m) for m in milestones}
    deliverables = [
        Deliverable(id="DEL-01", name="Security Framework"),
    ]
    work_packages = [
        WorkPackageSeed(
            id="WP-20",
            title="Configure OAuth",
            parent_deliverable_id="DEL-01",
            linked_milestones=["M2"],
        ),
        WorkPackageSeed(
            id="WP-21",
            title="Configure SAML",
            parent_deliverable_id="DEL-01",
            linked_milestones=["P1"],
        ),
    ]

    wp_to_ms, wp_to_basis, _ = map_work_packages_to_milestones(
        work_packages=work_packages,
        milestones=milestones,
        parsed_phases=parsed_phases,
        deliverables=deliverables,
    )

    assert wp_to_ms["WP-20"].id == "M2"
    assert wp_to_basis["WP-20"] == "Backlog link"
    assert wp_to_ms["WP-21"].id == "M1"
    assert wp_to_basis["WP-21"] == "Backlog link"


def test_work_package_referenced_in_milestone_text():
    """Rule 4: Work package ID cited in milestone critical_path_assumptions maps to that milestone."""
    milestones = [
        Milestone(id="M1", description="Phase 1: Inception", critical_path_assumptions=["WP-30 must finish on time"]),
        Milestone(id="M2", description="Phase 2: Execution"),
    ]
    parsed_phases = {m.id: parse_milestone_phase(m) for m in milestones}
    work_packages = [
        WorkPackageSeed(id="WP-30", title="Spike Investigation"),
    ]

    wp_to_ms, wp_to_basis, _ = map_work_packages_to_milestones(
        work_packages=work_packages,
        milestones=milestones,
        parsed_phases=parsed_phases,
    )

    assert wp_to_ms["WP-30"].id == "M1"
    assert wp_to_basis["WP-30"] == "Referenced by milestone"


# ==============================================================================
# Group D: Workstream Parsing & Taxonomy Deliverable Fallback
# ==============================================================================

def test_parse_milestone_phase_structured_fallback():
    """Structured phase / phase_display on Milestone is preserved when description has non-standard format."""
    m_phase = Milestone(
        id="M2",
        description="Data Schema Deployment: ETL pipeline verified and ready",
        phase="P2",
    )
    parsed = parse_milestone_phase(m_phase)
    assert parsed.phase_code == "P2"
    assert parsed.workstream_name == "P2"
    assert parsed.milestone_name == "Data Schema Deployment"
    assert parsed.has_phase_label is True

    m_display = Milestone(
        id="M3",
        description="Custom Test Suite signoff",
        phase_display="Testing & Quality Assurance",
    )
    parsed_display = parse_milestone_phase(m_display)
    assert parsed_display.workstream_name == "Testing & Quality Assurance"


def test_classify_milestone_deliverable_keyword_fallback():
    """Milestone description with 0 taxonomy keywords falls back to keywords in mapped deliverables."""
    milestone = Milestone(id="M1", description="Project Alignment Checkpoint Alpha")
    mapped_deliverables = [
        Deliverable(id="DEL-01", name="Database ETL & API Migration Pipeline"),
    ]

    code, basis = classify_milestone(milestone, mapped_deliverables=mapped_deliverables)
    assert code == "DAT"
    assert "Deliverable keyword:" in basis
    assert "etl" in basis or "migrat" in basis or "api" in basis or "data" in basis


def test_classify_milestone_unclassified_fallback():
    """Milestone with 0 taxonomy keywords and no matching deliverables falls back to Unclassified."""
    milestone = Milestone(id="M1", description="Vague Checkpoint Foo Bar")
    code, basis = classify_milestone(milestone, mapped_deliverables=[])
    assert code is None
    assert basis == "Unclassified - confirm workstream"


# ==============================================================================
# Group E: RAID Provenance Gate Reconciliation & Default-Fill Guard
# ==============================================================================

def test_raid_reconcile_merged_extracted_milestone_id():
    """RAID item referencing an extracted/merged milestone ID (e.g. M4 merged into M2) resolves to M2."""
    milestones = [
        Milestone(id="M1", description="Phase 1: Discovery accepted"),
        Milestone(id="M2", description="Phase 2: Build accepted", extracted_ids=["M2", "M4"]),
    ]
    parsed_phases = {m.id: parse_milestone_phase(m) for m in milestones}
    wbs_map = {"M1": "WBS-1", "M2": "WBS-2"}
    risk = RiskAssumption(
        id="RSK-01",
        description="Dependency on legacy API for extracted M4 delivery",
    )

    ws, ms_str, wbs_str, note = link_raid_item_v2(
        item=risk,
        milestones=milestones,
        deliv_mapping={},
        parsed_phases=parsed_phases,
        wbs_code_map=wbs_map,
    )

    assert ms_str == "M2"
    assert wbs_str == "WBS-2"
    assert note is not None
    assert "Refers to extracted M4 (now M2)" in note


def test_raid_reconcile_interim_checkpoint_milestone():
    """RAID item referencing an interim checkpoint (e.g. CP-01) resolves to parent milestone gate."""
    milestones = [
        Milestone(id="M1", description="Phase 1: Inception & Discovery accepted"),
        Milestone(id="M2", description="Phase 2: Implementation accepted"),
    ]
    checkpoints = [
        Milestone(id="CP-01", description="Phase 1 Smoke Testing Checkpoint"),
    ]
    parsed_phases = {m.id: parse_milestone_phase(m) for m in milestones}
    wbs_map = {"M1": "WBS-1", "M2": "WBS-2"}
    risk = RiskAssumption(
        id="RSK-02",
        description="Delay in environment provisioning before CP-01 signoff",
    )

    ws, ms_str, wbs_str, note = link_raid_item_v2(
        item=risk,
        milestones=milestones,
        deliv_mapping={},
        parsed_phases=parsed_phases,
        wbs_code_map=wbs_map,
        checkpoints=checkpoints,
    )

    assert ms_str == "M1"
    assert wbs_str == "WBS-1"
    assert note is not None
    assert "Refers to CP-01 (checkpoint of M1)" in note


def test_raid_detect_default_filled_milestone_and_deliverable():
    """When >=75% of >=4 items default to one milestone/deliverable, default-fill is ignored (Cross-phase)."""
    items = [
        DependencyAssumptionItem(id="DEP-01", description="General dep 1", linked_milestone="M1", linked_deliverable="DEL-01"),
        DependencyAssumptionItem(id="DEP-02", description="General dep 2", linked_milestone="M1", linked_deliverable="DEL-01"),
        DependencyAssumptionItem(id="DEP-03", description="General dep 3", linked_milestone="M1", linked_deliverable="DEL-01"),
        DependencyAssumptionItem(id="DEP-04", description="General dep 4", linked_milestone="M2", linked_deliverable="DEL-02"),
    ]

    default_ms = detect_default_filled_milestone(items)
    default_deliv = detect_default_filled_deliverable(items)
    assert default_ms == "M1"
    assert default_deliv == "DEL-01"

    milestones = [
        Milestone(id="M1", description="Phase 1: Setup accepted"),
        Milestone(id="M2", description="Phase 2: Build accepted"),
    ]
    parsed_phases = {m.id: parse_milestone_phase(m) for m in milestones}
    wbs_map = {"M1": "WBS-1", "M2": "WBS-2"}

    # Item 1 with default fill ignored -> Cross-phase
    ws, ms_str, wbs_str, note = link_raid_item_v2(
        item=items[0],
        milestones=milestones,
        deliv_mapping={},
        parsed_phases=parsed_phases,
        wbs_code_map=wbs_map,
        default_fill_milestone=default_ms,
        default_fill_deliverable=default_deliv,
    )

    assert ws == "Cross-phase"
    assert ms_str == ""
    assert wbs_str == ""
