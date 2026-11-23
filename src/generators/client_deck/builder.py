"""Pure builder module transforming StartupKitBaseline into ClientDeckModel (OUT-14)."""

import re
from typing import List, Optional, Sequence, Tuple
from src.core.interfaces import ILLMClient
from src.core.models import (
    Deliverable,
    Milestone,
    RiskAssumption,
    StartupKitBaseline,
)
from src.config import strip_deliverable_boilerplate
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
from src.generators.client_deck.fit import (
    condense_problem_statement,
    condense_solution_overview,
    condense_why_are_we_doing_this,
)

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

COMPLETION_PHRASE_REGEX = re.compile(
    r"(?:concludes|service period ends|deliverables accepted following|milestone sign-off|formal acceptance|acceptance following demonstration)",
    re.IGNORECASE,
)

ADMIN_PROCESS_DELIVERABLE_REGEX = re.compile(
    r"\b("
    r"sprint\s*sign-?offs?|"
    r"weekly\s*status\s*reports?|"
    r"sprint\s*plans?(?:\s+(?:and|&)\s+backlog|\s+alignment)?|"
    r"sprint\s*planning|"
    r"(?:final\s+)?(?:engagement\s+)?(?:completion\s+)?sign-?offs?(?:\s+documents?)?|"
    r"sign-?off\s+documents?\s+confirming\s+completion|"
    r"completion\s+of\s+(?:the\s+)?engagement|"
    r"engagement\s*completion|"
    r"(?:project|work|engagement)\s*documentation|"
    r"documentation\s+for\s+all\s+work|"
    r"licensing\s*inventory|"
    r"ip\s*assignment|"
    r"status\s*reporting"
    r")\b",
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


def format_success_criteria_prose(criteria: Sequence[str], summary: Optional[str] = None, fallback_doc: str = "Project Success Agreement") -> str:
    """Distill success criteria into narrative prose sentences (OUT-14.2 / HTL-50 / HTL-60 / HTL-116)."""
    if summary and summary.strip() and summary.strip() != "[CONFIRMATION REQUIRED]":
        scrubbed = scrub_commercial_clauses(summary.strip())
        if scrubbed:
            return scrubbed

    # Tier 2 Deterministic Fallback (HTL-60)
    clean = [
        c.strip().rstrip(";. ")
        for c in (criteria or [])
        if c and c.strip() and c.strip() != "[CONFIRMATION REQUIRED]" and not COMMERCIAL_EXCLUSION_REGEX.search(c)
    ]
    if not clean:
        return f"[To be confirmed in {fallback_doc}]"

    sentences = []
    for item in clean:
        s = item[0].upper() + item[1:] if len(item) > 1 else item.upper()
        sentences.append(s + ".")
    return " ".join(sentences)


def build_slide1_model(baseline: StartupKitBaseline) -> Slide1Model:
    """Build Slide 1 model with client sponsor and project name sourced from kit_header_values (HTL-49)."""
    headers = kit_header_values(baseline)
    client_sponsor = headers.get("client_sponsor") or "Client"
    if client_sponsor in ("N/A", "[CONFIRMATION REQUIRED]"):
        client_sponsor = "Client"
    project_name = headers.get("project_name") or baseline.project_name or "Project Baseline"
    return Slide1Model(client_name=client_sponsor, project_name=project_name)


def build_slide5_model(
    baseline: StartupKitBaseline,
    llm_client: Optional[ILLMClient] = None,
) -> Slide5Model:
    """Build Slide 5 model (Project Success Agreement / Engagement Overview - Why We're Here) with financial scrubbing (HTL-50 / HTL-54 / HTL-116)."""
    is_programmatic = bool(baseline.contract_type and any(k in baseline.contract_type.strip().lower() for k in ("programmatic", "retainer")))
    fallback_doc = "Engagement Overview" if is_programmatic else "Project Success Agreement"

    why_raw = (
        (baseline.charter.project_purpose if baseline.charter and baseline.charter.project_purpose and baseline.charter.project_purpose != "[CONFIRMATION REQUIRED]" else None)
        or (baseline.governance_context.executive_summary if baseline.governance_context and baseline.governance_context.executive_summary else None)
    )
    why = scrub_commercial_clauses(why_raw) if why_raw else ""
    if not why:
        why = "Establish core platform capabilities and deliver contracted business outcomes." if not why_raw or not COMMERCIAL_EXCLUSION_REGEX.search(why_raw) else f"[To be confirmed in {fallback_doc}]"
    elif not why.startswith("["):
        why = condense_why_are_we_doing_this(why, max_chars=180, llm_client=llm_client)

    # Read extracted problem statement directly (HTL-54)
    raw_problem = (
        baseline.charter.problem_statement
        if baseline.charter and baseline.charter.problem_statement and baseline.charter.problem_statement != "[CONFIRMATION REQUIRED]"
        else None
    )
    if raw_problem:
        problem = scrub_commercial_clauses(raw_problem)
        if not problem:
            problem = f"[To be confirmed in {fallback_doc} · Define current pain points with client]"
    else:
        problem = f"[To be confirmed in {fallback_doc} · Define current pain points with client]"

    if problem and not problem.startswith("["):
        problem = condense_problem_statement(problem, max_chars=180, llm_client=llm_client)

    raw_summary = (
        baseline.charter.success_criteria_summary
        if baseline.charter and baseline.charter.success_criteria_summary and baseline.charter.success_criteria_summary != "[CONFIRMATION REQUIRED]"
        else None
    )
    success = format_success_criteria_prose(
        baseline.charter.success_criteria if baseline.charter else [],
        summary=raw_summary,
        fallback_doc=fallback_doc,
    )
    return Slide5Model(
        why_are_we_doing_this=why,
        what_problem_are_we_solving=problem,
        what_does_success_look_like=success,
    )


def build_slide6_model(
    baseline: StartupKitBaseline,
    llm_client: Optional[ILLMClient] = None,
) -> Slide6Model:
    """Build Slide 6 model (What We Will Deliver / Focus) using canonical PMO Workbook schedule rows or agile workstreams (HTL-49 / HTL-50 / HTL-116)."""
    is_programmatic = bool(baseline.contract_type and any(k in baseline.contract_type.strip().lower() for k in ("programmatic", "retainer")))
    workstreams: List[WorkstreamBlock] = []

    if is_programmatic:
        raw_delivs = baseline.deliverables or []
        non_comm_delivs = []
        for d in raw_delivs:
            d_name = d.name or ""
            d_desc = d.description or ""
            comb = f"{d_name} {d_desc}"
            if COMMERCIAL_EXCLUSION_REGEX.search(comb) or COMPLETION_PHRASE_REGEX.search(d_name):
                continue
            desc_no_agreed = re.sub(r"as agreed in [^.]*sprint plans?", "", d_desc, flags=re.I)
            if ADMIN_PROCESS_DELIVERABLE_REGEX.search(f"{d_name} {desc_no_agreed}"):
                continue
            non_comm_delivs.append(d)

        section_titles = {
            "2.1.1": "Feature development",
            "2.1.2": "Security and reliability",
            "2.1.3": "Quality engineering and release support",
        }
        theme_keywords = [
            ("Security and reliability", re.compile(r"\b(hardening|defect|triage|remediation|reliability|connectivity|sync|stale-state|identity|login|security|audit|encryption|cert)\b", re.I)),
            ("Quality engineering and release support", re.compile(r"\b(test|testing|automated|simulator|t-stat|doppelio|release|train|regression|accessibility|localization|qa|quality)\b", re.I)),
            ("Feature development", re.compile(r"\b(feature|flow|flows|access|role|roles|permission|permissions|accessory|accessories|reminder|reminders|notification|notifications|alert|alerts|activity|service-experience|vacation|lockout|configuration|pairing|telemetry)\b", re.I)),
        ]

        grouped: Dict[str, List[str]] = {
            "Feature development": [],
            "Security and reliability": [],
            "Quality engineering and release support": [],
        }

        # Step A: Populate from surviving non-commercial deliverables
        for d in non_comm_delivs:
            loc = (d.source_reference.clause_or_slide if d.source_reference else "") or ""
            sow_ref = d.sow_reference or ""
            d_name = d.name or ""
            d_desc = d.description or ""
            full_text = f"{loc} {sow_ref} {d_name} {d_desc}"
            raw_item = d_desc if d_desc and d_desc != d_name and not COMPLETION_PHRASE_REGEX.search(d_desc) else d_name
            item_text = strip_deliverable_boilerplate(raw_item)

            sec_match = re.search(r"2\.1\.([123])", full_text)
            if sec_match:
                sec_key = f"2.1.{sec_match.group(1)}"
                grouped[section_titles[sec_key]].append(item_text)
                continue

            matched_theme = None
            for theme_name, regex in theme_keywords:
                if regex.search(full_text):
                    matched_theme = theme_name
                    break
            if matched_theme:
                grouped[matched_theme].append(item_text)
            else:
                grouped["Feature development"].append(item_text)

        # Step B: If fewer than 2 active theme groups resulted, enrich from high_level_scope
        active_theme_groups = [(k, v) for k, v in grouped.items() if v]
        if len(active_theme_groups) < 2 and baseline.charter and baseline.charter.high_level_scope:
            clean_scope = [
                s.strip().rstrip(";. ")
                for s in baseline.charter.high_level_scope
                if s and s.strip() and s.strip() != "[CONFIRMATION REQUIRED]"
                and not COMMERCIAL_EXCLUSION_REGEX.search(s)
                and not COMPLETION_PHRASE_REGEX.search(s)
                and not ADMIN_PROCESS_DELIVERABLE_REGEX.search(s)
            ]
            for s in clean_scope:
                matched_theme = None
                for theme_name, regex in theme_keywords:
                    if regex.search(s):
                        matched_theme = theme_name
                        break
                target = matched_theme or "Feature development"
                if s not in grouped[target]:
                    grouped[target].append(s)

            active_theme_groups = [(k, v) for k, v in grouped.items() if v]

        for title, items in active_theme_groups:
            workstreams.append(WorkstreamBlock(title=title, deliverables=items, overflow_count=0))

        if not workstreams:
            workstreams.append(
                WorkstreamBlock(
                    title="Feature development",
                    deliverables=["Sprint backlog features and roadmap workstream delivery"],
                    overflow_count=0,
                )
            )
    else:
        wb = build_workbook_model(baseline)
        names = {d.id: (d.name or d.description) for d in (baseline.deliverables or [])}
        m_dict = {m.id: m for m in (baseline.milestones or [])}
        level2 = [r for r in wb.schedule_rows if r.row_type == "Milestone"]
        if not level2:
            level2 = [r for r in wb.schedule_rows if r.row_type in ("Milestone", "Checkpoint")]

        if level2:
            for r in level2:
                m = m_dict.get(r.milestone_id)
                if m and m.description and not COMPLETION_PHRASE_REGEX.search(m.description) and (not r.name or r.name in [f"Phase {i}" for i in range(1, 10)] + [f"Milestone {i}" for i in range(1, 10)]):
                    raw_title = m.description
                else:
                    raw_title = r.name or (m.description if m and not COMPLETION_PHRASE_REGEX.search(m.description) else "") or r.workstream or "Phase Delivery"

                if COMMERCIAL_EXCLUSION_REGEX.search(raw_title) or COMPLETION_PHRASE_REGEX.search(raw_title):
                    title = scrub_commercial_clauses(raw_title)
                    if not title or COMPLETION_PHRASE_REGEX.search(title):
                        title = r.workstream or "Phase Delivery"
                else:
                    title = raw_title

                linked_ids = [x.strip() for x in (r.linked_deliverables or "").split(",") if x.strip()]

                deliv_items: List[str] = []
                for did in linked_ids:
                    d_name = names.get(did)
                    if d_name:
                        if COMMERCIAL_EXCLUSION_REGEX.search(d_name) or COMPLETION_PHRASE_REGEX.search(d_name):
                            continue
                        if d_name.startswith(did):
                            deliv_items.append(d_name)
                        else:
                            deliv_items.append(f"{did} {d_name}")
                    else:
                        if not COMMERCIAL_EXCLUSION_REGEX.search(did) and not COMPLETION_PHRASE_REGEX.search(did):
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
                        crit_fallback = d.acceptance_criteria[0] if (isinstance(d.acceptance_criteria, list) and d.acceptance_criteria) else (d.acceptance_criteria if isinstance(d.acceptance_criteria, str) else None)
                        d_name = d.name or crit_fallback or f"Deliverable {d.id}"
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

    # Solution Overview (HTL-60)
    overview = ""
    raw_overview = (
        baseline.charter.solution_overview
        if baseline.charter and baseline.charter.solution_overview and baseline.charter.solution_overview != "[CONFIRMATION REQUIRED]"
        else None
    )
    if raw_overview:
        overview = scrub_commercial_clauses(raw_overview)

    if not overview:
        # Tier 2 Deterministic Fallback:
        clean_scope = [
            s.strip().rstrip(";. ")
            for s in (baseline.charter.high_level_scope if baseline.charter else [])
            if s and s.strip() and s.strip() != "[CONFIRMATION REQUIRED]" and not COMMERCIAL_EXCLUSION_REGEX.search(s)
        ]
        if clean_scope:
            sentences = []
            for s in clean_scope:
                s_cap = s[0].upper() + s[1:] if len(s) > 1 else s.upper()
                sentences.append(s_cap + ".")
            overview = " ".join(sentences)
        elif baseline.charter and baseline.charter.project_purpose and baseline.charter.project_purpose != "[CONFIRMATION REQUIRED]":
            p = scrub_commercial_clauses(baseline.charter.project_purpose)
            if p:
                overview = p.rstrip(".") + "."

    if not overview:
        overview = "Comprehensive milestone-based delivery establishing core platform capabilities in alignment with contracted specifications."

    if overview and not overview.startswith("["):
        overview = condense_solution_overview(overview, max_chars=300, llm_client=llm_client)

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
                ).strip(" .,;:-")
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
    """Build Slide 15 model (Next Steps) with real stakeholder derivation and relative due dates (HTL-118)."""
    candidates: List[NextStepItem] = []

    # Helper to resolve client owner
    client_name = (
        baseline.charter.client_name
        if baseline.charter and baseline.charter.client_name and not baseline.charter.client_name.startswith("[")
        else "Client"
    )
    client_owner = None
    if baseline.stakeholders:
        for s in baseline.stakeholders:
            if s.name and not s.name.startswith("["):
                role_l = (s.role or "").lower()
                org_l = (s.organization or "").lower()
                if "client" in org_l or any(k in role_l for k in ("product owner", "client", "sponsor", "po", "lead")):
                    client_owner = s.name
                    break
    if not client_owner:
        client_owner = f"{client_name} Lead"

    # Helper to resolve toptal owner
    toptal_owner = None
    if baseline.charter:
        for role_val in (baseline.charter.delivery_manager, baseline.charter.talent_pm, baseline.charter.pmo_lead):
            if role_val and not role_val.startswith("["):
                toptal_owner = role_val
                break
    if not toptal_owner and baseline.stakeholders:
        for s in baseline.stakeholders:
            if s.name and not s.name.startswith("["):
                role_l = (s.role or "").lower()
                org_l = (s.organization or "").lower()
                if "toptal" in org_l or any(k in role_l for k in ("delivery manager", "talent pm", "product manager", "project manager", "pmo")):
                    toptal_owner = s.name
                    break
    if not toptal_owner:
        toptal_owner = "Delivery Manager"

    due_schedule = ["Sprint 1 Day 1", "Week 1", "Week 2", "Prior to Sprint 2"]
    due_idx = 0

    # 1. Customer obligations
    if baseline.sow_interpretation and baseline.sow_interpretation.customer_obligations:
        for ob in baseline.sow_interpretation.customer_obligations:
            clean_ob = ob.strip()
            if clean_ob and clean_ob != "[CONFIRMATION REQUIRED]" and not COMMERCIAL_EXCLUSION_REGEX.search(clean_ob):
                due_val = due_schedule[due_idx % len(due_schedule)]
                due_idx += 1
                candidates.append(NextStepItem(owner=client_owner, action=clean_ob, due=due_val))

    # 2. Open dependencies & assumptions
    if baseline.dependencies_assumptions:
        for da in baseline.dependencies_assumptions:
            if (da.status or "").lower() in ("open", "unresolved", "active"):
                if COMMERCIAL_EXCLUSION_REGEX.search(f"{da.category or ''} {da.description or ''}"):
                    continue
                owner = client_owner if "client" in (da.description or "").lower() or "client" in (da.category or "").lower() else toptal_owner
                due_val = due_schedule[due_idx % len(due_schedule)]
                due_idx += 1
                candidates.append(NextStepItem(owner=owner, action=da.description, due=due_val))

    # 3. Unassigned role placeholders
    if baseline.charter:
        if baseline.charter.delivery_manager == "[UNASSIGNED - TO BE CONFIRMED]":
            candidates.append(NextStepItem(owner=toptal_owner, action="Confirm Delivery Manager role assignment", due="Sprint 1 Day 1"))
        if baseline.charter.talent_pm == "[UNASSIGNED - TO BE CONFIRMED]":
            candidates.append(NextStepItem(owner=toptal_owner, action="Confirm Talent PM role assignment", due="Sprint 1 Day 1"))
        if baseline.charter.pmo_lead == "[UNASSIGNED - TO BE CONFIRMED]":
            candidates.append(NextStepItem(owner=toptal_owner, action="Confirm PMO Lead role assignment", due="Sprint 1 Day 1"))

    # 4. Open contract ambiguities
    if baseline.sow_interpretation and baseline.sow_interpretation.ambiguity_notes:
        for amb in baseline.sow_interpretation.ambiguity_notes:
            if amb.strip() and amb.strip() != "[CONFIRMATION REQUIRED]" and not COMMERCIAL_EXCLUSION_REGEX.search(amb):
                due_val = due_schedule[due_idx % len(due_schedule)]
                due_idx += 1
                candidates.append(NextStepItem(owner=client_owner, action=f"Clarify ambiguity: {amb.strip()}", due=due_val))

    # Zero-fabrication fallback if all candidates were scrubbed
    if not candidates:
        candidates = [
            NextStepItem(owner="PMO Lead", action="[None identified in SOW · Open items tracked in Project Delivery Workbook]", due="Week 1")
        ]

    return Slide15Model(next_steps=candidates[:4])


