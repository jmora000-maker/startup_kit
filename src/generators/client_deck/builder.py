"""Pure builder module transforming StartupKitBaseline into ClientDeckModel (OUT-14)."""

import re
from typing import List, Optional, Sequence, Tuple
from src.core.models import (
    Deliverable,
    Milestone,
    RiskAssumption,
    StartupKitBaseline,
)
from src.generators.kit_values import kit_header_values
from src.generators.pmo_workbook.builder import build_workbook_model
from src.generators.pmo_workbook.workstreams import parse_milestone_phase
from src.generators.client_deck.spec import (
    ClientDeckModel,
    NextStepItem,
    RiskItem,
    Slide1Model,
    Slide5Model,
    Slide6Model,
    Slide12Model,
    Slide15Model,
    WorkstreamBlock,
)
from src.generators.client_deck.trace import ClientDeckTraceManifest, TraceRef

COMMERCIAL_EXCLUSION_REGEX = re.compile(
    r"\b(hourly\s*rate|billing\s*rate|profit\s*margin|margin\s*erosion|fee\s*cap|fee\s*ceiling|budget\s*overrun|financial\s*burn|burn\s*rate|engagement\s*spend|contract\s*value|commercial\s*risk|commercial\s*terms|fixed[\s-]*fee|prepayment|billed\s*by\s*milestone|invoice\(s\)|change\s*order|payment\s*schedule)\b|\$\s*\d+",
    re.IGNORECASE,
)


def synthesize_problem_statement(baseline: StartupKitBaseline) -> str:
    """Deterministically synthesize 'What problem are we solving?' from baseline without LLM calls (HTL-48)."""
    purpose = (
        baseline.charter.project_purpose
        if baseline.charter and baseline.charter.project_purpose and baseline.charter.project_purpose != "[CONFIRMATION REQUIRED]"
        else ""
    ).strip()
    if purpose.endswith("."):
        purpose = purpose[:-1]

    raw_constraints: List[str] = []
    if baseline.sow_interpretation and baseline.sow_interpretation.constraints:
        raw_constraints.extend(
            [c.strip().rstrip(".") for c in baseline.sow_interpretation.constraints if c.strip() and c.strip() != "[CONFIRMATION REQUIRED]"]
        )
    elif baseline.charter and baseline.charter.major_startup_risks:
        raw_constraints.extend(
            [r.strip().rstrip(".") for r in baseline.charter.major_startup_risks if r.strip() and r.strip() != "[CONFIRMATION REQUIRED]"]
        )

    # Layer 1 content scoping: filter out commercial/financial clauses
    non_commercial_constraints = [
        c for c in raw_constraints if not COMMERCIAL_EXCLUSION_REGEX.search(c)
    ]

    purpose_clause = (purpose[0].lower() + purpose[1:]) if purpose else "deliver engagement objectives"

    if non_commercial_constraints:
        selected = [non_commercial_constraints[0]]
        if len(non_commercial_constraints) > 1 and (len(non_commercial_constraints[0]) + len(non_commercial_constraints[1])) < 100:
            selected.append(non_commercial_constraints[1])
        key_constraints = "; ".join(selected)
        return (
            f"Addressing operational bottlenecks and technical limitations to "
            f"{purpose_clause}, specifically resolving: {key_constraints}."
        )
    elif purpose and raw_constraints:
        return f"Addressing operational bottlenecks and technical limitations to {purpose_clause}."
    elif purpose:
        return f"Addressing existing legacy operational and technology challenges by executing: {purpose}."
    return "Addressing existing operational and technology challenges to establish core platform capabilities."


def format_success_criteria_prose(criteria: Sequence[str]) -> str:
    """Distill success criteria list into narrative prose sentences (OUT-14.2)."""
    clean_items = [
        c.strip().rstrip(".")
        for c in (criteria or [])
        if c.strip() and c.strip() != "[CONFIRMATION REQUIRED]"
    ]
    if not clean_items:
        return "Success will be achieved upon fulfilling all contracted deliverables, meeting defined quality benchmarks, and securing formal stakeholder acceptance."

    norm_items = [
        (it[0].lower() + it[1:] if len(it) > 1 else it.lower())
        for it in clean_items
    ]

    if len(norm_items) == 1:
        return f"Success is defined by {norm_items[0]}."
    if len(norm_items) == 2:
        return f"Success is defined by {norm_items[0]}, and {norm_items[1]}."

    joined = "; ".join(norm_items[:-1]) + f"; and {norm_items[-1]}."
    return f"Success is defined across key project milestones: {joined}"


