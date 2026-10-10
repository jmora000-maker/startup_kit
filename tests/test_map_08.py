"""Tests for MAP-08: SOW reference format normalization in traceability check."""

from datetime import date
import pytest
from src.config import normalize_sow_reference, extract_sow_references
from src.core.models import StartupKitBaseline, Deliverable, Milestone, SOWWorkItem, WorkPackageSeed
from src.generators.pmo_workbook.builder import build_workbook_model
from src.llm.validation import validate_and_repair_baseline
from src.review_ui.facts import build_fact_categories


def test_normalize_sow_reference_canonical_forms():
    """MAP-08: Verify canonical normalization across various reference formats."""
    # 1. Work Output variations
    assert normalize_sow_reference("WO-01") == "WO:1"
    assert normalize_sow_reference("WO-1") == "WO:1"
    assert normalize_sow_reference("Work Output 1") == "WO:1"
    assert normalize_sow_reference("Work Output 01") == "WO:1"
    assert normalize_sow_reference("Work Output #1") == "WO:1"
    assert normalize_sow_reference("WO 1") == "WO:1"
    assert normalize_sow_reference("WO-02") == "WO:2"
    assert normalize_sow_reference("Work Output 2") == "WO:2"

    # Distinct numbers must remain distinct
    assert normalize_sow_reference("WO-01") != normalize_sow_reference("Work Output 2")

    # 2. Deliverable variations
    assert normalize_sow_reference("Deliverable 1") == "DEL:1"
    assert normalize_sow_reference("Deliverable 01") == "DEL:1"
    assert normalize_sow_reference("Deliverable 1.1") == "DEL:1.1"
    assert normalize_sow_reference("D1") == "DEL:1"
    assert normalize_sow_reference("D01") == "DEL:1"
    assert normalize_sow_reference("D-01") == "DEL:1"
    assert normalize_sow_reference("DEL-01") == "DEL:1"
    assert normalize_sow_reference("DEL-1") == "DEL:1"

    # 3. Story variations (real SOW stories)
    assert normalize_sow_reference("Story 1") == "STORY:1"
    assert normalize_sow_reference("Story 01") == "STORY:1"
    assert normalize_sow_reference("Story-01") == "STORY:1"
    assert normalize_sow_reference("STORY-12") == "STORY:12"

    # 4. Synthetic SOW references (never conflated with real Story references)
    assert normalize_sow_reference("SOW-01") == "SYNTH:1"
    assert normalize_sow_reference("SOW-1") == "SYNTH:1"
    assert normalize_sow_reference("SOW-01") != normalize_sow_reference("Story 1")

    # 5. Phased synthetic references
    assert normalize_sow_reference("SOW-P1-01") == "SYNTH:P1:1"
    assert normalize_sow_reference("SOW-P1-1") == "SYNTH:P1:1"
    assert normalize_sow_reference("SOW-P2a-02") == "SYNTH:P2A:2"

    # 6. Task / WBS variations
    assert normalize_sow_reference("Task 1") == "TASK:1"
    assert normalize_sow_reference("Task 01") == "TASK:1"
    assert normalize_sow_reference("TASK-01") == "TASK:1"
    assert normalize_sow_reference("T-01") == "TASK:1"
    assert normalize_sow_reference("WBS 1.1") == "WBS:1.1"

    # 7. Section / Clause variations
    assert normalize_sow_reference("Section 3.1") == "SECTION:3.1"
    assert normalize_sow_reference("Clause 4") == "SECTION:4"
    assert normalize_sow_reference("§ 2.1") == "SECTION:2.1"


