"""Test acceptance mode decision (milestone-level vs per-deliverable) and resulting task structure."""

from datetime import date
from src.core.models import StartupKitBaseline, Milestone, Deliverable, ProjectStartupCharter
from src.generators.pmo_workbook.builder import (
    build_workbook_model,
    check_acceptance_mode,
)


def test_arc_baseline_acceptance_mode(arc_baseline):
    mode = check_acceptance_mode(arc_baseline)
    assert mode == "milestone-level"

    model = build_workbook_model(arc_baseline, start_date=date(2026, 10, 5))

    # In milestone-level mode: 6 tasks per milestone acceptance package
    for m_id in ["M1", "M2", "M3", "M4"]:
        pkg_tasks = [
            w for w in model.wbs_rows
            if w.level == 4 and w.milestone_id == m_id and not w.deliverable_id
            and not w.name.startswith("Confirm:") and "Kickoff" not in w.name
            and not w.name.startswith("Other")
        ]
        # Check acceptance tasks (v3 A1)
        task_names = [w.name for w in pkg_tasks]
        assert "Prepare milestone acceptance package and evidence" in task_names
        assert "Support client user acceptance testing" in task_names
        assert "Triage and address client review feedback" in task_names
        assert "Obtain formal milestone acceptance and sign-off" in task_names
        assert "Update schedule and RAID Log after acceptance" in task_names


def test_per_deliverable_acceptance_mode():
    baseline = StartupKitBaseline(
        project_name="Simple Project",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        charter=ProjectStartupCharter(
            project_name="Simple Project",
            client_name="Client Corp",
            contract_type="Time and Materials",
            delivery_manager="Jane Doe",
            talent_pm="John Smith",
            pmo_lead="Sarah Connor",
        ),
        milestones=[
            Milestone(id="M1", description="Phase 1 Deliverables Complete", external_date=date(2026, 11, 1))
        ],
        deliverables=[
            Deliverable(id="DEL-01", name="Custom Backend API", description="Custom Backend API", owner="Talent PM")
        ],
        backlog_seed=[],
        communications_plan=[],
        raid_items=[],
    )

    mode = check_acceptance_mode(baseline)
    assert mode == "per-deliverable"

    model = build_workbook_model(baseline, start_date=date(2026, 10, 5))

    # In per-deliverable mode: deliverable has submit/feedback/acceptance tasks
    deliv_tasks = [w.name for w in model.wbs_rows if w.level == 4 and w.deliverable_id == "DEL-01"]
    assert "Submit for client review" in deliv_tasks
    assert "Address client feedback and rework" in deliv_tasks
    assert "Obtain written client acceptance" in deliv_tasks

    # Milestone acceptance package task
    m_tasks = [w.name for w in model.wbs_rows if w.level == 4 and w.milestone_id == "M1" and not w.deliverable_id]
    assert "Confirm all M1 deliverables are accepted" in m_tasks
    assert "Update schedule and RAID Log after acceptance" in m_tasks
