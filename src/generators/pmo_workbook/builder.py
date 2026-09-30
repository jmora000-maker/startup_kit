"""Pure workbook model builder converting StartupKitBaseline into project delivery workbook rows (v2 spec)."""

import re
import logging
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple, Set, Sequence, Union

from src.config import sanitize_report_text, normalize_person_name
from src.generators.formatting import ACTION_TAG_REGEX
from src.core.models import (
    StartupKitBaseline,
    Milestone,
    Deliverable,
    WorkPackageSeed,
    RiskAssumption,
    DependencyAssumptionItem,
    ContractAmbiguityItem,
    CommunicationsPlanItem,
)
from src.generators.pmo_workbook.workstreams import (
    TAXONOMY,
    WORKSTREAM_NAMES,
    parse_milestone_phase,
    ParsedMilestonePhase,
)
from src.generators.pmo_workbook.task_library import (
    classify_deliverable_work_type,
    DeliverableTaskTemplate,
)
from src.generators.pmo_workbook.mapping import (
    natural_sort_key,
    map_deliverables_to_milestones_v2,
    map_work_packages_to_deliverables,
    detect_default_filled_milestone,
    link_raid_item_v2,
)
from src.generators.pmo_workbook.rows import (
    ScheduleRow,
    WBSRow,
    RAIDRow,
    WorkbookModel,
)

logger = logging.getLogger(__name__)

# Defensive filter: Drop any item matching this pattern
DEFENSIVE_FILTER_REGEX = re.compile(
    r"\b(G-?01|readiness\s+gate|startup\s+readiness|readiness\s+checklist|readiness\s+score|gate\s+decision)\b",
    re.IGNORECASE
)

# Week range patterns: "weeks 1–6", "weeks 1-6", "weeks 1 to 6", "week 5"
WEEK_RANGE_REGEX = re.compile(
    r"\bweeks?\s+(\d+)(?:\s*(?:–|—|-|to)\s*(\d+))?\b",
    re.IGNORECASE
)

# Milestone predecessor pattern in dependencies/assumptions
PREDECESSOR_REGEX = re.compile(
    r"(?:acceptance\s+of|completion\s+of|upon\s+acceptance\s+of?|upon\s+completion\s+of?|after)\s+(?P<phase>P\d+[a-z]?)\b",
    re.IGNORECASE
)


def next_working_day(d: date) -> date:
    """Return the next Monday-to-Friday working day strictly after date d."""
    res = d + timedelta(days=1)
    while res.weekday() >= 5:  # Saturday=5, Sunday=6
        res += timedelta(days=1)
    return res


def clean_text_v2(text: Optional[str]) -> str:
    """Sanitize report text, remove ACTION_TAG_REGEX matches, collapse whitespace and trim stray punctuation."""
    if not text:
        return ""
    sanitized = sanitize_report_text(str(text))
    cleaned = ACTION_TAG_REGEX.sub("", sanitized)
    # Collapse whitespace
    cleaned = " ".join(cleaned.split())
    # Trim stray ;, ,, and - at either end
    cleaned = cleaned.strip(" ;,-\t\r\n")
    return cleaned


def truncate_task_name(name: str, max_len: int = 120) -> Tuple[str, Optional[str]]:
    """Truncate task name to max_len characters at word boundary with '...'. Returns (name, note_if_truncated)."""
    if len(name) <= max_len:
        return name, None
    cut = name[:max_len - 3]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    truncated = f"{cut}..."
    note = f"Full name: {name}"
    return truncated, note


def deduplicate_notes(notes: Sequence[Optional[str]]) -> str:
    """De-duplicate non-empty notes while preserving order and join with '; '."""
    seen: Set[str] = set()
    result: List[str] = []
    for n in notes:
        if n and n.strip():
            clean_n = n.strip()
            if clean_n not in seen:
                seen.add(clean_n)
                result.append(clean_n)
    return "; ".join(result)


def normalize_owner_v2(owner: Optional[str]) -> Tuple[str, Optional[str]]:
    """Normalize owner string. Placeholders return [UNASSIGNED - TO BE CONFIRMED] with an unassigned note."""
    if not owner or not owner.strip():
        return "[UNASSIGNED - TO BE CONFIRMED]", "Owner unassigned"
    norm = normalize_person_name(owner.strip())
    norm_clean = clean_text_v2(norm)
    if not norm_clean or norm_clean in ("Unassigned", "[UNASSIGNED - TO BE CONFIRMED]"):
        return "[UNASSIGNED - TO BE CONFIRMED]", "Owner unassigned"
    return norm_clean, None


def is_defensive_excluded(text: str) -> bool:
    """Check if text contains defensive filter keywords."""
    if not text:
        return False
    return bool(DEFENSIVE_FILTER_REGEX.search(text))


def parse_week_range(text: str) -> Optional[Tuple[int, int]]:
    """Find and parse week range from text."""
    if not text:
        return None
    match = WEEK_RANGE_REGEX.search(text)
    if match:
        w_start = int(match.group(1))
        w_end = int(match.group(2)) if match.group(2) else w_start
        return (w_start, w_end)
    return None


def calculate_start_date(baseline: StartupKitBaseline, user_start_date: Optional[date] = None, today: Optional[date] = None) -> Tuple[date, str]:
    """Determine project start date and its basis string."""
    if user_start_date is not None:
        return user_start_date, "Provided"

    if today is None:
        today = date.today()

    ref_date = baseline.sow_awarded_date
    basis = "Assumed - first Monday after award; confirm"
    if ref_date is None:
        ref_date = today
        basis = "Assumed - first Monday after generation; confirm"

    # First Monday on or after ref_date
    days_to_monday = (0 - ref_date.weekday()) % 7
    calc_start = ref_date + timedelta(days=days_to_monday)
    return calc_start, basis


def check_acceptance_mode(baseline: StartupKitBaseline) -> str:
    """Decide acceptance mode once per project: 'milestone-level' or 'per-deliverable'."""
    text_blocks: List[str] = []
    for m in (baseline.milestones or []):
        text_blocks.append(m.description or "")
        text_blocks.extend(m.key_dependencies or [])
        text_blocks.extend(m.critical_path_assumptions or [])
    for d in (baseline.deliverables or []):
        text_blocks.append(d.acceptance_criteria or "")
        text_blocks.append(d.evidence_required or "")
        text_blocks.append(getattr(d, "rejection_rework_path", "") or "")
    for c in (baseline.communications_plan or []):
        text_blocks.append(c.name or "")
        text_blocks.append(c.format or "")
        text_blocks.append(c.cadence or "")
    for r in (baseline.raid_items or []):
        text_blocks.append(r.description or "")

    combined = " ".join(text_blocks).lower()
    if any(phrase in combined for phrase in ("acceptance review", "milestone sign-off", "milestone sign off", "end-of-milestone", "end of milestone", "end of each milestone")):
        return "milestone-level"
    return "per-deliverable"