def build_slide1_model(baseline: StartupKitBaseline) -> Slide1Model:
    """Build Slide 1 model with client sponsor and project name sourced from kit_header_values (HTL-49)."""
    headers = kit_header_values(baseline)
    client_sponsor = headers.get("client_sponsor") or "Client"
    if client_sponsor in ("N/A", "[CONFIRMATION REQUIRED]"):
        client_sponsor = "Client"
    project_name = headers.get("project_name") or baseline.project_name or "Project Baseline"
    return Slide1Model(client_name=client_sponsor, project_name=project_name)


def build_slide5_model(baseline: StartupKitBaseline) -> Slide5Model:
    """Build Slide 5 model (Project Success Agreement - Why We're Here)."""
    why = (
        (baseline.charter.project_purpose if baseline.charter and baseline.charter.project_purpose and baseline.charter.project_purpose != "[CONFIRMATION REQUIRED]" else None)
        or (baseline.governance_context.executive_summary if baseline.governance_context and baseline.governance_context.executive_summary else None)
        or "Establish core platform capabilities and deliver contracted business outcomes."
    )
    problem = synthesize_problem_statement(baseline)
    success = format_success_criteria_prose(baseline.charter.success_criteria if baseline.charter else [])
    return Slide5Model(
        why_are_we_doing_this=why,
        what_problem_are_we_solving=problem,
        what_does_success_look_like=success,
    )


def build_slide6_model(baseline: StartupKitBaseline) -> Slide6Model:
    """Build Slide 6 model (What We Will Deliver) using canonical PMO Workbook schedule rows (HTL-49)."""
    wb = build_workbook_model(baseline)
    names = {d.id: (d.name or d.description) for d in (baseline.deliverables or [])}
    m_dict = {m.id: m for m in (baseline.milestones or [])}

    level2 = [r for r in wb.schedule_rows if r.row_type == "Milestone"]
    if not level2:
        level2 = [r for r in wb.schedule_rows if r.row_type in ("Milestone", "Checkpoint")]

    workstreams: List[WorkstreamBlock] = []

    if level2:
        for r in level2:
            m = m_dict.get(r.milestone_id)
            if m and m.description and (not r.name or r.name in [f"Phase {i}" for i in range(1, 10)] + [f"Milestone {i}" for i in range(1, 10)]):
                title = m.description
            else:
                title = r.name or (m.description if m else "") or r.workstream or "Phase Delivery"

            linked_ids = [x.strip() for x in (r.linked_deliverables or "").split(",") if x.strip()]

            deliv_items: List[str] = []
            for did in linked_ids:
                d_name = names.get(did)
                if d_name:
                    if d_name.startswith(did):
                        deliv_items.append(d_name)
                    else:
                        deliv_items.append(f"{did} {d_name}")
                else:
                    deliv_items.append(did)

            workstreams.append(WorkstreamBlock(title=title, deliverables=deliv_items, overflow_count=0))
    elif baseline.deliverables:
        chunk_size = 3
        for i in range(0, len(baseline.deliverables), chunk_size):
            chunk = baseline.deliverables[i : i + chunk_size]
            title = f"Phase {i // chunk_size + 1} Delivery"
            deliv_items = []
            for d in chunk:
                d_name = d.name or d.acceptance_criteria or f"Deliverable {d.id}"
                did = d.id or ""
                if did and not d_name.startswith(did):
                    deliv_items.append(f"{did} {d_name}")
                else:
                    deliv_items.append(d_name)
            workstreams.append(WorkstreamBlock(title=title, deliverables=deliv_items, overflow_count=0))
    else:
        workstreams.append(
            WorkstreamBlock(
                title="Phase 1: Project Kickoff & Foundation",
                deliverables=["Architecture & Delivery Setup", "Core Workstream Alignment"],
                overflow_count=0,
            )
        )

    # Solution Overview
    overview = ""
    if baseline.charter and baseline.charter.high_level_scope:
        overview = " ".join([s.strip().rstrip(".") + "." for s in baseline.charter.high_level_scope if s.strip()])
    if not overview and baseline.charter and baseline.charter.project_purpose and baseline.charter.project_purpose != "[CONFIRMATION REQUIRED]":
        overview = baseline.charter.project_purpose
    if not overview:
        overview = "Comprehensive milestone-based delivery establishing core platform capabilities in alignment with contracted specifications."

    # Out of Scope
    out_of_scope: List[str] = []
    if baseline.charter and baseline.charter.exclusions:
        out_of_scope.extend([e.strip() for e in baseline.charter.exclusions if e.strip() and e.strip() != "[CONFIRMATION REQUIRED]"])
    if not out_of_scope and baseline.sow_interpretation and baseline.sow_interpretation.out_of_scope_items:
        out_of_scope.extend([e.strip() for e in baseline.sow_interpretation.out_of_scope_items if e.strip() and e.strip() != "[CONFIRMATION REQUIRED]"])
    if not out_of_scope:
        out_of_scope = ["Uncontracted feature modifications", "Third-party platform licensing costs", "Infrastructure hosting fees"]

    return Slide6Model(
        workstreams=workstreams,
        solution_overview=overview,
        out_of_scope=out_of_scope[:4],
    )


