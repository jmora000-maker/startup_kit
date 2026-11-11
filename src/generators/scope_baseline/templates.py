"""Deterministic extraction templates and commercial framing rules for Scope Baseline (HTL-108)."""

import logging
from typing import List, Optional
from src.core.models import StartupKitBaseline
from src.generators.scope_baseline.models import (
    ScopeBaselineSummaryRow,
    ChangeDecisionMatrixRow,
    DecisionRuleControlRow,
    ClassificationGuideRow,
    PracticalDecisionExample,
)

logger = logging.getLogger(__name__)


def resolve_contract_variant(contract_type: Optional[str]) -> str:
    """Normalize contract_type into either 'Fixed Bid' or 'Time and Materials'."""
    if not contract_type:
        logger.warning("Unset contract_type; defaulting Scope Baseline variant to 'Time and Materials'")
        return "Time and Materials"
    ct_lower = contract_type.strip().lower()
    if "fixed" in ct_lower:
        return "Fixed Bid"
    if any(k in ct_lower for k in ("time", "t&m", "tm", "materials", "hourly", "rate", "consumption")):
        return "Time and Materials"
    logger.warning("Unrecognized contract_type '%s'; defaulting Scope Baseline variant to 'Time and Materials'", contract_type)
    return "Time and Materials"


def _format_bullet_list(items: List[str], default_text: str = "None stated in baseline.") -> str:
    """Format a string list into bulleted text."""
    clean = [str(x).strip() for x in items if str(x).strip() and not str(x).startswith("[CONFIRMATION")]
    if not clean:
        return default_text
    return "\n".join(f"• {item}" if not item.startswith("•") else item for item in clean)