def _normalize_rating_v2(val: Optional[str]) -> Tuple[str, Optional[str]]:
    """Normalize Probability / Impact rating to High, Medium, Low."""
    if not val or not val.strip():
        return "", None
    v = val.strip().lower()
    if v in ("very high", "critical", "high"):
        return "High", None
    if v in ("medium", "moderate"):
        return "Medium", None
    if v in ("low", "very low"):
        return "Low", None
    return "Medium", f"Rating normalized from '{val}'"


def _normalize_status_v2(val: Optional[str]) -> Tuple[str, Optional[str]]:
    """Normalize RAID Status."""
    if not val or not val.strip():
        return "Open", None
    v = val.strip().lower()
    if v in ("open", "in progress", "monitoring", "escalated", "closed"):
        return val.title() if v != "in progress" else "In Progress", None
    if v in ("resolved", "done", "complete"):
        return "Closed", None
    if v in ("pending", "unconfirmed", "draft"):
        return "Open", None
    return "Open", f"Status normalized from '{val}'"


def build_workbook_model(
    baseline: StartupKitBaseline,
    today: Optional[date] = None,
    start_date: Optional[date] = None,
) -> WorkbookModel:
    """Pure builder that transforms a StartupKitBaseline into a complete WorkbookModel according to v2 spec."""
    if today is None:
        today = date.today()

    ctx = baseline.governance_context
    charter = baseline.charter
    comm_guard = baseline.commercial_guardrails
    comms = baseline.communications_plan or []

    client_name = (
        (ctx.client_name if ctx and ctx.client_name else None)
        or (charter.client_name if charter and getattr(charter, "client_name", None) else None)
        or (charter.client_sponsor if charter and getattr(charter, "client_sponsor", None) else None)
        or "N/A"
    )
    contract_type = (
        (charter.contract_type if charter and getattr(charter, "contract_type", None) else None)
        or (ctx.contract_type if ctx and getattr(ctx, "contract_type", None) else None)
        or "Time and Materials"
    )
    talent_pm = normalize_person_name(charter.talent_pm if charter and getattr(charter, "talent_pm", None) else "Unassigned")
    delivery_manager = normalize_person_name(charter.delivery_manager if charter and getattr(charter, "delivery_manager", None) else "Unassigned")

    proj_start_date, start_date_basis = calculate_start_date(baseline, start_date, today)

    # 1. Defensive filtering on baseline items
    excluded_items = 0

    filtered_milestones: List[Milestone] = []
    for m in (baseline.milestones or []):
        m_text = f"{m.id} {m.description or ''} {' '.join(m.key_dependencies or [])}"
        if is_defensive_excluded(m_text):
            logger.warning("Defensive filter dropped milestone: %s (%s)", m.id, m.description)
            excluded_items += 1
        else:
            filtered_milestones.append(m)

    filtered_deliverables: List[Deliverable] = []
    for d in (baseline.deliverables or []):
        d_text = f"{d.id} {d.name or ''} {d.description or ''} {d.acceptance_criteria or ''}"
        if is_defensive_excluded(d_text):
            logger.warning("Defensive filter dropped deliverable: %s (%s)", d.id, d.name)
            excluded_items += 1
        else:
            filtered_deliverables.append(d)

    filtered_backlog: List[WorkPackageSeed] = []
    for wp in (baseline.backlog_seed or []):
        wp_text = f"{wp.id} {wp.title or ''} {wp.description or ''}"
        if is_defensive_excluded(wp_text):
            logger.warning("Defensive filter dropped work package: %s (%s)", wp.id, wp.title)
            excluded_items += 1
        else:
            filtered_backlog.append(wp)

    filtered_raid_items: List[RiskAssumption] = []
    for r in (baseline.raid_items or []):
        r_id = getattr(r, "id", "") or getattr(r, "item_id", "") or ""
        r_text = f"{r_id} {r.description or ''} {getattr(r, 'risk_description', '')}"
        if is_defensive_excluded(r_text):
            logger.warning("Defensive filter dropped RAID item: %s (%s)", r_id, r.description)
            excluded_items += 1
        else:
            filtered_raid_items.append(r)

    filtered_deps: List[DependencyAssumptionItem] = []
    for dep in (baseline.dependencies_assumptions or []):
        dep_id = getattr(dep, "id", "") or getattr(dep, "item_id", "") or ""
        dep_text = f"{dep_id} {dep.description or ''}"
        if is_defensive_excluded(dep_text):
            logger.warning("Defensive filter dropped dependency item: %s (%s)", dep_id, dep.description)
            excluded_items += 1
        else:
            filtered_deps.append(dep)

    filtered_ambiguities: List[ContractAmbiguityItem] = []
    for amb in (baseline.contract_ambiguities or []):
        amb_text = f"{amb.anomaly_id} {amb.conflicting_clauses or ''} {amb.risk_impact or ''}"
        if is_defensive_excluded(amb_text):
            logger.warning("Defensive filter dropped contract ambiguity item: %s", amb.anomaly_id)
            excluded_items += 1
        else:
            filtered_ambiguities.append(amb)

    # 2. Parse milestone phases & week ranges
    parsed_phases: Dict[str, ParsedMilestonePhase] = {}
    for m in filtered_milestones:
        parsed_phases[m.id] = parse_milestone_phase(m)

    # Predecessors map: milestone_id -> predecessor_milestone_id
    ms_by_phase_code: Dict[str, Milestone] = {}
    for m in filtered_milestones:
        p = parsed_phases.get(m.id)
        if p and p.phase_code:
            ms_by_phase_code[p.phase_code.upper()] = m

    ms_predecessors: Dict[str, str] = {}
    ms_schedule_links: Dict[str, Set[str]] = {m.id: set() for m in filtered_milestones}

    for m in filtered_milestones:
        dep_texts = list(m.key_dependencies or []) + list(m.critical_path_assumptions or [])
        for dt in dep_texts:
            pred_match = PREDECESSOR_REGEX.search(dt)
            if pred_match:
                pred_phase = pred_match.group("phase").upper()
                if pred_phase in ms_by_phase_code and ms_by_phase_code[pred_phase].id != m.id:
                    pred_m = ms_by_phase_code[pred_phase]
                    ms_predecessors[m.id] = pred_m.id
                    ms_schedule_links[m.id].add(dt)

    # Date resolution per milestone
    ms_planned_start: Dict[str, Optional[date]] = {}
    ms_planned_finish: Dict[str, Optional[date]] = {}
    ms_date_basis: Dict[str, str] = {}
    ms_notes: Dict[str, List[str]] = {m.id: [] for m in filtered_milestones}

    for idx, m in enumerate(filtered_milestones):
        p = parsed_phases.get(m.id)
        if p and p.note:
            ms_notes[m.id].append(p.note)

        # Check week range
        week_range = parse_week_range(m.description or "")
        if not week_range:
            for cpa in (m.critical_path_assumptions or []):
                week_range = parse_week_range(cpa)
                if week_range:
                    break

        if m.external_date is not None:
            # Precedence 1: Contract date
            ms_planned_finish[m.id] = m.external_date
            ms_date_basis[m.id] = "Contract date"
            # Planned start: previous finish + 1 working day or project start date
            if idx == 0:
                ms_planned_start[m.id] = proj_start_date
            else:
                prev_finish = ms_planned_finish.get(filtered_milestones[idx - 1].id)
                ms_planned_start[m.id] = next_working_day(prev_finish) if prev_finish else proj_start_date
        elif week_range is not None:
            # Precedence 2: Week range
            w_a, w_b = week_range
            p_start = proj_start_date + timedelta(days=7 * (w_a - 1))
            p_finish = proj_start_date + timedelta(days=7 * (w_b - 1) + 4)
            ms_planned_start[m.id] = p_start
            ms_planned_finish[m.id] = p_finish
            ms_date_basis[m.id] = f"SOW estimate, weeks {w_a}–{w_b}" if w_a != w_b else f"SOW estimate, week {w_a}"
        else:
            # Precedence 3: To be confirmed
            ms_planned_start[m.id] = None
            ms_planned_finish[m.id] = None
            ms_date_basis[m.id] = "To be confirmed"
            ms_notes[m.id].append("Dates not stated in the SOW [CONFIRMATION REQUIRED]")

    # 3. Sort milestones in delivery sequence: planned_start, then external_date, then natural sort of ID
    def delivery_sort_key(m: Milestone):
        p_start = ms_planned_start.get(m.id) or date.max
        ext_d = m.external_date or date.max
        return (p_start, ext_d, natural_sort_key(m.id))

    sorted_milestones = sorted(filtered_milestones, key=delivery_sort_key)

    # Group milestones into phase workstreams preserving delivery order
    # Milestones sharing a phase code share a workstream
    workstream_groups: List[Tuple[str, List[Milestone]]] = []
    seen_workstreams: Dict[str, List[Milestone]] = {}

    for m in sorted_milestones:
        p = parsed_phases.get(m.id)
        ws_name = p.workstream_name if p else "Build & Configuration"
        if ws_name not in seen_workstreams:
            seen_workstreams[ws_name] = []
            workstream_groups.append((ws_name, seen_workstreams[ws_name]))
        seen_workstreams[ws_name].append(m)

    # 4. Map deliverables to milestones & work packages to deliverables
    deliv_mapping, wp_to_ms, deliv_to_matched_wp = map_deliverables_to_milestones_v2(
        filtered_deliverables, sorted_milestones, filtered_backlog, parsed_phases
    )
    unmapped_count = sum(1 for _, (_, _, is_unmapped) in deliv_mapping.items() if is_unmapped)

    # Deliverables per milestone
    delivs_by_ms: Dict[str, List[Deliverable]] = {m.id: [] for m in sorted_milestones}
    for d in filtered_deliverables:
        m_obj, _, _ = deliv_mapping[d.id]
        if m_obj.id in delivs_by_ms:
            delivs_by_ms[m_obj.id].append(d)
        else:
            delivs_by_ms[sorted_milestones[-1].id].append(d)

    # Sort deliverables in each milestone by natural sort of ID
    for m_id in delivs_by_ms:
        delivs_by_ms[m_id].sort(key=lambda d: natural_sort_key(d.id))

    # Work packages per milestone
    wps_by_ms: Dict[str, List[WorkPackageSeed]] = {m.id: [] for m in sorted_milestones}
    for wp in filtered_backlog:
        m_obj = wp_to_ms.get(wp.id, sorted_milestones[-1])
        wps_by_ms[m_obj.id].append(wp)

    # Map work packages to deliverables inside each milestone
    matched_wps_by_deliv: Dict[str, List[WorkPackageSeed]] = {}
    other_wps_by_ms: Dict[str, List[WorkPackageSeed]] = {}
    for m in sorted_milestones:
        m_delivs = delivs_by_ms[m.id]
        m_wps = wps_by_ms[m.id]
        deliv_wps, other_wps = map_work_packages_to_deliverables(m_wps, m_delivs)
        matched_wps_by_deliv.update(deliv_wps)
        other_wps_by_ms[m.id] = other_wps

    # 5. Build WBS and Schedule Rows
    wbs_rows: List[WBSRow] = []
    schedule_rows: List[ScheduleRow] = []

    # Map milestone ID to its Schedule WBS Code (e.g. "1.1", "2.1")
    ms_wbs_code_map: Dict[str, str] = {}
    # Map deliverable ID to its level 3 WBS Code (e.g. "1.1.2")
    deliv_wbs_code_map: Dict[str, str] = {}

    acceptance_mode = check_acceptance_mode(baseline)
    has_uat = any("uat" in (f"{m.description or ''} {' '.join(m.critical_path_assumptions or [])} {r.description or ''}").lower()
                  for m in (baseline.milestones or []) for r in (baseline.raid_items or []))

    # Identify project end date
    all_finish_dates = [ms_planned_finish[m.id] for m in sorted_milestones if ms_planned_finish.get(m.id)]
    proj_finish_date = max(all_finish_dates) if all_finish_dates else proj_start_date + timedelta(days=30)

    # Calculate WBS numbers
    current_ws_idx = 0

    for ws_name, ms_list in workstream_groups:
        current_ws_idx += 1
        ws_wbs_code = str(current_ws_idx)

        # Workstream Level 1 row in WBS
        wbs_rows.append(WBSRow(
            wbs_code=ws_wbs_code,
            level=1,
            element_type="Workstream",
            name=ws_name,
            workstream=ws_name,
            milestone_id="",
            deliverable_id="",
            source_id="",
            owner="",
            planned_start=None,
            planned_finish=None,
            milestone_date=None,
            status="",
            cadence="",
            predecessors="",
            acceptance_criteria="",
            linked_raid_ids="",
            source="Baseline - Milestone Plan",
            mapping_basis="",
            notes="",
            outline_level=0,
        ))

        # Schedule Level 1 Workstream row
        ws_starts = [ms_planned_start[m.id] for m in ms_list if ms_planned_start.get(m.id)]
        ws_finishes = [ms_planned_finish[m.id] for m in ms_list if ms_planned_finish.get(m.id)]
        ws_min_start = min(ws_starts) if ws_starts else None
        ws_max_finish = max(ws_finishes) if ws_finishes else None

        schedule_rows.append(ScheduleRow(
            wbs_code=ws_wbs_code,
            row_type="Workstream",
            workstream=ws_name,
            milestone_id="",
            name=ws_name,
            scope="",
            owner="",
            planned_start=ws_min_start,
            planned_finish=ws_max_finish,
            internal_buffer_date=None,
            external_date=None,
            date_basis="",
            status="",
            predecessor="",
            client_prerequisites="",
            critical_path_assumptions="",
            linked_deliverables="",
            linked_raid_ids="",
            source="Baseline - Milestone Plan",
            notes="",
            outline_level=0,
        ))

        # Milestones under this workstream
        for ms_idx_in_ws, m in enumerate(ms_list, 1):
            ms_wbs_code = f"{ws_wbs_code}.{ms_idx_in_ws}"
            ms_wbs_code_map[m.id] = ms_wbs_code

            p = parsed_phases.get(m.id)
            ms_name = p.milestone_name if p else (m.description or "")
            ms_scope_clean = p.milestone_scope_clean if p else ""
            ms_owner, ms_owner_note = normalize_owner_v2(m.owner or delivery_manager)

            m_delivs = delivs_by_ms[m.id]
            deliv_ids_str = ", ".join(d.id for d in m_delivs)

            # Filter out schedule links from client prerequisites
            raw_deps = m.key_dependencies or []
            sched_links = ms_schedule_links.get(m.id, set())
            client_prereq_deps = [clean_text_v2(dep) for dep in raw_deps if dep not in sched_links and clean_text_v2(dep)]
            client_prereqs_str = "; ".join(client_prereq_deps)

            cp_assumptions_str = "; ".join(clean_text_v2(cpa) for cpa in (m.critical_path_assumptions or []) if clean_text_v2(cpa))

            all_ms_notes = list(ms_notes.get(m.id, []))
            if ms_owner_note:
                all_ms_notes.append(ms_owner_note)
            final_ms_notes = deduplicate_notes(all_ms_notes)

            pred_ms_id = ms_predecessors.get(m.id, "")

            # Schedule Milestone row
            schedule_rows.append(ScheduleRow(
                wbs_code=ms_wbs_code,
                row_type="Milestone",
                workstream=ws_name,
                milestone_id=m.id,
                name=ms_name,
                scope=ms_scope_clean,
                owner=ms_owner,
                planned_start=ms_planned_start.get(m.id),
                planned_finish=ms_planned_finish.get(m.id),
                internal_buffer_date=m.internal_buffer_date,
                external_date=m.external_date,
                date_basis=ms_date_basis.get(m.id, "To be confirmed"),
                status="Not Started",
                predecessor=pred_ms_id,
                client_prerequisites=client_prereqs_str,
                critical_path_assumptions=cp_assumptions_str,
                linked_deliverables=deliv_ids_str,
                linked_raid_ids="",  # Populated after RAID pass
                source="Baseline - Milestone Plan",
                notes=final_ms_notes,
                outline_level=1,
            ))

            # Milestone Level 2 row in WBS
            wbs_rows.append(WBSRow(
                wbs_code=ms_wbs_code,
                level=2,
                element_type="Milestone",
                name=ms_name,
                workstream=ws_name,
                milestone_id=m.id,
                deliverable_id="",
                source_id="",
                owner=ms_owner,
                planned_start=ms_planned_start.get(m.id),
                planned_finish=ms_planned_finish.get(m.id),
                milestone_date=m.external_date or ms_planned_finish.get(m.id),
                status="Not Started",
                cadence="",
                predecessors=ms_wbs_code_map.get(pred_ms_id, "") if pred_ms_id else "",
                acceptance_criteria="",
                linked_raid_ids="",
                source="Baseline - Milestone Plan",
                mapping_basis="",
                notes=final_ms_notes,
                outline_level=1,
            ))

            current_l3_idx = 0
            last_prereq_wbs_code: Optional[str] = None
            deliverable_package_wbs_codes: List[str] = []

            # 7.1 Project Kickoff (First milestone only)
            if m == sorted_milestones[0]:
                current_l3_idx += 1
                kickoff_wbs_code = f"{ms_wbs_code}.{current_l3_idx}"
                kickoff_finish = proj_start_date + timedelta(days=4)

                wbs_rows.append(WBSRow(
                    wbs_code=kickoff_wbs_code,
                    level=3,
                    element_type="Work Package",
                    name="Project Kickoff",
                    workstream=ws_name,
                    milestone_id=m.id,
                    deliverable_id="",
                    source_id="",
                    owner=delivery_manager,
                    planned_start=proj_start_date,
                    planned_finish=kickoff_finish,
                    milestone_date=None,
                    status="Not Started",
                    cadence="",
                    predecessors="",
                    acceptance_criteria="",
                    linked_raid_ids="",
                    source="PM Best Practice",
                    mapping_basis="",
                    notes="",
                    outline_level=2,
                ))

                # Kickoff tasks
                kickoff_tasks: List[Tuple[str, str, str, str]] = []
                one_time_comms = [c for c in comms if clean_text_v2(c.cadence).lower() in ("one-time", "once", "at kickoff")]
                has_kickoff_comm = False

                for c in one_time_comms:
                    c_name = clean_text_v2(c.name)
                    c_aud = clean_text_v2(c.audience)
                    t_name = f"{c_name} for {c_aud}" if c_aud else c_name
                    c_owner = normalize_owner_v2(c.content_owner or delivery_manager)[0]
                    kickoff_tasks.append((t_name, c_owner, "Baseline - Communications Plan", c.id or ""))
                    if "kickoff" in c_name.lower() or "kick-off" in c_name.lower():
                        has_kickoff_comm = True

                if not has_kickoff_comm:
                    kickoff_tasks.append(("Hold client kickoff meeting", delivery_manager, "PM Best Practice", ""))

                kickoff_tasks.append(("Confirm scope, milestones, and acceptance approach with the client", delivery_manager, "PM Best Practice", ""))
                kickoff_tasks.append(("Confirm client approvers and escalation path", delivery_manager, "PM Best Practice", ""))
                kickoff_tasks.append(("Agree status reporting format and cadence", talent_pm, "PM Best Practice", ""))

                prev_task_wbs = ""
                for k_idx, (t_name, t_owner, t_src, t_src_id) in enumerate(kickoff_tasks, 1):
                    t_wbs = f"{kickoff_wbs_code}.{k_idx}"
                    t_name_trunc, t_note = truncate_task_name(t_name)
                    wbs_rows.append(WBSRow(
                        wbs_code=t_wbs,
                        level=4,
                        element_type="Task",
                        name=t_name_trunc,
                        workstream=ws_name,
                        milestone_id=m.id,
                        deliverable_id="",
                        source_id=t_src_id,
                        owner=t_owner,
                        planned_start=proj_start_date,
                        planned_finish=kickoff_finish,
                        milestone_date=None,
                        status="Not Started",
                        cadence="",
                        predecessors=prev_task_wbs,
                        acceptance_criteria="",
                        linked_raid_ids="",
                        source=t_src,
                        mapping_basis="",
                        notes=deduplicate_notes([t_note]),
                        outline_level=3,
                    ))
                    prev_task_wbs = t_wbs

            # 7.2 Client Prerequisites (when milestone has any)
            if client_prereq_deps:
                current_l3_idx += 1
                prereq_wbs_code = f"{ms_wbs_code}.{current_l3_idx}"
                m_start = ms_planned_start.get(m.id)

                wbs_rows.append(WBSRow(
                    wbs_code=prereq_wbs_code,
                    level=3,
                    element_type="Work Package",
                    name="Client Prerequisites",
                    workstream=ws_name,
                    milestone_id=m.id,
                    deliverable_id="",
                    source_id="",
                    owner=talent_pm,
                    planned_start=m_start,
                    planned_finish=m_start,
                    milestone_date=None,
                    status="Not Started",
                    cadence="",
                    predecessors="",
                    acceptance_criteria="",
                    linked_raid_ids="",
                    source="Baseline - Milestone Plan",
                    mapping_basis="",
                    notes="",
                    outline_level=2,
                ))

                prev_task_wbs = ""
                for pr_idx, dep_text in enumerate(client_prereq_deps, 1):
                    pr_task_wbs = f"{prereq_wbs_code}.{pr_idx}"
                    pr_task_name = f"Confirm: {dep_text}"
                    pr_task_name_trunc, pr_note = truncate_task_name(pr_task_name)
                    wbs_rows.append(WBSRow(
                        wbs_code=pr_task_wbs,
                        level=4,
                        element_type="Task",
                        name=pr_task_name_trunc,
                        workstream=ws_name,
                        milestone_id=m.id,
                        deliverable_id="",
                        source_id="",
                        owner=talent_pm,
                        planned_start=m_start,
                        planned_finish=m_start,
                        milestone_date=None,
                        status="Not Started",
                        cadence="",
                        predecessors=prev_task_wbs,
                        acceptance_criteria="",
                        linked_raid_ids="",
                        source="Baseline - Milestone Plan",
                        mapping_basis="",
                        notes=deduplicate_notes([pr_note]),
                        outline_level=3,
                    ))
                    prev_task_wbs = pr_task_wbs
                    last_prereq_wbs_code = pr_task_wbs

            # 7.3 Deliverables under this milestone
            for d in m_delivs:
                current_l3_idx += 1
                deliv_wbs_code = f"{ms_wbs_code}.{current_l3_idx}"
                deliv_wbs_code_map[d.id] = deliv_wbs_code
                deliverable_package_wbs_codes.append(deliv_wbs_code)

                d_name = clean_text_v2(d.name or d.description or "")
                d_owner, d_owner_note = normalize_owner_v2(d.owner or talent_pm)
                _, mapping_basis_str, _ = deliv_mapping[d.id]

                # Work type classification
                work_type, task_templates = classify_deliverable_work_type(d_name)

                # Acceptance criteria & evidence
                ac_text = clean_text_v2(d.acceptance_criteria)
                ev_text = clean_text_v2(d.evidence_required)
                criteria_parts = []
                if ac_text:
                    criteria_parts.append(ac_text)
                if ev_text:
                    criteria_parts.append(f"Evidence: {ev_text}")
                combined_criteria = "; ".join(criteria_parts)

                deliv_notes = [f"Work type: {work_type}"]
                if d_owner_note:
                    deliv_notes.append(d_owner_note)

                m_start = ms_planned_start.get(m.id)
                m_finish = m.internal_buffer_date if m.internal_buffer_date else ms_planned_finish.get(m.id)

                # Deliverable Level 3 row in WBS
                wbs_rows.append(WBSRow(
                    wbs_code=deliv_wbs_code,
                    level=3,
                    element_type="Deliverable",
                    name=d_name,
                    workstream=ws_name,
                    milestone_id=m.id,
                    deliverable_id=d.id,
                    source_id=d.id,
                    owner=d_owner,
                    planned_start=m_start,
                    planned_finish=m_finish,
                    milestone_date=None,
                    status="Not Started",
                    cadence="",
                    predecessors="",
                    acceptance_criteria=combined_criteria,
                    linked_raid_ids="",
                    source="Baseline - Deliverables",
                    mapping_basis=mapping_basis_str,
                    notes=deduplicate_notes(deliv_notes),
                    outline_level=2,
                ))

                # Deliverable Level 4 tasks
                matched_wps = matched_wps_by_deliv.get(d.id, [])
                task_rows_to_add: List[Tuple[str, str, str, str, str, str, Optional[str]]] = []
                # (name, owner, source, source_id, criteria, mapping_basis, note)

                # Work type tasks
                for tmpl in task_templates:
                    if tmpl.is_core and matched_wps:
                        # Replace core task with one task per work package
                        for wp in matched_wps:
                            wp_owner, wp_owner_n = normalize_owner_v2(wp.owner or talent_pm)
                            wp_title = clean_text_v2(wp.title)
                            wp_note = None
                            if wp.parent_deliverable_id and wp.parent_deliverable_id != d.id:
                                wp_note = f"Baseline backlog lists parent {wp.parent_deliverable_id}"
                            all_wp_notes = deduplicate_notes([wp_owner_n, wp_note])
                            task_rows_to_add.append((wp_title, wp_owner, "Baseline - Backlog", wp.id, "", "", all_wp_notes if all_wp_notes else None))
                    else:
                        tmpl_owner = talent_pm if tmpl.owner_role == "Talent PM" else delivery_manager
                        task_rows_to_add.append((tmpl.name, tmpl_owner, "PM Best Practice", "", "", "", None))

                # Assemble acceptance evidence
                task_rows_to_add.append(("Assemble acceptance evidence", talent_pm, "PM Best Practice", "", ev_text, "", None))

                # Internal quality review against acceptance criteria
                task_rows_to_add.append(("Internal quality review against acceptance criteria", delivery_manager, "PM Best Practice", "", "", "", None))

                # Per-deliverable acceptance mode only
                if acceptance_mode == "per-deliverable":
                    task_rows_to_add.append(("Submit for client review", talent_pm, "PM Best Practice", "", "", "", None))
                    task_rows_to_add.append(("Address client feedback and rework", talent_pm, "PM Best Practice", "", "", "", None))
                    task_rows_to_add.append(("Obtain written client acceptance", delivery_manager, "PM Best Practice", "", "", "", None))

                prev_task_wbs = ""
                for t_idx, (t_name, t_owner, t_src, t_src_id, t_crit, t_mb, t_note) in enumerate(task_rows_to_add, 1):
                    t_wbs = f"{deliv_wbs_code}.{t_idx}"
                    t_name_trunc, name_note = truncate_task_name(t_name)
                    all_t_notes = deduplicate_notes([t_note, name_note])

                    # First task depends on last client prerequisites task if one exists
                    if t_idx == 1:
                        task_pred = last_prereq_wbs_code or ""
                    else:
                        task_pred = prev_task_wbs

                    # Check work package dependency references
                    if t_src == "Baseline - Backlog" and t_src_id:
                        # find WP
                        for wp in matched_wps:
                            if wp.id == t_src_id:
                                for dep_ref in (wp.dependency_references or []):
                                    # find if dep_ref is in same milestone
                                    for other_wp in m_wps:
                                        if other_wp.id == dep_ref:
                                            # find other_wp WBS code if already generated
                                            pass

                    wbs_rows.append(WBSRow(
                        wbs_code=t_wbs,
                        level=4,
                        element_type="Task",
                        name=t_name_trunc,
                        workstream=ws_name,
                        milestone_id=m.id,
                        deliverable_id=d.id,
                        source_id=t_src_id,
                        owner=t_owner,
                        planned_start=m_start,
                        planned_finish=m_finish,
                        milestone_date=None,
                        status="Not Started",
                        cadence="",
                        predecessors=task_pred,
                        acceptance_criteria=t_crit,
                        linked_raid_ids="",
                        source=t_src,
                        mapping_basis=t_mb,
                        notes=all_t_notes,
                        outline_level=3,
                    ))
                    prev_task_wbs = t_wbs

            # 7.3 Other {workstream} work (when unmatched work packages exist)
            other_wps = other_wps_by_ms.get(m.id, [])
            if other_wps:
                current_l3_idx += 1
                other_wbs_code = f"{ms_wbs_code}.{current_l3_idx}"
                m_start = ms_planned_start.get(m.id)
                m_finish = m.internal_buffer_date if m.internal_buffer_date else ms_planned_finish.get(m.id)

                wbs_rows.append(WBSRow(
                    wbs_code=other_wbs_code,
                    level=3,
                    element_type="Work Package",
                    name=f"Other {ws_name} work",
                    workstream=ws_name,
                    milestone_id=m.id,
                    deliverable_id="",
                    source_id="",
                    owner=talent_pm,
                    planned_start=m_start,
                    planned_finish=m_finish,
                    milestone_date=None,
                    status="Not Started",
                    cadence="",
                    predecessors="",
                    acceptance_criteria="",
                    linked_raid_ids="",
                    source="Baseline - Backlog",
                    mapping_basis="",
                    notes="",
                    outline_level=2,
                ))

                prev_task_wbs = ""
                for owp_idx, owp in enumerate(other_wps, 1):
                    owp_wbs = f"{other_wbs_code}.{owp_idx}"
                    owp_owner, owp_owner_n = normalize_owner_v2(owp.owner or talent_pm)
                    owp_title = clean_text_v2(owp.title)
                    owp_note = None
                    if owp.parent_deliverable_id:
                        owp_note = f"Baseline backlog lists parent {owp.parent_deliverable_id}"
                    all_owp_notes = deduplicate_notes([owp_owner_n, owp_note])
                    owp_title_trunc, title_note = truncate_task_name(owp_title)

                    task_pred = (last_prereq_wbs_code or "") if owp_idx == 1 else prev_task_wbs

                    wbs_rows.append(WBSRow(
                        wbs_code=owp_wbs,
                        level=4,
                        element_type="Task",
                        name=owp_title_trunc,
                        workstream=ws_name,
                        milestone_id=m.id,
                        deliverable_id="",
                        source_id=owp.id,
                        owner=owp_owner,
                        planned_start=m_start,
                        planned_finish=m_finish,
                        milestone_date=None,
                        status="Not Started",
                        cadence="",
                        predecessors=task_pred,
                        acceptance_criteria="",
                        linked_raid_ids="",
                        source="Baseline - Backlog",
                        mapping_basis="",
                        notes=deduplicate_notes([all_owp_notes, title_note]),
                        outline_level=3,
                    ))
                    prev_task_wbs = owp_wbs

            # 7.4 Milestone Acceptance Package
            current_l3_idx += 1
            accept_pkg_wbs_code = f"{ms_wbs_code}.{current_l3_idx}"
            m_finish_date = ms_planned_finish.get(m.id)

            wbs_rows.append(WBSRow(
                wbs_code=accept_pkg_wbs_code,
                level=3,
                element_type="Work Package",
                name=f"{m.id} Milestone Acceptance",
                workstream=ws_name,
                milestone_id=m.id,
                deliverable_id="",
                source_id="",
                owner=delivery_manager,
                planned_start=ms_planned_start.get(m.id),
                planned_finish=m_finish_date,
                milestone_date=None,
                status="Not Started",
                cadence="",
                predecessors="",
                acceptance_criteria="",
                linked_raid_ids="",
                source="PM Best Practice",
                mapping_basis="",
                notes="",
                outline_level=2,
            ))

            # Acceptance tasks
            accept_tasks: List[Tuple[str, str, str, str]] = []
            per_ms_comms = [c for c in comms if clean_text_v2(c.cadence).lower() in ("end of each milestone", "per milestone", "each milestone")]

            if acceptance_mode == "milestone-level":
                accept_tasks.append(("Prepare milestone acceptance package and evidence", talent_pm, "PM Best Practice", ""))
                if has_uat:
                    accept_tasks.append((f"Support client UAT for {m.id}", delivery_manager, "PM Best Practice", ""))
                if per_ms_comms:
                    for c in per_ms_comms:
                        c_name = clean_text_v2(c.name)
                        c_aud = clean_text_v2(c.audience)
                        t_name = f"{c_name} for {c_aud}" if c_aud else c_name
                        c_owner = normalize_owner_v2(c.content_owner or delivery_manager)[0]
                        accept_tasks.append((t_name, c_owner, "Baseline - Communications Plan", c.id or ""))
                else:
                    accept_tasks.append(("Hold milestone acceptance review with client approvers", delivery_manager, "PM Best Practice", ""))
                accept_tasks.append(("Address client feedback and rework", talent_pm, "PM Best Practice", ""))
                accept_tasks.append(("Obtain milestone sign-off from the client's designated approvers", delivery_manager, "PM Best Practice", ""))
                accept_tasks.append(("Update schedule and RAID Log after acceptance", talent_pm, "PM Best Practice", ""))
            else:
                # Per-deliverable mode
                if has_uat:
                    accept_tasks.append((f"Support client UAT for {m.id}", delivery_manager, "PM Best Practice", ""))
                accept_tasks.append((f"Confirm all {m.id} deliverables are accepted", delivery_manager, "PM Best Practice", ""))
                accept_tasks.append(("Update schedule and RAID Log after acceptance", talent_pm, "PM Best Practice", ""))

            deliv_pkg_deps_str = ", ".join(deliverable_package_wbs_codes)

            prev_task_wbs = ""
            for a_idx, (a_name, a_owner, a_src, a_src_id) in enumerate(accept_tasks, 1):
                a_wbs = f"{accept_pkg_wbs_code}.{a_idx}"
                a_name_trunc, a_note = truncate_task_name(a_name)
                # First task depends on all deliverable packages
                if a_idx == 1:
                    a_pred = deliv_pkg_deps_str
                else:
                    a_pred = prev_task_wbs

                wbs_rows.append(WBSRow(
                    wbs_code=a_wbs,
                    level=4,
                    element_type="Task",
                    name=a_name_trunc,
                    workstream=ws_name,
                    milestone_id=m.id,
                    deliverable_id="",
                    source_id=a_src_id,
                    owner=a_owner,
                    planned_start=ms_planned_start.get(m.id),
                    planned_finish=m_finish_date,
                    milestone_date=None,
                    status="Not Started",
                    cadence="",
                    predecessors=a_pred,
                    acceptance_criteria="",
                    linked_raid_ids="",
                    source=a_src,
                    mapping_basis="",
                    notes=deduplicate_notes([a_note]),
                    outline_level=3,
                ))
                prev_task_wbs = a_wbs

    # 7.5 Final Workstream: Project Management (ongoing)
    current_ws_idx += 1
    pm_ws_code = str(current_ws_idx)
    pm_ws_name = "Project Management (ongoing)"

    wbs_rows.append(WBSRow(
        wbs_code=pm_ws_code,
        level=1,
        element_type="Workstream",
        name=pm_ws_name,
        workstream=pm_ws_name,
        milestone_id="",
        deliverable_id="",
        source_id="",
        owner="",
        planned_start=proj_start_date,
        planned_finish=proj_finish_date,
        milestone_date=None,
        status="",
        cadence="",
        predecessors="",
        acceptance_criteria="",
        linked_raid_ids="",
        source="PM Best Practice",
        mapping_basis="",
        notes="",
        outline_level=0,
    ))

    # Schedule Recurring row
    schedule_rows.append(ScheduleRow(
        wbs_code=pm_ws_code,
        row_type="Workstream",
        workstream=pm_ws_name,
        milestone_id="",
        name=pm_ws_name,
        scope="",
        owner="",
        planned_start=proj_start_date,
        planned_finish=proj_finish_date,
        internal_buffer_date=None,
        external_date=None,
        date_basis="",
        status="",
        predecessor="",
        client_prerequisites="",
        critical_path_assumptions="",
        linked_deliverables="",
        linked_raid_ids="",
        source="PM Best Practice",
        notes="",
        outline_level=0,
    ))

    pm_ms_code = f"{pm_ws_code}.1"
    schedule_rows.append(ScheduleRow(
        wbs_code=pm_ms_code,
        row_type="Recurring",
        workstream=pm_ws_name,
        milestone_id="",
        name="Ongoing Project Management & Reporting",
        scope="",
        owner=delivery_manager,
        planned_start=proj_start_date,
        planned_finish=proj_finish_date,
        internal_buffer_date=None,
        external_date=None,
        date_basis="",
        status="In Progress",
        predecessor="",
        client_prerequisites="",
        critical_path_assumptions="",
        linked_deliverables="",
        linked_raid_ids="",
        source="PM Best Practice",
        notes="Recurring activity, not a SOW milestone",
        outline_level=1,
    ))

    wbs_rows.append(WBSRow(
        wbs_code=pm_ms_code,
        level=2,
        element_type="Recurring",
        name="Ongoing Project Management & Reporting",
        workstream=pm_ws_name,
        milestone_id="",
        deliverable_id="",
        source_id="",
        owner=delivery_manager,
        planned_start=proj_start_date,
        planned_finish=proj_finish_date,
        milestone_date=None,
        status="In Progress",
        cadence="",
        predecessors="",
        acceptance_criteria="",
        linked_raid_ids="",
        source="PM Best Practice",
        mapping_basis="",
        notes="Recurring activity, not a SOW milestone",
        outline_level=1,
    ))

    # Level 3: Reporting and Control
    rep_wbs_code = f"{pm_ms_code}.1"
    wbs_rows.append(WBSRow(
        wbs_code=rep_wbs_code,
        level=3,
        element_type="Work Package",
        name="Reporting and Control",
        workstream=pm_ws_name,
        milestone_id="",
        deliverable_id="",
        source_id="",
        owner=delivery_manager,
        planned_start=proj_start_date,
        planned_finish=proj_finish_date,
        milestone_date=None,
        status="In Progress",
        cadence="",
        predecessors="",
        acceptance_criteria="",
        linked_raid_ids="",
        source="PM Best Practice",
        mapping_basis="",
        notes="",
        outline_level=2,
    ))

    # Tasks under Reporting and Control
    recurring_tasks: List[Tuple[str, str, str, str, str, str]] = []
    # (name, owner, source, source_id, cadence, criteria)

    # Recurring communications items
    for c in comms:
        c_cad = clean_text_v2(c.cadence)
        if c_cad.lower() not in ("one-time", "once", "at kickoff", "end of each milestone", "per milestone", "each milestone"):
            c_name = clean_text_v2(c.name)
            c_aud = clean_text_v2(c.audience)
            t_name = f"{c_name} for {c_aud}" if c_aud else c_name
            c_owner = normalize_owner_v2(c.content_owner or delivery_manager)[0]
            recurring_tasks.append((t_name, c_owner, "Baseline - Communications Plan", c.id or "", c_cad or "Weekly", ""))

    recurring_tasks.append(("Review and update the RAID Log", talent_pm, "PM Best Practice", "", "Weekly", ""))
    recurring_tasks.append(("Update schedule and WBS status", talent_pm, "PM Best Practice", "", "Weekly", ""))
    recurring_tasks.append(("Maintain the decision log", delivery_manager, "PM Best Practice", "", "As needed", ""))

    if comm_guard and getattr(comm_guard, "change_control_trigger", None):
        trigger_text = clean_text_v2(comm_guard.change_control_trigger)
        if trigger_text:
            recurring_tasks.append(("Raise change requests when triggers are met", delivery_manager, "Baseline - Commercial Guardrails", "", "As needed", trigger_text))

    for r_idx, (t_name, t_owner, t_src, t_src_id, t_cad, t_crit) in enumerate(recurring_tasks, 1):
        t_wbs = f"{rep_wbs_code}.{r_idx}"
        t_name_trunc, t_note = truncate_task_name(t_name)
        wbs_rows.append(WBSRow(
            wbs_code=t_wbs,
            level=4,
            element_type="Task",
            name=t_name_trunc,
            workstream=pm_ws_name,
            milestone_id="",
            deliverable_id="",
            source_id=t_src_id,
            owner=t_owner,
            planned_start=proj_start_date,
            planned_finish=proj_finish_date,
            milestone_date=None,
            status="In Progress",
            cadence=t_cad,
            predecessors="",  # Recurring tasks have no predecessors
            acceptance_criteria=t_crit,
            linked_raid_ids="",
            source=t_src,
            mapping_basis="",
            notes=deduplicate_notes([t_note]),
            outline_level=3,
        ))

    # 6. Build RAID Log
    raid_rows: List[RAIDRow] = []
    all_raw_raid: List[Union[RiskAssumption, DependencyAssumptionItem, ContractAmbiguityItem]] = (
        list(filtered_raid_items) + list(filtered_deps) + list(filtered_ambiguities)
    )

    default_fill_val = detect_default_filled_milestone(all_raw_raid)

    raid_counter = 0
    raid_links_by_ms: Dict[str, List[str]] = {m.id: [] for m in sorted_milestones}

    for item in all_raw_raid:
        raid_counter += 1
        raid_id = f"RAID-{raid_counter:02d}"

        if isinstance(item, ContractAmbiguityItem):
            item_type = "Issue"
            category = "Contract Clarification"
            desc = clean_text_v2(item.conflicting_clauses or item.risk_impact or "")
            src_val = "Baseline - Contract Clarifications"
            src_id = item.anomaly_id or ""
            owner_val, owner_n = normalize_owner_v2(talent_pm)
            prob, imp, sev = "", "", ""
            trig = ""
            mitig = clean_text_v2(item.recommended_clarification or "")
            due_d = None
            status_val, status_n = "Open", None
            decision_val = ""
            dep_val = ""
            r_notes = deduplicate_notes([owner_n, status_n])
        elif isinstance(item, DependencyAssumptionItem):
            item_type = clean_text_v2(item.type or "Dependency")
            category = clean_text_v2(getattr(item, "category", "") or "Technical Dependency")
            desc = clean_text_v2(item.description or "")
            src_val = "Baseline - Dependency Log"
            src_id = item.id or ""
            owner_val, owner_n = normalize_owner_v2(item.owner or talent_pm)
            prob, imp, sev = "", "", ""
            trig = ""
            mitig = ""
            due_d = getattr(item, "target_date", None)
            status_val, status_n = _normalize_status_v2(item.status)
            decision_val = ""
            dep_val = ""
            r_notes = deduplicate_notes([owner_n, status_n])
        else:  # RiskAssumption
            item_type = clean_text_v2(item.type or "Risk")
            category = clean_text_v2(getattr(item, "category", "") or "Delivery Risk")
            desc = clean_text_v2(getattr(item, "description", "") or getattr(item, "risk_description", "") or "")
            src_val = "Baseline - RAID Log"
            src_id = getattr(item, "id", "") or getattr(item, "item_id", "") or ""
            owner_val, owner_n = normalize_owner_v2(item.owner or talent_pm)
            prob, p_n = _normalize_rating_v2(getattr(item, "probability", None))
            imp, i_n = _normalize_rating_v2(getattr(item, "impact", None))
            sev = getattr(item, "severity", "") or ""
            trig = clean_text_v2(getattr(item, "trigger", "") or "")
            mitig = clean_text_v2(getattr(item, "mitigation", "") or "")
            due_d = getattr(item, "due_date", None)
            status_val, status_n = _normalize_status_v2(item.status)
            decision_val = clean_text_v2(getattr(item, "linked_decision", "") or "")
            dep_val = clean_text_v2(getattr(item, "linked_dependency", "") or getattr(item, "linked_dependency_or_assumption", "") or "")
            r_notes = deduplicate_notes([owner_n, p_n, i_n, status_n])

        ws_label, linked_ms_str, linked_wbs_str, link_note = link_raid_item_v2(
            item, sorted_milestones, deliv_mapping, parsed_phases, ms_wbs_code_map, default_fill_val
        )

        all_r_notes = deduplicate_notes([r_notes, link_note])

        # Track links for schedule row
        if linked_ms_str:
            for ms_id_part in [p.strip() for p in linked_ms_str.split(",")]:
                if ms_id_part in raid_links_by_ms:
                    raid_links_by_ms[ms_id_part].append(raid_id)

        raid_rows.append(RAIDRow(
            raid_id=raid_id,
            type=item_type,
            description=desc,
            category=category,
            workstream=ws_label,
            linked_milestone=linked_ms_str,
            linked_wbs_code=linked_wbs_str,
            owner=owner_val,
            probability=prob,
            impact=imp,
            severity=sev,
            trigger_or_early_warning=trig,
            mitigation_or_response=mitig,
            due_date=due_d,
            status=status_val,
            date_raised=today,
            last_updated=today,
            linked_decision=decision_val,
            linked_dependency_or_assumption=dep_val,
            source=src_val,
            source_id=src_id,
            notes=all_r_notes,
        ))

    # Update ScheduleRow linked_raid_ids
    updated_schedule_rows: List[ScheduleRow] = []
    for s in schedule_rows:
        if s.milestone_id and s.milestone_id in raid_links_by_ms:
            r_ids = ", ".join(raid_links_by_ms[s.milestone_id])
            updated_schedule_rows.append(ScheduleRow(
                wbs_code=s.wbs_code,
                row_type=s.row_type,
                workstream=s.workstream,
                milestone_id=s.milestone_id,
                name=s.name,
                scope=s.scope,
                owner=s.owner,
                planned_start=s.planned_start,
                planned_finish=s.planned_finish,
                internal_buffer_date=s.internal_buffer_date,
                external_date=s.external_date,
                date_basis=s.date_basis,
                status=s.status,
                predecessor=s.predecessor,
                client_prerequisites=s.client_prerequisites,
                critical_path_assumptions=s.critical_path_assumptions,
                linked_deliverables=s.linked_deliverables,
                linked_raid_ids=r_ids,
                source=s.source,
                notes=s.notes,
                outline_level=s.outline_level,
                child_row_range=s.child_row_range,
            ))
        else:
            updated_schedule_rows.append(s)

    # 7. Timeline weeks calculation
    timeline_weeks: List[date] = []
    timeline_truncated = False
    cur_week = proj_start_date - timedelta(days=proj_start_date.weekday())
    max_weeks = 52
    end_limit = proj_finish_date + timedelta(days=14)

    while cur_week <= end_limit:
        if len(timeline_weeks) >= max_weeks:
            timeline_truncated = True
            break
        timeline_weeks.append(cur_week)
        cur_week += timedelta(days=7)

    return WorkbookModel(
        project_name=baseline.project_name,
        client_name=client_name,
        contract_type=contract_type,
        talent_pm=talent_pm,
        delivery_manager=delivery_manager,
        start_date=proj_start_date,
        start_date_basis=start_date_basis,
        generation_date=today,
        schedule_rows=updated_schedule_rows,
        wbs_rows=wbs_rows,
        raid_rows=raid_rows,
        unmapped_deliverables_count=unmapped_count,
        timeline_weeks=timeline_weeks,
        timeline_truncated=timeline_truncated,
        excluded_items_count=excluded_items,
    )
