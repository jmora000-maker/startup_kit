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
    r"(?:\$\s*\d+(?:,\d{3})*(?:\.\d+)?(?:\s*[kKmMbB](?:illion)?)?)"
    r"|\b(?:\d+\s*(?:USD|dollars?))\b"
    r"|\b(?:hourly|billing|blended|daily|day)\s*rates?\b"
    r"|\b(?:rate|fee|budget)\s*caps?\b"
    r"|\b(?:fee\s*ceiling|budget\s*overrun|margin\s*erosion|profit\s*margin|financial\s*burn|burn\s*rate|engagement\s*spend|contract\s*value)\b"
    r"|\b(?:fixed[\s-]*fee|fixed[\s-]*bid|time\s*(?:and|&)\s*materials|T&M)\b"
    r"|\b(?:change\s*orders?|commercial\s*risks?|commercial\s*terms?|pricing\s*terms?|commercial\s*acceptance|deposit\s*acceptance|payment\s*gates?)\b"
    r"|\b(?:invoices?|invoicing|invoiced|billed\s*by\s*milestone|billing\s*milestones?|payment\s*schedules?|prepayments?|payment\s*terms?)\b"
    r"|\b(?:expense\s*reimbursements?|travel\s*expenses?)\b",
    re.IGNORECASE,
)


def scrub_commercial_clauses(text: str) -> str:
    """Scrub financial and commercial clauses/sentences from continuous prose text (HTL-50 / HTL-54)."""
    if not text or not text.strip():
        return ""
    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    clean_sentences = []
    for s in sentences:
        s_clean = s.strip()
        if not s_clean:
            continue
        if not COMMERCIAL_EXCLUSION_REGEX.search(s_clean):
            clean_sentences.append(s_clean)
        else:
            # Try sub-clause splitting on commas / semicolons / ' and '
            clauses = re.split(r"(?:,\s*(?:and\s+)?|;\s*|\s+and\s+)", s_clean)
            clean_clauses = [c.strip() for c in clauses if c.strip() and not COMMERCIAL_EXCLUSION_REGEX.search(c)]
            if clean_clauses:
                if len(clean_clauses) == 1:
                    clean_sentences.append(clean_clauses[0])
                else:
                    clean_sentences.append(", ".join(clean_clauses))
    if clean_sentences:
        return " ".join(clean_sentences)
    return ""


def _to_gerund(phrase: str) -> str:
    """Convert leading action verb in a phrase to gerund form (e.g. 'Deploy ...' -> 'deploying ...')."""
    clean = phrase.strip()
    if not clean:
        return ""
    words = clean.split()
    first = words[0].lower()
    rest = " ".join(words[1:]) if len(words) > 1 else ""

    if first.endswith("ing"):
        gerund = first
    else:
        verb_map = {
            "deploy": "deploying",
            "integrate": "integrating",
            "build": "building",
            "develop": "developing",
            "establish": "establishing",
            "migrate": "migrating",
            "implement": "implementing",
            "create": "creating",
            "deliver": "delivering",
            "configure": "configuring",
            "automate": "automating",
            "design": "designing",
            "scale": "scaling",
            "optimize": "optimizing",
            "refactor": "refactoring",
            "enhance": "enhancing",
            "modernize": "modernizing",
            "provide": "providing",
            "enable": "enabling",
            "support": "supporting",
            "transform": "transforming",
            "transition": "transitioning",
            "execute": "executing",
            "verify": "verifying",
            "validate": "validating",
            "consolidate": "consolidating",
            "incorporate": "incorporating",
            "onboard": "onboarding",
            "streamline": "streamlining",
            "centralize": "centralizing",
            "standardize": "standardizing",
            "accelerate": "accelerating",
            "upgrade": "upgrading",
            "replace": "replacing",
            "unify": "unifying",
            "introduce": "introducing",
            "move": "moving",
            "reduce": "reducing",
            "improve": "improving",
            "expand": "expanding",
            "launch": "launching",
            "set": "setting",
            "run": "running",
            "cut": "cutting",
            "align": "aligning",
            "address": "addressing",
            "resolve": "resolving",
            "ingest": "ingesting",
            "process": "processing",
        }
        if first in verb_map:
            gerund = verb_map[first]
        elif first.endswith("e") and not first.endswith(("ee", "oe", "ye")):
            gerund = first[:-1] + "ing"
        else:
            gerund = first + "ing"

    return f"{gerund} {rest}".strip() if rest else gerund


