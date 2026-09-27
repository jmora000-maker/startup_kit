"""Baseline aggregator and business rules engine."""

import logging
from datetime import timedelta, date
from typing import List, Optional, Set
from src.core.models import (
    CharterExtraction,
    DeliverablesExtraction,
    MilestonesExtraction,
    RAIDExtraction,
    QuestionsExtraction,
    SOWInterpretationExtraction,
    ScopeDecompositionExtraction,
    AcceptanceProcessExtraction,
    StakeholdersExtraction,
    CommunicationsExtraction,
    CommercialGuardrailsExtraction,
    TalentOnboardingExtraction,
    DecisionsExtraction,
    GovernanceContext,
    StartupKitBaseline,
    ProjectStartupCharter,
    SOWInterpretationSummary,
    Deliverable,
    Milestone,
    RiskAssumption,
    DependencyAssumptionItem,
    DecisionItem,
    WorkPackageSeed,
    CommunicationsPlanItem,
    Stakeholder,
    RACIItem,
    CommercialGuardrail,
    TalentOnboardingRecord,
    TalentMember,
    ReadinessChecklistItem,
    GateDecision,
    SourceReference,
    ContractAmbiguityItem,
    ContractConflictsExtraction,
    ReadinessWorkflowState,
)

logger = logging.getLogger(__name__)


