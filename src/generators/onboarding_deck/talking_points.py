"""Deterministic talking point generators for Onboarding Deck speaker notes (DECK-09, Appendix K.2, K.3)."""

from typing import List, Optional


def build_slide1_talking_points(
    client_sponsor: str,
    start_date: str,
    start_basis: str,
) -> str:
    """Speaker notes for Slide 1 (Cover)."""
    return (
        "TALKING POINTS:\n"
        "• Welcome the Talent PM and Talent Project Team to onboarding.\n"
        f"• Engagement for {client_sponsor} starting {start_date} ({start_basis}).\n"
        "• Review delivery charter, milestone commitments, acceptance criteria, and governance cadence.\n\n"
        "SOURCES: Startup Kit · Project Charter; Project Delivery Workbook · Project Schedule"
    )


def build_slide2_talking_points(
    contract_type: str,
    governance_tier: str,
    pmo_lead: str,
    delivery_manager: str,
    talent_pm: str,
    purpose: str,
    escalation_path: str,
    phase_count: int,
    start_date: str,
    finish_date: str,
) -> str:
    """Speaker notes for Slide 2 (Project Charter)."""
    return (
        "TALKING POINTS:\n"
        f"• Project operates under {contract_type} contract terms and {governance_tier} governance.\n"
        f"• Delivery leadership: PMO Lead {pmo_lead}, Delivery Manager {delivery_manager}, Talent PM {talent_pm}.\n"
        f"• Purpose: {purpose}.\n"
        f"• Escalation path: {escalation_path}.\n"
        f"• Delivery spans {phase_count} phases from {start_date} to {finish_date}.\n\n"
        "SOURCES: Startup Kit · Project Charter, SOW Interpretation Summary; Project Delivery Workbook · Project Schedule"
    )


def build_slide3_talking_points(
    phase_count: int,
    first_start: str,
    last_finish: str,
    milestones_count: int,
    checkpoints_count: int,
    workstreams_count: int,
    deliverables_count: int,
    date_basis: str,
) -> str:
    """Speaker notes for Slide 3 (Workstreams, Milestones, Deliverables and Dates)."""
    cp_text = f" and {checkpoints_count} checkpoints" if checkpoints_count > 0 else ""
    return (
        "TALKING POINTS:\n"
        f"• The project runs in {phase_count} phases, from {first_start} to {last_finish}.\n"
        f"• Delivery commits to {milestones_count} milestones{cp_text} across {workstreams_count} workstreams.\n"
        f"• All {deliverables_count} deliverables are mapped to baseline milestone dates.\n"
        f"• Date basis: {date_basis}.\n\n"
        "SOURCES: Project Delivery Workbook · Project Schedule; Startup Kit · Deliverables and Acceptance Matrix"
    )


def build_slide4_talking_points(
    review_window: str,
    client_approver: str,
    deliverables_count: int,
) -> str:
    """Speaker notes for Slide 4 (Acceptance Criteria)."""
    return (
        "TALKING POINTS:\n"
        "• Acceptance is conducted at milestone level following defined quality review gates.\n"
        f"• Milestone review window is {review_window} with client approver {client_approver}.\n"
        f"• All {deliverables_count} deliverable acceptance criteria must be verified with required completion evidence.\n"
        "• Submissions follow standard verification and rework remediation workflows.\n\n"
        "SOURCES: Project Delivery Workbook · WBS; Startup Kit · Deliverables and Acceptance Matrix"
    )


def build_slide5_talking_points(
    high_count: int,
    top_risk_id: str,
    top_risk_desc: str,
) -> str:
    """Speaker notes for Slide 5 (High-Risk Items)."""
    risk_summary = f"First priority risk is {top_risk_id}: {top_risk_desc}." if top_risk_id else "No critical risks identified in delivery baseline."
    return (
        "TALKING POINTS:\n"
        f"• Active RAID tracking monitors {high_count} items rated High severity.\n"
        f"• {risk_summary}\n"
        "• Mitigations and proactive response ownership are assigned across delivery phases.\n"
        "• New risks or issues should be raised via the delivery escalation path.\n\n"
        "SOURCES: Project Delivery Workbook · RAID Log; Startup Kit · Project Charter"
    )


def build_slide6_talking_points(
    client_stakeholder_count: int,
    comms_count: int,
    first_gate: str,
    first_prereq: str,
) -> str:
    """Speaker notes for Slide 6 (Client Collaboration)."""
    prereq_summary = f"First client prerequisite is required by {first_gate}: {first_prereq}." if first_prereq else "Client prerequisites are tracked per delivery phase."
    return (
        "TALKING POINTS:\n"
        f"• Engagement governance establishes regular cadence with {client_stakeholder_count} client stakeholders.\n"
        f"• Communications rhythm includes {comms_count} scheduled governance touchpoints.\n"
        f"• {prereq_summary}\n"
        "• Active alignment ensures clear decision rights and rapid resolution of open items.\n\n"
        "SOURCES: Startup Kit · Stakeholder and Responsibility Model, Communications and Reporting Plan; Project Delivery Workbook · Project Schedule"
    )
