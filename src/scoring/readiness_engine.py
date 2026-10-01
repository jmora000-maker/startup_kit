"""Authoritative Startup Readiness Scoring Engine and Action Required Item Generator."""

import re
from datetime import date
from typing import Dict, List, Optional, Tuple, Any
from src.core.models import (
    StartupKitBaseline,
    ReadinessChecklistItem,
    Deliverable,
    GateDecision,
    ActionRequiredItem,
    ReadinessWorkflowState,
)


class ReadinessScoringEngine:
    """Centralized, deterministic mathematical engine for Startup Readiness Scores and G-01 Gate Decisions."""

    # Dimension Weights (sum = 1.00)
    WEIGHT_MANDATORY_CONTROLS: float = 0.40
    WEIGHT_DELIVERABLES_RIGOR: float = 0.25
    WEIGHT_TALENT_STAFFING: float = 0.20
    WEIGHT_COMMERCIAL_RISK: float = 0.15

    # Checklist status point values
    STATUS_POINTS: Dict[str, float] = {
        "Complete": 1.00,
        "Approved": 1.00,
        "Approved with Exception": 0.85,
        "Review Required": 0.50,
        "In Progress": 0.50,
        "Confirmation Required": 0.30,
        "Exception Required": 0.20,
        "Rework Required": 0.00,
        "Not Started": 0.00,
    }

    # Authoritative mapping metadata for G01-01 through G01-15
    GATE_METADATA: Dict[str, Dict[str, Any]] = {
        "G01-01": {
            "criterion": "Startup Kit created within 1 day of delivery",
            "artifact": "Project Startup Charter",
            "target_table_title": "Project Startup Charter",
            "target_column_header": "Turnaround SLA & PMO Authorization",
            "default_action": "Log retroactive PMO waiver for delayed drafting",
            "default_owner": "PMO Lead",
            "delta": 1.5,
            "impact": "Clears G01-01 to Approved",
        },
        "G01-02": {
            "criterion": "Governance Tier assigned and cadence established",
            "artifact": "Project Startup Charter",
            "target_table_title": "Project Startup Charter",
            "target_column_header": "Delivery Model & Governance Tier",
            "default_action": "Confirm governance tier and agree weekly cadence",
            "default_owner": "PMO Lead",
            "delta": 2.0,
            "impact": "Clears G01-02 to Approved",
        },
        "G01-03": {
            "criterion": "Deliverables mapped to owners with explicit acceptance routes",
            "artifact": "Deliverables and Acceptance Matrix",
            "target_table_title": "Deliverables and Acceptance Matrix",
            "target_column_header": "Acceptance Criteria",
            "default_action": "Finalize acceptance test criteria and assign named delivery owner",
            "default_owner": "Talent PM",
            "delta": 3.5,
            "impact": "Clears G01-03 to Approved",
        },
        "G01-04": {
            "criterion": "Milestones committed with external dates and internal buffers",
            "artifact": "Milestone Delivery Plan",
            "target_table_title": "Milestone Delivery Plan",
            "target_column_header": "External Date",
            "default_action": "Agree milestone baseline with client sponsor and log 7-day buffer",
            "default_owner": "Delivery Manager",
            "delta": 3.0,
            "impact": "Clears G01-04 to Approved",
        },
        "G01-05": {
            "criterion": "Risks, Assumptions, Issues, and Dependencies seeded",
            "artifact": "RAID Log",
            "target_table_title": "RAID Log",
            "target_column_header": "Owner",
            "default_action": "Assign risk owners and document fallback mitigations",
            "default_owner": "Talent PM",
            "delta": 2.0,
            "impact": "Clears G01-05 to Approved",
        },
        "G01-06": {
            "criterion": "Talent PM and DM briefed on governance cadence and KO decks",
            "artifact": "Talent Onboarding Record",
            "target_table_title": "Talent Onboarding Record",
            "target_column_header": "Named Talent",
            "default_action": "Complete briefing on PMO cadences and approve KO deck",
            "default_owner": "PMO Lead",
            "delta": 1.5,
            "impact": "Clears G01-06 to Approved",
        },
        "G01-07": {
            "criterion": "Client onboarding prerequisites and platform access validated",
            "artifact": "SOW Interpretation Summary",
            "target_table_title": "SOW Interpretation Summary",
            "target_column_header": "Customer Obligations & Prerequisites",
            "default_action": "Issue access prerequisites list to client sponsor",
            "default_owner": "Delivery Manager",
            "delta": 2.5,
            "impact": "Clears G01-07 to Approved",
        },
        "G01-08": {
            "criterion": "Delivery Talent Roster staffed with key roles confirmed",
            "artifact": "Talent Onboarding Record",
            "target_table_title": "Talent Onboarding Record",
            "target_column_header": "Named Talent",
            "default_action": "Confirm candidate selection and lock staffing",
            "default_owner": "Delivery Manager",
            "delta": 2.5,
            "impact": "Clears G01-08 to Approved",
        },
        "G01-09": {
            "criterion": "Client Sponsor and escalation sign-off authority identified",
            "artifact": "Stakeholder and Responsibility Model",
            "target_table_title": "Stakeholder and Responsibility Model",
            "target_column_header": "Decision Rights",
            "default_action": "Confirm primary client sign-off authority and title",
            "default_owner": "PMO Lead",
            "delta": 2.0,
            "impact": "Clears G01-09 to Approved",
        },
        "G01-10": {
            "criterion": "RACI and decision rights aligned with client",
            "artifact": "RACI / Decision Rights Matrix",
            "target_table_title": "RACI / Decision Rights Matrix",
            "target_column_header": "Startup Control / Decision Activity",
            "default_action": "Align RACI matrix with client project sponsor",
            "default_owner": "PMO Lead",
            "delta": 1.5,
            "impact": "Clears G01-10 to Approved",
        },
        "G01-11": {
            "criterion": "Communications and reporting cadence agreed",
            "artifact": "Communications and Reporting Plan",
            "target_table_title": "Communications and Reporting Plan",
            "target_column_header": "Audience",
            "default_action": "Confirm weekly status distribution list",
            "default_owner": "Delivery Manager",
            "delta": 1.5,
            "impact": "Clears G01-11 to Approved",
        },
        "G01-12": {
            "criterion": "Commercial and margin guardrails established",
            "artifact": "Startup Readiness Checklist",
            "target_table_title": "SOW Interpretation Summary",
            "target_column_header": "Ambiguities & Clarification Notes",
            "default_action": "Review commercial terms during mobilization kickoff",
            "default_owner": "PMO Lead",
            "delta": 3.0,
            "impact": "Clears G01-12 to Approved",
        },
        "G01-13": {
            "criterion": "Change control and out-of-scope procedure confirmed",
            "artifact": "Startup Readiness Checklist",
            "target_table_title": "SOW Interpretation Summary",
            "target_column_header": "Ambiguities & Clarification Notes",
            "default_action": "Review change control procedure during mobilization kickoff",
            "default_owner": "PMO Lead",
            "delta": 2.0,
            "impact": "Clears G01-13 to Approved",
        },
        "G01-14": {
            "criterion": "Contractual ambiguities and conflicts analyzed",
            "artifact": "Contract Ambiguity & Conflict Analysis",
            "target_table_title": "Contract Ambiguity & Conflict Analysis",
            "target_column_header": "Recommended Clarification",
            "default_action": "Execute formal clarification note with client accounts",
            "default_owner": "PMO Lead",
            "delta": 3.5,
            "impact": "Clears G01-14 to Approved",
        },
        "G01-15": {
            "criterion": "Unresolved ambiguities and open questions listed",
            "artifact": "SOW Interpretation Summary",
            "target_table_title": "SOW Interpretation Summary",
            "target_column_header": "Ambiguities & Clarification Notes",
            "default_action": "Review open questions during mobilization kickoff",
            "default_owner": "PMO Lead",
            "delta": 2.5,
            "impact": "Clears G01-15 to Approved",
        },
    }

    @classmethod
    def compute_dimension_1(
        cls, checklist: List[ReadinessChecklistItem]
    ) -> Tuple[float, List[ReadinessChecklistItem]]:
        """Compute Dimension 1: Mandatory G-01 Controls (40% Weight).

        Formula:
            D1 = max(0.0, min(1.0, (sum(score(I_k)) / N) - (E * 0.02)))
        """
        if not checklist:
            return 0.0, []

        open_exceptions = [
            i for i in checklist if i.exception_required or i.status == "Exception Required"
        ]
        e_count = len(open_exceptions)

        total_points = sum(cls.STATUS_POINTS.get(item.status, 0.50) for item in checklist)
        base_score = total_points / len(checklist)
        dim1 = max(0.0, min(1.0, base_score - (e_count * 0.02)))
        return dim1, open_exceptions

    @classmethod
    def compute_dimension_2(cls, deliverables: List[Deliverable]) -> float:
        """Compute Dimension 2: Deliverable & Acceptance Rigor (25% Weight).

        Formula:
            score(d) = S_criteria(d) + S_owner(d) + S_route(d)
            D2 = (1 / |Deliverables|) * sum(score(d)) (or 0.50 if empty)
        """
        if not deliverables:
            return 0.50

        deliv_scores: List[float] = []
        for d in deliverables:
            s = 0.0
            if d.acceptance_criteria and "[CONFIRMATION REQUIRED]" not in d.acceptance_criteria and "UNASSIGNED" not in d.acceptance_criteria:
                s += 0.40
            if d.owner and "UNASSIGNED" not in d.owner.upper() and d.owner != "Unassigned":
                s += 0.30
            if (
                d.client_approver
                and "UNASSIGNED" not in d.client_approver.upper()
                and "[CONFIRMATION REQUIRED]" not in d.client_approver
                and d.client_approver.strip()
            ):
                s += 0.30
            deliv_scores.append(s)

        dim2 = sum(deliv_scores) / len(deliverables)
        return max(0.0, min(1.0, dim2))

    @classmethod
    def compute_dimension_3(cls, baseline: StartupKitBaseline) -> float:
        """Compute Dimension 3: Talent Staffing Readiness (20% Weight).

        Formula:
            D3 = S_leadership (max 0.60) + S_roster (max 0.40)
        """
        # Leadership check (+0.20 each for PMO Lead, DM, Talent PM)
        s_lead = 0.0
        gov = baseline.governance_context
        t_rec = baseline.talent_onboarding
        charter = baseline.charter

        pmo = (
            (charter.pmo_lead if charter and charter.pmo_lead else None)
            or (t_rec.pmo_lead if t_rec and t_rec.pmo_lead else None)
            or (gov.pmo_lead if gov and gov.pmo_lead else None)
            or baseline.author_name
        )
        dm = (
            (charter.delivery_manager if charter and charter.delivery_manager else None)
            or (t_rec.delivery_manager if t_rec and t_rec.delivery_manager else None)
            or (gov.delivery_manager if gov and gov.delivery_manager else None)
        )
        tpm = (
            (charter.talent_pm if charter and charter.talent_pm else None)
            or (t_rec.talent_pm if t_rec and t_rec.talent_pm else None)
            or (gov.talent_pm if gov and gov.talent_pm else None)
        )

        if pmo and "UNASSIGNED" not in pmo.upper() and pmo != "Unassigned":
            s_lead += 0.20
        if dm and "UNASSIGNED" not in dm.upper() and dm != "Unassigned":
            s_lead += 0.20
        if tpm and "UNASSIGNED" not in tpm.upper() and tpm != "Unassigned":
            s_lead += 0.20

        # Roster completeness check (max 0.40)
        s_roster = 0.20  # Default baseline if no roster provided
        if t_rec and t_rec.delivery_talent_roster:
            staffed_cnt = sum(
                1
                for tm in t_rec.delivery_talent_roster
                if tm.status
                and tm.status.lower() in ("confirmed", "active", "approved", "ready", "staffed", "assigned")
                and tm.name
                and "UNASSIGNED" not in tm.name.upper()
                and tm.name != "Unassigned"
            )
            total_roles = max(
                len(t_rec.delivery_talent_roster),
                len(t_rec.required_roles) if t_rec.required_roles else 0,
            )
            s_roster = 0.40 * (staffed_cnt / max(1, total_roles))

        return max(0.0, min(1.0, s_lead + s_roster))

    @classmethod
    def compute_dimension_4(cls, baseline: StartupKitBaseline) -> float:
        """Compute Dimension 4: Commercial & Risk Mitigation (15% Weight).

        Formula:
            D4 = max(0.0, min(1.0, S_raid + S_commercial - min(0.40, Q * 0.05)))
        """
        # RAID maturity (max 0.50): Base score 0.20 for identified RAID items + up to 0.30 for assigned owners
        if baseline.raid_items:
            owned_risks = sum(
                1
                for r in baseline.raid_items
                if r.owner and "UNASSIGNED" not in r.owner.upper() and r.owner != "Unassigned"
            )
            s_raid = 0.20 + (0.30 * (owned_risks / max(1, len(baseline.raid_items))))
        else:
            s_raid = 0.25

        # Commercial guardrails (max 0.50)
        s_comm = 0.25
        if baseline.commercial_guardrails:
            cg = baseline.commercial_guardrails
            has_confirmed_budget = bool(
                cg.budget_baseline
                and "CONFIRMATION REQUIRED" not in cg.budget_baseline.upper()
                and "UNASSIGNED" not in cg.budget_baseline.upper()
            )
            has_rules = bool(
                cg.contract_type_implication
                or cg.commercial_exposure_note
                or cg.approved_work_rule
                or cg.work_at_risk_rule
            )
            if has_confirmed_budget and has_rules:
                s_comm = 0.50
            elif has_confirmed_budget or has_rules:
                s_comm = 0.40
            else:
                s_comm = 0.30

        # Open question penalty (0.05 per item, capped at 0.40)
        q_penalty = min(0.40, len(baseline.open_questions) * 0.05)

        return max(0.0, min(1.0, s_raid + s_comm - q_penalty))

    @classmethod
    def compute_scores(cls, baseline: StartupKitBaseline) -> Tuple[float, Dict[str, float]]:
        """Calculate composite readiness score and dimension breakdown."""
        dim1, _ = cls.compute_dimension_1(baseline.readiness_checklist)
        dim2 = cls.compute_dimension_2(baseline.deliverables)
        dim3 = cls.compute_dimension_3(baseline)
        dim4 = cls.compute_dimension_4(baseline)

        composite = (
            dim1 * cls.WEIGHT_MANDATORY_CONTROLS
            + dim2 * cls.WEIGHT_DELIVERABLES_RIGOR
            + dim3 * cls.WEIGHT_TALENT_STAFFING
            + dim4 * cls.WEIGHT_COMMERCIAL_RISK
        )
        composite_score = round(composite * 100, 1)

        breakdown = {
            "mandatory_g01_controls": round(dim1 * 100, 1),
            "deliverable_acceptance_rigor": round(dim2 * 100, 1),
            "talent_staffing_readiness": round(dim3 * 100, 1),
            "commercial_risk_mitigation": round(dim4 * 100, 1),
        }
        return composite_score, breakdown

    @classmethod
    def determine_gate_decision(
        cls,
        composite_score: float,
        open_exceptions_count: int,
        has_questions: bool = False,
        sla_met: bool = True,
        segregation_verified: bool = True,
        author_name: str = "PMO Lead",
        reviewer_names: Optional[List[str]] = None,
        concurring_approver: Optional[str] = None,
        comments_prefix: str = "Readiness baseline reviewed against Section 4 requirements.",
    ) -> Tuple[GateDecision, ReadinessWorkflowState]:
        """Determine G-01 Gate Decision status and workflow state from scores and exception counts."""
        if composite_score < 70.0:
            gate_status = "Rework Required"
            workflow_state: ReadinessWorkflowState = "Clarification Pending"
            approved_with_exception = False
            rework_required = True
        elif composite_score >= 85.0 and open_exceptions_count == 0:
            gate_status = "Approved for Mobilize"
            workflow_state: ReadinessWorkflowState = (
                "Approved for Mobilize" if not has_questions else "Ready for G-01 Gate Review"
            )
            approved_with_exception = False
            rework_required = False
        else:
            # Score is >= 70.0, but either score < 85.0 or open_exceptions_count > 0
            gate_status = "Approved with Exception"
            workflow_state = "Approved with Exception"
            approved_with_exception = True
            rework_required = False

        comments = f"{comments_prefix} " + (
            f"{open_exceptions_count} exceptions noted; open validation items flagged for Mobilize kickoff."
            if open_exceptions_count or has_questions
            else "All controls baselined."
        )

        decision = GateDecision(
            gate_decision_status=gate_status,
            approver_name=author_name,
            approval_date=date.today(),
            decision_comments=comments,
            approved_with_exception=approved_with_exception,
            rework_required=rework_required,
            bypass_reason=(
                "Baseline drafted within 1 day; pending minor client confirmations"
                if open_exceptions_count
                else None
            ),
            bypass_approving_authority="PMO Lead" if open_exceptions_count else None,
            readiness_score=composite_score,
            readiness_breakdown={},
            workflow_state=workflow_state,
            sla_met=sla_met,
            segregation_of_duties_verified=segregation_verified,
            author_name=author_name,
            reviewer_names=reviewer_names or ["Delivery Manager", "Technical Lead"],
            concurring_approver_name=concurring_approver,
            open_exceptions_count=open_exceptions_count,
        )
        return decision, workflow_state

    @classmethod
    def match_question_to_gate_id(cls, question_text: str) -> str:
        """Map an open clarification question to the most relevant G-01 Checklist ID."""
        q_lower = question_text.lower()
        if any(w in q_lower for w in ("sponsor", "client lead", "sign-off authority", "client sponsor", "client contact", "escalation authority")):
            return "G01-09"
        elif any(w in q_lower for w in ("communication", "reporting", "cadence", "status report", "distribution", "psr")):
            return "G01-11"
        elif any(w in q_lower for w in ("onboarding", "prerequisite", "environment", "access", "iam", "credential", "obligation")):
            return "G01-07"
        elif any(w in q_lower for w in ("deliverable", "acceptance", "criteria", "pipeline", "backlog", "work package")):
            return "G01-03"
        elif any(w in q_lower for w in ("milestone", "delivery date", "buffer", "external date", "timeline", "schedule")):
            return "G01-04"
        elif any(w in q_lower for w in ("raid", "risk", "assumption", "dependency", "blocker")):
            return "G01-05"
        elif any(w in q_lower for w in ("briefing", "kickoff deck", "ko deck")):
            return "G01-06"
        elif any(w in q_lower for w in ("talent", "staffing", "roster", "candidate", "role", "developer", "architect", "engineer", "lead", "unassigned")):
            return "G01-08"
        elif any(w in q_lower for w in ("raci", "decision rights", "decision matrix")):
            return "G01-10"
        elif any(w in q_lower for w in ("budget", "margin", "commercial", "sow value", "fixed bid", "time and materials", "rate card", "cap")):
            return "G01-12"
        elif any(w in q_lower for w in ("change control", "change order", "out of scope", "scope change")):
            return "G01-13"
        elif any(w in q_lower for w in ("conflict", "ambiguity", "contradiction", "discrepancy", "clause")):
            return "G01-14"
        elif any(w in q_lower for w in ("sla", "1-day", "turnaround", "charter")):
            return "G01-01"
        elif any(w in q_lower for w in ("tier", "governance model")):
            return "G01-02"
        else:
            return "G01-15"

    @classmethod
    def synchronize_open_questions_with_artifacts(cls, baseline: StartupKitBaseline) -> None:
        """Reconcile and prune open questions whose underlying artifact defects have been resolved."""
        if not baseline.open_questions:
            return

        def _is_clean(val: Optional[str]) -> bool:
            if not val:
                return False
            v = val.strip().upper()
            return not ("UNASSIGNED" in v or "CONFIRMATION" in v or v in ("", "NONE", "N/A", "TBD", "[TBD]"))

        # Deduplicate while preserving order and stripping resolved markers
        seen_q = set()
        deduped: List[str] = []
        for q in baseline.open_questions:
            if not q or not q.strip():
                continue
            q_norm = q.strip()
            if "RESOLVED" in q_norm.upper():
                continue
            if q_norm.lower() not in seen_q:
                seen_q.add(q_norm.lower())
                deduped.append(q_norm)

        filtered_questions: List[str] = []
        for q in deduped:
            q_upper = q.upper()
            q_lower = q.lower()

            gate_id = cls.match_question_to_gate_id(q)

            # Check if gate or artifact is resolved
            if gate_id == "G01-03":
                m_del = re.search(r'(?:\[|\(|\b)(DEL(?:IV)?-?\d+)(?:\]|\)|\b)', q, re.IGNORECASE)
                if m_del and baseline.deliverables:
                    del_num = int(re.search(r'\d+', m_del.group(1)).group())
                    target_d = next((d for d in baseline.deliverables if re.search(r'\d+', d.id) and int(re.search(r'\d+', d.id).group()) == del_num), None)
                    if target_d and _is_clean(target_d.acceptance_criteria) and _is_clean(target_d.owner):
                        continue
                elif baseline.deliverables:
                    matched_d = next(
                        (d for d in baseline.deliverables if any(w in q_lower for w in (d.name or d.description or "").lower().split() if len(w) > 4)),
                        None
                    )
                    if matched_d and _is_clean(matched_d.acceptance_criteria) and _is_clean(matched_d.owner):
                        continue
                    if all(_is_clean(d.acceptance_criteria) and _is_clean(d.owner) for d in baseline.deliverables):
                        continue

            elif gate_id == "G01-04":
                m_ms = re.search(r'(?:\[|\(|\b)(M(?:S)?-?\d+)(?:\]|\)|\b)', q, re.IGNORECASE)
                if m_ms and baseline.milestones:
                    ms_num = int(re.search(r'\d+', m_ms.group(1)).group())
                    target_m = next((m for m in baseline.milestones if re.search(r'\d+', m.id) and int(re.search(r'\d+', m.id).group()) == ms_num), None)
                    if target_m and target_m.external_date is not None and _is_clean(target_m.owner):
                        continue
                elif baseline.milestones:
                    matched_m = next(
                        (m for m in baseline.milestones if any(w in q_lower for w in (m.description or "").lower().split() if len(w) > 4)),
                        None
                    )
                    if matched_m and matched_m.external_date is not None and _is_clean(matched_m.owner):
                        continue
                    if all(m.external_date is not None and _is_clean(m.owner) for m in baseline.milestones):
                        continue

            elif gate_id == "G01-07":
                sow = baseline.sow_interpretation
                if sow:
                    has_open_ob = any(not _is_clean(o) for o in sow.customer_obligations) if sow.customer_obligations else False
                    has_open_pf = any(not _is_clean(p) for p in sow.platform_environment_commitments) if sow.platform_environment_commitments else False
                    if not has_open_ob and not has_open_pf:
                        continue

            elif gate_id in ("G01-06", "G01-08"):
                dm_clean = False
                tpm_clean = False
                pmo_clean = False
                if baseline.charter:
                    dm_clean = _is_clean(baseline.charter.delivery_manager)
                    tpm_clean = _is_clean(baseline.charter.talent_pm)
                    pmo_clean = _is_clean(baseline.charter.pmo_lead)
                elif baseline.talent_onboarding:
                    dm_clean = _is_clean(baseline.talent_onboarding.delivery_manager)
                    tpm_clean = _is_clean(baseline.talent_onboarding.talent_pm)
                    pmo_clean = _is_clean(baseline.talent_onboarding.pmo_lead)

                if any(w in q_lower for w in ("delivery manager", "delivery lead", "dm")):
                    if dm_clean:
                        continue
                if any(w in q_lower for w in ("talent pm", "talent lead", "tpm")):
                    if tpm_clean:
                        continue
                if "pmo lead" in q_lower:
                    if pmo_clean:
                        continue

                t_rec = baseline.talent_onboarding
                if t_rec and t_rec.delivery_talent_roster:
                    matched_role = next(
                        (tm for tm in t_rec.delivery_talent_roster if tm.role.lower() in q_lower),
                        None
                    )
                    if matched_role and _is_clean(matched_role.name) and matched_role.status and matched_role.status.lower() in ("confirmed", "active", "approved", "ready", "staffed", "assigned"):
                        continue

                    all_staffed = all(
                        _is_clean(tm.name)
                        and tm.status
                        and tm.status.lower() in ("confirmed", "active", "approved", "ready", "staffed", "assigned")
                        for tm in t_rec.delivery_talent_roster
                    )
                    if all_staffed and dm_clean and tpm_clean:
                        continue

            elif gate_id == "G01-09":
                if baseline.stakeholders:
                    matched_stk = next(
                        (stk for stk in baseline.stakeholders if stk.name.lower() in q_lower or stk.role.lower() in q_lower),
                        None
                    )
                    if matched_stk and _is_clean(matched_stk.name) and _is_clean(matched_stk.decision_rights):
                        continue
                    all_stk_clean = all(
                        _is_clean(stk.name) and _is_clean(stk.decision_rights)
                        for stk in baseline.stakeholders
                    )
                    if all_stk_clean:
                        continue

            elif gate_id == "G01-11":
                if baseline.communications_plan:
                    all_com_clean = all(
                        _is_clean(c.audience) and _is_clean(c.content_owner)
                        for c in baseline.communications_plan
                    )
                    if all_com_clean:
                        continue

            elif gate_id == "G01-12":
                cg = baseline.commercial_guardrails
                if cg and _is_clean(cg.budget_baseline):
                    continue

            elif gate_id == "G01-13":
                cg = baseline.commercial_guardrails
                if cg and _is_clean(cg.change_order_route):
                    continue

            elif gate_id in ("G01-14", "G01-15"):
                if baseline.contract_ambiguities:
                    all_amb_resolved = all(
                        getattr(ca, "status", "Open").lower() == "resolved"
                        or "RESOLVED" in getattr(ca, "recommended_clarification", "").upper()
                        for ca in baseline.contract_ambiguities
                    )
                    if all_amb_resolved:
                        continue

            filtered_questions.append(q)

        baseline.open_questions = filtered_questions

    @classmethod
    def synchronize_checklist_with_artifacts(cls, baseline: StartupKitBaseline) -> None:
        """Automatically synchronize G-01 checklist items with the state of Section 4 artifacts."""
        cls.synchronize_open_questions_with_artifacts(baseline)
        if not baseline.readiness_checklist:
            return

        chk_map = {item.item_id: item for item in baseline.readiness_checklist}

        # G01-01: Turnaround SLA & Charter Authorization
        if "G01-01" in chk_map:
            item = chk_map["G01-01"]
            if baseline.sla_met:
                item.status = "Complete"
                item.exception_required = False
                item.exception_details = None
            else:
                item.status = "Exception Required"
                item.exception_required = True
                if not item.exception_details:
                    item.exception_details = "Startup Kit creation exceeded 1 business day SLA."

        # G01-02: Governance Tier & Cadence
        if "G01-02" in chk_map:
            item = chk_map["G01-02"]
            tier = (baseline.charter.governance_tier if baseline.charter else None) or baseline.governance_tier or "Partnered"
            has_buffers = any(bool(m.internal_buffer_date) for m in baseline.milestones) if baseline.milestones else False
            if has_buffers:
                item.evidence = f"Governance Tier confirmed as '{tier}' with tailored buffers and reporting."
            else:
                item.evidence = f"Governance Tier confirmed as '{tier}' with reporting cadence."

            if (baseline.charter and baseline.charter.governance_tier) or baseline.governance_tier:
                item.status = "Complete"
                item.exception_required = False
                item.exception_details = None
            else:
                item.status = "Review Required"
                item.exception_required = True
                if not item.exception_details:
                    item.exception_details = "Governance tier and reporting cadence pending alignment."

        # G01-03: Deliverables & Acceptance Criteria (v4 B8: check client_approver too)
        if "G01-03" in chk_map:
            item = chk_map["G01-03"]
            has_deliv_defects = False
            if not baseline.deliverables:
                has_deliv_defects = True
            else:
                for d in baseline.deliverables:
                    if (
                        not d.acceptance_criteria
                        or "[CONFIRMATION REQUIRED]" in d.acceptance_criteria
                        or "UNASSIGNED" in d.acceptance_criteria
                        or not d.owner
                        or "UNASSIGNED" in d.owner.upper()
                        or d.owner == "Unassigned"
                        or not d.client_approver
                        or "UNASSIGNED" in d.client_approver.upper()
                        or "[CONFIRMATION REQUIRED]" in d.client_approver
                    ):
                        has_deliv_defects = True
                        break
            if not has_deliv_defects:
                item.status = "Complete"
                item.exception_required = False
                item.exception_details = None
            else:
                item.status = "Review Required"
                item.exception_required = True
                if not item.exception_details:
                    item.exception_details = "Deliverables pending acceptance criteria confirmation, owner assignment, or client approver."

        # G01-04: Milestones with external dates and internal buffers
        if "G01-04" in chk_map:
            item = chk_map["G01-04"]
            has_ms_defects = False
            if not baseline.milestones:
                has_ms_defects = False
            else:
                for m in baseline.milestones:
                    if (
                        m.external_date is None
                        or not m.owner
                        or "UNASSIGNED" in m.owner.upper()
                        or m.owner == "Unassigned"
                    ):
                        has_ms_defects = True
                        break
            if not has_ms_defects:
                item.status = "Complete"
                item.exception_required = False
                item.exception_details = None
            else:
                item.status = "Confirmation Required"
                item.exception_required = True
                if not item.exception_details:
                    item.exception_details = "Milestone dates unconfirmed."

        # G01-05: RAID Log seeded with owners and mitigations
        if "G01-05" in chk_map:
            item = chk_map["G01-05"]
            has_raid_defects = False
            if baseline.raid_items:
                for r in baseline.raid_items:
                    mitigation_text = (r.mitigation_or_response or "")
                    if (
                        not r.owner
                        or "UNASSIGNED" in r.owner.upper()
                        or r.owner == "Unassigned"
                    ):
                        has_raid_defects = True
                        break
            if not has_raid_defects:
                item.status = "Complete"
                item.exception_required = False
                item.exception_details = None
            else:
                item.status = "Review Required"
                item.exception_required = True
                if not item.exception_details:
                    item.exception_details = "RAID log items or dependencies pending owner assignment or mitigation."

        # G01-06: Onboarding briefings & KO deck
        if "G01-06" in chk_map:
            item = chk_map["G01-06"]
            charter = baseline.charter
            t_rec = baseline.talent_onboarding
            dm = (charter.delivery_manager if charter else None) or (t_rec.delivery_manager if t_rec else None)
            tpm = (charter.talent_pm if charter else None) or (t_rec.talent_pm if t_rec else None)
            has_unassigned_roles = (
                not dm
                or "UNASSIGNED" in str(dm).upper()
                or not tpm
                or "UNASSIGNED" in str(tpm).upper()
            )
            if not has_unassigned_roles:
                item.status = "Complete"
                item.exception_required = False
                item.exception_details = None
            else:
                item.status = "In Progress"
                item.exception_required = True
                if not item.exception_details:
                    item.exception_details = "Talent PM / Delivery Manager onboarding briefing pending."

        # G01-07: Client onboarding prerequisites & platform access
        if "G01-07" in chk_map:
            item = chk_map["G01-07"]
            if item.status in ("Complete", "Approved") and not item.exception_required:
                item.status = "Complete"
                item.exception_required = False
                item.exception_details = None
            else:
                has_sow_defects = False
                if not baseline.sow_interpretation or not baseline.sow_interpretation.customer_obligations:
                    has_sow_defects = True
                else:
                    for o in baseline.sow_interpretation.customer_obligations:
                        if not str(o).strip() or any(p in str(o).upper() for p in ("CONFIRMATION REQUIRED", "UNDEFINED", "UNASSIGNED", "TBD")):
                            has_sow_defects = True
                            break
                if not has_sow_defects:
                    item.status = "Complete"
                    item.exception_required = False
                    item.exception_details = None
                else:
                    item.status = "Review Required"
                    item.exception_required = True
                    if not item.exception_details:
                        item.exception_details = "Customer prerequisites and environment access pending confirmation."

        # G01-08: Delivery Talent Roster staffed (v6 B7)
        if "G01-08" in chk_map:
            item = chk_map["G01-08"]
            t_rec = baseline.talent_onboarding
            roster = t_rec.delivery_talent_roster if t_rec else []
            n_roles = len(roster)
            m_named = sum(
                1 for tm in roster
                if tm.name and "UNASSIGNED" not in tm.name.upper() and tm.name != "Unassigned" and tm.status.lower() not in ("pending", "needs alignment", "unassigned", "staffing required")
            )
            if n_roles > 0:
                item.evidence = f"{n_roles} delivery talent roles listed; {m_named} named"
            if m_named < n_roles or n_roles == 0:
                item.status = "In Progress"
                item.exception_required = True
                if not item.exception_details:
                    item.exception_details = "Talent roster staffing in progress."
            else:
                item.status = "Complete"
                item.exception_required = False
                item.exception_details = None

        # G01-09: Client Sponsor & escalation authority
        if "G01-09" in chk_map:
            item = chk_map["G01-09"]
            has_sponsor_defect = False
            if baseline.stakeholders:
                for sh in baseline.stakeholders:
                    if "UNASSIGNED" in sh.name.upper() or "CONFIRMATION REQUIRED" in (sh.decision_rights or "").upper():
                        has_sponsor_defect = True
                        break
            if not has_sponsor_defect:
                item.status = "Complete"
                item.exception_required = False
                item.exception_details = None
            else:
                item.status = "Review Required"
                item.exception_required = True
                if not item.exception_details:
                    item.exception_details = "Client sponsor and decision escalation path pending confirmation."

        # G01-10: RACI aligned
        if "G01-10" in chk_map:
            item = chk_map["G01-10"]
            item.status = "Complete"
            item.exception_required = False
            item.exception_details = None

        # G01-11: Communications cadence (v4 B8: list actual comms plan names)
        if "G01-11" in chk_map:
            item = chk_map["G01-11"]
            has_comm_defect = False
            comm_names = []
            if baseline.communications_plan:
                comm_names = [c.name for c in baseline.communications_plan if c.name]
                if any("CONFIRMATION REQUIRED" in (c.audience or "").upper() for c in baseline.communications_plan):
                    has_comm_defect = True
            if comm_names:
                item.evidence = ", ".join(comm_names)
            if not has_comm_defect:
                item.status = "Complete"
                item.exception_required = False
                item.exception_details = None
            else:
                item.status = "Review Required"
                item.exception_required = True
                if not item.exception_details:
                    item.exception_details = "Communications cadence pending confirmation."

        # G01-12 & G01-13: Commercial guardrails
        if "G01-12" in chk_map:
            item = chk_map["G01-12"]
            item.status = "Complete"
            item.exception_required = False
            item.exception_details = None

        if "G01-13" in chk_map:
            item = chk_map["G01-13"]
            item.status = "Complete"
            item.exception_required = False
            item.exception_details = None

        # G01-14: Contract ambiguities analyzed (v4 B8)
        if "G01-14" in chk_map:
            item = chk_map["G01-14"]
            num_amb = len(baseline.contract_ambiguities) if baseline.contract_ambiguities else 0
            if num_amb > 0:
                item.evidence = f"{num_amb} contractual ambiguities logged with recommended clarifications."
                any_open = any(getattr(a, "status", "Open").lower() in ("open", "pending") for a in baseline.contract_ambiguities)
                if any_open:
                    item.status = "Review Required"
                    item.exception_required = False
                    item.exception_details = None
                else:
                    item.status = "Complete"
                    item.exception_required = False
                    item.exception_details = None
            else:
                item.evidence = "No contractual ambiguities logged."
                item.status = "Complete"
                item.exception_required = False
                item.exception_details = None

        # G01-15: Open questions
        if "G01-15" in chk_map:
            item = chk_map["G01-15"]
            if not baseline.open_questions:
                item.status = "Complete"
                item.exception_required = False
                item.exception_details = None
            else:
                item.status = "Review Required"
                item.evidence = f"{len(baseline.open_questions)} validation points logged for mobilization confirmation."
                item.exception_required = False
                item.exception_details = None

        # Update approval_status for all items
        for item in baseline.readiness_checklist:
            if item.status in ("Complete", "Approved"):
                item.approval_status = "Approved"
            elif item.exception_required or item.status == "Exception Required":
                item.approval_status = "Exception Required"
            elif item.status == "Confirmation Required":
                item.approval_status = "Pending Confirmation"
            else:
                item.approval_status = "Pending Review"

    @classmethod
    def generate_action_required_items(
        cls, baseline: StartupKitBaseline
    ) -> List[ActionRequiredItem]:
        """Generate discrete, 1-to-1 ActionRequiredItems mapped to specific cell-level defects and questions.

        Preserves invariants:
          1. len([a for a in items if a.item_type == 'Open Exception']) == open_exceptions_count
          2. len([a for a in items if a.item_type == 'Open Clarification']) == len(baseline.open_questions)
          3. round(baseline.readiness_score + sum(a.score_recovery_delta), 1) <= 100.0
          4. Every ActionRequiredItem.owner matches checklist item owner
        """
        action_items: List[ActionRequiredItem] = []
        checklist_by_id = {item.item_id: item for item in baseline.readiness_checklist}
        act_counter = 1

        # Helper to get checklist owner
        def _get_owner(gate_id: str, default_role: str = "PMO Lead") -> str:
            chk = checklist_by_id.get(gate_id)
            if chk and chk.owner and "UNASSIGNED" not in chk.owner.upper() and chk.owner != "Unassigned":
                return chk.owner
            meta = cls.GATE_METADATA.get(gate_id, {})
            return meta.get("default_owner", default_role)

        # 1. Generate Open Exceptions (exactly 1 per checklist item with exception_required or status == "Exception Required")
        for item in baseline.readiness_checklist:
            if item.exception_required or item.status == "Exception Required":
                meta = cls.GATE_METADATA.get(item.item_id, {})
                gate_id = item.item_id
                owner = item.owner or meta.get("default_owner", "PMO Lead")
                artifact = item.related_section4_artifact or meta.get("artifact", "Section 4 Artifact")
                target_table = meta.get("target_table_title", artifact)
                target_col = meta.get("target_column_header", "General")
                target_entity_id = None
                desc = item.exception_details or f"Formal exception logged for {item.gate_criterion} ({item.status})."
                req_action = meta.get("default_action", "Resolve open exception prior to kickoff.")
                score_delta = meta.get("delta", 2.0)

                # Find specific entity defect corresponding to this gate exception
                if gate_id == "G01-03" and baseline.deliverables:
                    # Find first unconfirmed or unassigned deliverable
                    unconfirmed_d = next(
                        (d for d in baseline.deliverables if not d.acceptance_criteria or "[CONFIRMATION REQUIRED]" in d.acceptance_criteria or "UNASSIGNED" in d.acceptance_criteria or not d.owner or "UNASSIGNED" in d.owner.upper() or d.owner == "Unassigned"),
                        baseline.deliverables[0] if baseline.deliverables else None
                    )
                    if unconfirmed_d:
                        target_table = "Deliverables and Acceptance Matrix"
                        target_entity_id = unconfirmed_d.id
                        if not unconfirmed_d.acceptance_criteria or "[CONFIRMATION REQUIRED]" in unconfirmed_d.acceptance_criteria or "UNASSIGNED" in unconfirmed_d.acceptance_criteria:
                            target_col = "Acceptance Criteria"
                            desc = f"Deliverable {unconfirmed_d.id} ({unconfirmed_d.name}) lacks objective acceptance criteria."
                            req_action = f"Define objective UAT pass criteria and sign-off metrics for {unconfirmed_d.id}."
                        else:
                            target_col = "Owner"
                            desc = f"Deliverable {unconfirmed_d.id} ({unconfirmed_d.name}) has unassigned delivery ownership."
                            req_action = f"Assign named delivery owner for {unconfirmed_d.id}."
                        score_delta = round(max(0.5, (0.40 / max(1, len(baseline.deliverables))) * cls.WEIGHT_DELIVERABLES_RIGOR * 100.0 + 2.0), 1)

                elif gate_id == "G01-04" and baseline.milestones:
                    unconfirmed_m = next(
                        (m for m in baseline.milestones if m.external_date is None or m.internal_buffer_date is None or not m.owner or "UNASSIGNED" in m.owner.upper() or m.owner == "Unassigned"),
                        baseline.milestones[0] if baseline.milestones else None
                    )
                    if unconfirmed_m:
                        target_table = "Milestone Delivery Plan"
                        target_entity_id = unconfirmed_m.id
                        target_col = "External Date" if unconfirmed_m.external_date is None else ("Internal Buffer Date" if unconfirmed_m.internal_buffer_date is None else "Owner")
                        desc = f"Milestone {unconfirmed_m.id} ({unconfirmed_m.description}) commitment date or buffer unconfirmed."
                        req_action = f"Lock external milestone date and 7-day internal buffer for {unconfirmed_m.id}."
                        score_delta = round(max(0.5, 3.0), 1)

                elif gate_id == "G01-05" and baseline.raid_items:
                    unconfirmed_r = next(
                        (r for r in baseline.raid_items if not r.owner or "UNASSIGNED" in r.owner.upper() or r.owner == "Unassigned" or (not getattr(r, "mitigation_or_response", None) or "TBD" in getattr(r, "mitigation_or_response", "").upper())),
                        baseline.raid_items[0] if baseline.raid_items else None
                    )
                    if unconfirmed_r:
                        target_table = "RAID Log"
                        target_entity_id = getattr(unconfirmed_r, "id", None) or unconfirmed_r.description[:25]
                        target_col = "Owner" if (not unconfirmed_r.owner or "UNASSIGNED" in unconfirmed_r.owner.upper() or unconfirmed_r.owner == "Unassigned") else "Mitigation / Response"
                        desc = f"RAID item '{unconfirmed_r.description}' lacks assigned owner or mitigation."
                        req_action = f"Assign risk owner and document mitigation for '{unconfirmed_r.description[:30]}'."
                        score_delta = round(max(0.5, (0.50 / max(1, len(baseline.raid_items))) * cls.WEIGHT_COMMERCIAL_RISK * 100.0 + 1.5), 1)

                elif gate_id == "G01-08" and baseline.talent_onboarding and baseline.talent_onboarding.delivery_talent_roster:
                    unstaffed_tm = next(
                        (tm for tm in baseline.talent_onboarding.delivery_talent_roster if not tm.name or "UNASSIGNED" in tm.name.upper() or tm.status.lower() in ("pending", "needs alignment", "unassigned", "staffing required")),
                        baseline.talent_onboarding.delivery_talent_roster[0] if baseline.talent_onboarding.delivery_talent_roster else None
                    )
                    if unstaffed_tm:
                        target_table = "Talent Onboarding Record"
                        target_entity_id = unstaffed_tm.role
                        target_col = "Named Talent / Staffing Status"
                        desc = f"Delivery talent role '{unstaffed_tm.role}' is unstaffed / pending confirmation."
                        req_action = f"Confirm candidate selection and lock staffing for {unstaffed_tm.role}."
                        score_delta = round(max(0.5, (0.40 / max(1, len(baseline.talent_onboarding.delivery_talent_roster))) * cls.WEIGHT_TALENT_STAFFING * 100.0 + 2.0), 1)

                action_items.append(
                    ActionRequiredItem(
                        action_id=f"ACT-{act_counter:02d}",
                        item_type="Open Exception",
                        checklist_id=gate_id,
                        related_artifact=artifact,
                        target_table_title=target_table,
                        target_column_header=target_col,
                        target_entity_id=target_entity_id,
                        finding_description=desc,
                        required_action=req_action,
                        owner=owner,
                        resolution_deadline="Prior to Mobilize Kickoff",
                        score_recovery_delta=score_delta,
                        target_gate_impact=meta.get("impact", f"Clears {gate_id} to Approved"),
                    )
                )
                act_counter += 1

        # 2. Generate Open Clarifications (1 per open_question not already covered by an anomaly action)
        for q in baseline.open_questions:
            m_amb = re.match(r'^\[([A-Z0-9_\-]+)\]', q.strip())
            if m_amb:
                amb_id = m_amb.group(1)
                if any(a.target_entity_id == amb_id for a in action_items):
                    continue

            mapped_gate_id = cls.match_question_to_gate_id(q)
            meta = cls.GATE_METADATA.get(mapped_gate_id, {})
            checklist_item = checklist_by_id.get(mapped_gate_id)

            owner = (
                checklist_item.owner
                if checklist_item and checklist_item.owner and "UNASSIGNED" not in checklist_item.owner.upper() and checklist_item.owner != "Unassigned"
                else meta.get("default_owner", "PMO Lead")
            )
            artifact = (
                checklist_item.related_section4_artifact
                if checklist_item and checklist_item.related_section4_artifact
                else meta.get("artifact", "SOW Interpretation Summary")
            )
            target_table = "SOW Interpretation Summary"
            target_col = "Ambiguities & Clarification Notes"
            target_entity_id = None
            req_action = meta.get("default_action", "Review and clarify during mobilization kickoff.")
            score_delta = round(max(0.5, (0.05 * cls.WEIGHT_COMMERCIAL_RISK * 100.0) + 1.0), 1)

            # Map question to specific entity if referenced in text
            q_lower = q.lower()
            if mapped_gate_id == "G01-03" and baseline.deliverables:
                stop_words = {'design', 'plan', 'document', 'documentation', 'report', 'deliverable', 'deliverables', 'data', 'acceptance', 'criteria', 'review', 'specific', 'pipeline', 'matrix'}
                for d in baseline.deliverables:
                    d_id_match = d.id.lower() in q_lower
                    d_name_words = [w for w in re.findall(r'\w+', (d.name or d.description or "").lower()) if len(w) > 3 and w not in stop_words]
                    d_name_match = any(w in q_lower for w in d_name_words) if d_name_words else False
                    if d_id_match or d_name_match:
                        has_ac_action = any(a.target_entity_id == d.id and a.target_column_header == "Acceptance Criteria" for a in action_items)
                        if not has_ac_action:
                            target_table = "Deliverables and Acceptance Matrix"
                            target_col = "Acceptance Criteria"
                            target_entity_id = d.id
                            req_action = f"Clarify and confirm acceptance criteria for {d.id}."
                            break
                        elif not d.client_approver or "UNASSIGNED" in d.client_approver.upper() or "[CONFIRMATION REQUIRED]" in d.client_approver:
                            target_table = "Deliverables and Acceptance Matrix"
                            target_col = "Client Approver"
                            target_entity_id = d.id
                            req_action = f"Confirm client sign-off approver for {d.id}."
                            break
                        elif not d.owner or "UNASSIGNED" in d.owner.upper() or d.owner == "Unassigned":
                            target_table = "Deliverables and Acceptance Matrix"
                            target_col = "Owner"
                            target_entity_id = d.id
                            req_action = f"Assign named delivery owner for {d.id}."
                            break
                if not target_entity_id:
                    target_table = "SOW Interpretation Summary"
                    target_col = "Ambiguities & Clarification Notes"
                    req_action = f"Review deliverable validation point during kickoff: {q}"

            elif mapped_gate_id == "G01-04" and baseline.milestones:
                stop_words_m = {'date', 'dates', 'milestone', 'milestones', 'schedule', 'timeline', 'delivery', 'plan', 'project', 'external', 'internal', 'buffer', 'occur'}
                for m in baseline.milestones:
                    m_id_match = m.id.lower() in q_lower
                    m_desc_words = [w for w in re.findall(r'\w+', (m.description or "").lower()) if len(w) > 3 and w not in stop_words_m]
                    m_desc_match = any(w in q_lower for w in m_desc_words) if m_desc_words else False
                    if m_id_match or m_desc_match:
                        has_ext_action = any(a.target_entity_id == m.id and a.target_column_header == "External Date" for a in action_items)
                        target_table = "Milestone Delivery Plan"
                        target_entity_id = m.id
                        if not has_ext_action:
                            target_col = "External Date"
                            req_action = f"Confirm external milestone schedule for {m.id}."
                        elif m.internal_buffer_date is None:
                            target_col = "Internal Buffer Date"
                            req_action = f"Confirm internal buffer schedule for {m.id}."
                        else:
                            target_col = "Owner"
                            req_action = f"Confirm milestone owner for {m.id}."
                        break
                if not target_entity_id:
                    target_table = "SOW Interpretation Summary"
                    target_col = "Ambiguities & Clarification Notes"
                    req_action = f"Confirm milestone schedule during kickoff: {q}"

            elif mapped_gate_id == "G01-08" and baseline.talent_onboarding and baseline.talent_onboarding.delivery_talent_roster:
                stop_words_t = {'talent', 'staffing', 'role', 'roles', 'requirement', 'requirements', 'resource', 'resources', 'delivery', 'team', 'member', 'measured', 'performance'}
                for tm in baseline.talent_onboarding.delivery_talent_roster:
                    tm_words = [w for w in re.findall(r'\w+', tm.role.lower()) if len(w) > 3 and w not in stop_words_t]
                    if (tm.role.lower() in q_lower) or (tm_words and any(w in q_lower for w in tm_words)):
                        target_table = "Talent Onboarding Record"
                        target_col = "Named Talent"
                        target_entity_id = tm.role
                        req_action = f"Confirm candidate staffing for {tm.role}."
                        break
                if not target_entity_id:
                    target_table = "SOW Interpretation Summary"
                    target_col = "Ambiguities & Clarification Notes"
                    req_action = f"Review staffing requirements during kickoff: {q}"

            elif mapped_gate_id == "G01-09" and baseline.stakeholders:
                for sh in baseline.stakeholders:
                    if sh.name.lower() in q_lower or (sh.role and sh.role.lower() in q_lower):
                        target_table = "Stakeholder and Responsibility Model"
                        target_col = "Decision Rights"
                        target_entity_id = sh.name
                        req_action = f"Confirm client sign-off sponsor authority for {sh.name}."
                        break
                if not target_entity_id and baseline.stakeholders:
                    target_table = "Stakeholder and Responsibility Model"
                    target_col = "Decision Rights"
                    target_entity_id = baseline.stakeholders[0].name
                    req_action = "Confirm client sign-off sponsor authority."

            elif mapped_gate_id == "G01-11" and baseline.communications_plan:
                target_table = "Communications and Reporting Plan"
                target_col = "Audience"
                target_entity_id = baseline.communications_plan[0].name
                req_action = "Confirm weekly status report distribution list."

            elif mapped_gate_id == "G01-07":
                clean_q = re.sub(r'\[\s*(?:CONFIRMATION\s*REQUIRED|CONFIRMATION_REQUIRED|UNDEFINED|UNASSIGNED|UNASSIGNED\s*-\s*TO\s*BE\s*CONFIRMED|TBD)\s*\]', '', q, flags=re.IGNORECASE).strip()
                clean_q = re.sub(r'\s{2,}', ' ', clean_q).strip()
                target_table = "SOW Interpretation Summary"
                target_col = "Customer Obligations & Prerequisites"
                req_action = f"Issue access prerequisites list to client sponsor: {clean_q or q}"

            else:
                clean_q = re.sub(r'\[\s*(?:CONFIRMATION\s*REQUIRED|CONFIRMATION_REQUIRED|UNDEFINED|UNASSIGNED|UNASSIGNED\s*-\s*TO\s*BE\s*CONFIRMED|TBD)\s*\]', '', q, flags=re.IGNORECASE).strip()
                clean_q = re.sub(r'\s{2,}', ' ', clean_q).strip()
                target_table = "SOW Interpretation Summary"
                target_col = "Ambiguities & Clarification Notes"
                req_action = f"Review and clarify during mobilization kickoff: {clean_q or q}"

            clean_q = re.sub(r'\[?(?:CONFIRMATION REQUIRED|UNDEFINED|UNASSIGNED|UNASSIGNED\s*-\s*TO BE CONFIRMED)\]?', '', q, flags=re.IGNORECASE).strip()
            clean_q = re.sub(r'\s{2,}', ' ', clean_q).strip()

            action_items.append(
                ActionRequiredItem(
                    action_id=f"ACT-{act_counter:02d}",
                    item_type="Open Clarification",
                    checklist_id=mapped_gate_id,
                    related_artifact=artifact,
                    target_table_title=target_table,
                    target_column_header=target_col,
                    target_entity_id=target_entity_id,
                    finding_description=clean_q or q,
                    required_action=req_action,
                    owner=owner,
                    resolution_deadline="Prior to Mobilize Kickoff",
                    score_recovery_delta=score_delta,
                    target_gate_impact=meta.get("impact", f"Clears {mapped_gate_id} to Approved"),
                )
            )
            act_counter += 1

        # 3. Enforce Score Recovery Invariant: baseline_score + sum(deltas) <= 100.0
        max_recovery = round(max(0.0, 100.0 - baseline.readiness_score), 1)
        total_raw_delta = round(sum(a.score_recovery_delta for a in action_items), 1)

        if total_raw_delta > max_recovery and total_raw_delta > 0:
            scale = max_recovery / total_raw_delta
            for a in action_items:
                a.score_recovery_delta = round(a.score_recovery_delta * scale, 1)

            # Fix rounding drift if sum exceeds max_recovery
            current_sum = round(sum(a.score_recovery_delta for a in action_items), 1)
            if current_sum > max_recovery and action_items:
                excess = round(current_sum - max_recovery, 1)
                action_items[-1].score_recovery_delta = round(
                    max(0.0, action_items[-1].score_recovery_delta - excess), 1
                )

        # 4. Link action items to affected domain artifacts
        cls.link_action_items_to_artifacts(baseline, action_items)

        return action_items

    @classmethod
    def link_action_items_to_artifacts(
        cls, baseline: StartupKitBaseline, action_items: Optional[List[ActionRequiredItem]] = None
    ) -> None:
        """Link generated action items strictly to matching domain artifacts based on target entity IDs."""
        items = action_items if action_items is not None else baseline.action_required_items

        # Reset existing links
        if baseline.deliverables:
            for d in baseline.deliverables:
                d.linked_action_id = None
        if baseline.milestones:
            for m in baseline.milestones:
                m.linked_action_id = None
        if baseline.backlog_seed:
            for wp in baseline.backlog_seed:
                wp.linked_action_id = None
        if baseline.dependencies_assumptions:
            for da in baseline.dependencies_assumptions:
                da.linked_action_id = None
        if baseline.raid_items:
            for r in baseline.raid_items:
                r.linked_action_id = None
        if baseline.talent_onboarding and baseline.talent_onboarding.delivery_talent_roster:
            for tm in baseline.talent_onboarding.delivery_talent_roster:
                tm.linked_action_id = None
        if baseline.contract_ambiguities:
            for ca in baseline.contract_ambiguities:
                ca.linked_action_id = None
        if baseline.stakeholders:
            for sh in baseline.stakeholders:
                sh.linked_action_id = None
        if baseline.communications_plan:
            for cp in baseline.communications_plan:
                cp.linked_action_id = None

        if not items:
            return

        for act in items:
            if not act.target_entity_id:
                continue

            ent_id = act.target_entity_id.lower().strip()
            tbl = (act.target_table_title or "").lower().strip()

            # 1. Deliverables
            if "deliverable" in tbl and baseline.deliverables:
                for d in baseline.deliverables:
                    if d.id.lower().strip() == ent_id and d.linked_action_id is None:
                        d.linked_action_id = act.action_id
                        break

            # 2. Milestones
            elif "milestone" in tbl and baseline.milestones:
                for m in baseline.milestones:
                    if m.id.lower().strip() == ent_id and m.linked_action_id is None:
                        m.linked_action_id = act.action_id
                        break

            # 3. Work Packages / Backlog Seed
            elif "backlog" in tbl or "scope" in tbl and baseline.backlog_seed:
                for wp in baseline.backlog_seed:
                    if wp.id.lower().strip() == ent_id and wp.linked_action_id is None:
                        wp.linked_action_id = act.action_id
                        break

            # 4. RAID Log
            elif "raid" in tbl and baseline.raid_items:
                for r in baseline.raid_items:
                    r_id = (getattr(r, "id", None) or r.description[:25]).lower().strip()
                    if (r_id == ent_id or ent_id in r_id or r_id in ent_id) and r.linked_action_id is None:
                        r.linked_action_id = act.action_id
                        break

            # 5. Talent Onboarding
            elif "talent" in tbl and baseline.talent_onboarding and baseline.talent_onboarding.delivery_talent_roster:
                for tm in baseline.talent_onboarding.delivery_talent_roster:
                    if tm.role.lower().strip() == ent_id and tm.linked_action_id is None:
                        tm.linked_action_id = act.action_id
                        break

            # 7. Stakeholders
            elif "stakeholder" in tbl and baseline.stakeholders:
                for sh in baseline.stakeholders:
                    if sh.name.lower().strip() == ent_id and sh.linked_action_id is None:
                        sh.linked_action_id = act.action_id
                        break

            # 8. Communications Plan
            elif "communication" in tbl and baseline.communications_plan:
                for cp in baseline.communications_plan:
                    if cp.name.lower().strip() == ent_id and cp.linked_action_id is None:
                        cp.linked_action_id = act.action_id
                        break

    @classmethod
    def evaluate_and_rescore(cls, baseline: StartupKitBaseline) -> StartupKitBaseline:
        """Recalculate dimensional readiness scores, gate decision, and action items for a baseline."""
        cls.synchronize_open_questions_with_artifacts(baseline)
        cls.synchronize_checklist_with_artifacts(baseline)
        composite_score, readiness_breakdown = cls.compute_scores(baseline)
        open_exceptions = [
            i for i in baseline.readiness_checklist if i.exception_required or i.status == "Exception Required"
        ]
        has_questions = len(baseline.open_questions) > 0

        pmo_val = baseline.charter.pmo_lead if baseline.charter else (baseline.author_name or "PMO Lead")
        author_name = baseline.author_name or pmo_val or "PMO Lead"

        gate_decision, workflow_state = cls.determine_gate_decision(
            composite_score=composite_score,
            open_exceptions_count=len(open_exceptions),
            has_questions=has_questions,
            sla_met=baseline.sla_met,
            segregation_verified=baseline.segregation_of_duties_verified,
            author_name=author_name,
            reviewer_names=baseline.reviewer_names,
            concurring_approver=baseline.concurring_approver_name,
            comments_prefix="Readiness baseline re-evaluated against Section 4 requirements.",
        )
        gate_decision.readiness_breakdown = readiness_breakdown

        baseline.readiness_score = composite_score
        baseline.readiness_breakdown = readiness_breakdown
        baseline.workflow_state = workflow_state
        baseline.gate_decision = gate_decision
        if baseline.governance_context:
            baseline.governance_context.workflow_state = workflow_state

        action_required_items = cls.generate_action_required_items(baseline)
        baseline.action_required_items = action_required_items
        cls.link_action_items_to_artifacts(baseline)

        return baseline

    @classmethod
    def calculate_score_recovery(cls, action_items: List[ActionRequiredItem]) -> float:
        """Calculate total estimated score recovery potential from action items."""
        return round(sum(a.score_recovery_delta for a in action_items), 1)
