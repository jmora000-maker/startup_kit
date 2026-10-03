"""Unit test for WBS-05: Milestone Acceptance task name uses plain communications item name without audience expansion."""

from datetime import date
from src.core.models import (
    StartupKitBaseline,
    Milestone,
    Deliverable,
    CommunicationsPlanItem,
)
from src.generators.pmo_workbook.builder import build_workbook_model


def test_wbs_05_milestone_acceptance_task_name_no_audience_expansion():
    """WBS-05: Task name for Milestone Acceptance Review is plain comms name, never expanded with audience/approvers."""
    milestones = [
        Milestone(id="M1", description="P1 Foundation accepted: shell and IAM", external_date=date(2026, 11, 17), owner="Delivery Manager"),
    ]
    deliverables = [
        Deliverable(id="DEL-01", name="Core Microservices", milestone_id="M1", client_approver="Client Contact (Mike Magwire), Client approvers (including Satya) and Toptal Delivery Team"),
    ]
    comms = [
        CommunicationsPlanItem(
            id="COM-06",
            name="Milestone Acceptance Review",
            audience="Client Contact (Mike Magwire), Client approvers (including Satya) and Toptal Delivery Team",
            purpose="Formal sign-off of milestone deliverables",
            frequency="Per milestone",
            owner="Delivery Manager",
            channel="Meeting",
        )
    ]
    baseline = StartupKitBaseline(
        project_name="WBS-05 Test",
        milestones=milestones,
        deliverables=deliverables,
        communications_plan=comms,
    )
    model = build_workbook_model(baseline, start_date=date(2026, 10, 5))

    accept_pkg = next(w for w in model.wbs_rows if w.element_type == "Work Package" and "Milestone Acceptance" in w.name)
    tasks = [w for w in model.wbs_rows if w.level == 4 and w.wbs_code.startswith(accept_pkg.wbs_code + ".")]

    # Task 3 is the acceptance review task
    review_task = tasks[2]
    assert review_task.name == "Milestone Acceptance Review"
    assert "Mike Magwire" not in review_task.name
    assert "Satya" not in review_task.name
