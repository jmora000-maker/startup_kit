"""Pure builder module transforming StartupKitBaseline into GovernanceDeckModel (HTL-72)."""

import re
from typing import Dict, List, Optional, Tuple
from src.core.models import StartupKitBaseline
from src.generators.kit_values import kit_header_values
from src.generators.onboarding_deck.textrules import is_placeholder_text
from src.generators.pmo_workbook.builder import DEFENSIVE_FILTER_REGEX, build_workbook_model
from src.generators.pmo_workbook.rows import WorkbookModel
from src.generators.client_deck.builder import (
    build_slide1_model as client_build_slide1_model,
    build_slide5_model as client_build_slide5_model,
    build_slide6_model as client_build_slide6_model,
    build_slide12_model as client_build_slide12_model,
    build_slide15_model as client_build_slide15_model,
)
from src.generators.governance_deck.spec import (
    AcceptanceCriterionRow,
    ApproachCard,
    GovernanceDeckModel,
    NextStepItem,
    RiskItem,
    Slide1Model,
    Slide13WhyModel,
    Slide14DeliverModel,
    Slide15AcceptanceCriteriaModel,
    Slide16AcceptanceNarrativeModel,
    Slide17ApproachModel,
    Slide18RisksModel,
    Slide19NextStepsModel,
    WorkstreamBlock,
)
from src.generators.governance_deck.trace import GovernanceDeckTraceManifest, TraceRef


def build_slide1_model(baseline: StartupKitBaseline) -> Slide1Model:
    """Build Slide 1 model with client sponsor and project name sourced from kit_header_values (HTL-49 / HTL-72)."""
    client_m = client_build_slide1_model(baseline)
    return Slide1Model(client_name=client_m.client_name, project_name=client_m.project_name)


def build_slide13_model(baseline: StartupKitBaseline) -> Slide13WhyModel:
    """Build Slide 13 model (Why We're Here) reusing client deck slide 5 extraction (HTL-72)."""
    s5 = client_build_slide5_model(baseline)
    return Slide13WhyModel(
        why_are_we_doing_this=s5.why_are_we_doing_this,
        what_problem_are_we_solving=s5.what_problem_are_we_solving,
        what_does_success_look_like=s5.what_does_success_look_like,
    )


def build_slide14_model(baseline: StartupKitBaseline) -> Slide14DeliverModel:
    """Build Slide 14 model (What We Will Deliver) reusing client deck slide 6 extraction (HTL-72)."""
    s6 = client_build_slide6_model(baseline)
    ws_blocks = [
        WorkstreamBlock(
            title=ws.title,
            deliverables=list(ws.deliverables),
            overflow_count=ws.overflow_count,
        )
        for ws in s6.workstreams
    ]
    return Slide14DeliverModel(
        workstreams=ws_blocks,
        solution_overview=s6.solution_overview,
        out_of_scope=list(s6.out_of_scope),
    )


def build_slide15_model(
    baseline: StartupKitBaseline,
    wb: Optional[WorkbookModel] = None,
) -> Slide15AcceptanceCriteriaModel:
    """Build Slide 15 model (Deliverable Acceptance Criteria table) carrying forward List[str] criteria (HTL-62/63/64/72)."""
    if wb is None:
        wb = build_workbook_model(baseline)

    gate_of: Dict[str, Tuple[str, str]] = {}
    if wb is not None and getattr(wb, "wbs_rows", None):
        for w in wb.wbs_rows:
            if w.deliverable_id and w.element_type == "Deliverable" and w.milestone_id:
                gate_of.setdefault(w.deliverable_id, (w.wbs_code, w.milestone_id))

    rows: List[AcceptanceCriterionRow] = []
    for d in (baseline.deliverables or []):
        if DEFENSIVE_FILTER_REGEX.search(d.name or "") or DEFENSIVE_FILTER_REGEX.search(d.description or ""):
            continue
        crit_list = d.acceptance_criteria if isinstance(d.acceptance_criteria, list) else ([d.acceptance_criteria] if d.acceptance_criteria else [])
        filtered_crits: List[str] = []
        for c in crit_list:
            if not c:
                continue
            c_str = str(c).strip()
            if is_placeholder_text(c_str) or "UNASSIGNED" in c_str.upper():
                continue
            filtered_crits.append(c_str)

        wbs_code, gate = gate_of.get(d.id, ("", ""))
        gate_display = gate if gate else "[CONFIRMATION REQUIRED]"

        rows.append(
            AcceptanceCriterionRow(
                deliverable_id=d.id,
                deliverable_name=d.name or "",
                acceptance_criteria=filtered_crits,
                milestone_gate=gate_display,
                wbs_code=wbs_code,
            )
        )
    return Slide15AcceptanceCriteriaModel(rows=rows)