def is_commercial_risk(risk: RiskAssumption) -> bool:
    """Return True if risk relates to commercial, pricing, margin, or financial terms."""
    category = (risk.category or "").lower().strip()
    if category in ("commercial", "financial", "pricing", "margin", "billing", "financial risk"):
        return True
    text_corpus = f"{risk.category or ''} {risk.description or ''} {risk.mitigation_or_response or ''}"
    return bool(COMMERCIAL_EXCLUSION_REGEX.search(text_corpus))


def build_slide12_model(baseline: StartupKitBaseline) -> Slide12Model:
    """Build Slide 12 model (Initial Risk Register) excluding commercial risks."""
    prob_map = {"high": 3, "medium": 2, "med": 2, "low": 1}
    impact_map = {"high": 3, "medium": 2, "med": 2, "low": 1}

    qualifying_risks: List[Tuple[int, int, int, RiskAssumption]] = []

    for r in (baseline.raid_items or []):
        if (r.type or "").strip().lower() != "risk":
            continue
        if is_commercial_risk(r):
            continue

        p_str = (r.probability or "Medium").strip().lower()
        i_str = (r.impact or "Medium").strip().lower()
        p_val = prob_map.get(p_str, 2)
        i_val = impact_map.get(i_str, 2)
        score = p_val * i_val

        qualifying_risks.append((score, p_val, i_val, r))

    # Sort descending by severity score, prob, impact
    qualifying_risks.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3].id or ""))

    risk_items: List[RiskItem] = []
    for score, p_val, i_val, r in qualifying_risks[:3]:
        p_label = (r.probability or "Med").capitalize()
        i_label = (r.impact or "Med").capitalize()
        prob_impact = f"{p_label}/{i_label}"
        target_date = str(r.due_date) if r.due_date else "TBD"
        desc = f"{r.id}: {r.description}" if r.id and not r.description.startswith(r.id) else r.description

        risk_items.append(
            RiskItem(
                id=r.id or f"RSK-{len(risk_items)+1:02d}",
                description=desc,
                prob_impact=prob_impact,
                mitigation=r.mitigation_or_response or "Active monitoring by Delivery Manager and PMO",
                target_date=target_date,
                severity_score=score,
            )
        )

    return Slide12Model(risks=risk_items)


def build_slide15_model(baseline: StartupKitBaseline) -> Slide15Model:
    """Build Slide 15 model (Next Steps) with literal TBD due dates."""
    candidates: List[NextStepItem] = []

    # 1. Customer obligations
    if baseline.sow_interpretation and baseline.sow_interpretation.customer_obligations:
        for ob in baseline.sow_interpretation.customer_obligations:
            clean_ob = ob.strip()
            if clean_ob and clean_ob != "[CONFIRMATION REQUIRED]":
                candidates.append(NextStepItem(owner="[Client]", action=clean_ob, due="TBD"))

    # 2. Open dependencies & assumptions
    if baseline.dependencies_assumptions:
        for da in baseline.dependencies_assumptions:
            if (da.status or "").lower() in ("open", "unresolved", "active"):
                if COMMERCIAL_EXCLUSION_REGEX.search(f"{da.category or ''} {da.description or ''}"):
                    continue
                owner = "[Client]" if "client" in (da.description or "").lower() or "client" in (da.category or "").lower() else "[Toptal]"
                candidates.append(NextStepItem(owner=owner, action=da.description, due="TBD"))

    # 3. Unassigned role placeholders
    if baseline.charter:
        if baseline.charter.delivery_manager == "[UNASSIGNED - TO BE CONFIRMED]":
            candidates.append(NextStepItem(owner="[Toptal]", action="Confirm Delivery Manager role assignment", due="TBD"))
        if baseline.charter.talent_pm == "[UNASSIGNED - TO BE CONFIRMED]":
            candidates.append(NextStepItem(owner="[Toptal]", action="Confirm Talent PM role assignment", due="TBD"))
        if baseline.charter.pmo_lead == "[UNASSIGNED - TO BE CONFIRMED]":
            candidates.append(NextStepItem(owner="[Toptal]", action="Confirm PMO Lead role assignment", due="TBD"))

    # 4. Open contract ambiguities
    if baseline.sow_interpretation and baseline.sow_interpretation.ambiguity_notes:
        for amb in baseline.sow_interpretation.ambiguity_notes:
            if amb.strip() and amb.strip() != "[CONFIRMATION REQUIRED]":
                candidates.append(NextStepItem(owner="[Client]", action=f"Clarify ambiguity: {amb.strip()}", due="TBD"))

    # Default fallback steps if none found
    if not candidates:
        candidates = [
            NextStepItem(owner="[Client]", action="Provide access to target systems, repositories, and environments", due="TBD"),
            NextStepItem(owner="[Toptal]", action="Finalize Project Success Agreement and team onboarding with sponsor", due="TBD"),
            NextStepItem(owner="[Client]", action="Confirm named reviewer(s) and sign-off cadence for deliverables", due="TBD"),
        ]

    return Slide15Model(next_steps=candidates[:4])


