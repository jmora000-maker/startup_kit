import copy
from datetime import date
from src.core.models import (
    StartupKitBaseline,
    Deliverable,
    Milestone,
    SOWWorkItem,
    WorkPackageSeed,
)
from src.generators.pmo_workbook.builder import build_workbook_model
from src.generators.pmo_workbook.workstreams import classify_milestone, parse_milestone_phase
from src.review_ui import facts as review


def test_map_09_non_phase_milestones_preserved_distinct():
    """MAP-09: Projects without phase codes (e.g. discovery engagements) must NOT collapse all milestones into one."""
    milestones = [
        Milestone(id="M1", description="Project Kickoff and Alignment"),
        Milestone(id="M2", description="Discovery Interviews and Environment Review"),
        Milestone(id="M3", description="Architecture and Workflow Assessment"),
        Milestone(id="M4", description="AI Enablement Feasibility Analysis"),
        Milestone(id="M5", description="Tooling and Pipeline Evaluation"),
        Milestone(id="M6", description="Modernization Strategy Synthesis"),
        Milestone(id="M7", description="Draft Findings and Roadmap Review"),
        Milestone(id="M8", description="Final Report and Deliverable Preparation"),
        Milestone(id="M9", description="Client sign-off and acceptance of Work Output"),
    ]

    delivs = [
        Deliverable(id="DEL-01", name="Discovery & Onboarding Summary", description="Summary of discovery interviews and findings", sow_reference="WO-01"),
        Deliverable(id="DEL-02", name="Task-Level Project Plan", description="Detailed project plan and roadmap", sow_reference="WO-02"),
        Deliverable(id="DEL-03", name="Weekly Status Report", description="Weekly project status reporting", sow_reference=None),
        Deliverable(id="DEL-04", name="Sign-Off Document", description="Final sign-off document", sow_reference=None),
    ]

    catalogue = [
        SOWWorkItem(reference="WO-01", reference_kind="Deliverable number", title="Discovery Summary", phase="", owner="Toptal", type="Documentation"),
        SOWWorkItem(reference="WO-02", reference_kind="Deliverable number", title="Project Plan", phase="", owner="Toptal", type="Documentation"),
    ]

    wp = [
        WorkPackageSeed(id="WP-01", parent_deliverable_id="DEL-01", title="Discovery", sow_reference="WO-01", owner="Toptal"),
        WorkPackageSeed(id="WP-02", parent_deliverable_id="DEL-02", title="Plan", sow_reference="WO-02", owner="Toptal"),
    ]

    baseline = StartupKitBaseline(
        project_name="GitLab Modernization & AI Enablement Discovery",
        deliverables=delivs,
        milestones=milestones,
        sow_stories_catalogue=catalogue,
        backlog_seed=wp,
    )

    wb = build_workbook_model(baseline, today=date(2026, 10, 10))

    # 1. Milestone count check: all 9 milestones must be distinct schedule rows
    schedule_ms_ids = [r.milestone_id for r in wb.schedule_rows if r.row_type == "Milestone"]
    assert len(schedule_ms_ids) == 9
    assert set(schedule_ms_ids) == {f"M{i}" for i in range(1, 10)}

    # 2. Check WBS Level 2 milestone rows: must contain all 9 milestones
    wbs_ms_ids = [w.milestone_id for w in wb.wbs_rows if w.level == 2 and w.element_type == "Milestone"]
    assert len(wbs_ms_ids) == 9
    assert set(wbs_ms_ids) == {f"M{i}" for i in range(1, 10)}


def test_map_09_keyword_matched_milestone_unaffected():
    """MAP-09: Milestones with keyword matches (e.g. architecture) are classified into taxonomy workstreams and emit no warning."""
    ms = Milestone(
        id="M1",
        description="Architecture Blueprint and System Architecture Approved",
    )
    ws_code, basis = classify_milestone(ms)
    assert ws_code == "DES"
    assert "Keyword: architecture" in basis or "Keyword: architect" in basis or "Keyword: blueprint" in basis

    parsed = parse_milestone_phase(ms)
    assert parsed.workstream_name == "Design & Architecture"
    assert parsed.note == "Workstream inferred from keywords - confirm"

    baseline = StartupKitBaseline(
        project_name="Architecture Project",
        deliverables=[Deliverable(id="DEL-01", name="Architecture Blueprint", sow_reference="WO-01")],
        milestones=[ms],
        sow_stories_catalogue=[SOWWorkItem(reference="WO-01", reference_kind="Deliverable number", title="Arch", phase="", owner="Toptal", type="Documentation")],
        backlog_seed=[WorkPackageSeed(id="WP-01", parent_deliverable_id="DEL-01", title="Arch Task", sow_reference="WO-01", owner="Toptal")],
    )

    wb = build_workbook_model(baseline, today=date(2026, 10, 10))
    # No TR-01 finding for unclassified workstream
    if baseline.validation_report:
        unclassified_findings = [
            f for f in baseline.validation_report.findings
            if f.invariant_id == "TR-01" and "Workstream classification" in f.message
        ]
        assert unclassified_findings == []