def test_map_08_traceability_normalization_gitlab_baseline():
    """MAP-08: Deliverables tagged WO-01/WO-02 match catalogue tagged Work Output 1/Work Output 2."""
    delivs = [
        Deliverable(id="DEL-01", name="Discovery & Onboarding Summary", description="Discovery phase", sow_reference="WO-01"),
        Deliverable(id="DEL-02", name="Task-Level Project Plan", description="Project plan", sow_reference="WO-02"),
    ]
    milestones = [
        Milestone(id="M1", description="Project Kickoff"),
        Milestone(id="M2", description="Project Sign-off"),
    ]
    catalogue = [
        SOWWorkItem(reference="Work Output 1", reference_kind="Deliverable number", title="Discovery & Onboarding Summary", phase="", owner="Toptal", type="Documentation"),
        SOWWorkItem(reference="Work Output 2", reference_kind="Deliverable number", title="Task-Level Project Plan", phase="", owner="Toptal", type="Documentation"),
    ]
    baseline = StartupKitBaseline(
        project_name="GitLab Modernization & AI Enablement Discovery",
        deliverables=delivs,
        milestones=milestones,
        sow_stories_catalogue=catalogue,
        backlog_seed=[]
    )

    validate_and_repair_baseline(baseline)
    wb = build_workbook_model(baseline, today=date(2026, 10, 3))

    # SOW References in traceability dictionary
    sow_trace = wb.traceability["SOW References"]
    assert sow_trace["missing_ids"] == []

    # Validation findings should not have any TR-01 warning for missing SOW references
    tr_findings = [f for f in baseline.validation_report.findings if f.invariant_id == "TR-01" and "Unmatched SOW References" in f.message]
    assert tr_findings == []


def test_map_08_traceability_normalization_reverse_tagging():
    """MAP-08: Deliverables tagged Work Output 1/Work Output 2 match catalogue tagged WO-01/WO-02."""
    delivs = [
        Deliverable(id="DEL-01", name="Discovery & Onboarding Summary", description="Discovery phase", sow_reference="Work Output 1"),
        Deliverable(id="DEL-02", name="Task-Level Project Plan", description="Project plan", sow_reference="Work Output 2"),
    ]
    milestones = [
        Milestone(id="M1", description="Project Kickoff"),
        Milestone(id="M2", description="Project Sign-off"),
    ]
    catalogue = [
        SOWWorkItem(reference="WO-01", reference_kind="Story ID", title="Discovery & Onboarding Summary", phase="", owner="Toptal", type="Documentation"),
        SOWWorkItem(reference="WO-02", reference_kind="Story ID", title="Task-Level Project Plan", phase="", owner="Toptal", type="Documentation"),
    ]
    baseline = StartupKitBaseline(
        project_name="GitLab Modernization & AI Enablement Discovery",
        deliverables=delivs,
        milestones=milestones,
        sow_stories_catalogue=catalogue,
        backlog_seed=[]
    )

    validate_and_repair_baseline(baseline)
    wb = build_workbook_model(baseline, today=date(2026, 10, 3))

    sow_trace = wb.traceability["SOW References"]
    assert sow_trace["missing_ids"] == []

    tr_findings = [f for f in baseline.validation_report.findings if f.invariant_id == "TR-01" and "Unmatched SOW References" in f.message]
    assert tr_findings == []


def test_map_08_genuine_mismatch_detected():
    """MAP-08: Genuine mismatch (different numbers: WO-01 vs Work Output 2) is still caught."""
    delivs = [
        Deliverable(id="DEL-01", name="Discovery & Onboarding Summary", description="Discovery phase", sow_reference="WO-01"),
    ]
    milestones = [
        Milestone(id="M1", description="Project Kickoff"),
    ]
    catalogue = [
        SOWWorkItem(reference="WO-01", reference_kind="Deliverable number", title="Discovery & Onboarding Summary", phase="", owner="Toptal", type="Documentation"),
        SOWWorkItem(reference="Work Output 2", reference_kind="Deliverable number", title="Task-Level Project Plan", phase="", owner="Toptal", type="Documentation"),
    ]
    backlog = [
        WorkPackageSeed(id="WP-01", parent_deliverable_id="DEL-01", title="Discovery Task", sow_reference="WO-01", owner="Toptal")
    ]
    baseline = StartupKitBaseline(
        project_name="GitLab Modernization & AI Enablement Discovery",
        deliverables=delivs,
        milestones=milestones,
        sow_stories_catalogue=catalogue,
        backlog_seed=backlog
    )

    wb = build_workbook_model(baseline, today=date(2026, 10, 3))

    sow_trace = wb.traceability["SOW References"]
    assert "Work Output 2" in sow_trace["missing_ids"]

    tr_findings = [f for f in baseline.validation_report.findings if f.invariant_id == "TR-01" and "Unmatched SOW References" in f.message]
    assert len(tr_findings) == 1
    assert "Work Output 2" in tr_findings[0].message