def build_client_deck_model(baseline: StartupKitBaseline) -> ClientDeckModel:
    """Build complete ClientDeckModel and populate trace manifest."""
    project_name = baseline.project_name or "Project Baseline"
    slide1 = build_slide1_model(baseline)
    slide5 = build_slide5_model(baseline)
    slide6 = build_slide6_model(baseline)
    slide12 = build_slide12_model(baseline)
    slide15 = build_slide15_model(baseline)

    manifest = ClientDeckTraceManifest(project_name=project_name)

    # Slide 1 Traces
    manifest.add(
        slide=1,
        shape="Shape;92",
        element="Title Header",
        displayed_value=f"{slide1.client_name}\n{slide1.project_name} Kickoff",
        traces=[
            TraceRef(artifact="Kit", locator="Header table", key="Client Sponsor", field="client_sponsor"),
            TraceRef(artifact="Kit", locator="Header table", key="Project Name", field="project_name"),
        ],
    )

    # Slide 5 Traces
    manifest.add(
        slide=5,
        shape="Shape;176",
        element="Why are we doing this?",
        displayed_value=slide5.why_are_we_doing_this,
        traces=[TraceRef(artifact="Charter", locator="Project Purpose", key="project_purpose", field="project_purpose")],
    )
    manifest.add(
        slide=5,
        shape="Shape;180",
        element="What problem are we solving?",
        displayed_value=slide5.what_problem_are_we_solving,
        traces=[
            TraceRef(artifact="Charter", locator="Project Purpose", key="project_purpose", field="project_purpose"),
            TraceRef(artifact="SOWInterpretation", locator="Constraints", key="constraints", field="constraints"),
        ],
        derived="Deterministic Synthesis",
    )
    manifest.add(
        slide=5,
        shape="Shape;184",
        element="What does success look like?",
        displayed_value=slide5.what_does_success_look_like,
        traces=[TraceRef(artifact="Charter", locator="Success Criteria", key="success_criteria", field="success_criteria")],
        derived="Prose Distillation",
    )

    # Slide 6 Traces
    manifest.add(
        slide=6,
        shape="Shape;194",
        element="Solution Overview",
        displayed_value=slide6.solution_overview,
        traces=[TraceRef(artifact="Charter", locator="High Level Scope", key="high_level_scope", field="high_level_scope")],
    )
    for idx, ws in enumerate(slide6.workstreams):
        manifest.add(
            slide=6,
            shape=f"Workstream Block {idx+1}",
            element=f"Workstream {idx+1}: {ws.title}",
            displayed_value="; ".join(ws.deliverables),
            traces=[TraceRef(artifact="Milestones", locator="Phase / Milestone", key=ws.title, field="deliverables")],
        )

    # Slide 12 Traces
    for idx, risk in enumerate(slide12.risks):
        manifest.add(
            slide=12,
            shape="Shape;312",
            element=f"Risk Row {idx+1}: {risk.id}",
            displayed_value=f"{risk.description} | {risk.prob_impact} | {risk.mitigation}",
            traces=[TraceRef(artifact="RAID", locator="Risks", key=risk.id, field="description")],
        )

    # Slide 15 Traces
    for idx, step in enumerate(slide15.next_steps):
        manifest.add(
            slide=15,
            shape="Shape;345",
            element=f"Next Step Row {idx+1}",
            displayed_value=f"{step.owner}: {step.action} (Due: {step.due})",
            traces=[TraceRef(artifact="Baseline", locator="Open Items", key=f"Step {idx+1}", field="action")],
        )

    return ClientDeckModel(
        project_name=project_name,
        slide1=slide1,
        slide5=slide5,
        slide6=slide6,
        slide12=slide12,
        slide15=slide15,
        manifest=manifest,
    )