def build_table1_summary_rows(baseline: StartupKitBaseline, variant: str) -> List[ScopeBaselineSummaryRow]:
    """Build the 6 rows for Table 1: Scope Baseline Summary."""
    charter = baseline.charter
    sow_int = baseline.sow_interpretation
    is_fixed = variant == "Fixed Bid"

    # Row 1: Engagement Objective & Purpose
    purpose_parts = []
    if charter and charter.project_purpose and not charter.project_purpose.startswith("[CONFIRMATION"):
        purpose_parts.append(charter.project_purpose)
    if charter and charter.problem_statement and not charter.problem_statement.startswith("[CONFIRMATION"):
        purpose_parts.append(f"Problem Solved: {charter.problem_statement}")
    if charter and charter.delivery_objectives:
        purpose_parts.append("Key Objectives:\n" + _format_bullet_list(charter.delivery_objectives))
    auth_r1 = "\n\n".join(purpose_parts) if purpose_parts else "Authorized project delivery objectives as defined in the project charter and baseline."

    excl_parts = []
    if charter and charter.exclusions:
        excl_parts.extend(charter.exclusions)
    if sow_int and sow_int.out_of_scope_items:
        excl_parts.extend(sow_int.out_of_scope_items)
    excl_r1 = _format_bullet_list(excl_parts, default_text="Any strategic initiatives, uncontracted transformation work, or activities outside stated project objectives.")

    # Row 2: Application Scope & Boundary
    app_scope = []
    if charter and charter.high_level_scope:
        app_scope.extend(charter.high_level_scope)
    if sow_int and sow_int.platform_environment_commitments:
        app_scope.extend(sow_int.platform_environment_commitments)
    auth_r2 = _format_bullet_list(app_scope, default_text="Core application features, technical pipelines, and contracted platforms specified in the SOW.")
    excl_r2 = _format_bullet_list(
        [x for x in excl_parts if any(k in x.lower() for k in ("platform", "system", "environment", "infra", "app", "integration", "migration"))] or
        ["Third-party systems, unlisted external APIs, legacy platform remediation, or uncontracted target environments."],
        default_text="Third-party system modifications and uncontracted technical environments."
    )

    # Row 3: Authorized Deliverables & Work Streams
    deliv_items = []
    if baseline.deliverables:
        for d in baseline.deliverables:
            desc = f" ({d.description})" if d.description and not d.description.startswith("[CONFIRMATION") else ""
            deliv_items.append(f"{d.id}: {d.name}{desc}")
    elif charter and charter.key_deliverables_summary:
        deliv_items.extend(charter.key_deliverables_summary)
    auth_r3 = _format_bullet_list(deliv_items, default_text="Formally contracted project deliverables and milestone gates.")
    excl_r3 = (
        "Uncontracted features, ancillary documentation not specified in deliverable acceptance criteria, and post-delivery custom enhancements without an approved Change Order."
        if is_fixed else
        "Requests exceeding approved weekly capacity allocations or unapproved work packages outside active work authorizations."
    )

    # Row 4: Delivery Model & Service Boundaries (Neutral framing)
    delivery_model_str = charter.delivery_model if (charter and charter.delivery_model) else "Toptal Talent Team (Agile/Milestone Hybrid)"
    if is_fixed:
        auth_r4 = (
            f"Delivery structured under {delivery_model_str}. Team execution is bounded strictly to the contracted milestone "
            "deliverables and formal acceptance review windows. Services include delivery execution, milestone reporting, and structured handoffs."
        )
        excl_r4 = (
            "Ongoing operational production support, uncontracted continuous consulting, ad-hoc organizational change management, "
            "and out-of-scope architectural investigations not tied to milestone acceptance."
        )
    else:
        auth_r4 = (
            f"Delivery structured under {delivery_model_str}. Team effort is governed by agreed work package prioritization and authorized "
            "weekly capacity allocations. Services encompass contracted technical execution, structured advisory/assessment, and delivery coordination."
        )
        excl_r4 = (
            "24/7 on-call production operations, unapproved staffing additions, off-hours support outside authorized burn envelopes, "
            "and delivery efforts exceeding agreed Not-to-Exceed (NTE) thresholds."
        )

    # Row 5: Operating Assumptions & Dependencies
    dep_items = []
    if baseline.dependencies_assumptions:
        for item in baseline.dependencies_assumptions:
            impact = f" [Impact: {item.impact_if_unmet}]" if item.impact_if_unmet else ""
            dep_items.append(f"{item.id} ({item.type}): {item.description}{impact}")
    elif sow_int and sow_int.dependencies:
        dep_items.extend(sow_int.dependencies)
    if sow_int and sow_int.customer_obligations:
        for cob in sow_int.customer_obligations:
            dep_items.append(f"Client Obligation: {cob}")
    auth_r5 = _format_bullet_list(dep_items, default_text="Timely client reviews, environment provisioning, credential access, and designated stakeholder approvals.")
    excl_r5 = (
        "Absorbing project delays caused by unfulfilled client prerequisites or third-party blockers without schedule or commercial adjustment."
    )

    # Row 6: Commercial Controls & Governance
    guardrails = baseline.commercial_guardrails
    gov_tier = baseline.governance_tier or "Partnered"
    if is_fixed:
        approved_rule = guardrails.approved_work_rule if guardrails else "Only authorized project scope and approved Change Orders are authorized for execution."
        change_trigger = guardrails.change_control_trigger if guardrails else "Material scope shift, timeline variance > 5 days, or deliverable criteria alteration."
        auth_r6 = (
            f"Governance Tier: {gov_tier} (Fixed Bid). {approved_rule} Billing is tied directly to formal deliverable and milestone acceptance. "
            f"Change trigger: {change_trigger}."
        )
        excl_r6 = (
            "Unapproved work-at-risk, verbal scope changes, informal requirement additions, or work performed without a countersigned Change Order."
        )
    else:
        approved_rule = guardrails.approved_work_rule if guardrails else "Only authorized work packages and prioritized tasks within agreed weekly effort caps are authorized for execution."
        change_trigger = guardrails.change_control_trigger if guardrails else "Burn rate exceeding weekly cap by >10% or scope addition requiring NTE increase."
        auth_r6 = (
            f"Governance Tier: {gov_tier} (Time & Materials). {approved_rule} Billing is based on approved timesheets and authorized effort burn. "
            f"Change trigger: {change_trigger}."
        )
        excl_r6 = (
            "Effort burn exceeding contractual NTE ceiling, work on unauthorized tasks or out-of-scope work packages, or unbudgeted staffing additions without written approval."
        )

    return [
        ScopeBaselineSummaryRow(
            dimension="Engagement Objective & Purpose",
            authorized_work=auth_r1,
            excluded_scope=excl_r1,
        ),
        ScopeBaselineSummaryRow(
            dimension="Application Scope & Boundary",
            authorized_work=auth_r2,
            excluded_scope=excl_r2,
        ),
        ScopeBaselineSummaryRow(
            dimension="Authorized Deliverables & Work Streams",
            authorized_work=auth_r3,
            excluded_scope=excl_r3,
        ),
        ScopeBaselineSummaryRow(
            dimension="Delivery Model & Service Boundaries",
            authorized_work=auth_r4,
            excluded_scope=excl_r4,
        ),
        ScopeBaselineSummaryRow(
            dimension="Operating Assumptions & Dependencies",
            authorized_work=auth_r5,
            excluded_scope=excl_r5,
        ),
        ScopeBaselineSummaryRow(
            dimension="Commercial Controls & Governance",
            authorized_work=auth_r6,
            excluded_scope=excl_r6,
        ),
    ]


