"""Pure builder for DeckModel converting StartupKitBaseline and WorkbookModel into slide structures (DECK-03, Appendix K.2)."""

import re
from dataclasses import dataclass, field
from datetime import date
from typing import List, Dict, Any, Optional, Tuple, Sequence, Set

from src.core.models import (
    StartupKitBaseline,
    Deliverable,
    Milestone,
    Stakeholder,
    CommunicationsPlanItem,
    DecisionItem,
    CommercialGuardrail,
    RiskAssumption,
    DependencyAssumptionItem,
)
from src.generators.pmo_workbook.builder import build_workbook_model
from src.generators.pmo_workbook.rows import WorkbookModel, ScheduleRow, WBSRow, RAIDRow
from src.generators.onboarding_deck.trace import TraceRef, DeckTraceManifest
from src.generators.onboarding_deck.talking_points import (
    build_slide1_talking_points,
    build_slide2_talking_points,
    build_slide3_talking_points,
    build_slide4_talking_points,
    build_slide5_talking_points,
    build_slide6_talking_points,
)

PLACEHOLDER_REGEX = re.compile(
    r"\[(?:CONFIRMATION REQUIRED|TBD|UNASSIGNED|TO BE CONFIRMED|ACT-[^\]]+)\]",
    re.IGNORECASE,
)

DEFENSIVE_FILTER_REGEX = re.compile(
    r"\b(G-?01|g01|readiness\s+gate|startup\s+readiness|readiness\s+checklist|readiness\s+score|gate\s+decision|gate\s+approval|startup\s+kit|mobiliz\w*|ACT-\d+)\b",
    re.IGNORECASE,
)


def format_placeholder_value(val: Optional[str]) -> Tuple[str, bool]:
    """Format placeholder text. Returns (formatted_text, is_placeholder)."""
    if not val or not str(val).strip():
        return "To be confirmed", True
    val_str = str(val).strip()
    if (
        (val_str.startswith("[") and val_str.endswith("]"))
        or "UNASSIGNED" in val_str.upper()
        or "CONFIRMATION REQUIRED" in val_str.upper()
        or "TO BE CONFIRMED" in val_str.upper()
        or "TBD" in val_str.upper()
        or "ACT-" in val_str.upper()
    ):
        return "To be confirmed", True
    return val_str, False


def truncate_at_clause_boundary(text: str, max_words: int = 15, max_chars: Optional[int] = None) -> str:
    """Shorten text strictly by cutting at a clause boundary without rewording (DECK-05, DECK-08)."""
    if not text:
        return ""
    text_clean = re.sub(r"\s+", " ", text).strip()
    words = text_clean.split(" ")
    if len(words) <= max_words and (max_chars is None or len(text_clean) <= max_chars):
        return text_clean

    # Find candidate clause cut points within word limit
    candidate = " ".join(words[:max_words])
    for delim in [". ", "; ", ": ", " - ", ", "]:
        last_idx = candidate.rfind(delim)
        if last_idx > int(len(candidate) * 0.4):
            return candidate[:last_idx + (1 if delim.startswith(".") else 0)].strip()
    return candidate.strip()


def compute_deck20_rating(probability: str, impact: str) -> str:
    """Recompute rating per DECK-20 rule."""
    p_up = (probability or "").strip().capitalize()
    i_up = (impact or "").strip().capitalize()

    if (p_up == "High" and i_up in ("High", "Medium")) or (i_up == "High" and p_up in ("High", "Medium")):
        return "High"
    if p_up == "Low" and i_up == "Low":
        return "Low"
    return "Medium"


def compute_deck20_score(probability: str, impact: str) -> int:
    """Compute score (P x I) per DECK-20: High=3, Medium=2, Low=1."""
    score_map = {"High": 3, "Medium": 2, "Low": 1}
    p_val = score_map.get((probability or "").strip().capitalize(), 1)
    i_val = score_map.get((impact or "").strip().capitalize(), 1)
    return p_val * i_val


@dataclass
class CoverSlideData:
    title: str
    subtitle: str
    client_sponsor: str
    start_date_str: str
    start_date_basis: str
    speaker_notes: str


@dataclass
class KeyFactRow:
    label: str
    value: str
    is_placeholder: bool = False
    trace: Optional[TraceRef] = None