def test_map_08_fact_review_clean_when_matching():
    """MAP-08: Fact Review displays no TR-01 finding when references match via canonical normalization."""
    delivs = [
        Deliverable(id="DEL-01", name="Discovery & Onboarding Summary", description="Discovery phase", sow_reference="WO-01"),
        Deliverable(id="DEL-02", name="Task-Level Project Plan", description="Project plan", sow_reference="WO-02"),
    ]
    milestones = [
        Milestone(id="M1", description="Project Kickoff"),
        Milestone(id="M2", description="Project Sign-off"),
    ]
    catalogue = [
        SOWWorkItem(reference="Work Output 1", reference_kind="Deliverable number", title="Discovery & Onboarding Summary", phase="", owner="Toptal", type="Documentation"),
        SOWWorkItem(reference="Work Output 2", reference_kind="Deliverable number", title="Task-Level Project Plan", phase="", owner="Toptal", type="Documentation"),
    ]
    baseline = StartupKitBaseline(
        project_name="GitLab Modernization & AI Enablement Discovery",
        deliverables=delivs,
        milestones=milestones,
        sow_stories_catalogue=catalogue,
        backlog_seed=[]
    )

    validate_and_repair_baseline(baseline)
    categories = {c.key: c for c in build_fact_categories(baseline)}

    if "validation_findings" in categories:
        val_cat = categories["validation_findings"]
        labels_and_values = [(f.label, f.value) for f in val_cat.fields]
        tr_fields = [
            (lbl, val) for lbl, val in labels_and_values
            if "TR-01" in lbl and "Unmatched SOW References" in val
        ]
        assert tr_fields == []


def test_map_08_synthetic_and_real_story_conflation_prevention():
    """MAP-08: A synthetic SOW-01 placeholder on a deliverable must NEVER falsely match a real 'Story 1' catalogue item."""
    # Deliverable has a synthetic SOW-01 reference
    delivs = [
        Deliverable(id="DEL-01", name="Generic Platform Work", description="Synthetic deliverable", sow_reference="SOW-01"),
    ]
    milestones = [
        Milestone(id="M1", description="Project Kickoff"),
    ]
    # SOW catalogue has an UNRELATED real Story 1 from the contract
    catalogue = [
        SOWWorkItem(
            reference="Story 1",
            reference_kind="Story ID",
            title="Real Contract Story: User Authentication Flow",
            phase="",
            owner="Toptal",
            type="Build"
        ),
    ]
    baseline = StartupKitBaseline(
        project_name="Platform Modernization",
        deliverables=delivs,
        milestones=milestones,
        sow_stories_catalogue=catalogue,
        backlog_seed=[]
    )

    wb = build_workbook_model(baseline, today=date(2026, 10, 3))

    # Traceability check must detect that 'Story 1' is missing (not falsely satisfied by synthetic 'SOW-01')
    sow_trace = wb.traceability["SOW References"]
    assert "Story 1" in sow_trace["missing_ids"]

    # Must also emit a TR-01 ValidationFinding warning
    assert baseline.validation_report is not None
    tr_findings = [f for f in baseline.validation_report.findings if f.invariant_id == "TR-01" and "Unmatched SOW References" in f.message]
    assert len(tr_findings) == 1
    assert "Story 1" in tr_findings[0].message


def test_map_12_hypercare_capacity_non_numeric_synthetic_reference_matches():
    """MAP-12: Non-numeric synthetic reference 'Hypercare Capacity' matches between deliverable/backlog and SOW catalogue without false warnings."""
    deliv = Deliverable(
        id="DEL-20",
        name="Four-Week Hypercare Support",
        description="Post-launch hypercare support",
        sow_reference="Hypercare Capacity",
    )
    milestone = Milestone(
        id="M4",
        description="P3 Launch accepted: System live and hypercare support delivered.",
    )
    catalogue_item = SOWWorkItem(
        reference="Hypercare Capacity",
        reference_kind="Synthetic",
        title="Hypercare Capacity: up to 160 hours",
        phase="P3 Launch",
        owner="Toptal Delivery Team",
        type="Build",
    )
    wp = WorkPackageSeed(
        id="WP-36",
        parent_deliverable_id="DEL-20",
        title="Hypercare Capacity: up to 160 hours of developer and QA support",
        sow_reference="Hypercare Capacity",
        owner="Toptal Delivery Team",
    )
    baseline = StartupKitBaseline(
        project_name="ARC Genomics Platform Implementation",
        deliverables=[deliv],
        milestones=[milestone],
        sow_stories_catalogue=[catalogue_item],
        backlog_seed=[wp],
    )

    wb = build_workbook_model(baseline, today=date(2026, 10, 10))

    sow_trace = wb.traceability["SOW References"]
    assert sow_trace["missing_ids"] == []
    assert sow_trace["in_baseline"] == 1
    assert sow_trace["in_workbook"] == 1
    assert sow_trace["synthetic"] is True

    # No TR-01 warning should be emitted for SOW references
    if baseline.validation_report:
        tr_findings = [f for f in baseline.validation_report.findings if f.invariant_id == "TR-01" and "Unmatched SOW References" in f.message]
        assert tr_findings == []