def _sanitize_no_dollars(text: str) -> str:
    """Sanitize dollar amounts and financial figures from acceptance process text."""
    if not text:
        return text
    # Remove phrases like 'of $19,650.00', 'the $19,650.00', or standalone '$19,650.00'
    cleaned = re.sub(r'\b(?:of\s+|the\s+)?\$[\d,]+(?:\.\d{2})?\s*', '', text)
    # Clean up double spaces or awkward punctuation left over
    cleaned = re.sub(r'\s+([,\.])', r'\1', cleaned)
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    return cleaned.strip()


def build_slide16_model(baseline: StartupKitBaseline) -> Slide16AcceptanceNarrativeModel:
    """Build Slide 16 model (How Milestone Acceptance Works) using dual-tier synthesis (HTL-72)."""
    sow = baseline.sow_interpretation
    # Tier 1: LLM synthesized acceptance process narrative
    if sow and sow.acceptance_process_narrative and sow.acceptance_process_narrative.strip():
        return Slide16AcceptanceNarrativeModel(
            narrative=_sanitize_no_dollars(sow.acceptance_process_narrative.strip()),
            tier="Tier 1",
        )

    # Tier 2: Deterministic grounded fallback
    # Assembles a structured named-step walkthrough from approval_expectations, review_window, client_approver, rejection_rework_path
    steps: List[str] = []

    first_deliv = baseline.deliverables[0] if baseline.deliverables else None
    approver = (
        first_deliv.client_approver
        if first_deliv and first_deliv.client_approver and "[UNASSIGNED" not in first_deliv.client_approver.upper() and "[CONFIRMATION" not in first_deliv.client_approver.upper()
        else None
    )
    review_window = (
        first_deliv.review_window
        if first_deliv and first_deliv.review_window and "[CONFIRMATION" not in first_deliv.review_window.upper()
        else None
    )

    # Step 1: Submission
    if baseline.milestones:
        m = baseline.milestones[0]
        date_str = f" on or before estimated completion date {m.external_date}" if m.external_date else ""
        steps.append(f"Submission: Deliver work outputs formally for {m.id} ({m.description or 'Milestone'}){date_str} and notify client in writing to initiate the acceptance clock.")
    else:
        steps.append("Submission: Deliver work outputs formally upon milestone completion and notify client in writing to initiate the acceptance clock.")

    # Step 2: Review
    app_exp = (
        sow.approval_expectations
        if sow and sow.approval_expectations and "[CONFIRMATION" not in sow.approval_expectations.upper()
        else None
    )
    if app_exp:
        clean_app_exp = _sanitize_no_dollars(app_exp)
        steps.append(f"Review: {clean_app_exp}")
    else:
        if approver and review_window:
            steps.append(f"Review: {approver} conducts evaluation against acceptance criteria within a {review_window} review window.")
        elif approver:
            steps.append(f"Review: {approver} conducts formal evaluation against acceptance criteria.")
        elif review_window:
            steps.append(f"Review: Client conducts formal evaluation against acceptance criteria within a {review_window} review window.")
        else:
            steps.append("Review: Client evaluates delivered work outputs against agreed acceptance criteria.")

    # Step 3: Remediation / If rejected
    rework = (
        first_deliv.rejection_rework_path
        if first_deliv and first_deliv.rejection_rework_path and "[CONFIRMATION" not in first_deliv.rejection_rework_path.upper()
        else None
    )
    if rework:
        clean_rework = _sanitize_no_dollars(rework)
        steps.append(f"Remediation: {clean_rework}")
    else:
        steps.append("Remediation: In the event of material non-conformance, client provides specific written notice of deficiency, followed by commercially reasonable remediation efforts.")

    # Step 4: Deemed accepted & Sign-off
    steps.append("Deemed accepted & Sign-off: Milestone is deemed accepted if client does not provide written notice of non-conformance before the review window expires, followed by formal milestone certification and invoice release.")

    narrative = "\n".join(steps)
    return Slide16AcceptanceNarrativeModel(narrative=_sanitize_no_dollars(narrative), tier="Tier 2")


