"""Tests for MAP-10: Traceability check warnings routed to ValidationReport and Fact Review."""

from datetime import date
from src.core.models import StartupKitBaseline, Deliverable, Milestone, SOWWorkItem, RiskAssumption, WorkPackageSeed
from src.generators.pmo_workbook.builder import build_workbook_model
from src.llm.validation import validate_and_repair_baseline
from src.review_ui.facts import build_fact_categories, get_blocking_validation_errors, prepare_review_baseline


def test_map_10_traceability_warning_routed_to_validation_report():
    """MAP-10: SOW reference mismatch in traceability check must be appended to baseline.validation_report."""
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
    initial_findings_count = len(baseline.validation_report.findings)

    wb = build_workbook_model(baseline, today=date(2026, 10, 3))

    assert baseline.validation_report is not None
    assert len(baseline.validation_report.findings) > initial_findings_count

    tr_findings = [f for f in baseline.validation_report.findings if f.invariant_id == "TR-01"]
    assert len(tr_findings) == 1
    finding = tr_findings[0]
    assert finding.severity == "warning"
    assert "Traceability check: Missing SOW References in workbook:" in finding.message
    assert "'Work Output 1'" in finding.message and "'Work Output 2'" in finding.message


def test_map_10_fact_review_displays_traceability_finding():
    """MAP-10: Fact Review's validation-findings category displays traceability findings."""
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

    reviewed_baseline = prepare_review_baseline(baseline)
    categories = {c.key: c for c in build_fact_categories(reviewed_baseline)}

    assert "validation_findings" in categories
    val_cat = categories["validation_findings"]
    labels_and_values = [(f.label, f.value) for f in val_cat.fields]

    matching_fields = [
        (lbl, val) for lbl, val in labels_and_values
        if "TR-01" in lbl and "Missing SOW References in workbook" in val
    ]
    assert len(matching_fields) == 1
    lbl, val = matching_fields[0]
    assert lbl == "warning - TR-01"
    assert "Work Output 1" in val and "Work Output 2" in val


def test_map_10_warning_does_not_block_approval():
    """MAP-10: Traceability warning does not block HTL-08 Approve button."""
    delivs = [
        Deliverable(id="DEL-01", name="Discovery & Onboarding Summary", description="Discovery phase", sow_reference="WO-01"),
    ]
    catalogue = [
        SOWWorkItem(reference="Work Output 1", reference_kind="Deliverable number", title="Discovery & Onboarding Summary", phase="", owner="Toptal", type="Documentation"),
    ]
    baseline = StartupKitBaseline(
        project_name="GitLab Modernization & AI Enablement Discovery",
        deliverables=delivs,
        milestones=[Milestone(id="M1", description="Project Kickoff")],
        sow_stories_catalogue=catalogue,
        backlog_seed=[]
    )

    validate_and_repair_baseline(baseline)
    build_workbook_model(baseline, today=date(2026, 10, 3))

    blocking_errors = get_blocking_validation_errors(baseline.validation_report)
    assert blocking_errors == []


def test_map_10_all_traceability_checks_route_findings():
    """MAP-10: All missing item checks (deliverables, work packages, RAID, etc.) route as warning findings."""
    baseline = StartupKitBaseline(
        project_name="Sample Project",
        deliverables=[
            Deliverable(id="DEL-01", name="Covered Deliverable"),
            Deliverable(id="DEL-02", name="Genuinely Missing Deliverable")
        ],
        milestones=[
            Milestone(id="M1", description="Phase 1 Gate")
        ],
        raid_items=[
            RiskAssumption(id="RSK-01", description="Risk 1", probability="Medium", impact="High", owner="Talent PM"),
            RiskAssumption(id="RSK-02", description="Risk 2", probability="Low", impact="Medium", owner="Talent PM"),
        ],
        backlog_seed=[
            WorkPackageSeed(id="WP-01", title="WP 1", parent_deliverable_id="DEL-01", sow_reference="SOW-01", owner="Toptal"),
            WorkPackageSeed(id="WP-02", title="WP 2", parent_deliverable_id="DEL-01", sow_reference="SOW-02", owner="Toptal"),
        ]
    )

    validate_and_repair_baseline(baseline)
    build_workbook_model(baseline, today=date(2026, 10, 3))

    assert baseline.validation_report is not None
    findings = baseline.validation_report.findings
    assert all(f.severity in ("warning", "repaired") for f in findings)
    assert get_blocking_validation_errors(baseline.validation_report) == []


def test_map_10_build_fact_categories_double_call_safety():
    """Calling build_fact_categories multiple times (simulating Streamlit reruns) must not mutate baseline or compound findings."""
    milestones_np = [
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
        Deliverable(id="DEL-01", name="Discovery Summary", description="Discovery", sow_reference="WO-01"),
        Deliverable(id="DEL-02", name="Project Plan", description="Plan", sow_reference="WO-02"),
    ]
    catalogue = [
        SOWWorkItem(reference="Work Output 1", reference_kind="Deliverable number", title="Discovery Summary", phase="", owner="Toptal", type="Documentation"),
        SOWWorkItem(reference="Work Output 2", reference_kind="Deliverable number", title="Project Plan", phase="", owner="Toptal", type="Documentation"),
    ]
    baseline_np = StartupKitBaseline(
        project_name="GitLab Modernization",
        deliverables=delivs,
        milestones=milestones_np,
        sow_stories_catalogue=catalogue,
        backlog_seed=[]
    )
    validate_and_repair_baseline(baseline_np)

    # First call
    c1 = build_fact_categories(baseline_np)
    ms_ids_1 = [m.id for m in baseline_np.milestones]
    findings_count_1 = len(baseline_np.validation_report.findings)

    # Second call
    c2 = build_fact_categories(baseline_np)
    ms_ids_2 = [m.id for m in baseline_np.milestones]
    findings_count_2 = len(baseline_np.validation_report.findings)

    assert ms_ids_1 == ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"]
    assert ms_ids_2 == ms_ids_1
    assert findings_count_1 == findings_count_2

    # Phased baseline undergoing defensive reduction
    m1 = Milestone(id="M1", description="P1 Phase 1 acceptance review", key_dependencies=["Dep 1"], critical_path_assumptions=["Assumption 1"])
    m2 = Milestone(id="M2", description="P1 Discovery & Requirements complete", key_dependencies=["Dep 2"])
    m3 = Milestone(id="M3", description="P1 Architecture approved")
    m4 = Milestone(id="M4", description="P1 Build completed")
    m5 = Milestone(id="M5", description="P1 accepted", key_dependencies=["Dep 5"])

    baseline_p = StartupKitBaseline(
        project_name="Phased Project",
        deliverables=[Deliverable(id="DEL-01", name="Core Deliverable", description="Phase 1 deliverable")],
        milestones=[m1, m2, m3, m4, m5],
        interim_checkpoints=[],
        backlog_seed=[]
    )

    build_fact_categories(baseline_p)
    assert [m.id for m in baseline_p.milestones] == ["M1", "M2", "M3", "M4", "M5"]
    assert baseline_p.milestones[4].key_dependencies == ["Dep 5"]
    assert baseline_p.milestones[4].merged_milestone_ids == []

    build_fact_categories(baseline_p)
    assert [m.id for m in baseline_p.milestones] == ["M1", "M2", "M3", "M4", "M5"]
    assert baseline_p.milestones[4].key_dependencies == ["Dep 5"]
    assert baseline_p.milestones[4].merged_milestone_ids == []