@dataclass
class CharterSlideData:
    title: str
    kicker: str
    key_facts: List[KeyFactRow]
    purpose: str
    purpose_trace: Optional[TraceRef]
    delivery_model: str
    delivery_model_trace: Optional[TraceRef]
    escalation_path: str
    escalation_trace: Optional[TraceRef]
    phases: List[str]
    phase_traces: List[Optional[TraceRef]]
    exclusions: List[str]
    exclusion_traces: List[Optional[TraceRef]]
    overflow_exclusions: int
    speaker_notes: str


@dataclass
class TableRowData:
    cells: List[str]
    is_placeholder: List[bool]
    is_overflow: bool = False
    traces: List[Optional[TraceRef]] = field(default_factory=list)


@dataclass
class ScheduleSlideData:
    title: str
    kicker: str
    headers: List[str]
    rows: List[TableRowData]
    speaker_notes: str


@dataclass
class AcceptanceSlideData:
    title: str
    kicker: str
    steps: List[str]
    step_traces: List[Optional[TraceRef]]
    review_window: str
    review_window_trace: Optional[TraceRef]
    client_approver: str
    client_approver_trace: Optional[TraceRef]
    is_approver_placeholder: bool
    headers: List[str]
    rows: List[TableRowData]
    speaker_notes: str


@dataclass
class RisksSlideData:
    title: str
    kicker: str
    headers: List[str]
    rows: List[TableRowData]
    speaker_notes: str


@dataclass
class CollaborationSlideData:
    title: str
    kicker: str
    client_roles: List[str]
    client_role_traces: List[Optional[TraceRef]]
    client_roles_overflow: int
    working_rhythm: List[str]
    working_rhythm_traces: List[Optional[TraceRef]]
    working_rhythm_overflow: int
    prerequisites: List[str]
    prerequisite_traces: List[Optional[TraceRef]]
    prerequisites_overflow: int
    speaker_notes: str


@dataclass
class DeckModel:
    project_name: str
    client_name: str
    cover_slide: CoverSlideData
    charter_slide: CharterSlideData
    schedule_slide: ScheduleSlideData
    acceptance_slide: AcceptanceSlideData
    risks_slide: RisksSlideData
    collaboration_slide: CollaborationSlideData
    manifest: DeckTraceManifest