def build_table2_change_matrix_rows(baseline: StartupKitBaseline, variant: str) -> List[ChangeDecisionMatrixRow]:
    """Build the 4 rows for Table 2: Change Decision Matrix."""
    is_fixed = variant == "Fixed Bid"

    if is_fixed:
        return [
            ChangeDecisionMatrixRow(
                classification="Clarification",
                trigger_condition="Minor requirement interpretation or design refinement within an authorized deliverable that does not affect cost, acceptance criteria, or milestone dates.",
                governance_action="Logged in Project Decision Log by Talent PM and Delivery Manager; aligned with client lead in weekly cadence.",
                commercial_impact="Zero commercial impact. Delivered within existing fixed-fee milestone price.",
            ),
            ChangeDecisionMatrixRow(
                classification="Reprioritization",
                trigger_condition="Client requests adjusting the sequence of work packages or swapping an equivalent feature within an in-progress deliverable without increasing total effort or altering milestone acceptance dates.",
                governance_action="Delivery Manager and PMO Lead evaluate equal complexity trade-off; documented in Decision Log with written client concurrence.",
                commercial_impact="Neutral budget impact. Milestone delivery schedule and total fixed price remain unchanged.",
            ),
            ChangeDecisionMatrixRow(
                classification="Expansion",
                trigger_condition="Client requests new functional scope, additional environments, or material modification to contracted deliverable acceptance criteria.",
                governance_action="Execution halts on requested item; Delivery Manager scopes impact and PMO Lead drafts formal Change Order with revised pricing and timeline for executive sign-off.",
                commercial_impact="Material commercial impact. Requires formal Change Order adjusting total fixed contract fee and milestone schedule.",
            ),
            ChangeDecisionMatrixRow(
                classification="Dependency Impact",
                trigger_condition="Client prerequisite delay (e.g., environment access, stakeholder review sign-off, or external API provision) exceeds contractual turnaround window.",
                governance_action="Delivery Manager raises formal Risk/Blocker notification; PMO Lead initiates Schedule Relief protocol and adjusts impacted milestone dates.",
                commercial_impact="Schedule baseline extended by equivalent delay duration. If standby effort is incurred, commercial adjustment or stand-down protocol is enacted.",
            ),
        ]
    else:
        return [
            ChangeDecisionMatrixRow(
                classification="Clarification",
                trigger_condition="Interpretation of requirements, methodology refinement, or operational detailing within authorized work packages that fits within standard weekly capacity.",
                governance_action="Talent PM / Delivery Lead clarifies task specifications; aligned with Client Lead in regular delivery cadence without formal escalation.",
                commercial_impact="Zero commercial impact. Consumes standard authorized weekly hourly capacity.",
            ),
            ChangeDecisionMatrixRow(
                classification="Reprioritization",
                trigger_condition="Client directs shifting team focus to higher-priority work packages or deferring scheduled tasks within the authorized delivery cycle.",
                governance_action="Talent PM resequences task priorities with Client Lead; Delivery Manager confirms burn rate and capacity alignment.",
                commercial_impact="Budget neutral within authorized capacity envelope; consumes standard weekly hours without NTE variance.",
            ),
            ChangeDecisionMatrixRow(
                classification="Expansion",
                trigger_condition="Client requests additional work streams, expanded project scope, or staffing additions that will exhaust the current NTE budget ceiling.",
                governance_action="Delivery Manager forecasts budget impact; PMO Lead initiates Work Authorization / NTE ceiling increase request for client executive approval.",
                commercial_impact="Material commercial impact. Requires authorized increase to total NTE fee ceiling or extended billing authorization.",
            ),
            ChangeDecisionMatrixRow(
                classification="Dependency Impact",
                trigger_condition="Client dependency, data provision delay, or access blocker impedes active delivery tasks, risking inefficient team burn.",
                governance_action="Talent PM pivots team to unblocked work packages; Delivery Manager issues blocker escalation. If idle, team stand-down or capacity throttle is triggered.",
                commercial_impact="Hours burn redirected to secondary productive tasks to protect investment; schedule timeline adjusted without unapproved budget burn.",
            ),
        ]