def synthesize_problem_statement(baseline: StartupKitBaseline) -> str:
    """Deterministically synthesize 'What problem are we solving?' from baseline without LLM calls (HTL-48 / HTL-50 / HTL-54).

    Frames charter.project_purpose around current-state operational bottlenecks and transformation gaps
    without injecting granular build tasks from delivery_objectives or high_level_scope.
    Falls back to explicit placeholder if no project purpose is available.
    """
    purpose_raw = (
        baseline.charter.project_purpose
        if baseline.charter and baseline.charter.project_purpose and baseline.charter.project_purpose != "[CONFIRMATION REQUIRED]"
        else ""
    ).strip()
    purpose = scrub_commercial_clauses(purpose_raw)
    if purpose.endswith("."):
        purpose = purpose[:-1]

    if purpose:
        purpose_clause = (purpose[0].lower() + purpose[1:]) if len(purpose) > 1 else purpose.lower()
        if purpose_clause.startswith(("move ", "transition ", "transform ", "upgrade ", "migrate ", "shift ", "evolve ")):
            return f"Resolving operational bottlenecks and manual limitations to {purpose_clause}."
        elif purpose_clause.startswith(("establish ", "deploy ", "build ", "develop ", "implement ", "create ", "deliver ")):
            return f"Addressing operational bottlenecks and technology transition gaps to {purpose_clause}."
        else:
            return f"Resolving existing operational bottlenecks and transition challenges to enable: {purpose_clause}."

    return "[To be confirmed in Project Success Agreement · Define current pain points with client]"


def format_success_criteria_prose(criteria: Sequence[str]) -> str:
    """Distill success criteria list into narrative prose sentences (OUT-14.2 / HTL-50)."""
    clean_items = [
        c.strip().rstrip(".")
        for c in (criteria or [])
        if c.strip() and c.strip() != "[CONFIRMATION REQUIRED]" and not COMMERCIAL_EXCLUSION_REGEX.search(c)
    ]
    if not clean_items:
        return "[To be confirmed in Project Success Agreement]"

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
    """Build Slide 5 model (Project Success Agreement - Why We're Here) with financial scrubbing (HTL-50)."""
    why_raw = (
        (baseline.charter.project_purpose if baseline.charter and baseline.charter.project_purpose and baseline.charter.project_purpose != "[CONFIRMATION REQUIRED]" else None)
        or (baseline.governance_context.executive_summary if baseline.governance_context and baseline.governance_context.executive_summary else None)
    )
    why = scrub_commercial_clauses(why_raw) if why_raw else ""
    if not why:
        why = "Establish core platform capabilities and deliver contracted business outcomes." if not why_raw or not COMMERCIAL_EXCLUSION_REGEX.search(why_raw) else "[To be confirmed in Project Success Agreement]"

    problem = synthesize_problem_statement(baseline)
    success = format_success_criteria_prose(baseline.charter.success_criteria if baseline.charter else [])
    return Slide5Model(
        why_are_we_doing_this=why,
        what_problem_are_we_solving=problem,
        what_does_success_look_like=success,
    )


def build_slide6_model(baseline: StartupKitBaseline) -> Slide6Model:
    """Build Slide 6 model (What We Will Deliver) using canonical PMO Workbook schedule rows (HTL-49 / HTL-50)."""
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
                raw_title = m.description
            else:
                raw_title = r.name or (m.description if m else "") or r.workstream or "Phase Delivery"

            if COMMERCIAL_EXCLUSION_REGEX.search(raw_title):
                title = scrub_commercial_clauses(raw_title)
                if not title:
                    title = r.workstream or "Phase Delivery"
            else:
                title = raw_title

            linked_ids = [x.strip() for x in (r.linked_deliverables or "").split(",") if x.strip()]

            deliv_items: List[str] = []
            for did in linked_ids:
                d_name = names.get(did)
                if d_name:
                    if COMMERCIAL_EXCLUSION_REGEX.search(d_name):
                        continue
                    if d_name.startswith(did):
                        deliv_items.append(d_name)
                    else:
                        deliv_items.append(f"{did} {d_name}")
                else:
                    if not COMMERCIAL_EXCLUSION_REGEX.search(did):
                        deliv_items.append(did)

            if not deliv_items:
                deliv_items = ["[No non-commercial deliverables identified for this phase · See Project Delivery Workbook]"]

            workstreams.append(WorkstreamBlock(title=title, deliverables=deliv_items, overflow_count=0))
    elif baseline.deliverables:
        chunk_size = 3
        non_comm_delivs = [d for d in baseline.deliverables if not COMMERCIAL_EXCLUSION_REGEX.search(f"{d.name or ''} {d.description or ''}")]
        active_delivs = non_comm_delivs if non_comm_delivs else []
        if active_delivs:
            for i in range(0, len(active_delivs), chunk_size):
                chunk = active_delivs[i : i + chunk_size]
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
                    title="Phase 1 Delivery",
                    deliverables=["[No non-commercial deliverables identified for this phase · See Project Delivery Workbook]"],
                    overflow_count=0,
                )
            )
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
        non_comm_scope = [s for s in baseline.charter.high_level_scope if s.strip() and not COMMERCIAL_EXCLUSION_REGEX.search(s)]
        if non_comm_scope:
            overview = " ".join([s.strip().rstrip(".") + "." for s in non_comm_scope])
    if not overview and baseline.charter and baseline.charter.project_purpose and baseline.charter.project_purpose != "[CONFIRMATION REQUIRED]":
        overview = scrub_commercial_clauses(baseline.charter.project_purpose)
    if not overview:
        overview = "Comprehensive milestone-based delivery establishing core platform capabilities in alignment with contracted specifications."

    # Out of Scope
    out_of_scope: List[str] = []
    if baseline.charter and baseline.charter.exclusions:
        out_of_scope.extend([e.strip() for e in baseline.charter.exclusions if e.strip() and e.strip() != "[CONFIRMATION REQUIRED]" and not COMMERCIAL_EXCLUSION_REGEX.search(e)])
    if not out_of_scope and baseline.sow_interpretation and baseline.sow_interpretation.out_of_scope_items:
        out_of_scope.extend([e.strip() for e in baseline.sow_interpretation.out_of_scope_items if e.strip() and e.strip() != "[CONFIRMATION REQUIRED]" and not COMMERCIAL_EXCLUSION_REGEX.search(e)])
    if not out_of_scope:
        out_of_scope = ["None explicitly identified in SOW exclusions."]

    return Slide6Model(
        workstreams=workstreams,
        solution_overview=overview,
        out_of_scope=out_of_scope[:4],
    )