def test_map_12_genuinely_missing_non_numeric_reference_produces_warning():
    """MAP-12: A genuinely missing non-numeric reference in catalogue produces clear Unmatched SOW References warning."""
    deliv = Deliverable(
        id="DEL-01",
        name="Discovery & Planning",
        description="Discovery phase",
        sow_reference="WO-01",
    )
    milestone = Milestone(
        id="M1",
        description="Project Kickoff",
    )
    catalogue = [
        SOWWorkItem(
            reference="WO-01",
            reference_kind="Deliverable number",
            title="Discovery & Planning",
            phase="",
            owner="Toptal",
            type="Documentation",
        ),
        SOWWorkItem(
            reference="Hypercare Capacity",
            reference_kind="Synthetic",
            title="Hypercare Capacity: up to 160 hours",
            phase="",
            owner="Toptal",
            type="Build",
        ),
    ]
    wp = WorkPackageSeed(
        id="WP-01",
        parent_deliverable_id="DEL-01",
        title="Discovery Task",
        sow_reference="WO-01",
        owner="Toptal",
    )
    baseline = StartupKitBaseline(
        project_name="Platform Implementation",
        deliverables=[deliv],
        milestones=[milestone],
        sow_stories_catalogue=catalogue,
        backlog_seed=[wp],
    )

    wb = build_workbook_model(baseline, today=date(2026, 10, 10))

    sow_trace = wb.traceability["SOW References"]
    assert "Hypercare Capacity" in sow_trace["missing_ids"]

    assert baseline.validation_report is not None
    tr_findings = [f for f in baseline.validation_report.findings if f.invariant_id == "TR-01" and "Unmatched SOW References" in f.message]
    assert len(tr_findings) == 1
    assert "Hypercare Capacity" in tr_findings[0].message


def test_map_12_comma_separated_references_including_synthetic_match():
    """MAP-12: Deliverable with comma-separated references ('WO-01, Hypercare Capacity') matches both catalogue items."""
    deliv = Deliverable(
        id="DEL-01",
        name="Hybrid Scope Package",
        description="Delivery and hypercare scope",
        sow_reference="WO-01, Hypercare Capacity",
    )
    milestone = Milestone(
        id="M1",
        description="Gate 1",
    )
    catalogue = [
        SOWWorkItem(
            reference="Work Output 1",
            reference_kind="Deliverable number",
            title="Discovery & Planning",
            phase="",
            owner="Toptal",
            type="Documentation",
        ),
        SOWWorkItem(
            reference="Hypercare Capacity",
            reference_kind="Synthetic",
            title="Hypercare Capacity",
            phase="",
            owner="Toptal",
            type="Build",
        ),
    ]
    wp = WorkPackageSeed(
        id="WP-01",
        parent_deliverable_id="DEL-01",
        title="Delivery Task",
        sow_reference="WO-01, Hypercare Capacity",
        owner="Toptal",
    )
    baseline = StartupKitBaseline(
        project_name="Platform Implementation",
        deliverables=[deliv],
        milestones=[milestone],
        sow_stories_catalogue=catalogue,
        backlog_seed=[wp],
    )

    wb = build_workbook_model(baseline, today=date(2026, 10, 10))

    sow_trace = wb.traceability["SOW References"]
    assert sow_trace["missing_ids"] == []
    assert sow_trace["in_baseline"] == 3
    assert sow_trace["in_workbook"] == 2
    if baseline.validation_report:
        tr_findings = [f for f in baseline.validation_report.findings if f.invariant_id == "TR-01" and "Unmatched SOW References" in f.message]
        assert tr_findings == []