def build_client_deck_model(
    baseline: StartupKitBaseline,
    llm_client: Optional[ILLMClient] = None,
) -> ClientDeckModel:
    """Build complete ClientDeckModel and populate trace manifest."""
    project_name = baseline.project_name or "Project Baseline"
    slide1 = build_slide1_model(baseline)
    slide5 = build_slide5_model(baseline, llm_client=llm_client)
    slide6 = build_slide6_model(baseline, llm_client=llm_client)
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
    if baseline.charter and baseline.charter.project_purpose and baseline.charter.project_purpose != "[CONFIRMATION REQUIRED]":
        why_traces = [TraceRef(artifact="Charter", locator="Project Purpose", key="project_purpose", field="project_purpose")]
        why_derived = None
    elif baseline.governance_context and baseline.governance_context.executive_summary:
        why_traces = [TraceRef(artifact="GovernanceContext", locator="Executive Summary", key="executive_summary", field="executive_summary")]
        why_derived = "Fallback"
    else:
        why_traces = [TraceRef(artifact="Charter", locator="Project Purpose", key="project_purpose", field="project_purpose")]
        why_derived = "Default"

    manifest.add(
        slide=5,
        shape="Shape;176",
        element="Why are we doing this?",
        displayed_value=slide5.why_are_we_doing_this,
        traces=why_traces,
        derived=why_derived,
    )

    if baseline.charter and baseline.charter.problem_statement and baseline.charter.problem_statement != "[CONFIRMATION REQUIRED]":
        prob_traces = [TraceRef(artifact="Charter", locator="Problem Statement", key="problem_statement", field="problem_statement")]
        prob_derived = None
    else:
        prob_traces = [TraceRef(artifact="Charter", locator="Problem Statement", key="problem_statement", field="problem_statement")]
        prob_derived = "Fallback"

    manifest.add(
        slide=5,
        shape="Shape;180",
        element="What problem are we solving?",
        displayed_value=slide5.what_problem_are_we_solving,
        traces=prob_traces,
        derived=prob_derived,
    )

    if baseline.charter and baseline.charter.success_criteria_summary and baseline.charter.success_criteria_summary != "[CONFIRMATION REQUIRED]":
        succ_traces = [TraceRef(artifact="Charter", locator="Success Criteria Summary", key="success_criteria_summary", field="success_criteria_summary")]
        succ_derived = None
    elif baseline.charter and baseline.charter.success_criteria:
        succ_traces = [TraceRef(artifact="Charter", locator="Success Criteria", key="success_criteria", field="success_criteria")]
        succ_derived = "Deterministic Fallback"
    else:
        succ_traces = [TraceRef(artifact="Charter", locator="Success Criteria", key="success_criteria", field="success_criteria")]
        succ_derived = "Default"

    manifest.add(
        slide=5,
        shape="Shape;184",
        element="What does success look like?",
        displayed_value=slide5.what_does_success_look_like,
        traces=succ_traces,
        derived=succ_derived,
    )

    # Slide 6 Traces
    if baseline.charter and baseline.charter.solution_overview and baseline.charter.solution_overview != "[CONFIRMATION REQUIRED]":
        so_traces = [TraceRef(artifact="Charter", locator="Solution Overview", key="solution_overview", field="solution_overview")]
        so_derived = None
    elif baseline.charter and baseline.charter.high_level_scope:
        so_traces = [TraceRef(artifact="Charter", locator="High Level Scope", key="high_level_scope", field="high_level_scope")]
        so_derived = "Deterministic Fallback"
    elif baseline.charter and baseline.charter.project_purpose and baseline.charter.project_purpose != "[CONFIRMATION REQUIRED]":
        so_traces = [TraceRef(artifact="Charter", locator="Project Purpose", key="project_purpose", field="project_purpose")]
        so_derived = "Deterministic Fallback"
    else:
        so_traces = [TraceRef(artifact="Charter", locator="Solution Overview", key="solution_overview", field="solution_overview")]
        so_derived = "Default"

    manifest.add(
        slide=6,
        shape="Shape;194",
        element="Solution Overview",
        displayed_value=slide6.solution_overview,
        traces=so_traces,
        derived=so_derived,
    )
    for idx, ws in enumerate(slide6.workstreams):
        manifest.add(
            slide=6,
            shape=f"Workstream Block {idx+1}",
            element=f"Workstream {idx+1}: {ws.title}",
            displayed_value="; ".join(ws.deliverables),
            traces=[TraceRef(artifact="Milestones", locator="Phase / Milestone", key=ws.title, field="deliverables")],
        )
    if slide6.out_of_scope:
        if baseline.charter and baseline.charter.exclusions:
            oos_traces = [TraceRef(artifact="Charter", locator="Exclusions", key="exclusions", field="exclusions")]
            oos_derived = None
        elif baseline.sow_interpretation and baseline.sow_interpretation.out_of_scope_items:
            oos_traces = [TraceRef(artifact="SOWInterpretation", locator="Out of Scope Items", key="out_of_scope_items", field="out_of_scope_items")]
            oos_derived = None
        else:
            oos_traces = [TraceRef(artifact="Charter", locator="Exclusions", key="exclusions", field="exclusions")]
            oos_derived = "Default"

        manifest.add(
            slide=6,
            shape="Shape;202",
            element="Out of Scope",
            displayed_value="; ".join(slide6.out_of_scope),
            traces=oos_traces,
            derived=oos_derived,
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
        contract_type=baseline.contract_type or (baseline.charter.contract_type if baseline.charter else "") or "",
        slide1=slide1,
        slide5=slide5,
        slide6=slide6,
        slide12=slide12,
        slide15=slide15,
        manifest=manifest,
    )