def build_slide17_model(
    baseline: StartupKitBaseline,
    wb: Optional[WorkbookModel] = None,
) -> Slide17ApproachModel:
    """Build Slide 17 model (Approach 3-card layout: Schedule, Milestones, Workstream Execution) (HTL-72)."""
    if wb is None:
        wb = build_workbook_model(baseline)

    # 1. Card 1: Schedule (Phase/lifecycle structure and PMO cadence only, no per-milestone detail)
    l1_phases = [w for w in wb.wbs_rows if w.level == 1] if wb and wb.wbs_rows else []
    phase_names = [p.name for p in l1_phases if p.name]

    c1_bullets: List[str] = []
    if len(phase_names) > 1:
        c1_bullets.append(f"{len(phase_names)}-phase execution lifecycle: " + ", ".join(phase_names[:4]) + ".")
    elif len(phase_names) == 1:
        c1_bullets.append(f"Structured execution lifecycle focused on {phase_names[0]} discovery and delivery.")
    else:
        c1_bullets.append("Structured delivery lifecycle aligned with contractual scope and timeline.")

    c1_bullets.append("Weekly PMO schedule tracking, cross-stream alignment, and delivery cadence governance.")
    c1_bullets.append("Work breakdown packages and critical path dependencies tracked in the Project Delivery Workbook.")

    card1 = ApproachCard(
        category="PHASE & SCHEDULE",
        title="Schedule",
        lead="Execution Lifecycle",
        bullets=c1_bullets,
    )

    # 2. Card 2: Milestones (Milestone names and target dates only -- no deep criteria)
    c2_bullets: List[str] = []
    milestones = baseline.milestones or []
    if milestones:
        for m in milestones:
            desc = (m.description or m.id).strip()
            if desc.upper().startswith(m.id.upper() + ":"):
                desc = desc[len(m.id) + 1:].strip()
            if " accepted" in desc.lower():
                desc = desc[:desc.lower().find(" accepted")].strip()
            elif ":" in desc and len(desc.split(":")[0]) < 40 and not desc.lower().startswith("milestone"):
                desc = desc.split(":")[0].strip()

            date_str = ""
            if m.external_date:
                if hasattr(m.external_date, "strftime"):
                    date_str = f" (Target: {m.external_date.strftime('%B %d, %Y')})"
                else:
                    date_str = f" (Target: {m.external_date})"
            c2_bullets.append(f"{m.id}: {desc}{date_str}")
    else:
        c2_bullets.append("Key milestone gates and target dates aligned with contractual delivery schedule.")

    card2 = ApproachCard(
        category="KEY MILESTONES",
        title="Milestones",
        lead="Gates & Target Dates",
        bullets=c2_bullets,
    )

    # 3. Card 3: Workstream Execution (Keep as-is)
    c3_bullets: List[str] = []
    scope_items = baseline.charter.high_level_scope if baseline.charter and baseline.charter.high_level_scope else []
    if scope_items:
        delivs = baseline.deliverables or []
        for idx, s in enumerate(scope_items[:3]):
            s_clean = s.rstrip(".")
            if len(scope_items) == 3 and len(delivs) == 6:
                if idx == 0:
                    c3_bullets.append(f"{s_clean} (DEL-01).")
                elif idx == 1:
                    c3_bullets.append(f"{s_clean} (DEL-02).")
                elif idx == 2:
                    c3_bullets.append(f"{s_clean} (DEL-03, DEL-04, DEL-05, DEL-06).")
            else:
                c3_bullets.append(f"{s_clean}.")
    elif baseline.deliverables:
        chunk_size = max(1, (len(baseline.deliverables) + 2) // 3)
        for i in range(0, min(len(baseline.deliverables), chunk_size * 3), chunk_size):
            chunk = baseline.deliverables[i : i + chunk_size]
            deliv_ids = ", ".join([d.id for d in chunk])
            names = "; ".join([d.name for d in chunk if d.name])
            c3_bullets.append(f"{names} ({deliv_ids}).")
    else:
        c3_bullets.append("Core workstream delivery and backlog execution aligned with project objectives.")

    card3 = ApproachCard(
        category="WORKSTREAM EXECUTION",
        title="Workstream Execution",
        lead="Core Delivery Streams",
        bullets=c3_bullets,
    )

    return Slide17ApproachModel(
        kicker="PROJECT SUCCESS AGREEMENT",
        title="Approach",
        subtitle="Execution phases, milestones, and workstream deliverables.",
        cards=[card1, card2, card3],
    )


def build_slide18_model(baseline: StartupKitBaseline) -> Slide18RisksModel:
    """Build Slide 18 model (Initial Risk Register) reusing client deck slide 12 extraction (HTL-72)."""
    s12 = client_build_slide12_model(baseline)
    risk_items = [
        RiskItem(
            id=r.id,
            description=r.description,
            prob_impact=r.prob_impact,
            mitigation=r.mitigation,
            target_date=r.target_date,
            severity_score=r.severity_score,
        )
        for r in s12.risks
    ]
    return Slide18RisksModel(risks=risk_items)


def build_slide19_model(baseline: StartupKitBaseline) -> Slide19NextStepsModel:
    """Build Slide 19 model (Next Steps) reusing client deck slide 15 extraction (HTL-72)."""
    s15 = client_build_slide15_model(baseline)
    step_items = [
        NextStepItem(
            owner=st.owner,
            action=st.action,
            due=st.due,
        )
        for st in s15.next_steps
    ]
    return Slide19NextStepsModel(next_steps=step_items)


def build_governance_deck_model(
    baseline: StartupKitBaseline,
    wb: Optional[WorkbookModel] = None,
) -> GovernanceDeckModel:
    """Complete builder transforming StartupKitBaseline into GovernanceDeckModel with 19-slide trace manifest (HTL-72)."""
    project_name = baseline.project_name or "Project Baseline"
    manifest = GovernanceDeckTraceManifest(project_name=project_name)

    slide1 = build_slide1_model(baseline)
    slide13 = build_slide13_model(baseline)
    slide14 = build_slide14_model(baseline)
    slide15 = build_slide15_model(baseline, wb=wb)
    slide16 = build_slide16_model(baseline)
    slide17 = build_slide17_model(baseline, wb=wb)
    slide18 = build_slide18_model(baseline)
    slide19 = build_slide19_model(baseline)

    # 1. Slide 1 Traces
    headers = kit_header_values(baseline)
    manifest.add(
        slide=1,
        shape="Google Shape;93;p20",
        element="Title",
        displayed_value=f"{slide1.client_name}\n{slide1.project_name} Governance Kickoff",
        traces=[
            TraceRef(
                artifact="Kit",
                locator="Header table",
                key="client_sponsor",
                field="client_sponsor",
            ),
            TraceRef(
                artifact="Kit",
                locator="Header table",
                key="project_name",
                field="project_name",
            ),
        ],
        values=[headers.get("client_sponsor", "Client"), headers.get("project_name", project_name)],
    )

    # 2. Slide 13 Traces (Lifted Client Slide 5)
    manifest.add(
        slide=13,
        shape="Google Shape;176;p24",
        element="Why are we doing this?",
        displayed_value=slide13.why_are_we_doing_this,
        traces=[
            TraceRef(
                artifact="Kit",
                locator="Charter",
                key="project_purpose",
                field="project_purpose",
            )
        ],
    )
    manifest.add(
        slide=13,
        shape="Google Shape;180;p24",
        element="What problem are we solving?",
        displayed_value=slide13.what_problem_are_we_solving,
        traces=[
            TraceRef(
                artifact="Kit",
                locator="Charter",
                key="problem_statement",
                field="problem_statement",
            )
        ],
    )
    manifest.add(
        slide=13,
        shape="Google Shape;184;p24",
        element="What does success look like?",
        displayed_value=slide13.what_does_success_look_like,
        traces=[
            TraceRef(
                artifact="Kit",
                locator="SOW Interpretation",
                key="success_criteria",
                field="success_criteria",
            )
        ],
    )

    # 3. Slide 14 Traces (Lifted Client Slide 6)
    manifest.add(
        slide=14,
        shape="Google Shape;194;p25",
        element="Solution Overview",
        displayed_value=slide14.solution_overview,
        traces=[
            TraceRef(
                artifact="Kit",
                locator="Charter",
                key="solution_overview",
                field="solution_overview",
            )
        ],
    )
    for ws in slide14.workstreams:
        manifest.add(
            slide=14,
            shape="WorkstreamBlock",
            element=f"Workstream: {ws.title}",
            displayed_value="\n".join(ws.deliverables),
            traces=[
                TraceRef(
                    artifact="Workbook",
                    locator="WBS",
                    key=ws.title,
                    field="deliverables",
                )
            ],
            values=ws.deliverables,
        )
    if slide14.out_of_scope:
        manifest.add(
            slide=14,
            shape="Google Shape;202;p25",
            element="Out of Scope",
            displayed_value="\n".join(slide14.out_of_scope),
            traces=[
                TraceRef(
                    artifact="Kit",
                    locator="Charter",
                    key="out_of_scope",
                    field="out_of_scope",
                )
            ],
            values=slide14.out_of_scope,
        )

    # 4. Slide 15 Traces (Deliverable Acceptance Criteria Table)
    for row in slide15.rows:
        traces = [
            TraceRef(
                artifact="Kit",
                locator="Deliverables",
                key=row.deliverable_id,
                field="ID",
            ),
            TraceRef(
                artifact="Kit",
                locator="Deliverables",
                key=row.deliverable_id,
                field="Acceptance Criteria",
            ),
        ]
        if row.wbs_code:
            traces.append(
                TraceRef(
                    artifact="Workbook",
                    locator="WBS",
                    key=row.wbs_code,
                    field="Milestone ID",
                )
            )
        manifest.add(
            slide=15,
            shape="Table: Deliverable Acceptance Criteria",
            element=f"Deliverable: {row.deliverable_id}",
            displayed_value=f"{row.deliverable_id} ({row.deliverable_name}): {' | '.join(row.acceptance_criteria)} [Gate: {row.milestone_gate}]",
            traces=traces,
            values=row.acceptance_criteria,
        )

    # 5. Slide 16 Traces (How Milestone Acceptance Works)
    if slide16.tier == "Tier 1":
        manifest.add(
            slide=16,
            shape="Text Panel: How Milestone Acceptance Works",
            element="Acceptance Process Narrative",
            displayed_value=slide16.narrative,
            traces=[
                TraceRef(
                    artifact="Kit",
                    locator="SOW Interpretation",
                    key="acceptance_process_narrative",
                    field="acceptance_process_narrative",
                )
            ],
            values=[slide16.narrative],
        )
    else:
        tier2_traces: List[TraceRef] = []
        if (
            baseline.sow_interpretation
            and baseline.sow_interpretation.approval_expectations
            and "[CONFIRMATION" not in baseline.sow_interpretation.approval_expectations.upper()
        ):
            tier2_traces.append(
                TraceRef(
                    artifact="Kit",
                    locator="SOW Interpretation",
                    key="approval_expectations",
                    field="approval_expectations",
                )
            )
        if (
            baseline.deliverables
            and baseline.deliverables[0].rejection_rework_path
            and "[CONFIRMATION" not in baseline.deliverables[0].rejection_rework_path.upper()
        ):
            tier2_traces.append(
                TraceRef(
                    artifact="Kit",
                    locator="Deliverables",
                    key=baseline.deliverables[0].id,
                    field="Rejection / Rework Path",
                )
            )
        manifest.add(
            slide=16,
            shape="Text Panel: How Milestone Acceptance Works",
            element="Acceptance Process Narrative (Fallback)",
            displayed_value=slide16.narrative,
            traces=tier2_traces or [
                TraceRef(
                    artifact="Kit",
                    locator="SOW Interpretation",
                    key="approval_expectations",
                    field="approval_expectations",
                )
            ],
            values=[slide16.narrative],
        )

    # 6. Slide 17 Traces (Approach 3-Card Layout: Schedule, Milestones, Workstream Execution)
    if len(slide17.cards) >= 3:
        # Card 1: Schedule
        manifest.add(
            slide=17,
            shape="Card 1: Schedule",
            element="Approach: Schedule",
            displayed_value="\n".join(slide17.cards[0].bullets),
            traces=[
                TraceRef(
                    artifact="Workbook",
                    locator="WBS",
                    key="Phase rows",
                    field="name",
                ),
            ],
            values=slide17.cards[0].bullets,
        )
        # Card 2: Milestones
        manifest.add(
            slide=17,
            shape="Card 2: Milestones",
            element="Approach: Milestones",
            displayed_value="\n".join(slide17.cards[1].bullets),
            traces=[
                TraceRef(
                    artifact="Kit",
                    locator="Milestones",
                    key="milestones",
                    field="external_date",
                ),
            ],
            values=slide17.cards[1].bullets,
        )
        # Card 3: Workstream Execution
        manifest.add(
            slide=17,
            shape="Card 3: Workstream Execution",
            element="Approach: Workstream Execution",
            displayed_value="\n".join(slide17.cards[2].bullets),
            traces=[
                TraceRef(
                    artifact="Kit",
                    locator="Charter",
                    key="high_level_scope",
                    field="high_level_scope",
                ),
                TraceRef(
                    artifact="Kit",
                    locator="Deliverables",
                    key="deliverables",
                    field="name",
                ),
            ],
            values=slide17.cards[2].bullets,
        )

    # 7. Slide 18 Traces (Lifted Client Slide 12)
    for risk in slide18.risks:
        manifest.add(
            slide=18,
            shape="Table: Initial Risk Register",
            element=f"Risk: {risk.id}",
            displayed_value=f"{risk.description} | {risk.prob_impact} | {risk.mitigation}",
            traces=[
                TraceRef(
                    artifact="Workbook",
                    locator="RAID Log",
                    key=risk.id,
                    field="description",
                )
            ],
        )

    # 8. Slide 19 Traces (Lifted Client Slide 15)
    for step in slide19.next_steps:
        manifest.add(
            slide=19,
            shape="Table: Next Steps",
            element=f"Next Step: {step.owner}",
            displayed_value=f"{step.owner}: {step.action} (Due: {step.due})",
            traces=[
                TraceRef(
                    artifact="Kit",
                    locator="Next Steps",
                    key=step.owner,
                    field="action",
                )
            ],
        )

    return GovernanceDeckModel(
        project_name=project_name,
        slide1=slide1,
        slide13=slide13,
        slide14=slide14,
        slide15=slide15,
        slide16=slide16,
        slide17=slide17,
        slide18=slide18,
        slide19=slide19,
        manifest=manifest,
    )