def build_table3_decision_rules_rows(baseline: StartupKitBaseline, variant: str) -> List[DecisionRuleControlRow]:
    """Build the 5 rows for Table 3: Decision Rules & Commercial Controls."""
    is_fixed = variant == "Fixed Bid"

    if is_fixed:
        return [
            DecisionRuleControlRow(
                control_dimension="Deliverable Boundary",
                governing_rule="Work is strictly gated by the formal deliverable acceptance criteria documented in the SOW.",
                boundary_violation_trigger="Request for features, documentation formats, or integrations not specified in signed acceptance criteria.",
                commercial_control_route="Execution rejected or routed through formal Change Order process with explicit fee adjustment.",
            ),
            DecisionRuleControlRow(
                control_dimension="Domain & Application Scope",
                governing_rule="Development and configuration are restricted to the explicitly listed platforms, systems, and APIs.",
                boundary_violation_trigger="Requests to integrate unlisted legacy systems, build on unsupported clouds, or support external platforms.",
                commercial_control_route="Delivery Manager issues Scope Notice; work deferred until supplemental SOW / Change Order is executed.",
            ),
            DecisionRuleControlRow(
                control_dimension="Service Depth & Delivery Boundaries",
                governing_rule="Services are bounded to milestone-driven design and build activities within the contracted delivery model.",
                boundary_violation_trigger="Requests for ongoing production on-call support, continuous operational maintenance, or general advisory.",
                commercial_control_route="PMO Lead clarifies delivery model boundary and directs client to separate Managed Services or T&M advisory agreement.",
            ),
            DecisionRuleControlRow(
                control_dimension="Effort Burn & NTE Ceilings",
                governing_rule="Milestone price is fixed; delivery team manages internal effort variance to meet agreed milestone dates.",
                boundary_violation_trigger="Internal effort overrun or unauthorized work-at-risk performed without written PMO Lead approval.",
                commercial_control_route="Zero billing variance passed to client; internal review required for team velocity and scope containment.",
            ),
            DecisionRuleControlRow(
                control_dimension="Core Dependency Health",
                governing_rule="Client must provide environments, access credentials, and review feedback within agreed contractual SLA windows.",
                boundary_violation_trigger="Client dependency unmet after 5 business days from agreed validation date.",
                commercial_control_route="Delivery Manager issues formal Dependency Delay Notice; downstream milestone dates extended on a day-for-day basis.",
            ),
        ]
    else:
        return [
            DecisionRuleControlRow(
                control_dimension="Deliverable Boundary",
                governing_rule="Work is guided by prioritized deliverable plans and authorized work packages aligned with overall SOW objectives.",
                boundary_violation_trigger="Direction to execute tasks that do not align with SOW objectives or lack documented client acceptance criteria.",
                commercial_control_route="Talent PM pauses task execution until Client Lead clarifies criteria and priority.",
            ),
            DecisionRuleControlRow(
                control_dimension="Domain & Application Scope",
                governing_rule="Activities focus on contracted target architectures, source repositories, and deployment environments.",
                boundary_violation_trigger="Introduction of complex out-of-scope technology stacks that dilute delivery capacity or derail scheduled milestones.",
                commercial_control_route="Delivery Manager assesses skill and capacity impact; aligns with client on delivery trade-offs.",
            ),
            DecisionRuleControlRow(
                control_dimension="Service Depth & Delivery Boundaries",
                governing_rule="Team provides technical execution, domain assessment, and delivery advisory within authorized weekly capacity.",
                boundary_violation_trigger="Requests for 24/7 incident management or unbudgeted off-hours standby.",
                commercial_control_route="Delivery Manager enforces standard working hours policy and proposes formal on-call rate structure if required.",
            ),
            DecisionRuleControlRow(
                control_dimension="Effort Burn & NTE Ceilings",
                governing_rule="Weekly hours are capped at contracted allocations; total spend is strictly bounded by contractual NTE ceiling.",
                boundary_violation_trigger="Burn rate exceeds weekly allocation by >10% or total project spend reaches 80% NTE threshold.",
                commercial_control_route="PMO Lead delivers monthly burn forecast and submits formal NTE Increase Amendment prior to budget exhaustion.",
            ),
            DecisionRuleControlRow(
                control_dimension="Core Dependency Health",
                governing_rule="Team requires timely unblocking and environment availability to maintain productive delivery progress and burn efficiency.",
                boundary_violation_trigger="External blocker halts active delivery tasks with no immediate secondary work packages available.",
                commercial_control_route="Delivery Manager triggers delivery plan resequencing; if blocker exceeds 3 days, stand-down or capacity reduction is enacted to protect client budget.",
            ),
        ]