def build_deck_model(
    baseline: StartupKitBaseline,
    workbook_model: Optional[WorkbookModel] = None,
    start_date: Optional[date] = None,
) -> DeckModel:
    """Build pure DeckModel from baseline and workbook_model (DECK-03, Appendix K.2)."""
    if workbook_model is None:
        workbook_model = build_workbook_model(baseline, start_date=start_date)

    project_name = baseline.project_name or "Project"
    client_name = (
        baseline.governance_context.client_name
        if baseline.governance_context and baseline.governance_context.client_name
        else (baseline.charter.client_sponsor if baseline.charter and baseline.charter.client_sponsor else "Client")
    )
    kicker = f"{project_name.upper()} · TALENT TEAM ONBOARDING"
    manifest = DeckTraceManifest(project_name=project_name)

    # Resolve start date and basis
    resolved_start_date = workbook_model.start_date.isoformat()
    start_basis = workbook_model.start_date_basis  # "Provided" or "Assumed"

    # -------------------------------------------------------------
    # SLIDE 1: Cover (CUSTOM_1)
    # -------------------------------------------------------------
    cover_title_trace = TraceRef("Startup Kit", "Project Charter", "Project Name", "Project Name")
    cover_client_trace = TraceRef("Startup Kit", "Project Charter", "Client Sponsor", "Client Sponsor")
    cover_date_trace = TraceRef("Project Delivery Workbook", "Project Schedule", "Title Row 3", "Start Date")

    cover_subtitle = f"Talent Team Onboarding · {client_name} · Start {resolved_start_date}"
    slide1_notes = build_slide1_talking_points(
        client_sponsor=client_name,
        start_date=resolved_start_date,
        start_basis=start_basis,
    )

    cover_slide = CoverSlideData(
        title=project_name,
        subtitle=cover_subtitle,
        client_sponsor=client_name,
        start_date_str=resolved_start_date,
        start_date_basis=start_basis,
        speaker_notes=slide1_notes,
    )
    manifest.add_entry(1, "Title", project_name, cover_title_trace)
    manifest.add_entry(1, "Client Sponsor", client_name, cover_client_trace)
    manifest.add_entry(1, "Start Date", resolved_start_date, cover_date_trace)

    # -------------------------------------------------------------
    # SLIDE 2: Project Charter (CUSTOM_16)
    # -------------------------------------------------------------
    # Left Card: Key Facts
    gov_tier = baseline.governance_tier or "Partnered"
    contract_type = baseline.contract_type or "Time and Materials"
    tpm_val, tpm_ph = format_placeholder_value(baseline.charter.talent_pm if baseline.charter else None)
    dm_val, dm_ph = format_placeholder_value(baseline.charter.delivery_manager if baseline.charter else None)
    pmo_val, pmo_ph = format_placeholder_value(baseline.charter.pmo_lead if baseline.charter else None)

    key_facts = [
        KeyFactRow("Client Sponsor", client_name, False, TraceRef("Startup Kit", "Project Charter", "Client Sponsor", "Client Sponsor")),
        KeyFactRow("Contract Type", contract_type, False, TraceRef("Startup Kit", "Project Charter", "Contract Type", "Contract Type")),
        KeyFactRow("Governance Tier", gov_tier, False, TraceRef("Startup Kit", "Project Charter", "Governance Tier", "Governance Tier")),
        KeyFactRow("Start Date", f"{resolved_start_date} ({start_basis})", False, TraceRef("Project Delivery Workbook", "Project Schedule", "Title Row 3", "Start Date")),
        KeyFactRow("Talent PM", tpm_val, tpm_ph, TraceRef("Startup Kit", "Project Charter", "Talent PM", "Talent PM")),
        KeyFactRow("Delivery Manager", dm_val, dm_ph, TraceRef("Startup Kit", "Project Charter", "Delivery Manager", "Delivery Manager")),
        KeyFactRow("PMO Lead", pmo_val, pmo_ph, TraceRef("Startup Kit", "Project Charter", "PMO Lead", "PMO Lead")),
    ]

    for kf in key_facts:
        manifest.add_entry(2, f"Key Fact: {kf.label}", kf.value, kf.trace)

    # Middle Card: Purpose and delivery model
    raw_purpose = baseline.charter.project_purpose if baseline.charter else "To be confirmed"
    purpose_clean = truncate_at_clause_boundary(raw_purpose, max_words=25)
    purpose_trace = TraceRef("Startup Kit", "Project Charter", "Project Purpose", "Project Purpose")
    manifest.add_entry(2, "Project Purpose", purpose_clean, purpose_trace)

    raw_model = baseline.charter.delivery_model if baseline.charter else "Toptal Talent Team (Agile/Milestone Hybrid)"
    model_clean = truncate_at_clause_boundary(raw_model, max_words=20)
    model_trace = TraceRef("Startup Kit", "Project Charter", "Delivery Model", "Delivery Model")
    manifest.add_entry(2, "Delivery Model", model_clean, model_trace)

    raw_esc = baseline.charter.escalation_path if baseline.charter else "Talent PM / Delivery Manager -> PMO Lead -> Director, PMO"
    esc_clean = truncate_at_clause_boundary(raw_esc, max_words=20)
    esc_trace = TraceRef("Startup Kit", "Project Charter", "Escalation Path", "Escalation Path")
    manifest.add_entry(2, "Escalation Path", esc_clean, esc_trace)

    # Right Card: Phases and boundaries
    phase_names: List[str] = []
    phase_traces: List[Optional[TraceRef]] = []
    for s_row in workbook_model.schedule_rows:
        if s_row.row_type == "Workstream" and s_row.workstream:
            if s_row.workstream not in phase_names:
                phase_names.append(s_row.workstream)
                tr = TraceRef("Project Delivery Workbook", "Project Schedule", s_row.workstream, "Workstream")
                phase_traces.append(tr)
                manifest.add_entry(2, f"Phase: {s_row.workstream}", s_row.workstream, tr)

    exclusions_all: List[str] = []
    exclusion_traces_all: List[Optional[TraceRef]] = []
    if baseline.sow_interpretation and baseline.sow_interpretation.out_of_scope_items:
        for idx, exc in enumerate(baseline.sow_interpretation.out_of_scope_items, start=1):
            if DEFENSIVE_FILTER_REGEX.search(exc):
                continue
            exc_clean = truncate_at_clause_boundary(exc, max_words=15)
            tr = TraceRef("Startup Kit", "SOW Interpretation Summary", f"Exclusion {idx}", "Out of Scope")
            exclusions_all.append(exc_clean)
            exclusion_traces_all.append(tr)

    max_exc = 4
    if len(exclusions_all) <= max_exc:
        exclusions = exclusions_all
        exclusion_traces = exclusion_traces_all
        overflow_exc = 0
    else:
        exclusions = exclusions_all[:max_exc]
        exclusion_traces = exclusion_traces_all[:max_exc]
        overflow_exc = len(exclusions_all) - max_exc

    for idx, (exc, tr) in enumerate(zip(exclusions, exclusion_traces), start=1):
        manifest.add_entry(2, f"Exclusion {idx}", exc, tr)

    # Schedule dates for talking points
    schedule_milestones = [s for s in workbook_model.schedule_rows if s.row_type == "Milestone"]
    first_finish = schedule_milestones[0].planned_start.isoformat() if schedule_milestones and schedule_milestones[0].planned_start else resolved_start_date
    last_finish = schedule_milestones[-1].planned_finish.isoformat() if schedule_milestones and schedule_milestones[-1].planned_finish else resolved_start_date

    slide2_notes = build_slide2_talking_points(
        contract_type=contract_type,
        governance_tier=gov_tier,
        pmo_lead=pmo_val,
        delivery_manager=dm_val,
        talent_pm=tpm_val,
        purpose=purpose_clean,
        escalation_path=esc_clean,
        phase_count=len(phase_names),
        start_date=first_finish,
        finish_date=last_finish,
    )

    charter_slide = CharterSlideData(
        title="Project Charter",
        kicker=kicker,
        key_facts=key_facts,
        purpose=purpose_clean,
        purpose_trace=purpose_trace,
        delivery_model=model_clean,
        delivery_model_trace=model_trace,
        escalation_path=esc_clean,
        escalation_trace=esc_trace,
        phases=phase_names,
        phase_traces=phase_traces,
        exclusions=exclusions,
        exclusion_traces=exclusion_traces,
        overflow_exclusions=overflow_exc,
        speaker_notes=slide2_notes,
    )

    # -------------------------------------------------------------
    # SLIDE 3: Workstreams, Milestones, Deliverables and Dates (CUSTOM_16)
    # -------------------------------------------------------------
    sched_headers = ["Workstream", "Milestone", "Dates", "Deliverables"]
    sched_rows_all: List[TableRowData] = []

    deliv_name_map: Dict[str, str] = {d.id: d.name for d in baseline.deliverables}
    total_deck_delivs = len(baseline.deliverables)

    prev_workstream = ""
    for s_row in workbook_model.schedule_rows:
        if s_row.row_type in ("Milestone", "Checkpoint"):
            ws_col = s_row.workstream if s_row.workstream != prev_workstream else ""
            prev_workstream = s_row.workstream

            clean_ms_name = truncate_at_clause_boundary(s_row.name, max_words=10)
            if s_row.row_type == "Milestone":
                ms_text = f"{s_row.milestone_id}: {clean_ms_name}"
            else:
                ms_text = f"{s_row.milestone_id}: {clean_ms_name}"

            # Format dates
            p_start = s_row.planned_start.isoformat() if s_row.planned_start else ""
            p_fin = s_row.planned_finish.isoformat() if s_row.planned_finish else ""
            if p_start and p_fin:
                dates_text = f"{p_start} – {p_fin}"
            elif p_fin:
                dates_text = p_fin
            else:
                dates_text = "To be confirmed"

            # Deliverables column
            deliv_ids = [did.strip() for did in (s_row.linked_deliverables or "").split(",") if did.strip()]
            if not deliv_ids:
                deliv_text = "—"
            elif total_deck_delivs <= 20:
                deliv_lines = [f"{did} {truncate_at_clause_boundary(deliv_name_map.get(did, ''), max_words=6)}" for did in deliv_ids]
                deliv_text = "\n".join(deliv_lines)
            else:
                deliv_text = ", ".join(deliv_ids)

            t1 = TraceRef("Project Delivery Workbook", "Project Schedule", s_row.milestone_id, "Workstream") if ws_col else None
            t2 = TraceRef("Project Delivery Workbook", "Project Schedule", s_row.milestone_id, "Milestone")
            t3 = TraceRef("Project Delivery Workbook", "Project Schedule", s_row.milestone_id, "Planned Finish")
            t4 = TraceRef("Project Delivery Workbook", "Project Schedule", s_row.milestone_id, "Linked Deliverables")

            sched_rows_all.append(TableRowData(
                cells=[ws_col, ms_text, dates_text, deliv_text],
                is_placeholder=[False, False, dates_text == "To be confirmed", False],
                traces=[t1, t2, t3, t4],
            ))

    # Capacity = 12 rows max (including overflow row)
    max_sched_cap = 12
    sched_rows: List[TableRowData] = []
    if len(sched_rows_all) <= max_sched_cap:
        sched_rows = sched_rows_all
    else:
        sched_rows = sched_rows_all[:max_sched_cap - 1]
        omitted = sched_rows_all[max_sched_cap - 1:]
        omitted_ids = []
        for o in omitted:
            m_match = re.match(r"(M\d+|CP-\d+)", o.cells[1])
            if m_match:
                omitted_ids.append(m_match.group(1))
        overflow_text = f"+{len(omitted)} more: {', '.join(omitted_ids)} (see Project Delivery Workbook · Project Schedule)"
        sched_rows.append(TableRowData(
            cells=[overflow_text, "", "", ""],
            is_placeholder=[False] * 4,
            is_overflow=True,
            traces=[None] * 4,
        ))

    for r_idx, r in enumerate(sched_rows, start=1):
        if not r.is_overflow:
            for c_idx, (c_val, c_tr) in enumerate(zip(r.cells, r.traces)):
                manifest.add_entry(3, f"R{r_idx}C{c_idx+1}", c_val, c_tr)

    num_ms = sum(1 for s in workbook_model.schedule_rows if s.row_type == "Milestone")
    num_cp = sum(1 for s in workbook_model.schedule_rows if s.row_type == "Checkpoint")
    date_basis_sample = schedule_milestones[0].date_basis if schedule_milestones else "To be confirmed"

    slide3_notes = build_slide3_talking_points(
        phase_count=len(phase_names),
        first_start=first_finish,
        last_finish=last_finish,
        milestones_count=num_ms,
        checkpoints_count=num_cp,
        workstreams_count=len(phase_names),
        deliverables_count=total_deck_delivs,
        date_basis=date_basis_sample,
    )

    schedule_slide = ScheduleSlideData(
        title="Workstreams, Milestones, Deliverables and Dates",
        kicker=kicker,
        headers=sched_headers,
        rows=sched_rows,
        speaker_notes=slide3_notes,
    )

    # -------------------------------------------------------------
    # SLIDE 4: Acceptance Criteria (CUSTOM_16)
    # -------------------------------------------------------------
    # Left Card: How acceptance works (first gate tasks from WBS)
    first_gate_id = schedule_milestones[0].milestone_id if schedule_milestones else "M1"
    first_gate_wbs_tasks = [
        w.name for w in workbook_model.wbs_rows
        if w.milestone_id == first_gate_id and "Milestone Acceptance" in w.workstream or "Milestone Acceptance" in w.name or w.level == 4
    ][:6]

    if not first_gate_wbs_tasks:
        first_gate_wbs_tasks = [
            "Confirm completion evidence against deliverable criteria",
            "Conduct formal milestone acceptance review meeting",
            "Record client sign-off or defect remediation items",
        ]

    step_traces = [
        TraceRef("Project Delivery Workbook", "WBS", f"{first_gate_id} Step {i+1}", "Task Name")
        for i, t in enumerate(first_gate_wbs_tasks)
    ]
    for i, (st, tr) in enumerate(zip(first_gate_wbs_tasks, step_traces), start=1):
        manifest.add_entry(4, f"Acceptance Step {i}", st, tr)

    raw_review_window = baseline.deliverables[0].review_window if baseline.deliverables else None
    review_window_val, rw_ph = format_placeholder_value(raw_review_window)
    if not rw_ph:
        review_window_val = truncate_at_clause_boundary(raw_review_window, max_words=8)
    review_win_trace = TraceRef("Startup Kit", "Deliverables and Acceptance Matrix", "DEL-01", "Review Window")
    manifest.add_entry(4, "Review Window", review_window_val, review_win_trace)

    first_deliv_appr = baseline.deliverables[0].client_approver if baseline.deliverables else None
    appr_val, appr_ph = format_placeholder_value(first_deliv_appr)
    appr_trace = TraceRef("Startup Kit", "Deliverables and Acceptance Matrix", "DEL-01", "Client Approver")
    manifest.add_entry(4, "Client Approver", appr_val, appr_trace)

    # Right Table: One row per deliverable: DEL-xx · Acceptance Criteria · Gate
    # Map deliverable -> gate from WBS
    deliv_gate_map: Dict[str, str] = {}
    for w in workbook_model.wbs_rows:
        if w.deliverable_id and w.milestone_id:
            deliv_gate_map[w.deliverable_id] = w.milestone_id

    acc_headers = ["ID", "Acceptance Criteria", "Gate"]
    acc_rows_all: List[TableRowData] = []

    for d in baseline.deliverables:
        if DEFENSIVE_FILTER_REGEX.search(d.name) or DEFENSIVE_FILTER_REGEX.search(d.description):
            continue
        crit_raw = d.acceptance_criteria or "To be confirmed"
        crit_clean = truncate_at_clause_boundary(crit_raw, max_words=15)
        gate_val = deliv_gate_map.get(d.id, "M1")

        t1 = TraceRef("Startup Kit", "Deliverables and Acceptance Matrix", d.id, "ID")
        t2 = TraceRef("Startup Kit", "Deliverables and Acceptance Matrix", d.id, "Acceptance Criteria")
        t3 = TraceRef("Project Delivery Workbook", "WBS", d.id, "Milestone ID")

        acc_rows_all.append(TableRowData(
            cells=[d.id, crit_clean, gate_val],
            is_placeholder=[False, crit_clean == "To be confirmed", False],
            traces=[t1, t2, t3],
        ))

    # Capacity = 14 rows max (including overflow row)
    max_acc_cap = 14
    acc_rows: List[TableRowData] = []
    if len(acc_rows_all) <= max_acc_cap:
        acc_rows = acc_rows_all
    else:
        acc_rows = acc_rows_all[:max_acc_cap - 1]
        omitted = acc_rows_all[max_acc_cap - 1:]
        omitted_ids = [o.cells[0] for o in omitted]
        overflow_text = f"+{len(omitted)} more: {', '.join(omitted_ids)} (see Startup Kit · Deliverables and Acceptance Matrix)"
        acc_rows.append(TableRowData(
            cells=[overflow_text, "", ""],
            is_placeholder=[False] * 3,
            is_overflow=True,
            traces=[None] * 3,
        ))

    for r_idx, r in enumerate(acc_rows, start=1):
        if not r.is_overflow:
            for c_idx, (c_val, c_tr) in enumerate(zip(r.cells, r.traces)):
                manifest.add_entry(4, f"R{r_idx}C{c_idx+1}", c_val, c_tr)

    slide4_notes = build_slide4_talking_points(
        review_window=review_window_val,
        client_approver=appr_val,
        deliverables_count=total_deck_delivs,
    )

    acceptance_slide = AcceptanceSlideData(
        title="Acceptance Criteria",
        kicker=kicker,
        steps=first_gate_wbs_tasks,
        step_traces=step_traces,
        review_window=review_window_val,
        review_window_trace=review_win_trace,
        client_approver=appr_val,
        client_approver_trace=appr_trace,
        is_approver_placeholder=appr_ph,
        headers=acc_headers,
        rows=acc_rows,
        speaker_notes=slide4_notes,
    )

    # -------------------------------------------------------------
    # SLIDE 5: High-Risk Items (CUSTOM_16)
    # -------------------------------------------------------------
    # Selection: Workbook RAID Log rows of type Risk or Issue
    # Order by Score descending, then RAID ID
    raid_candidates: List[Tuple[int, RAIDRow]] = []
    for r in workbook_model.raid_rows:
        if r.type in ("Risk", "Issue") and not DEFENSIVE_FILTER_REGEX.search(r.description):
            score = compute_deck20_score(r.probability, r.impact)
            raid_candidates.append((score, r))

    # High rating candidates first
    high_candidates = [item for item in raid_candidates if compute_deck20_rating(item[1].probability, item[1].impact) == "High"]
    high_candidates.sort(key=lambda x: (-x[0], x[1].raid_id))

    selected_raid_tuples = list(high_candidates)
    if len(selected_raid_tuples) < 3:
        remaining = [item for item in raid_candidates if item not in selected_raid_tuples]
        remaining.sort(key=lambda x: (-x[0], x[1].raid_id))
        selected_raid_tuples.extend(remaining[:3 - len(selected_raid_tuples)])

    risk_headers = ["ID", "Item", "Rating", "Owner", "Response", "Phase"]
    risk_rows_all: List[TableRowData] = []

    for score, r in selected_raid_tuples:
        source_id_str = f" ({r.source_id})" if r.source_id and r.source_id != r.raid_id else ""
        id_display = f"{r.raid_id}{source_id_str}"
        desc_clean = truncate_at_clause_boundary(r.description, max_words=15)
        rating_calc = compute_deck20_rating(r.probability, r.impact)
        owner_val, owner_ph = format_placeholder_value(r.owner)
        resp_clean = truncate_at_clause_boundary(r.mitigation_or_response, max_words=15)
        phase_val = r.workstream if r.workstream else "Cross-phase"

        t1 = TraceRef("Project Delivery Workbook", "RAID Log", r.raid_id, "RAID ID")
        t2 = TraceRef("Project Delivery Workbook", "RAID Log", r.raid_id, "Description")
        t3 = TraceRef("Project Delivery Workbook", "RAID Log", r.raid_id, "Probability and Impact")
        t4 = TraceRef("Project Delivery Workbook", "RAID Log", r.raid_id, "Owner")
        t5 = TraceRef("Project Delivery Workbook", "RAID Log", r.raid_id, "Mitigation / Response")
        t6 = TraceRef("Project Delivery Workbook", "RAID Log", r.raid_id, "Workstream")

        risk_rows_all.append(TableRowData(
            cells=[id_display, desc_clean, rating_calc, owner_val, resp_clean, phase_val],
            is_placeholder=[False, False, False, owner_ph, False, False],
            traces=[t1, t2, t3, t4, t5, t6],
        ))

    # Capacity = 6 rows max (including overflow row)
    max_risk_cap = 6
    risk_rows: List[TableRowData] = []
    if len(risk_rows_all) <= max_risk_cap:
        risk_rows = risk_rows_all
    else:
        risk_rows = risk_rows_all[:max_risk_cap - 1]
        omitted = risk_rows_all[max_risk_cap - 1:]
        omitted_ids = [o.cells[0].split(" ")[0] for o in omitted]
        overflow_text = f"+{len(omitted)} more: {', '.join(omitted_ids)} (see Project Delivery Workbook · RAID Log)"
        risk_rows.append(TableRowData(
            cells=[overflow_text, "", "", "", "", ""],
            is_placeholder=[False] * 6,
            is_overflow=True,
            traces=[None] * 6,
        ))

    for r_idx, r in enumerate(risk_rows, start=1):
        if not r.is_overflow:
            for c_idx, (c_val, c_tr) in enumerate(zip(r.cells, r.traces)):
                manifest.add_entry(5, f"R{r_idx}C{c_idx+1}", c_val, c_tr)

    top_id = selected_raid_tuples[0][1].raid_id if selected_raid_tuples else ""
    top_desc = truncate_at_clause_boundary(selected_raid_tuples[0][1].description, max_words=10) if selected_raid_tuples else ""

    slide5_notes = build_slide5_talking_points(
        high_count=len(high_candidates),
        top_risk_id=top_id,
        top_risk_desc=top_desc,
    )

    risks_slide = RisksSlideData(
        title="High-Risk Items",
        kicker=kicker,
        headers=risk_headers,
        rows=risk_rows,
        speaker_notes=slide5_notes,
    )

    # -------------------------------------------------------------
    # SLIDE 6: Client Collaboration (CUSTOM_16)
    # -------------------------------------------------------------
    # Card 1: Client roles and approvers (Stakeholders where Organization is Client)
    client_sh_all: List[str] = []
    client_sh_traces_all: List[Optional[TraceRef]] = []

    for idx, sh in enumerate(baseline.stakeholders, start=1):
        if DEFENSIVE_FILTER_REGEX.search(sh.name):
            continue
        # Check if organization is Client or Client Sponsor
        org_lower = (sh.organization or "").lower()
        if "client" in org_lower or client_name.lower() in org_lower or "sponsor" in (sh.role or "").lower():
            role_part = sh.role or "Stakeholder"
            dec_part = truncate_at_clause_boundary(sh.decision_rights or "Standard", max_words=8)
            item_text = f"{sh.name} ({role_part}): {dec_part}"
            tr = TraceRef("Startup Kit", "Stakeholder and Responsibility Model", sh.name, "Role and Decision Rights")
            client_sh_all.append(item_text)
            client_sh_traces_all.append(tr)

    max_sh = 5
    if len(client_sh_all) <= max_sh:
        client_roles = client_sh_all
        client_role_traces = client_sh_traces_all
        sh_overflow = 0
    else:
        client_roles = client_sh_all[:max_sh]
        client_role_traces = client_sh_traces_all[:max_sh]
        sh_overflow = len(client_sh_all) - max_sh

    for idx, (cr, tr) in enumerate(zip(client_roles, client_role_traces), start=1):
        manifest.add_entry(6, f"Client Role {idx}", cr, tr)

    # Card 2: Working rhythm (Communications plan items: {Item}: {Cadence})
    comms_all: List[str] = []
    comms_traces_all: List[Optional[TraceRef]] = []

    for idx, cp in enumerate(baseline.communications_plan, start=1):
        if DEFENSIVE_FILTER_REGEX.search(cp.name):
            continue
        c_name = cp.name
        c_cadence = cp.cadence or "Weekly"
        item_text = f"{c_name}: {c_cadence}"
        tr = TraceRef("Startup Kit", "Communications and Reporting Plan", cp.name, "Name and Cadence")
        comms_all.append(item_text)
        comms_traces_all.append(tr)

    max_comms = 7
    if len(comms_all) <= max_comms:
        working_rhythm = comms_all
        working_rhythm_traces = comms_traces_all
        comms_overflow = 0
    else:
        working_rhythm = comms_all[:max_comms]
        working_rhythm_traces = comms_traces_all[:max_comms]
        comms_overflow = len(comms_all) - max_comms

    for idx, (wr, tr) in enumerate(zip(working_rhythm, working_rhythm_traces), start=1):
        manifest.add_entry(6, f"Working Rhythm {idx}", wr, tr)

    # Card 3: What we need from the client (Client prerequisites, earliest gate first)
    prereqs_all: List[str] = []
    prereqs_traces_all: List[Optional[TraceRef]] = []

    for s_row in schedule_milestones:
        if s_row.client_prerequisites and s_row.client_prerequisites.strip():
            p_text = truncate_at_clause_boundary(s_row.client_prerequisites, max_words=12)
            gate_label = s_row.milestone_id or s_row.name
            full_prereq = f"{gate_label}: {p_text}"
            tr = TraceRef("Project Delivery Workbook", "Project Schedule", s_row.milestone_id, "Client Prerequisites")
            prereqs_all.append(full_prereq)
            prereqs_traces_all.append(tr)

    max_prereqs = 6
    if len(prereqs_all) <= max_prereqs:
        prerequisites = prereqs_all
        prerequisite_traces = prereqs_traces_all
        prereqs_overflow = 0
    else:
        prerequisites = prereqs_all[:max_prereqs]
        prerequisite_traces = prereqs_traces_all[:max_prereqs]
        prereqs_overflow = len(prereqs_all) - max_prereqs

    for idx, (pr, tr) in enumerate(zip(prerequisites, prerequisite_traces), start=1):
        manifest.add_entry(6, f"Client Prerequisite {idx}", pr, tr)

    first_gate_name = schedule_milestones[0].milestone_id if schedule_milestones else "P1"
    first_prereq_val = truncate_at_clause_boundary(schedule_milestones[0].client_prerequisites, max_words=8) if schedule_milestones and schedule_milestones[0].client_prerequisites else ""

    slide6_notes = build_slide6_talking_points(
        client_stakeholder_count=len(client_sh_all),
        comms_count=len(comms_all),
        first_gate=first_gate_name,
        first_prereq=first_prereq_val,
    )

    collaboration_slide = CollaborationSlideData(
        title="Client Collaboration",
        kicker=kicker,
        client_roles=client_roles,
        client_role_traces=client_role_traces,
        client_roles_overflow=sh_overflow,
        working_rhythm=working_rhythm,
        working_rhythm_traces=working_rhythm_traces,
        working_rhythm_overflow=comms_overflow,
        prerequisites=prerequisites,
        prerequisite_traces=prerequisite_traces,
        prerequisites_overflow=prereqs_overflow,
        speaker_notes=slide6_notes,
    )

    return DeckModel(
        project_name=project_name,
        client_name=client_name,
        cover_slide=cover_slide,
        charter_slide=charter_slide,
        schedule_slide=schedule_slide,
        acceptance_slide=acceptance_slide,
        risks_slide=risks_slide,
        collaboration_slide=collaboration_slide,
        manifest=manifest,
    )