def is_commercial_risk(risk: RiskAssumption) -> bool:
    """Return True if risk relates to commercial, pricing, margin, or financial terms (HTL-50 / HTL-54)."""
    category = (risk.category or "").lower().strip()
    if category in ("commercial", "financial", "pricing", "margin", "billing", "financial risk"):
        return True
    text_corpus = f"{risk.category or ''} {risk.description or ''}"
    return bool(COMMERCIAL_EXCLUSION_REGEX.search(text_corpus))


def build_slide12_model(baseline: StartupKitBaseline) -> Slide12Model:
    """Build Slide 12 model (Initial Risk Register) excluding commercial risks with zero-fabrication fallback (HTL-50 / HTL-54)."""
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

        mitigation_raw = r.mitigation_or_response or "Active monitoring by Delivery Manager and PMO"
        if COMMERCIAL_EXCLUSION_REGEX.search(mitigation_raw):
            mitigation_clean = scrub_commercial_clauses(mitigation_raw)
            if not mitigation_clean:
                mitigation_clean = re.sub(
                    r"(?:,\s*)?(?:and\s+)?(?:manage|raise|process|issue)\s+(?:a\s+)?(?:Change Order|change order)[^.]*",
                    "",
                    mitigation_raw,
                    flags=re.IGNORECASE,
                ).strip().rstrip(",")
                if not mitigation_clean:
                    mitigation_clean = (
                        "Report defects early and agree remediation timelines with Client"
                        if "defect" in mitigation_raw.lower()
                        else "Active monitoring by Delivery Manager and PMO"
                    )
        else:
            mitigation_clean = mitigation_raw

        risk_items.append(
            RiskItem(
                id=r.id or f"RSK-{len(risk_items)+1:02d}",
                description=desc,
                prob_impact=prob_impact,
                mitigation=mitigation_clean,
                target_date=target_date,
                severity_score=score,
            )
        )

    if not risk_items:
        risk_items.append(
            RiskItem(
                id="RSK-01",
                description="[No non-commercial risks identified at kickoff · See RAID Log]",
                prob_impact="—",
                mitigation="Active monitoring by Delivery Manager and PMO",
                target_date="TBD",
                severity_score=0,
            )
        )

    return Slide12Model(risks=risk_items)


def build_slide15_model(baseline: StartupKitBaseline) -> Slide15Model:
    """Build Slide 15 model (Next Steps) with literal TBD due dates and financial scrubbing."""
    candidates: List[NextStepItem] = []

    # 1. Customer obligations
    if baseline.sow_interpretation and baseline.sow_interpretation.customer_obligations:
        for ob in baseline.sow_interpretation.customer_obligations:
            clean_ob = ob.strip()
            if clean_ob and clean_ob != "[CONFIRMATION REQUIRED]" and not COMMERCIAL_EXCLUSION_REGEX.search(clean_ob):
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
            if amb.strip() and amb.strip() != "[CONFIRMATION REQUIRED]" and not COMMERCIAL_EXCLUSION_REGEX.search(amb):
                candidates.append(NextStepItem(owner="[Client]", action=f"Clarify ambiguity: {amb.strip()}", due="TBD"))

    # Zero-fabrication fallback if all candidates were scrubbed
    if not candidates:
        candidates = [
            NextStepItem(owner="[PMO]", action="[None identified in SOW · Open items tracked in Project Delivery Workbook]", due="TBD")
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