def test_map_09_unclassifiable_milestone_gets_neutral_placeholder_and_tr01_finding():
    """MAP-09: Milestones with no phase code and no matching keywords get 'Unclassified' placeholder and a TR-01 warning finding."""
    ms = Milestone(
        id="M1",
        description="Kickoff and Scope Alignment Complete",
    )
    ws_code, basis = classify_milestone(ms)
    assert ws_code is None
    assert basis == "Unclassified - confirm workstream"

    parsed = parse_milestone_phase(ms)
    assert parsed.workstream_name == "Unclassified"
    assert parsed.note == "Workstream unclassified - confirm"

    baseline = StartupKitBaseline(
        project_name="Unclassified Milestone Project",
        deliverables=[Deliverable(id="DEL-01", name="Kickoff Artifact", sow_reference="WO-01")],
        milestones=[ms],
        sow_stories_catalogue=[SOWWorkItem(reference="WO-01", reference_kind="Deliverable number", title="Kickoff", phase="", owner="Toptal", type="Documentation")],
        backlog_seed=[WorkPackageSeed(id="WP-01", parent_deliverable_id="DEL-01", title="Kickoff Task", sow_reference="WO-01", owner="Toptal")],
    )

    wb = build_workbook_model(baseline, today=date(2026, 10, 10))

    assert baseline.validation_report is not None
    unclassified_findings = [
        f for f in baseline.validation_report.findings
        if f.invariant_id == "TR-01" and "Workstream classification" in f.message
    ]
    assert len(unclassified_findings) == 1
    assert unclassified_findings[0].severity == "warning"
    assert "Milestone 'M1' could not be confidently classified into a workstream category; assigned 'Unclassified'" in unclassified_findings[0].message

    # Confirm schedule row uses the Unclassified workstream
    sched_ms = [r for r in wb.schedule_rows if r.milestone_id == "M1"]
    assert len(sched_ms) == 1
    assert sched_ms[0].workstream == "Unclassified"


def test_map_09_fact_review_correction_propagates_to_workbook_model():
    """MAP-09: Correcting a milestone's phase/workstream in Fact Review propagates to workbook model and removes the warning."""
    ms = Milestone(
        id="M1",
        description="Kickoff and Scope Alignment Complete",
    )
    baseline = StartupKitBaseline(
        project_name="Unclassified Milestone Project",
        deliverables=[Deliverable(id="DEL-01", name="Kickoff Artifact", sow_reference="WO-01")],
        milestones=[ms],
        sow_stories_catalogue=[SOWWorkItem(reference="WO-01", reference_kind="Deliverable number", title="Kickoff", phase="", owner="Toptal", type="Documentation")],
        backlog_seed=[WorkPackageSeed(id="WP-01", parent_deliverable_id="DEL-01", title="Kickoff Task", sow_reference="WO-01", owner="Toptal")],
    )

    # 1. Before correction: produces Unclassified and warning finding
    reviewed_baseline = review.prepare_review_baseline(baseline)
    categories = review.build_fact_categories(reviewed_baseline)

    # 2. Reviewer corrects milestone phase to 'P1 Inception & Discovery'
    submitted = review.extracted_values(categories)
    submitted["milestones.M1.phase"] = "P1 Inception & Discovery"

    facts, corrections = review.compute_review(categories, submitted)
    assert facts["milestones"] == review.HUMAN_CORRECTED

    corrected_baseline = review.apply_corrections(reviewed_baseline, corrections)
    assert corrected_baseline.milestones[0].phase == "P1"
    assert corrected_baseline.milestones[0].phase_display == "P1 Inception & Discovery"

    # 3. Build workbook from corrected baseline
    wb = build_workbook_model(corrected_baseline, today=date(2026, 10, 10))
    sched_ms = [r for r in wb.schedule_rows if r.milestone_id == "M1"]
    assert len(sched_ms) == 1
    assert sched_ms[0].workstream == "P1 Inception & Discovery"

    # Warning finding should not be emitted on corrected baseline
    if corrected_baseline.validation_report:
        unclassified_findings = [
            f for f in corrected_baseline.validation_report.findings
            if f.invariant_id == "TR-01" and "Workstream classification" in f.message
        ]
        assert unclassified_findings == []
