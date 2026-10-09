"""Tests for MAP-09 milestone and workstream consistency across artifacts."""

from datetime import date
import pytest
from src.core.models import StartupKitBaseline, Deliverable, Milestone, SOWWorkItem
from src.generators.pmo_workbook.builder import build_workbook_model
from src.llm.validation import validate_and_repair_baseline


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

    baseline = StartupKitBaseline(
        project_name="GitLab Modernization & AI Enablement Discovery",
        deliverables=delivs,
        milestones=milestones,
        backlog_seed=[]
    )

    validate_and_repair_baseline(baseline)
    wb = build_workbook_model(baseline, today=date(2026, 10, 3))

    # 1. Milestone count check: all 9 milestones must be distinct schedule rows
    schedule_ms_ids = [r.milestone_id for r in wb.schedule_rows if r.row_type == "Milestone"]
    assert len(schedule_ms_ids) == 9
    assert schedule_ms_ids == ["M1", "M6", "M7", "M8", "M9", "M2", "M4", "M3", "M5"] or set(schedule_ms_ids) == {f"M{i}" for i in range(1, 10)}

    # 2. Check WBS Level 2 milestone rows: must contain all 9 milestones
    wbs_ms_ids = [w.milestone_id for w in wb.wbs_rows if w.level == 2 and w.element_type == "Milestone"]
    assert len(wbs_ms_ids) == 9
    assert set(wbs_ms_ids) == {f"M{i}" for i in range(1, 10)}


def test_map_09_phased_milestones_defensive_separation():
    """Phased projects with phase codes (e.g. > 4 milestones with P1/P2) still undergo defensive separation when un-reconciled."""
    milestones = [
        Milestone(id="M1", description="P1 Discovery & Requirements complete"),
        Milestone(id="M2", description="P1 Architecture approved"),
        Milestone(id="M3", description="P1 Build completed"),
        Milestone(id="M4", description="P1 Testing completed"),
        Milestone(id="M5", description="P1 accepted and signed off"),
    ]

    baseline = StartupKitBaseline(
        project_name="Phased Project",
        deliverables=[Deliverable(id="DEL-01", name="Core Deliverable", description="Phase 1 deliverable")],
        milestones=milestones,
        interim_checkpoints=[],
        backlog_seed=[]
    )

    wb = build_workbook_model(baseline, today=date(2026, 10, 3))
    schedule_ms = [r for r in wb.schedule_rows if r.row_type == "Milestone"]
    schedule_cps = [r for r in wb.schedule_rows if r.row_type == "Checkpoint"]

    # In phased project with > 4 milestones and no checkpoints, defensive separation separates gate from checkpoints
    assert len(schedule_ms) == 1
    assert len(schedule_cps) == 4