class BaselineAggregator:
    """Aggregates intermediate domain extractions and enforces PMO startup business rules."""

    def aggregate(
        self,
        charter: CharterExtraction,
        deliverables_ext: DeliverablesExtraction,
        milestones_ext: MilestonesExtraction,
        raid_ext: RAIDExtraction,
        questions_ext: Optional[QuestionsExtraction] = None,
        sow_interpretation_ext: Optional[SOWInterpretationExtraction] = None,
        backlog_ext: Optional[ScopeDecompositionExtraction] = None,
        acceptance_ext: Optional[AcceptanceProcessExtraction] = None,
        stakeholders_ext: Optional[StakeholdersExtraction] = None,
        communications_ext: Optional[CommunicationsExtraction] = None,
        commercial_ext: Optional[CommercialGuardrailsExtraction] = None,
        talent_ext: Optional[TalentOnboardingExtraction] = None,
        decisions_ext: Optional[DecisionsExtraction] = None,
        conflicts_ext: Optional[ContractConflictsExtraction] = None,
        sow_awarded_date: Optional[date] = None,
        kit_drafted_date: Optional[date] = None,
    ) -> StartupKitBaseline:
        """Combine extractions and apply validation and business rules."""
        questions: List[str] = list(questions_ext.open_questions) if questions_ext else []
        seen_questions: Set[str] = set(questions)

        def add_question(q: str):
            if q not in seen_questions:
                seen_questions.add(q)
                questions.append(q)

        # 1. Process Deliverables and check acceptance criteria & ownership
        deliverables: List[Deliverable] = [d.model_copy() for d in deliverables_ext.deliverables]
        for deliv in deliverables:
            if not deliv.acceptance_criteria:
                deliv.acceptance_criteria = None
                add_question(
                    f"Deliverable '{deliv.id}: {deliv.description}' is missing explicit contractual acceptance criteria. [CONFIRMATION REQUIRED]"
                )
            if not deliv.owner or deliv.owner in ("Unassigned", "[UNASSIGNED - TO BE CONFIRMED]"):
                deliv.owner = "[UNASSIGNED - TO BE CONFIRMED]"
                add_question(
                    f"Deliverable '{deliv.id}: {deliv.description}' owner is unassigned. [CONFIRMATION REQUIRED]"
                )
            if deliv.source_reference and deliv.source_reference.confidence_score < 0.7:
                add_question(
                    f"[Low Confidence: {deliv.source_reference.confidence_score:.2f}] Review deliverable '{deliv.id}' extracted from {deliv.source_reference.document_name} ({deliv.source_reference.clause_or_slide or 'N/A'})."
                )

        # 2. Process Milestones and calculate internal buffers if needed
        milestones: List[Milestone] = [m.model_copy() for m in milestones_ext.milestones]
        buffer_days = 7
        if charter.governance_tier == "Elevated":
            buffer_days = 10
        elif charter.governance_tier == "Guided":
            buffer_days = 3

        for ms in milestones:
            if ms.external_date is None:
                add_question(
                    f"Milestone '{ms.id}: {ms.description}' has no committed external delivery date. [CONFIRMATION REQUIRED]"
                )
            elif ms.internal_buffer_date is None:
                ms.internal_buffer_date = ms.external_date - timedelta(days=buffer_days)

            if ms.source_reference and ms.source_reference.confidence_score < 0.7:
                add_question(
                    f"[Low Confidence: {ms.source_reference.confidence_score:.2f}] Review milestone '{ms.id}' extracted from {ms.source_reference.document_name} ({ms.source_reference.clause_or_slide or 'N/A'})."
                )

        # 3. Separate RAID, Dependencies/Assumptions, and Decisions
        raw_raid_items = [r.model_copy() for r in raid_ext.items]
        raid_items: List[RiskAssumption] = []
        dependencies_assumptions: List[DependencyAssumptionItem] = []

        dep_idx = 1
        asm_idx = 1
        for item in raw_raid_items:
            if item.source_reference and item.source_reference.confidence_score < 0.7:
                add_question(
                    f"[Low Confidence: {item.source_reference.confidence_score:.2f}] Review {item.type} '{item.description}' extracted from {item.source_reference.document_name}."
                )

            if item.type in ("Dependency", "Assumption"):
                item_id = f"DEP-{dep_idx:02d}" if item.type == "Dependency" else f"ASM-{asm_idx:02d}"
                if item.type == "Dependency":
                    dep_idx += 1
                else:
                    asm_idx += 1

                da_item = DependencyAssumptionItem(
                    id=item_id,
                    type=item.type,
                    description=item.description,
                    category=item.category if hasattr(item, "category") and item.category else "Technical",
                    source_reference=item.source_reference,
                    owner=item.owner if item.owner != "Unassigned" else "[UNASSIGNED - TO BE CONFIRMED]",
                    status=item.status or "Open",
                    impact_if_unmet="Delivery delay / milestone impediment",
                    escalation_trigger="Milestone slip or unconfirmed prerequisite",
                    linked_milestone=milestones[0].id if milestones else None,
                    linked_deliverable=deliverables[0].id if deliverables else None,
                )
                dependencies_assumptions.append(da_item)
            else:
                # Risk or Issue remains in RAID Log
                raid_items.append(item)

        # 4. Process Contract Ambiguities & Conflicts (NFR-02)
        contract_ambiguities: List[ContractAmbiguityItem] = []
        if conflicts_ext and conflicts_ext.ambiguities:
            contract_ambiguities = list(conflicts_ext.ambiguities)
        elif sow_interpretation_ext and sow_interpretation_ext.ambiguity_notes:
            for idx, note in enumerate(sow_interpretation_ext.ambiguity_notes):
                contract_ambiguities.append(
                    ContractAmbiguityItem(
                        anomaly_id=f"AMB-{idx+1:02d}",
                        category="Scope Contradiction",
                        conflicting_clauses=note,
                        risk_impact="Potential scope creep or delivery friction during execution",
                        recommended_clarification=f"Clarify and align terms for: {note}",
                        status="Open",
                        source_reference=charter.source_reference
                    )
                )

        # Automatically link detected conflicts to open questions and RAID risks
        for ambiguity in contract_ambiguities:
            add_question(f"[{ambiguity.anomaly_id}] {ambiguity.recommended_clarification}")
            if not any(ambiguity.anomaly_id in r.description for r in raid_items):
                raid_items.append(
                    RiskAssumption(
                        type="Risk",
                        description=f"Contractual Ambiguity ({ambiguity.anomaly_id}): {ambiguity.conflicting_clauses}",
                        owner="PMO Lead",
                        status="Open",
                        source_reference=ambiguity.source_reference or charter.source_reference,
                        category="Commercial",
                        impact="High" if "date" in ambiguity.category.lower() or "scope" in ambiguity.category.lower() else "Medium",
                        severity="High" if "date" in ambiguity.category.lower() else "Medium",
                        trigger_or_early_warning="Discrepancy identified during Startup Kit Readiness audit",
                        mitigation_or_response=f"Clarify with Sales / Client: {ambiguity.recommended_clarification}"
                    )
                )

        # 5. Process Decisions
        decisions: List[DecisionItem] = []
        if decisions_ext and decisions_ext.decisions:
            decisions = list(decisions_ext.decisions)
        else:
            decisions = [
                DecisionItem(
                    id="DEC-01",
                    decision_text=f"Project Governance Tier baselined as '{charter.governance_tier}' with standard PMO cadence.",
                    decision_owner=charter.pmo_lead or "[UNASSIGNED - TO BE CONFIRMED]",
                    status="Approved",
                    rationale="Assigned based on project scope, contract model, and risk profile.",
                    source_reference=charter.source_reference
                ),
                DecisionItem(
                    id="DEC-02",
                    decision_text=f"Contract baseline established under '{charter.contract_type}' terms.",
                    decision_owner=charter.delivery_manager or "Delivery Manager",
                    status="Approved",
                    rationale="Aligned to signed Statement of Work and commercial boundaries.",
                    source_reference=charter.source_reference
                )
            ]

        # 6. Check role assignments
        if not charter.delivery_manager or charter.delivery_manager == "[UNASSIGNED - TO BE CONFIRMED]":
            add_question("Delivery Manager role is unassigned. [CONFIRMATION REQUIRED]")
        if not charter.talent_pm or charter.talent_pm == "[UNASSIGNED - TO BE CONFIRMED]":
            add_question("Talent PM role is unassigned. [CONFIRMATION REQUIRED]")
        if not charter.pmo_lead or charter.pmo_lead == "[UNASSIGNED - TO BE CONFIRMED]":
            add_question("PMO Lead role is unassigned. [CONFIRMATION REQUIRED]")

        # 7. Build Project Startup Charter (Layer 1)
        charter_obj = ProjectStartupCharter(
            project_name=charter.project_name or "Project Baseline",
            client_name=charter.client_name,
            project_purpose=charter.project_purpose or charter.executive_summary or "[CONFIRMATION REQUIRED]",
            delivery_objectives=charter.delivery_objectives or [
                f"Successfully deliver and validate {d.name or d.description}" for d in deliverables[:4]
            ],
            success_criteria=charter.success_criteria or [
                "Contractual deliverables accepted by designated client sponsor within review window",
                "Milestone delivery achieved within agreed external dates and internal buffers",
                "Adherence to Toptal PMO governance cadence and commercial margin guardrails"
            ],
            high_level_scope=charter.high_level_scope or [d.name or d.description for d in deliverables],
            exclusions=charter.exclusions or [
                "Custom infrastructure outside documented cloud provider scope",
                "Unapproved out-of-scope feature requests without formal Change Order"
            ],
            key_deliverables_summary=[f"{d.id}: {d.name or d.description}" for d in deliverables],
            key_milestones_summary=[
                f"{m.id}: {m.description} ({m.external_date.strftime('%Y-%m-%d') if m.external_date else '[DATE TBD]'})"
                for m in milestones
            ],
            contract_type=charter.contract_type,
            governance_tier=charter.governance_tier,
            delivery_model="Toptal Talent Team (Agile/Milestone Hybrid)",
            governance_model=f"PMO {charter.governance_tier} Tier Governance Model",
            major_startup_risks=[r.description for r in raid_items if r.type == "Risk"][:3] or [
                "Client access provisioning and environment availability delays",
                "Timely client feedback and deliverable sign-off turnaround"
            ],
            delivery_manager=charter.delivery_manager or "[UNASSIGNED - TO BE CONFIRMED]",
            talent_pm=charter.talent_pm or "[UNASSIGNED - TO BE CONFIRMED]",
            pmo_lead=charter.pmo_lead or "[UNASSIGNED - TO BE CONFIRMED]",
            escalation_path="Talent PM / Delivery Manager -> PMO Lead -> Director, PMO",
            unresolved_assumptions_status=(
                f"{len(dependencies_assumptions)} dependencies/assumptions logged, awaiting mobilization validation"
                if dependencies_assumptions else "No critical open assumptions"
            ),
            source_reference=charter.source_reference
        )

        # 8. Build SOW Interpretation Summary (Layer 1)
        if sow_interpretation_ext:
            sow_summary = SOWInterpretationSummary(
                contracted_deliverables=sow_interpretation_ext.contracted_deliverables or [d.name or d.description for d in deliverables],
                out_of_scope_items=sow_interpretation_ext.out_of_scope_items or charter_obj.exclusions,
                customer_obligations=sow_interpretation_ext.customer_obligations or [
                    "Provision cloud accounts, IAM roles, and environment access",
                    "Timely review and formal sign-offs within agreed review window",
                    "Provide technical architecture specifications and sample datasets"
                ],
                assumptions=sow_interpretation_ext.assumptions or [da.description for da in dependencies_assumptions if da.type == "Assumption"],
                constraints=sow_interpretation_ext.constraints or [
                    f"Governance tier cadence: {charter.governance_tier}",
                    f"Contractual model: {charter.contract_type}"
                ],
                platform_environment_commitments=sow_interpretation_ext.platform_environment_commitments or [
                    "[UNDEFINED]"
                ],
                dependencies=sow_interpretation_ext.dependencies or [da.description for da in dependencies_assumptions if da.type == "Dependency"],
                approval_expectations=sow_interpretation_ext.approval_expectations or "Written sign-off by Client Approver within 5 business days of submission.",
                ambiguity_notes=sow_interpretation_ext.ambiguity_notes or [q for q in questions if "[CONFIRMATION REQUIRED]" in q],
                confirmation_required_items=[q for q in questions if "[CONFIRMATION REQUIRED]" in q],
                contract_ambiguities=contract_ambiguities,
                source_reference=sow_interpretation_ext.source_reference or charter.source_reference
            )
        else:
            sow_summary = SOWInterpretationSummary(
                contracted_deliverables=[d.name or d.description for d in deliverables],
                out_of_scope_items=charter_obj.exclusions,
                customer_obligations=[
                    "Provision cloud accounts, IAM roles, and environment access",
                    "Timely review and formal sign-offs within agreed review window",
                    "Provide technical architecture specifications and sample datasets"
                ],
                assumptions=[da.description for da in dependencies_assumptions if da.type == "Assumption"] or [
                    "Standard working hours and remote talent team execution",
                    "Client environment availability in advance of milestone execution"
                ],
                constraints=[
                    f"Governance tier cadence: {charter.governance_tier}",
                    f"Contractual model: {charter.contract_type}"
                ],
                platform_environment_commitments=[
                    "[UNDEFINED]"
                ],
                dependencies=[da.description for da in dependencies_assumptions if da.type == "Dependency"] or [
                    "Third-party API access tokens and enterprise credentials",
                    "Architecture review board sign-off"
                ],
                approval_expectations="Written sign-off by Client Approver within 5 business days of submission.",
                ambiguity_notes=[q for q in questions if "[CONFIRMATION REQUIRED]" in q],
                confirmation_required_items=[q for q in questions if "[CONFIRMATION REQUIRED]" in q],
                contract_ambiguities=contract_ambiguities,
                source_reference=charter.source_reference
            )

        # 9. Build Scope Decomposition / Backlog Seed (Layer 2)
        backlog_seed: List[WorkPackageSeed] = []
        if backlog_ext and backlog_ext.work_packages:
            backlog_seed = list(backlog_ext.work_packages)
        else:
            for i, deliv in enumerate(deliverables):
                wp = WorkPackageSeed(
                    id=f"WP-{i+1:02d}",
                    parent_deliverable_id=deliv.id,
                    title=f"Work Package: {deliv.name or deliv.description}",
                    description=f"Decomposition and implementation tasks for {deliv.id}.",
                    preliminary_sequence=i + 1,
                    owner=deliv.owner if deliv.owner != "Unassigned" else "[UNASSIGNED - TO BE CONFIRMED]",
                    dependency_references=[da.id for da in dependencies_assumptions[:2]],
                    linked_milestones=[m.id for m in milestones[:1]],
                    linked_acceptance_items=[deliv.acceptance_criteria or "[CONFIRMATION REQUIRED]"],
                    uncertain_scope=deliv.acceptance_criteria is None,
                    status="Draft"
                )
                backlog_seed.append(wp)

        # 10. Build Communications Plan (Layer 2)
        communications_plan: List[CommunicationsPlanItem] = []
        if communications_ext and communications_ext.communications:
            communications_plan = list(communications_ext.communications)
        else:
            communications_plan = [
                CommunicationsPlanItem(
                    id="COM-01",
                    name="Weekly Check-in (30 min)",
                    audience="Talent PM, Delivery Manager, PMO Lead",
                    content_owner=charter.talent_pm or "Talent PM",
                    cadence="Weekly (30 min)",
                    governance_tier_applicability="All Tiers",
                    format="Virtual Meeting",
                    delivery_day="Every Tuesday",
                    escalation_route="PMO Lead -> Director, PMO",
                    pmo_health_rating_notes="Evidence is exchanged at the weekly check-in; PMO Lead assesses project health."
                ),
                CommunicationsPlanItem(
                    id="COM-02",
                    name="Weekly Project Status Report (PSR)",
                    audience="Client Sponsor, Delivery Manager, PMO Lead",
                    content_owner=charter.talent_pm or "Talent PM",
                    cadence="Weekly",
                    governance_tier_applicability="All Tiers",
                    format="Written Report (Email / Portal)",
                    delivery_day="Every Friday COB",
                    escalation_route="PMO Lead -> Director, PMO",
                    pmo_health_rating_notes="PMO Lead independently issues health rating before executive distribution."
                )
            ]
            if charter.governance_tier in ("Partnered", "Elevated"):
                communications_plan.append(
                    CommunicationsPlanItem(
                        id="COM-03",
                        name="Monthly / Quarterly Business Review (MBR/QBR - G-07)",
                        audience="Executive Sponsors, Director PMO, Client VP",
                        content_owner=charter.delivery_manager or "Delivery Manager",
                        cadence="Monthly",
                        governance_tier_applicability="Partnered, Elevated",
                        format="Executive Presentation Deck",
                        delivery_day="Last Thursday of Month",
                        escalation_route="Director, PMO",
                        pmo_health_rating_notes="Strategic governance, milestone progress, and budget burndown review."
                    )
                )
            if charter.governance_tier == "Elevated":
                communications_plan.append(
                    CommunicationsPlanItem(
                        id="COM-04",
                        name="Daily Standup & Blocker Sync",
                        audience="Delivery Team, Talent PM, Tech Lead",
                        content_owner=charter.talent_pm or "Talent PM",
                        cadence="Daily (15 min)",
                        governance_tier_applicability="Elevated",
                        format="Virtual Standup",
                        delivery_day="Monday - Friday",
                        escalation_route="Talent PM -> Delivery Manager",
                        pmo_health_rating_notes="Immediate impediment clearing and blocker escalation."
                    )
                )

        # 11. Build Stakeholder Model and RACI Matrix (Layer 3 - including PMO)
        pmo_lead_name = charter.pmo_lead or "[UNASSIGNED - TO BE CONFIRMED]"
        dir_pmo_name = "Director, PMO"

        stakeholders: List[Stakeholder] = []
        if stakeholders_ext and stakeholders_ext.stakeholders:
            stakeholders = list(stakeholders_ext.stakeholders)
            # Ensure PMO Lead and Director, PMO exist
            has_pmo = any("pmo lead" in s.role.lower() for s in stakeholders)
            has_dir = any("director" in s.role.lower() and "pmo" in s.role.lower() for s in stakeholders)
            if not has_pmo:
                stakeholders.insert(0, Stakeholder(
                    name=pmo_lead_name,
                    role="PMO Lead",
                    organization="Toptal PMO",
                    decision_rights="G-01 Gate Sign-off, Talent Staffing/Replacement, Work-at-Risk Approvals, Delivery Risk & Recovery",
                    approver_responsibilities="G-01 Gate, Baseline Exceptions, PMO Health Ratings, Talent Baseline Sign-off",
                    escalation_responsibility="Director, PMO",
                    reporting_accountability="Independent Weekly Health Rating, Leadership Rollup"
                ))
            if not has_dir:
                stakeholders.insert(1, Stakeholder(
                    name=dir_pmo_name,
                    role="Director, PMO",
                    organization="Toptal PMO Leadership",
                    decision_rights="Elevated Tier Approvals, Major Commercial Exception Sign-offs, Executive Escalations",
                    approver_responsibilities="Elevated Tier G-01 Concurrence, Governance Policy Exceptions",
                    escalation_responsibility="VP, Delivery / Executive Leadership",
                    reporting_accountability="Executive PMO Portfolio Review"
                ))
        else:
            stakeholders = [
                Stakeholder(
                    name=pmo_lead_name,
                    role="PMO Lead",
                    organization="Toptal PMO",
                    decision_rights="G-01 Gate Sign-off, Talent Staffing/Replacement, Work-at-Risk Approvals, Delivery Risk & Recovery",
                    approver_responsibilities="G-01 Gate, Baseline Exceptions, PMO Health Ratings, Talent Baseline Sign-off",
                    escalation_responsibility="Director, PMO",
                    reporting_accountability="Independent Weekly Health Rating, Leadership Rollup"
                ),
                Stakeholder(
                    name=dir_pmo_name,
                    role="Director, PMO",
                    organization="Toptal PMO Leadership",
                    decision_rights="Elevated Tier Approvals, Major Commercial Exception Sign-offs, Executive Escalations",
                    approver_responsibilities="Elevated Tier G-01 Concurrence, Governance Policy Exceptions",
                    escalation_responsibility="VP, Delivery / Executive Leadership",
                    reporting_accountability="Executive PMO Portfolio Review"
                ),
                Stakeholder(
                    name=charter.delivery_manager or "[UNASSIGNED - TO BE CONFIRMED]",
                    role="Delivery Manager",
                    organization="Toptal",
                    decision_rights="Voice of the customer, scope accountability, client alignment",
                    approver_responsibilities="Scope change alignment, handoff readiness",
                    escalation_responsibility="PMO Lead",
                    reporting_accountability="Weekly PSR Review"
                ),
                Stakeholder(
                    name=charter.talent_pm or "[UNASSIGNED - TO BE CONFIRMED]",
                    role="Talent PM",
                    organization="Toptal",
                    decision_rights="Project delivery, sprint coordination, day-to-day execution",
                    approver_responsibilities="Work package progress, deliverable submission drafts",
                    escalation_responsibility="Delivery Manager",
                    reporting_accountability="Weekly PSR Author"
                ),
                Stakeholder(
                    name=charter.client_name or "[CLIENT SPONSOR - TO BE CONFIRMED]",
                    role="Client Sponsor / Approver",
                    organization="Client",
                    decision_rights="Contractual approvals, deliverable sign-offs, change orders",
                    approver_responsibilities="Deliverables acceptance, SOW amendments",
                    escalation_responsibility="Client Executive Leadership",
                    reporting_accountability="Recipient of Weekly PSR & MBR"
                )
            ]

        raci_matrix = [
            RACIItem(decision_or_activity="Startup readiness (G-01 gate)", pmo_lead="R, A", delivery_manager="C", talent_pm="C", sales_accounts="C", client="I"),
            RACIItem(decision_or_activity="Talent staffing & replacement", pmo_lead="R, A", delivery_manager="C", talent_pm="C", sales_accounts="C", client="I"),
            RACIItem(decision_or_activity="Work at risk / commercial exceptions", pmo_lead="R, A", delivery_manager="I", talent_pm="I", sales_accounts="C", client="I"),
            RACIItem(decision_or_activity="Scope & change", pmo_lead="R", delivery_manager="A", talent_pm="—", sales_accounts="C, R", client="A"),
            RACIItem(decision_or_activity="Delivery risk & recovery", pmo_lead="R, A", delivery_manager="C", talent_pm="R", sales_accounts="I", client="I"),
        ]

        # 12. Build Commercial Guardrails (Layer 3)
        if commercial_ext and commercial_ext.commercial_guardrails:
            commercial_guardrails = commercial_ext.commercial_guardrails
        elif charter.contract_type == "Fixed Bid":
            commercial_guardrails = CommercialGuardrail(
                contract_type_implication="Fixed Bid contract: Strict scope boundary controls, deliverable acceptance precision, and milestone contingency buffers are mandatory to protect margin.",
                billing_consumption_assumption="Invoicing tied strictly to formal client milestone acceptance sign-offs.",
                staffing_assumption="Fixed capacity and sprint budget allocations; headcount increases require formal SOW amendment.",
                commercial_exposure_note="Delivery delays directly erode project margin. Scope creep without Change Order is prohibited.",
                approved_work_rule="Only explicitly contracted SOW deliverables and approved Change Orders are authorized for execution.",
                non_approved_work_rule="Zero execution of out-of-scope requests without executed Change Order.",
                work_at_risk_rule="Work-at-risk strictly forbidden on Fixed Bid without written PMO Lead and Director sign-off.",
                change_control_trigger="Any requirement change, client delay > 3 days, or deliverable rework exceeding standard window.",
                change_order_route="PMO Lead leads -> DM aligns client -> Client approves -> Contracting issues change order.",
                budget_baseline="[CONFIRMATION REQUIRED - CONTRACT FIXED PRICE]",
                variance_indicator="Green (<5% variance)",
                margin_risk_indicator="Medium" if charter.governance_tier == "Elevated" else "Low",
                escalation_threshold="Milestone slip > 3 days or rework effort > 10% of deliverable budget."
            )
        else:
            commercial_guardrails = CommercialGuardrail(
                contract_type_implication="Time and Materials contract: Emphasizes burn visibility, weekly timesheet oversight, staffing allocation efficiency, and customer dependency tracking.",
                billing_consumption_assumption="Weekly timesheet approval and hourly/daily burn rate tracking against budget cap.",
                staffing_assumption="Dedicated talent staffing as agreed in SOW; rate card billing per active role.",
                commercial_exposure_note="Client dependency delays must be logged immediately to prevent unfunded team standby burn.",
                approved_work_rule="Work executed according to prioritized backlog agreed in weekly check-ins.",
                non_approved_work_rule="Tasks exceeding agreed monthly burn ceiling require client written authorization.",
                work_at_risk_rule="Work-at-risk requires PMO Lead confirmation if PO or budget ceiling is exhausted.",
                change_control_trigger="Budget burndown exceeding forecast by >10% or scope change requiring talent roster adjustments.",
                change_order_route="PMO Lead leads -> DM aligns client -> Client approves -> Contracting issues change order.",
                budget_baseline="[CONFIRMATION REQUIRED - T&M BUDGET CAP]",
                variance_indicator="Green (<5% variance)",
                margin_risk_indicator="Low",
                escalation_threshold="Burn rate variance > 10% or client dependency blocker > 2 days."
            )

        # 13. Build Talent Onboarding Record (Layer 3)
        if talent_ext and talent_ext.talent_onboarding:
            talent_onboarding = talent_ext.talent_onboarding
        else:
            talent_onboarding = TalentOnboardingRecord(
                talent_pm=charter.talent_pm or "[UNASSIGNED - TO BE CONFIRMED]",
                delivery_manager=charter.delivery_manager or "[UNASSIGNED - TO BE CONFIRMED]",
                pmo_lead=pmo_lead_name,
                onboarding_completion_date=None,
                onboarding_attendees=[
                    pmo_lead_name,
                    charter.delivery_manager or "Delivery Manager",
                    charter.talent_pm or "Talent PM"
                ],
                artifacts_walked_through=[
                    "Startup Readiness Checklist (G-01)",
                    "Project Startup Charter",
                    "SOW Interpretation Summary & Contract Ambiguities",
                    "Milestone Delivery Plan",
                    "Scope Decomposition / Backlog Seed",
                    "Deliverables and Acceptance Matrix",
                    "Dependency and Assumption Log",
                    "RAID Log & Decision Log Seed",
                    "Communications and Reporting Plan",
                    "Stakeholder and Responsibility Model (including PMO)",
                    "RACI / Decision Rights Matrix",
                    "Commercial and Margin Guardrails"
                ],
                delivery_talent_roster=[
                    TalentMember(
                        role="Delivery Manager",
                        name=charter.delivery_manager or "[UNASSIGNED - TO BE CONFIRMED]",
                        required_skills="Delivery Governance, Client Management",
                        status="Confirmed" if charter.delivery_manager and "UNASSIGNED" not in charter.delivery_manager else "Staffing Required"
                    ),
                    TalentMember(
                        role="Talent PM",
                        name=charter.talent_pm or "[UNASSIGNED - TO BE CONFIRMED]",
                        required_skills="Agile Coordination, PMO Delivery",
                        status="Confirmed" if charter.talent_pm and "UNASSIGNED" not in charter.talent_pm else "Staffing Required"
                    ),
                    TalentMember(
                        role="Technical Lead / Senior Engineer",
                        name="[UNASSIGNED - TO BE CONFIRMED]",
                        required_skills="Architecture, Cloud Infrastructure, CI/CD",
                        status="Staffing Required"
                    )
                ],
                required_roles=["Delivery Manager", "Talent PM", "Technical Lead / Senior Engineer"],
                required_skills=["Cloud Architecture", "Agile Execution", "DevOps / CI/CD", "Stakeholder Governance"],
                staffing_gaps=[
                    "Delivery team staffing roster to be confirmed during Readiness."
                ] if any("UNASSIGNED" in str(x) for x in [charter.delivery_manager, charter.talent_pm]) else [],
                replacement_plan="PMO Lead coordinates talent matching within 5 business days if replacement needed.",
                team_baseline_review_confirmation=True
            )

        # 14. 1-Day Creation SLA Tracking & Segregation of Duties
        awarded_dt = sow_awarded_date or (date.today() - timedelta(days=1))
        drafted_dt = kit_drafted_date or date.today()
        sla_met = (drafted_dt - awarded_dt).days <= 1

        author_name = pmo_lead_name
        dm_name = charter.delivery_manager or "Delivery Manager"
        tech_lead_name = "Technical Lead"
        reviewer_names = [dm_name, tech_lead_name]
        approver_name = author_name
        concurring_approver = dir_pmo_name if charter.governance_tier == "Elevated" else None
        segregation_verified = (author_name not in reviewer_names)

        # 15. Build G-01 Startup Readiness Checklist
        has_unconfirmed_delivs = any(d.acceptance_criteria is None for d in deliverables)
        has_unconfirmed_dates = any(m.external_date is None for m in milestones)
        has_unassigned_roles = any("UNASSIGNED" in str(x) for x in [charter.delivery_manager, charter.talent_pm])
        has_ambiguities = len(contract_ambiguities) > 0

        readiness_checklist = [
            ReadinessChecklistItem(
                item_id="G01-01",
                gate_criterion="Startup Kit created within 1 day of delivery handoff (SLA)",
                related_section4_artifact="Project Startup Charter",
                owner=author_name,
                status="Complete" if sla_met else "Exception Required",
                evidence=f"Startup Kit drafted on {drafted_dt.strftime('%Y-%m-%d')} (SOW awarded {awarded_dt.strftime('%Y-%m-%d')}). SLA {'Met' if sla_met else 'Breached'}.",
                exception_required=not sla_met,
                exception_details="Startup Kit creation exceeded 1 business day SLA." if not sla_met else None,
                approval_status="Approved" if sla_met else "Exception Required"
            ),
            ReadinessChecklistItem(
                item_id="G01-02",
                gate_criterion="Governance tier assigned and cadence established",
                related_section4_artifact="Project Startup Charter",
                owner=author_name,
                status="Complete",
                evidence=f"Governance Tier confirmed as '{charter.governance_tier}' with tailored buffers and reporting.",
                approval_status="Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-03",
                gate_criterion="SOW interpretation and contract scope baseline agreed",
                related_section4_artifact="SOW Interpretation Summary",
                owner=author_name,
                status="Review Required" if questions else "Complete",
                evidence=f"SOW deliverables ({len(deliverables)}), exclusions, obligations, and constraints mapped.",
                exception_required=bool(questions),
                exception_details="Open clarification questions pending Mobilize kickoff." if questions else None,
                approval_status="Pending Review" if questions else "Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-04",
                gate_criterion="Milestone delivery plan with external dates and internal buffers committed",
                related_section4_artifact="Milestone Delivery Plan",
                owner=dm_name,
                status="Confirmation Required" if has_unconfirmed_dates else "Complete",
                evidence=f"{len(milestones)} milestones mapped with external dates and internal buffer calculations.",
                exception_required=has_unconfirmed_dates,
                exception_details="Uncommitted milestone dates require client confirmation." if has_unconfirmed_dates else None,
                approval_status="Pending Confirmation" if has_unconfirmed_dates else "Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-05",
                gate_criterion="Scope decomposition and backlog seed created",
                related_section4_artifact="Scope Decomposition / Backlog Seed",
                owner=charter.talent_pm or "Talent PM",
                status="Complete",
                evidence=f"{len(backlog_seed)} work packages seeded from contracted deliverables.",
                approval_status="Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-06",
                gate_criterion="Deliverables mapped to owners with explicit acceptance routes",
                related_section4_artifact="Deliverables and Acceptance Matrix",
                owner=charter.talent_pm or "Talent PM",
                status="Review Required" if has_unconfirmed_delivs else "Complete",
                evidence=f"{len(deliverables)} deliverables mapped to acceptance routes and evidence expectations.",
                exception_required=has_unconfirmed_delivs,
                exception_details="Unstated acceptance criteria flagged for client confirmation." if has_unconfirmed_delivs else None,
                approval_status="Pending Review" if has_unconfirmed_delivs else "Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-07",
                gate_criterion="Critical dependencies and assumptions logged and owned",
                related_section4_artifact="Dependency and Assumption Log",
                owner=charter.talent_pm or "Talent PM",
                status="Complete",
                evidence=f"{len(dependencies_assumptions)} dependencies and assumptions logged and assigned.",
                approval_status="Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-08",
                gate_criterion="Top delivery and margin risks documented in RAID Log",
                related_section4_artifact="RAID Log",
                owner=dm_name,
                status="Complete",
                evidence=f"{len(raid_items)} risks/issues and {len(decisions)} decisions baselined.",
                approval_status="Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-09",
                gate_criterion="Communications and reporting cadence defined",
                related_section4_artifact="Communications and Reporting Plan",
                owner=charter.talent_pm or "Talent PM",
                status="Complete",
                evidence=f"Weekly check-in, weekly PSR, and MBR cadence defined for {charter.governance_tier} tier.",
                approval_status="Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-10",
                gate_criterion="Stakeholder map and escalation path baselined (including PMO)",
                related_section4_artifact="Stakeholder and Responsibility Model",
                owner=dm_name,
                status="Complete",
                evidence=f"{len(stakeholders)} key stakeholder roles (including PMO Lead & Director) and escalation paths identified.",
                approval_status="Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-11",
                gate_criterion="RACI and PMO decision rights matrix baselined",
                related_section4_artifact="RACI / Decision Rights Matrix",
                owner=author_name,
                status="Complete",
                evidence="Standard PMO decision rights and AR-10 accountability model baselined.",
                approval_status="Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-12",
                gate_criterion="Commercial guardrails and margin protections established",
                related_section4_artifact="Commercial and Margin Guardrails",
                owner=author_name,
                status="Complete",
                evidence=f"Commercial controls and work-at-risk rules defined for {charter.contract_type}.",
                approval_status="Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-13",
                gate_criterion="Talent PM, DM, and team onboarded using Startup Kit",
                related_section4_artifact="Talent Onboarding Record",
                owner=author_name,
                status="In Progress" if has_unassigned_roles else "Complete",
                evidence="Talent onboarding walkthrough session mapped against Section 4 artifacts.",
                exception_required=has_unassigned_roles,
                exception_details="Talent roster staffing in progress." if has_unassigned_roles else None,
                approval_status="Pending Review" if has_unassigned_roles else "Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-14",
                gate_criterion="Contractual ambiguities and conflicts logged with risk-impact mitigations",
                related_section4_artifact="SOW Interpretation Summary",
                owner=author_name,
                status="Review Required" if has_ambiguities else "Complete",
                evidence=f"{len(contract_ambiguities)} contractual ambiguities extracted with citations.",
                exception_required=has_ambiguities,
                exception_details="Contractual conflicts require alignment during sales handoff." if has_ambiguities else None,
                approval_status="Pending Review" if has_ambiguities else "Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-15",
                gate_criterion="Unresolved ambiguities and open questions listed",
                related_section4_artifact="Startup Readiness Checklist",
                owner=author_name,
                status="Review Required" if questions else "Complete",
                evidence=f"{len(questions)} validation points logged for mobilization confirmation.",
                approval_status="Pending Review" if questions else "Approved"
            ),
        ]

        # 16. Calculate Startup Readiness Score (NFR-04)
        status_points = {
            "Complete": 1.0,
            "Approved": 1.0,
            "Approved with Exception": 0.85,
            "In Progress": 0.5,
            "Review Required": 0.5,
            "Confirmation Required": 0.3,
            "Exception Required": 0.2,
            "Rework Required": 0.0,
            "Not Started": 0.0,
        }
        total_items = len(readiness_checklist)
        total_score_items = sum(status_points.get(item.status, 0.5) for item in readiness_checklist)
        dim1 = (total_score_items / total_items) if total_items > 0 else 0.0
        open_exceptions = [i for i in readiness_checklist if i.exception_required or i.status == "Exception Required"]
        dim1 = max(0.0, min(1.0, dim1 - (len(open_exceptions) * 0.03)))

        # 2. Deliverable & Acceptance Rigor (25% Weight)
        if deliverables:
            deliv_scores = []
            for d in deliverables:
                s = 0.0
                if d.acceptance_criteria and "[CONFIRMATION REQUIRED]" not in d.acceptance_criteria:
                    s += 0.4
                if d.owner and "UNASSIGNED" not in d.owner.upper() and d.owner != "Unassigned":
                    s += 0.3
                if d.client_approver and "UNASSIGNED" not in d.client_approver.upper():
                    s += 0.3
                deliv_scores.append(s)
            dim2 = sum(deliv_scores) / len(deliverables)
        else:
            dim2 = 0.0
        dim2 = max(0.0, min(1.0, dim2))

        # 3. Talent & Staffing Readiness (20% Weight)
        dim3 = 0.0
        if talent_onboarding:
            if talent_onboarding.delivery_manager and "UNASSIGNED" not in talent_onboarding.delivery_manager.upper():
                dim3 += 0.35
            if talent_onboarding.talent_pm and "UNASSIGNED" not in talent_onboarding.talent_pm.upper():
                dim3 += 0.35
            if talent_onboarding.delivery_talent_roster:
                confirmed_cnt = sum(1 for tm in talent_onboarding.delivery_talent_roster if tm.status == "Confirmed")
                dim3 += 0.30 * (confirmed_cnt / len(talent_onboarding.delivery_talent_roster))
            else:
                dim3 += 0.15
        dim3 = max(0.0, min(1.0, dim3))

        # 4. Commercial & Risk Mitigation (15% Weight)
        dim4 = 0.0
        if raid_items:
            owned_risks = sum(1 for r in raid_items if r.owner and "UNASSIGNED" not in r.owner.upper() and r.owner != "Unassigned")
            dim4 += 0.40 * min(1.0, (owned_risks / max(1, len(raid_items))))
        else:
            dim4 += 0.20
        if commercial_guardrails:
            dim4 += 0.30
        q_penalty = max(0.0, 1.0 - (len(questions) * 0.05))
        dim4 += 0.30 * q_penalty
        dim4 = max(0.0, min(1.0, dim4))

        composite_score = round((dim1 * 0.40 + dim2 * 0.25 + dim3 * 0.20 + dim4 * 0.15) * 100, 1)
        readiness_breakdown = {
            "mandatory_g01_controls": round(dim1 * 100, 1),
            "deliverable_acceptance_rigor": round(dim2 * 100, 1),
            "talent_staffing_readiness": round(dim3 * 100, 1),
            "commercial_risk_mitigation": round(dim4 * 100, 1),
        }

        # 17. Gate Decision and Workflow State
        if composite_score >= 85.0 and not open_exceptions:
            gate_status = "Approved for Mobilize"
            workflow_state: ReadinessWorkflowState = "Ready for G-01 Gate Review"
        elif open_exceptions or composite_score >= 70.0:
            gate_status = "Approved with Exception"
            workflow_state = "Approved with Exception" if not questions else "Ready for G-01 Gate Review"
        else:
            gate_status = "Rework Required"
            workflow_state = "Clarification Pending"

        gate_decision = GateDecision(
            gate_decision_status=gate_status,
            approver_name=author_name,
            approval_date=date.today(),
            decision_comments="Readiness baseline verified against Section 4 requirements. " + (
                f"{len(open_exceptions)} exceptions noted; open validation items flagged for Mobilize kickoff." if open_exceptions or questions else "All controls baselined."
            ),
            approved_with_exception=bool(open_exceptions),
            rework_required=(composite_score < 70.0),
            bypass_reason="Baseline drafted within 1 day; pending minor client confirmations" if open_exceptions else None,
            bypass_approving_authority="PMO Lead",
            readiness_score=composite_score,
            readiness_breakdown=readiness_breakdown,
            workflow_state=workflow_state,
            sla_met=sla_met,
            segregation_of_duties_verified=segregation_verified,
            author_name=author_name,
            reviewer_names=reviewer_names,
            concurring_approver_name=concurring_approver,
            open_exceptions_count=len(open_exceptions),
        )

        # 18. Build Governance Context (for backwards compatibility)
        gov_context = GovernanceContext(
            project_name=charter_obj.project_name,
            governance_tier=charter_obj.governance_tier,
            contract_type=charter_obj.contract_type,
            client_name=charter_obj.client_name,
            delivery_manager=charter_obj.delivery_manager,
            talent_pm=charter_obj.talent_pm,
            pmo_lead=charter_obj.pmo_lead,
            executive_summary=charter.executive_summary or charter_obj.project_purpose,
            workflow_state=workflow_state,
            sla_met=sla_met
        )

        return StartupKitBaseline(
            project_name=charter_obj.project_name,
            governance_tier=charter_obj.governance_tier,
            contract_type=charter_obj.contract_type,
            governance_context=gov_context,
            charter=charter_obj,
            sow_interpretation=sow_summary,
            deliverables=deliverables,
            milestones=milestones,
            backlog_seed=backlog_seed,
            dependencies_assumptions=dependencies_assumptions,
            raid_items=raid_items,
            decisions=decisions,
            communications_plan=communications_plan,
            stakeholders=stakeholders,
            raci_matrix=raci_matrix,
            commercial_guardrails=commercial_guardrails,
            talent_onboarding=talent_onboarding,
            readiness_checklist=readiness_checklist,
            gate_decision=gate_decision,
            open_questions=questions,
            contract_ambiguities=contract_ambiguities,
            readiness_score=composite_score,
            readiness_breakdown=readiness_breakdown,
            workflow_state=workflow_state,
            sow_awarded_date=awarded_dt,
            kit_drafted_date=drafted_dt,
            sla_met=sla_met,
            author_name=author_name,
            reviewer_names=reviewer_names,
            approver_name=approver_name,
            concurring_approver_name=concurring_approver,
            segregation_of_duties_verified=segregation_verified
        )

    def recalculate_readiness(self, baseline: StartupKitBaseline) -> StartupKitBaseline:
        """Recalculate dimensional readiness scores and G-01 Gate Decision for an existing or updated baseline."""
        status_points = {
            "Complete": 1.0,
            "Approved": 1.0,
            "Approved with Exception": 0.85,
            "In Progress": 0.5,
            "Review Required": 0.5,
            "Confirmation Required": 0.3,
            "Exception Required": 0.2,
            "Rework Required": 0.0,
            "Not Started": 0.0,
        }

        # 1. Synchronize checklist items with baseline data state
        dm_val = baseline.charter.delivery_manager if baseline.charter else None
        tpm_val = baseline.charter.talent_pm if baseline.charter else None
        pmo_val = baseline.charter.pmo_lead if baseline.charter else (baseline.author_name or "PMO Lead")

        has_unconfirmed_delivs = any(d.acceptance_criteria is None or "[CONFIRMATION REQUIRED]" in d.acceptance_criteria for d in baseline.deliverables) if baseline.deliverables else False
        has_unconfirmed_dates = any(m.external_date is None for m in baseline.milestones) if baseline.milestones else False
        has_unassigned_roles = any("UNASSIGNED" in str(x).upper() for x in [dm_val, tpm_val]) if (dm_val or tpm_val) else True
        has_ambiguities = len(baseline.contract_ambiguities) > 0
        has_questions = len(baseline.open_questions) > 0

        for item in baseline.readiness_checklist:
            if item.item_id == "G01-01" and baseline.sla_met:
                if item.status == "Exception Required":
                    item.status = "Complete"
                    item.exception_required = False
                    item.exception_details = None
            elif item.item_id == "G01-03" and not has_questions:
                if item.status in ("Review Required", "Exception Required", "In Progress"):
                    item.status = "Complete"
                    item.exception_required = False
                    item.exception_details = None
            elif item.item_id == "G01-04" and not has_unconfirmed_dates and baseline.milestones:
                if item.status in ("Confirmation Required", "Review Required", "In Progress"):
                    item.status = "Complete"
                    item.exception_required = False
                    item.exception_details = None
            elif item.item_id == "G01-06" and not has_unconfirmed_delivs and baseline.deliverables:
                if item.status in ("Review Required", "Confirmation Required", "In Progress"):
                    item.status = "Complete"
                    item.exception_required = False
                    item.exception_details = None
            elif item.item_id == "G01-13" and not has_unassigned_roles:
                if item.status in ("In Progress", "Review Required", "Confirmation Required"):
                    item.status = "Complete"
                    item.exception_required = False
                    item.exception_details = None
            elif item.item_id == "G01-14" and not has_ambiguities:
                if item.status in ("Review Required", "Exception Required"):
                    item.status = "Complete"
                    item.exception_required = False
                    item.exception_details = None
            elif item.item_id == "G01-15" and not has_questions:
                if item.status in ("Review Required", "Exception Required"):
                    item.status = "Complete"
                    item.exception_required = False
                    item.exception_details = None

            # Keep exception_required aligned with status
            if item.status in ("Complete", "Approved"):
                item.exception_required = False
                item.exception_details = None
                item.approval_status = "Approved"
            elif item.status == "Exception Required":
                item.exception_required = True
                if not item.exception_details:
                    item.exception_details = f"Exception logged for {item.gate_criterion}."

        # 2. Dim 1: Mandatory G-01 Controls (40% Weight)
        total_items = len(baseline.readiness_checklist)
        total_score_items = sum(status_points.get(item.status, 0.5) for item in baseline.readiness_checklist)
        dim1 = (total_score_items / total_items) if total_items > 0 else 0.0
        open_exceptions = [i for i in baseline.readiness_checklist if i.exception_required or i.status == "Exception Required"]
        dim1 = max(0.0, min(1.0, dim1 - (len(open_exceptions) * 0.03)))

        # 3. Dim 2: Deliverable & Acceptance Rigor (25% Weight)
        if baseline.deliverables:
            deliv_scores = []
            for d in baseline.deliverables:
                s = 0.0
                if d.acceptance_criteria and "[CONFIRMATION REQUIRED]" not in d.acceptance_criteria:
                    s += 0.4
                if d.owner and "UNASSIGNED" not in d.owner.upper() and d.owner != "Unassigned":
                    s += 0.3
                if d.client_approver and "UNASSIGNED" not in d.client_approver.upper():
                    s += 0.3
                deliv_scores.append(s)
            dim2 = sum(deliv_scores) / len(baseline.deliverables)
        else:
            dim2 = 0.0
        dim2 = max(0.0, min(1.0, dim2))

        # 4. Dim 3: Talent & Staffing Readiness (20% Weight)
        dim3 = 0.0
        t_rec = baseline.talent_onboarding
        dm_name = t_rec.delivery_manager if t_rec else dm_val
        tpm_name = t_rec.talent_pm if t_rec else tpm_val
        if dm_name and "UNASSIGNED" not in dm_name.upper():
            dim3 += 0.35
        if tpm_name and "UNASSIGNED" not in tpm_name.upper():
            dim3 += 0.35
        if t_rec and t_rec.delivery_talent_roster:
            confirmed_cnt = sum(1 for tm in t_rec.delivery_talent_roster if tm.status.lower() in ("confirmed", "active", "approved", "ready"))
            dim3 += 0.30 * (confirmed_cnt / max(1, len(t_rec.delivery_talent_roster)))
        else:
            dim3 += 0.15
        dim3 = max(0.0, min(1.0, dim3))

        # 5. Dim 4: Commercial & Risk Mitigation (15% Weight)
        dim4 = 0.0
        if baseline.raid_items:
            owned_risks = sum(1 for r in baseline.raid_items if r.owner and "UNASSIGNED" not in r.owner.upper() and r.owner != "Unassigned")
            dim4 += 0.40 * min(1.0, (owned_risks / max(1, len(baseline.raid_items))))
        else:
            dim4 += 0.20
        if baseline.commercial_guardrails:
            dim4 += 0.30
        q_penalty = max(0.0, 1.0 - (len(baseline.open_questions) * 0.05))
        dim4 += 0.30 * q_penalty
        dim4 = max(0.0, min(1.0, dim4))

        composite_score = round((dim1 * 0.40 + dim2 * 0.25 + dim3 * 0.20 + dim4 * 0.15) * 100, 1)
        readiness_breakdown = {
            "mandatory_g01_controls": round(dim1 * 100, 1),
            "deliverable_acceptance_rigor": round(dim2 * 100, 1),
            "talent_staffing_readiness": round(dim3 * 100, 1),
            "commercial_risk_mitigation": round(dim4 * 100, 1),
        }

        # 6. Gate Decision and Workflow State
        if composite_score >= 85.0 and not open_exceptions:
            gate_status = "Approved for Mobilize"
            workflow_state = "Approved for Mobilize"
        elif open_exceptions or composite_score >= 70.0:
            gate_status = "Approved with Exception"
            workflow_state = "Approved with Exception"
        else:
            gate_status = "Rework Required"
            workflow_state = "Clarification Pending"

        author_name = baseline.author_name or pmo_val or "PMO Lead"
        gate_decision = GateDecision(
            gate_decision_status=gate_status,
            approver_name=author_name,
            approval_date=date.today(),
            decision_comments="Readiness baseline recalculated against Section 4 requirements. " + (
                f"{len(open_exceptions)} exceptions noted; open validation items flagged for Mobilize kickoff." if open_exceptions or has_questions else "All controls baselined."
            ),
            approved_with_exception=bool(open_exceptions),
            rework_required=(composite_score < 70.0),
            bypass_reason="Baseline drafted within 1 day; pending minor client confirmations" if open_exceptions else None,
            bypass_approving_authority="PMO Lead",
            readiness_score=composite_score,
            readiness_breakdown=readiness_breakdown,
            workflow_state=workflow_state,
            sla_met=baseline.sla_met,
            segregation_of_duties_verified=baseline.segregation_of_duties_verified,
            author_name=author_name,
            reviewer_names=baseline.reviewer_names,
            concurring_approver_name=baseline.concurring_approver_name,
            open_exceptions_count=len(open_exceptions),
        )

        baseline.readiness_score = composite_score
        baseline.readiness_breakdown = readiness_breakdown
        baseline.workflow_state = workflow_state
        baseline.gate_decision = gate_decision
        if baseline.governance_context:
            baseline.governance_context.workflow_state = workflow_state

        return baseline
