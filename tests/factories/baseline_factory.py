"""tests/factories/baseline_factory.py

Synthetic baseline factory for regression and invariant testing (HTL-69).
Constructs completely isolated, clean StartupKitBaseline instances from scratch
without borrowing data or structure from any real client fixture.
"""

from datetime import date
from typing import Any, Dict, List, Optional
from src.core.models import (
    CommunicationsPlanItem,
    Deliverable,
    GovernanceContext,
    GovernanceTier,
    Milestone,
    ProjectStartupCharter,
    RiskAssumption,
    SOWInterpretationSummary,
    Stakeholder,
    StartupKitBaseline,
)
from src.llm.validation import validate_and_repair_baseline


def create_test_baseline(
    project_name: str = "Test Alpha Modernization",
    client_name: str = "Acme Global Industries",
    governance_tier: GovernanceTier = "Partnered",
    contract_type: str = "Fixed Bid",
    sow_title: str = "Acme SOW-01 Delivery Engagement",
    start_date: Optional[date] = date(2026, 11, 2),
    **overrides: Any,
) -> StartupKitBaseline:
    """Construct a clean, synthetic StartupKitBaseline from scratch.

    All default strings, objectives, deliverables, and milestones use strictly
    neutral synthetic terms ('Acme', 'Test Alpha', 'Workstream 1') to eliminate
    cross-client contamination risks.
    """
    charter_kwargs: Dict[str, Any] = {
        "project_name": project_name,
        "client_name": client_name,
        "project_purpose": f"Delivery and cloud enablement for {project_name}.",
        "problem_statement": "Legacy system bottlenecks require architectural modernization and automated testing.",
        "solution_overview": f"Engagement delivers core architecture, test automation, and deployment pipelines for {client_name}.",
        "success_criteria_summary": "Client achieves verifiable milestone acceptance and validated delivery artifacts.",
        "delivery_objectives": ["Establish target architecture", "Execute milestone deliverables"],
        "success_criteria": ["Formal milestone acceptance sign-off", "100% deliverables verified"],
        "high_level_scope": ["Architecture definition", "Core implementation", "Integration verification"],
        "exclusions": ["Hardware procurement", "Post-launch operational maintenance"],
        "key_deliverables_summary": ["DEL-01: Target Architecture Specification", "DEL-02: Core Platform Release"],
        "key_milestones_summary": [f"M1: Phase 1 Acceptance Gate (due {start_date or '2026-11-30'})"],
        "contract_type": contract_type,
        "governance_tier": governance_tier,
        "delivery_model": "Toptal Talent Team (Agile/Milestone Hybrid)",
        "governance_model": f"PMO {governance_tier} Tier Governance Model",
        "major_startup_risks": ["Resource availability during initial sprint; mitigated by staffing lead time."],
        "delivery_manager": "Sarah Connor",
        "talent_pm": "John Matrix",
        "pmo_lead": "Alex PMO",
    }
    if "charter" in overrides:
        if isinstance(overrides["charter"], dict):
            charter_kwargs.update(overrides.pop("charter"))
            charter = ProjectStartupCharter(**charter_kwargs)
        else:
            charter = overrides.pop("charter")
    else:
        charter = ProjectStartupCharter(**charter_kwargs)

    gov_ctx = overrides.pop("governance_context", None) or GovernanceContext(
        project_name=project_name,
        client_name=client_name,
        contract_type=contract_type,
        governance_tier=governance_tier,
        sow_title=sow_title,
        sow_effective_date=start_date.isoformat() if start_date else "2026-11-02",
    )

    sow_interp_kwargs: Dict[str, Any] = {
        "contracted_deliverables": ["DEL-01", "DEL-02"],
        "out_of_scope_items": ["Production infrastructure hosting", "Third-party license procurement"],
        "customer_obligations": ["Provide access to staging environments and SMEs within 3 business days"],
        "assumptions": ["Standard cloud IAM access provided prior to sprint start"],
        "constraints": ["Milestone completion required within SOW schedule"],
        "platform_environment_commitments": ["Staging environment available for integration testing"],
        "dependencies": ["Client technical lead availability for weekly sync"],
        "approval_expectations": "Formal written sign-off within 5 business days of deliverable submission",
        "acceptance_process_narrative": (
            "Inputs ready: Environment access and SME availability verified.\n"
            "Execution: Work outputs delivered per milestone schedule.\n"
            "Submission: Formal completion notice delivered to client approver.\n"
            "Review: Client evaluates outputs within 5 business days.\n"
            "Deemed accepted: Absence of written notice within 5 business days constitutes acceptance.\n"
            "Triage: Non-conformances communicated in writing with required remediation details.\n"
            "Remediation: Supplier modifies output using commercially reasonable efforts.\n"
            "Rework limit: SOW terminable after 3 repeated un-remedied attempts.\n"
            "Sign-off and invoicing: Acceptance sign-off triggers milestone invoice."
        ),
        "ambiguity_notes": [],
        "confirmation_required_items": [],
    }
    if "sow_interpretation" in overrides:
        if isinstance(overrides["sow_interpretation"], dict):
            sow_interp_kwargs.update(overrides.pop("sow_interpretation"))
            sow_interp = SOWInterpretationSummary(**sow_interp_kwargs)
        else:
            sow_interp = overrides.pop("sow_interpretation")
    else:
        sow_interp = SOWInterpretationSummary(**sow_interp_kwargs)

    default_deliverables = [
        Deliverable(
            id="DEL-01",
            name="Target Architecture Specification",
            description="Comprehensive target-state cloud architecture design and component specifications.",
            acceptance_criteria=["Architecture addresses in-scope components", "Trade-offs and interface specs documented"],
            submission_target_date=start_date.isoformat() if start_date else "2026-11-15",
            review_window="5 business days",
            client_approver="Evelyn Napier (Client Contact)",
        ),
        Deliverable(
            id="DEL-02",
            name="Core Platform Release",
            description="Initial containerized application release deployed to staging.",
            acceptance_criteria=["Automated test suite achieves ≥ 90% pass rate", "Deployment runbook validated"],
            submission_target_date=start_date.isoformat() if start_date else "2026-11-30",
            review_window="5 business days",
            client_approver="Evelyn Napier (Client Contact)",
        ),
    ]

    default_milestones = [
        Milestone(
            id="MS-01",
            description="Milestone 1: Phase 1 Acceptance Gate",
            external_date=start_date or date(2026, 11, 30),
            linked_deliverables="DEL-01, DEL-02",
            critical_path_assumptions=["Fee invoiced upon formal acceptance."],
        )
    ]

    baseline_kwargs: Dict[str, Any] = {
        "project_name": project_name,
        "governance_tier": governance_tier,
        "contract_type": contract_type,
        "governance_context": gov_ctx,
        "charter": charter,
        "sow_interpretation": sow_interp,
        "deliverables": overrides.pop("deliverables", default_deliverables),
        "milestones": overrides.pop("milestones", default_milestones),
        "interim_checkpoints": overrides.pop("interim_checkpoints", []),
        "backlog_seed": overrides.pop("backlog_seed", []),
        "dependencies_assumptions": overrides.pop("dependencies_assumptions", []),
        "raid_items": overrides.pop("raid_items", [
            RiskAssumption(
                id="RA-01",
                category="Risk",
                description="Third-party API specification changes may impact integration timeline.",
                impact="Medium",
                mitigation="Lock API contract schemas in Week 1.",
                owner="Technical Lead",
            )
        ]),
        "decisions": overrides.pop("decisions", []),
        "communications_plan": overrides.pop("communications_plan", [
            CommunicationsPlanItem(
                id="COM-01",
                name="Weekly Delivery Sync",
                cadence="Weekly",
                audience="Project Team",
                content_owner="Talent PM",
            )
        ]),
        "stakeholders": overrides.pop("stakeholders", [
            Stakeholder(
                name="Evelyn Napier",
                role="Client Executive Sponsor",
                organization="Client",
                decision_rights="Signs off on milestone deliverables and budget",
            )
        ]),
        "raci_matrix": overrides.pop("raci_matrix", []),
        "readiness_checklist": overrides.pop("readiness_checklist", []),
        "action_required_items": overrides.pop("action_required_items", []),
        "open_questions": overrides.pop("open_questions", []),
        "contract_ambiguities": overrides.pop("contract_ambiguities", []),
        "sow_stories_catalogue": overrides.pop("sow_stories_catalogue", []),
        "author_name": "Alex PMO",
        "approver_name": "Alex PMO",
    }
    baseline_kwargs.update(overrides)

    baseline = StartupKitBaseline(**baseline_kwargs)
    validate_and_repair_baseline(baseline)
    return baseline