def build_table4_classification_guide_rows(baseline: StartupKitBaseline, variant: str) -> List[ClassificationGuideRow]:
    """Build the 4 rows for Table 4: Scope Classification Guide."""
    is_fixed = variant == "Fixed Bid"

    if is_fixed:
        return [
            ClassificationGuideRow(
                classification="Clarification",
                operational_characteristics="Refining acceptance criteria, UI/UX details, or technical design within an authorized deliverable.",
                budget_milestone_impact="No cost impact ($0); milestone schedule unchanged.",
                approval_pathway="Talent PM & DM approval; logged in Project Decision Log.",
            ),
            ClassificationGuideRow(
                classification="Reprioritization",
                operational_characteristics="Swapping equivalent complexity work packages or reordering tasks within a deliverable.",
                budget_milestone_impact="Budget neutral; milestone delivery dates unchanged.",
                approval_pathway="DM & Client Lead written alignment; PMO Lead concurrence.",
            ),
            ClassificationGuideRow(
                classification="Expansion",
                operational_characteristics="Adding new functional modules, third-party integrations, or expanding deliverable boundaries.",
                budget_milestone_impact="Increases fixed contract price and/or extends timeline.",
                approval_pathway="PMO Lead & Contracting issue formal Change Order; client sign-off.",
            ),
            ClassificationGuideRow(
                classification="Dependency Impact",
                operational_characteristics="Client review turnaround delays, delayed credentials, or late client-owned prerequisites.",
                budget_milestone_impact="Schedule extended day-for-day; potential standby fee.",
                approval_pathway="DM notice to Client Sponsor; PMO Lead schedule update.",
            ),
        ]
    else:
        return [
            ClassificationGuideRow(
                classification="Clarification",
                operational_characteristics="Detailing activity requirements, clarifying assessment criteria, or refining execution approach.",
                budget_milestone_impact="Consumes planned weekly hours; zero variance to burn rate.",
                approval_pathway="Talent PM & Client Lead alignment; logged in Decision Log.",
            ),
            ClassificationGuideRow(
                classification="Reprioritization",
                operational_characteristics="Reordering work priorities, resequencing tasks, or deferring non-critical activities.",
                budget_milestone_impact="Zero budget impact; effort stays within weekly envelope.",
                approval_pathway="Client Lead directive; DM capacity and burn alignment.",
            ),
            ClassificationGuideRow(
                classification="Expansion",
                operational_characteristics="Introducing new workstreams, adding roles, or expanding scope beyond authorized NTE hours.",
                budget_milestone_impact="Requires contractual NTE ceiling increase or added billing.",
                approval_pathway="PMO Lead & Client Executive execute SOW Amendment / NTE Increase.",
            ),
            ClassificationGuideRow(
                classification="Dependency Impact",
                operational_characteristics="Third-party outages, delayed data/environment access, or unavailable client SMEs.",
                budget_milestone_impact="Team pivots; if unresolvable, capacity throttled to avoid burn.",
                approval_pathway="DM escalation; PMO Lead & Client Lead agree standby protocol.",
            ),
        ]


def build_table5_fallback_examples(baseline: StartupKitBaseline, variant: str) -> List[PracticalDecisionExample]:
    """Deterministic fallback synthesizing 4 grounded practical decision scenarios if LLM synthesis is bypassed or unavailable."""
    is_fixed = variant == "Fixed Bid"
    proj_name = baseline.project_name or "Project"
    
    # Grounding elements from real baseline
    deliv_name = baseline.deliverables[0].name if baseline.deliverables else "Core Solution Deliverable"
    dep_desc = baseline.dependencies_assumptions[0].description if baseline.dependencies_assumptions else "Client cloud environment and API credentials"
    excl_desc = baseline.charter.exclusions[0] if (baseline.charter and baseline.charter.exclusions) else "Third-party platform legacy remediation and custom reporting integrations"

    if is_fixed:
        return [
            PracticalDecisionExample(
                classification="Clarification",
                scenario_description=f"During execution of '{deliv_name}', the client requests adjusting the data validation logic and schema error formatting to align with internal data naming standards.",
                analysis="The request refines internal formatting within the agreed deliverable boundary without adding new functional workflows or altering milestone delivery dates.",
                resolution_and_governance="Classified as Clarification. Talent PM approves refinement within active delivery cycle; logged in Decision Log with zero impact on milestone price or delivery schedule.",
            ),
            PracticalDecisionExample(
                classification="Reprioritization",
                scenario_description=f"The client requests delivering the reporting dashboard module ahead of the automated export utility within '{deliv_name}' to support an upcoming executive demo.",
                analysis="The two components have equivalent estimated effort and fall entirely within the authorized milestone boundary. Total effort and completion date are unaffected.",
                resolution_and_governance="Classified as Reprioritization. Delivery Manager and Client Lead approve the sequence trade-off in writing; documented in Decision Log with no change to contract price.",
            ),
            PracticalDecisionExample(
                classification="Expansion",
                scenario_description=f"The client requests extending '{deliv_name}' to incorporate '{excl_desc}', which was explicitly excluded in the SOW.",
                analysis="The requested functionality represents out-of-scope work that requires additional architectural build, testing, and dedicated effort not budgeted in the fixed fee.",
                resolution_and_governance="Classified as Expansion. Delivery Manager halts out-of-scope work; PMO Lead drafts formal Change Order with additional fee and milestone extension for client executive sign-off.",
            ),
            PracticalDecisionExample(
                classification="Dependency Impact",
                scenario_description=f"Delivery is blocked because '{dep_desc}' is delayed by 7 business days past the scheduled validation date.",
                analysis="The contractual dependency is a prerequisite for deliverable verification and end-to-end testing, impeding milestone sign-off through no fault of the delivery team.",
                resolution_and_governance="Classified as Dependency Impact. Delivery Manager issues formal Blocker Notice; PMO Lead adjusts downstream milestone gates day-for-day under the contractual Schedule Relief protocol.",
            ),
        ]
    else:
        return [
            PracticalDecisionExample(
                classification="Clarification",
                scenario_description=f"During delivery review for '{deliv_name}', the client lead clarifies the acceptance criteria for error notification handling.",
                analysis="Clarifies implementation details for an authorized task without expanding project scope or exceeding weekly capacity.",
                resolution_and_governance="Classified as Clarification. Talent PM updates task acceptance criteria in the deliverable plan; executed within standard weekly capacity.",
            ),
            PracticalDecisionExample(
                classification="Reprioritization",
                scenario_description=f"The client requests deferring two lower-priority integration tasks in '{deliv_name}' to expedite a high-priority data processing workflow in the upcoming delivery cycle.",
                analysis="Total estimated effort and weekly team capacity remain balanced, shifting focus without increasing overall effort burn.",
                resolution_and_governance="Classified as Reprioritization. Client Lead reorders work priorities; Delivery Manager confirms burn rate stays within weekly hours cap.",
            ),
            PracticalDecisionExample(
                classification="Expansion",
                scenario_description=f"The client requests spinning up an additional work stream to build '{excl_desc}', which will cause total project spend to exceed the contractual NTE ceiling.",
                analysis="Adding new functional scope and dedicated engineering capacity represents a material scope expansion beyond the authorized NTE budget envelope.",
                resolution_and_governance="Classified as Expansion. PMO Lead and Delivery Manager prepare a forecast impact assessment; client executive executes a formal Work Authorization / NTE ceiling increase.",
            ),
            PracticalDecisionExample(
                classification="Dependency Impact",
                scenario_description=f"Development on '{deliv_name}' is impeded due to a 5-day outage and delayed access provisioning for '{dep_desc}'.",
                analysis="The access blocker prevents engineering progress on primary delivery tasks, creating a risk of inefficient hours burn.",
                resolution_and_governance="Classified as Dependency Impact. Talent PM pivots the team to secondary work packages; Delivery Manager escalates to Client Sponsor to resolve access without wasteful burn.",
            ),
        ]
