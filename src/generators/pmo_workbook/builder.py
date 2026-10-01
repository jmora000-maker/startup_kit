"""Pure workbook model builder converting StartupKitBaseline into project delivery workbook rows (v3 spec)."""

import re
import math
import logging
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple, Set, Sequence, Union, Any

from src.config import (
    sanitize_report_text,
    normalize_person_name,
    extract_sow_references,
    detect_sow_reference_kind,
)
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
    SOWWorkItem,
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
    get_work_type_verb,
)
from src.generators.pmo_workbook.mapping import (
    natural_sort_key,
    map_deliverables_to_milestones_v2,
    map_work_packages_to_deliverables,
    detect_default_filled_milestone,
    detect_default_filled_deliverable,
    detect_backlog_phase_order,
    detect_degenerate_work_packages,
    strip_work_package_prefix,
    link_raid_item_v2,
    score_evidence_consistency,
    tokenize_v2,
    compute_idf,
    compute_score,
    extract_usable_sow_references,
    match_item_to_deliverables_by_reference,
)
from src.generators.pmo_workbook.rows import (
    ScheduleRow,
    WBSRow,
    RAIDRow,
    WorkbookModel,
)

logger = logging.getLogger(__name__)

# Defensive filter: Drop any item matching this pattern (MS-07, Appendix C, INV-04)
DEFENSIVE_FILTER_REGEX = re.compile(
    r"\b(G-?01|g01|readiness\s+gate|startup\s+readiness|readiness\s+checklist|readiness\s+score|gate\s+decision|gate\s+approval|startup\s+kit|mobiliz\w*|ACT-\d+)\b",
    re.IGNORECASE
)

# Week range patterns: "weeks 1–6", "weeks 1-6", "weeks 1 to 6", "week 5"
WEEK_RANGE_REGEX = re.compile(
    r"\bweeks?\s+(\d+)(?:\s*(?:–|—|-|to)\s*(\d+))?\b",
    re.IGNORECASE
)

# Milestone predecessor schedule link trigger words (v3 A3)
SCHEDULE_TRIGGER_REGEX = re.compile(
    r"\b(accept|acceptance|accepted|complete|completion|sign-off|signoff|after|before|begins|starts)\b",
    re.IGNORECASE
)

# Sequential-gate predecessor regex (v4 A15)
SEQUENTIAL_GATE_REGEX = re.compile(
    r"run[s]?\s+(?:sequentially|in\s+sequence)|sequential\s+(?:acceptance\s+)?gates?|each\s+milestone\s+(?:is\s+an\s+acceptance\s+gate|depends\s+on\s+(?:the\s+)?acceptance\s+of\s+the\s+previous)|after\s+the\s+prior\s+milestone\s+is\s+accepted",
    re.IGNORECASE
)

# Citation pattern 1: [V1] doc_name, ref: text (v3 A7)
CITATION_FMT1_REGEX = re.compile(
    r"^\s*\[V\d+\]\s*(?P<doc>[^,]+?\.(?:pdf|docx|pptx))\s*,?\s*(?P<ref>[^:]*?)\s*:\s*(?P<text>.+)$",
    re.IGNORECASE
)
CONTRACT_REF_REGEX = CITATION_FMT1_REGEX

# Citation pattern 2: Exhibit A, ... / Attachment ... (v6 A28, Rev 2 RAID-03)
EXHIBIT_REGEX = re.compile(
    r"\b((?:Exhibit|Attachment|Appendix|Schedule|Annex)\s+(?:[0-9]+(?:\.[0-9]+)*|[A-Z]\b|[IVXLCDM]+\b)(?:,\s*[^,:\n]+)?)\b",
    re.IGNORECASE
)
DOC_FILE_REGEX = re.compile(
    r"\b([A-Za-z0-9_\-]+\.(?:pdf|docx|pptx))\b",
    re.IGNORECASE
)


def extract_contract_reference(text: Optional[str]) -> Tuple[str, Optional[str]]:
    r"""Extract contract reference from text per v4 A16, v6 A28, RAID-03.
    
    Tries formats in order, combined with SOW reference and section extraction:
      1. [V1] DocName.pdf, ref: text
      2. Exhibit / Attachment / Document file citations
      3. SOW references and Section numbers
      
    Returns: (contract_reference, note_if_none)
    """
    if not text:
        return "Not cited", "No clause reference in baseline"

    # Format 1: [V1] bracket citation
    m = CITATION_FMT1_REGEX.match(text)
    if m:
        doc_str = m.group("doc").strip()
        ref_str = m.group("ref").strip()
        ref = f"{doc_str}, {ref_str}" if ref_str else doc_str
        return ref, None

    # Check for Exhibit or document file citation
    exhibit_match = EXHIBIT_REGEX.search(text)
    doc_match = DOC_FILE_REGEX.search(text)
    exhibit_or_doc = ""
    if exhibit_match:
        exhibit_or_doc = exhibit_match.group(1).strip()
    elif doc_match:
        exhibit_or_doc = doc_match.group(1).strip()

    # Extract SOW story IDs / SOW references
    raw_stories = extract_sow_references(text)
    stories: List[str] = [s for s in raw_stories if not re.match(r"^(?:Section|Clause|§)\s*\d", s, re.IGNORECASE)]

    # Section numbers
    raw_sections = re.findall(r"\b(?:Section|Clause|§)\s*(\d+(?:\.\d+)*)\b", text, re.IGNORECASE)
    sections: List[str] = []
    for s in raw_sections:
        if s not in sections:
            sections.append(s)

    parts: List[str] = []
    if exhibit_or_doc:
        parts.append(exhibit_or_doc)
    if stories:
        parts.append(f"Stories: {', '.join(stories)}")
    if sections:
        parts.append(f"Sections: {', '.join(sections)}")

    if parts:
        candidate = " | ".join(parts)
        # Final validation check per RAID-03: must contain file ext, Exhibit word, SOW ref, or section number
        has_ext = bool(re.search(r'\.[a-zA-Z0-9]{2,4}\b', candidate))
        has_exhibit = bool(EXHIBIT_REGEX.search(candidate))
        has_sow_ref = bool(re.search(r'\b(?:[A-Z][A-Z0-9]{1,9}-\d{2,6}|Deliverable\s+\d+(?:\.\d+)*|D\d+(?:\.\d+)*|Task\s+\d+(?:\.\d+)*|WBS\s+\d+(?:\.\d+)*|SOW-\d+(?:-\d+)?)\b', candidate, re.IGNORECASE))
        has_section = bool(re.search(r'\b(?:Sections?|Clause|§)\s*:?\s*\d+(?:\.\d+)*\b', candidate, re.IGNORECASE))
        if has_ext or has_exhibit or has_sow_ref or has_section:
            return candidate, None

    return "Not cited", "No clause reference in baseline"


def extract_story_ids_for_deliverable(d: Deliverable) -> List[str]:
    """Extract SOW references (Story IDs, Deliverable numbers, Task codes, Sections, Synthetic) for a deliverable in order (v5 A21, A22, v6 Section 1.1)."""
    stories: List[str] = []
    # 1. From sow_reference
    if getattr(d, "sow_reference", None):
        for s in extract_sow_references(d.sow_reference):
            if s not in stories:
                stories.append(s)
    # 2. From name or description if any
    text = f"{d.name or ''} {d.description or ''}"
    for s in extract_sow_references(text):
        if s not in stories:
            stories.append(s)
    return stories


def build_synthetic_work_items(baseline: StartupKitBaseline) -> List[SOWWorkItem]:
    """Build synthetic SOW work items from contracted deliverables list when SOW has no identifiers (v6 Section 1.1)."""
    scope_items: List[str] = []
    if baseline.sow_interpretation and baseline.sow_interpretation.contracted_deliverables:
        scope_items = baseline.sow_interpretation.contracted_deliverables
    elif baseline.charter and baseline.charter.high_level_scope:
        scope_items = baseline.charter.high_level_scope

    if not scope_items:
        return []

    from src.generators.pmo_workbook.mapping import _extract_phase_codes_from_text
    phase_counters: Dict[str, int] = {}
    global_counter = 0
    work_items: List[SOWWorkItem] = []

    for item in scope_items:
        item_clean = clean_text_v2(item)
        if not item_clean:
            continue
        pcs = _extract_phase_codes_from_text(item_clean)
        phase_str = pcs[0].upper() if pcs else ""

        if phase_str:
            phase_counters[phase_str] = phase_counters.get(phase_str, 0) + 1
            idx = phase_counters[phase_str]
            ref = f"SOW-{phase_str}-{idx:02d}"
        else:
            global_counter += 1
            ref = f"SOW-{global_counter:02d}"

        toks = tokenize_v2(item_clean)
        fingerprint = sorted(set(toks))

        work_items.append(SOWWorkItem(
            reference=ref,
            reference_kind="Synthetic",
            title=item_clean,
            phase=phase_str,
            owner="Toptal Delivery Team",
            type="Build",
            fingerprint=fingerprint,
        ))

    return work_items


# Per-milestone communications cadence/name pattern (v3 A6)
PER_MILESTONE_COMM_REGEX = re.compile(
    r"each\s+milestone|per\s+milestone|end\s+of\s+(each|every)\s+milestone|milestone\s+acceptance",
    re.IGNORECASE
)


def next_working_day(d: date) -> date:
    """Return the next Monday-to-Friday working day strictly after date d."""
    res = d + timedelta(days=1)
    while res.weekday() >= 5:  # Saturday=5, Sunday=6
        res += timedelta(days=1)
    return res


def last_working_day_before(d: date) -> date:
    """Return the previous Monday-to-Friday working day strictly before date d."""
    res = d - timedelta(days=1)
    while res.weekday() >= 5:  # Saturday=5, Sunday=6
        res -= timedelta(days=1)
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


def clean_contract_text(text: Optional[str]) -> str:
    """Clean text for contract clarification rows without removing contract references (v3 A7)."""
    if not text:
        return ""
    cleaned = ACTION_TAG_REGEX.sub("", str(text))
    cleaned = " ".join(cleaned.split())
    return cleaned.strip(" ;,-\t\r\n")


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
    raw_str = owner.strip()
    norm = normalize_person_name(raw_str)
    norm_clean = clean_text_v2(norm)
    if not norm_clean or norm_clean.upper() in ("UNASSIGNED", "[UNASSIGNED]", "TBD", "[TBD]", "[UNASSIGNED - TO BE CONFIRMED]") or "UNASSIGNED" in norm_clean.upper() or "TBD" in norm_clean.upper():
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
        basis = "Assumed - first Monday after generation date; confirm"

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
    """Pure builder that transforms a StartupKitBaseline into a complete WorkbookModel according to v3 spec."""
    if today is None:
        today = date.today()

    ctx = baseline.governance_context
    charter = baseline.charter
    comm_guard = baseline.commercial_guardrails
    comms = baseline.communications_plan or []
    sow_interp = baseline.sow_interpretation
    contracted_deliverables = sow_interp.contracted_deliverables if sow_interp else []

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

    # Predecessors map: milestone_id -> predecessor_milestone_ids (v3 A3)
    ms_by_phase_code: Dict[str, Milestone] = {}
    ms_by_num: Dict[int, Milestone] = {}
    for m in filtered_milestones:
        p = parsed_phases.get(m.id)
        if p and p.phase_code:
            ms_by_phase_code[p.phase_code.upper()] = m
        num_match = re.search(r"\d+", m.id)
        if num_match:
            ms_by_num[int(num_match.group(0))] = m

    ms_predecessors: Dict[str, List[str]] = {m.id: [] for m in filtered_milestones}
    ms_schedule_links: Dict[str, Set[str]] = {m.id: set() for m in filtered_milestones}

    for m in filtered_milestones:
        dep_texts = list(m.key_dependencies or []) + list(m.critical_path_assumptions or [])
        for dt in dep_texts:
            if not dt or not dt.strip():
                continue
            # Check if this dependency/assumption is a schedule link (v3 A3)
            if SCHEDULE_TRIGGER_REGEX.search(dt):
                # Check for reference to another milestone
                matched_preds: List[Milestone] = []
                for other_m in filtered_milestones:
                    if other_m.id == m.id:
                        continue
                    p_other = parsed_phases.get(other_m.id)
                    p_code = p_other.phase_code.upper() if p_other and p_other.phase_code else ""
                    p_name = p_other.milestone_name if p_other else ""
                    p_ws = p_other.workstream_name if p_other else ""

                    # Check phase code (e.g. P1, P2a)
                    if p_code and re.search(r"\b" + re.escape(p_code) + r"\b", dt, re.IGNORECASE):
                        matched_preds.append(other_m)
                    # Check full phase name (e.g. P1 Foundation, P2a Services and Data)
                    elif p_name and len(p_name) >= 3 and re.search(r"\b" + re.escape(p_name) + r"\b", dt, re.IGNORECASE):
                        matched_preds.append(other_m)
                    elif p_ws and len(p_ws) >= 3 and re.search(r"\b" + re.escape(p_ws) + r"\b", dt, re.IGNORECASE):
                        matched_preds.append(other_m)
                    # Check Milestone N
                    elif re.search(r"\b" + re.escape(other_m.id) + r"\b", dt, re.IGNORECASE):
                        matched_preds.append(other_m)

                if matched_preds:
                    ms_schedule_links[m.id].add(dt)
                    for pred_m in matched_preds:
                        if pred_m.id not in ms_predecessors[m.id]:
                            ms_predecessors[m.id].append(pred_m.id)

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

    # Sequential-gate predecessors check (v4 A15)
    sequential_gate_source_id: Optional[str] = None
    for dep in filtered_deps:
        if SEQUENTIAL_GATE_REGEX.search(dep.description or ""):
            sequential_gate_source_id = dep.id
            break
    if not sequential_gate_source_id:
        for m in filtered_milestones:
            for text in (m.critical_path_assumptions or []) + (m.key_dependencies or []):
                if SEQUENTIAL_GATE_REGEX.search(text):
                    id_match = re.search(r'\b(ASM-\d+|DEP-\d+|RSK-\d+|ISS-\d+)\b', text)
                    if id_match:
                        sequential_gate_source_id = id_match.group(1)
                    else:
                        sequential_gate_source_id = "SOW"
                    break
            if sequential_gate_source_id:
                break
    if not sequential_gate_source_id and sow_interp:
        for text in (sow_interp.assumptions or []) + (sow_interp.dependencies or []):
            if SEQUENTIAL_GATE_REGEX.search(text):
                sequential_gate_source_id = "SOW"
                break
    if not sequential_gate_source_id:
        for r in filtered_raid_items:
            if SEQUENTIAL_GATE_REGEX.search(r.description or ""):
                sequential_gate_source_id = getattr(r, "id", "") or "RAID"
                break

    if sequential_gate_source_id:
        for s_idx in range(1, len(sorted_milestones)):
            curr_m = sorted_milestones[s_idx]
            if not ms_predecessors[curr_m.id]:
                prev_m = sorted_milestones[s_idx - 1]
                ms_predecessors[curr_m.id].append(prev_m.id)
                ms_notes[curr_m.id].append(f"Predecessor from sequential-gate assumption ({sequential_gate_source_id})")

    # DT-06: Predecessor sanity: drop any predecessor pointing to same or later gate in delivery order
    ms_order_index = {m.id: i for i, m in enumerate(sorted_milestones)}
    for curr_m in sorted_milestones:
        curr_idx = ms_order_index[curr_m.id]
        sanitized_preds = []
        for p in ms_predecessors.get(curr_m.id, []):
            p_idx = ms_order_index.get(p)
            if p_idx is not None and p_idx < curr_idx:
                sanitized_preds.append(p)
            else:
                logger.warning(
                    "DT-06: Predecessor %s on %s is forward/self/invalid and has been dropped.",
                    p, curr_m.id
                )
        ms_predecessors[curr_m.id] = sanitized_preds

    # Group milestones into phase workstreams preserving delivery order (v3 A1: exactly one per SOW phase)
    workstream_groups: List[Tuple[str, List[Milestone]]] = []
    seen_workstreams: Dict[str, List[Milestone]] = {}

    for m in sorted_milestones:
        p = parsed_phases.get(m.id)
        ws_name = p.workstream_name if p else "Build & Configuration"
        if ws_name not in seen_workstreams:
            seen_workstreams[ws_name] = []
            workstream_groups.append((ws_name, seen_workstreams[ws_name]))
        seen_workstreams[ws_name].append(m)

    # 4. Map deliverables to milestones & work packages to deliverables (v3 A2, v4 A14, MAP-03)
    sow_catalogue = getattr(baseline, "sow_stories_catalogue", None)
    deliv_mapping, wp_to_ms, deliv_to_matched_wp = map_deliverables_to_milestones_v2(
        filtered_deliverables, sorted_milestones, filtered_backlog, parsed_phases, contracted_deliverables, sow_catalogue
    )
    unmapped_count = sum(1 for _, (_, _, is_unmapped) in deliv_mapping.items() if is_unmapped)
    is_backlog_phase_order_detected, _ = detect_backlog_phase_order(filtered_backlog, sorted_milestones, filtered_deliverables)

    # Deliverables per milestone
    delivs_by_ms: Dict[str, List[Deliverable]] = {m.id: [] for m in sorted_milestones}
    for d in filtered_deliverables:
        m_obj, _, _ = deliv_mapping[d.id]
        if m_obj.id in delivs_by_ms:
            delivs_by_ms[m_obj.id].append(d)
        else:
            delivs_by_ms[sorted_milestones[-1].id].append(d)

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

    # Build Story Index (v4 A17, v6 Section 1.1)
    story_to_deliv_ids: Dict[str, Set[str]] = {}
    for d in filtered_deliverables:
        text = f"{d.name or ''} {d.description or ''} {d.acceptance_criteria or ''} {d.sow_reference or ''}"
        for s in extract_usable_sow_references(text):
            story_to_deliv_ids.setdefault(s, set()).add(d.id)

    for wp in filtered_backlog:
        text = f"{wp.title or ''} {wp.description or ''} {wp.sow_reference or ''}"
        for s in extract_usable_sow_references(text):
            wp_deliv_id = None
            for d_id, wps in matched_wps_by_deliv.items():
                if any(w.id == wp.id for w in wps):
                    wp_deliv_id = d_id
                    break
            if not wp_deliv_id and wp.parent_deliverable_id:
                wp_deliv_id = wp.parent_deliverable_id
            if wp_deliv_id:
                story_to_deliv_ids.setdefault(s, set()).add(wp_deliv_id)

    deliv_to_linked_raid_ids: Dict[str, List[str]] = {d.id: [] for d in filtered_deliverables}

    # Evidence consistency flags (v3 A9)
    evidence_flags_map = score_evidence_consistency(filtered_deliverables)
    flagged_deliv_ids = set(evidence_flags_map.keys())

    # 5. Build WBS and Schedule Rows
    wbs_rows: List[WBSRow] = []
    schedule_rows: List[ScheduleRow] = []

    story_catalogue_titles: Dict[str, str] = {}
    if hasattr(baseline, "sow_stories_catalogue") and baseline.sow_stories_catalogue:
        for st in baseline.sow_stories_catalogue:
            ref_val = getattr(st, "reference", None) or getattr(st, "id", None)
            if ref_val and getattr(st, "title", None):
                story_catalogue_titles[ref_val] = st.title

    # If no story/work item IDs exist anywhere in deliverables or catalogue, build synthetic work items (v6 Section 1.1)
    has_any_sow_refs = any(extract_story_ids_for_deliverable(d) for d in filtered_deliverables)
    if not has_any_sow_refs:
        synthetic_items = build_synthetic_work_items(baseline)
        if synthetic_items:
            for item in synthetic_items:
                story_catalogue_titles[item.reference] = item.title

            # Match synthetic items to deliverables
            deliv_tokens_map = {d.id: tokenize_v2(f"{d.name or ''} {d.description or ''}") for d in filtered_deliverables}
            for s_item in synthetic_items:
                best_d = None
                best_score = -1.0
                for d in filtered_deliverables:
                    d_ms, _, _ = deliv_mapping.get(d.id, (None, "", False))
                    d_phase = ""
                    if d_ms:
                        d_phase = d_ms.id.replace("M", "P")
                    score = 0.0
                    if s_item.phase and d_phase and (s_item.phase in d_phase or d_phase in s_item.phase):
                        score += 1.0
                    d_toks = deliv_tokens_map.get(d.id, [])
                    if d_toks and s_item.fingerprint:
                        overlap = len(set(s_item.fingerprint) & set(d_toks))
                        score += overlap / max(len(s_item.fingerprint), 1)
                    if score > best_score:
                        best_score = score
                        best_d = d
                if best_d is not None:
                    existing_refs = extract_sow_references(best_d.sow_reference or "")
                    if s_item.reference not in existing_refs:
                        best_d.sow_reference = f"{best_d.sow_reference or ''}, {s_item.reference}".strip(", ")
    degenerate_wp_ids = detect_degenerate_work_packages(filtered_backlog, filtered_deliverables)

    # Multi-deliverable work package scoring (MAP-07)
    wp_also_covers: Dict[str, List[str]] = {}
    deliv_covered_by: Dict[str, List[str]] = {}
    all_deliv_names = [d_item.name or d_item.description or "" for d_item in filtered_deliverables]
    all_deliv_toks = [tokenize_v2(name) for name in all_deliv_names]

    for d_item in filtered_deliverables:
        assigned_wps = matched_wps_by_deliv.get(d_item.id, [])
        non_deg_wps = [w for w in assigned_wps if w.id not in degenerate_wp_ids]
        d_gate, _, _ = deliv_mapping.get(d_item.id, (None, "", False))
        d_work_type, _ = classify_deliverable_work_type(d_item.name or d_item.description or "")
        for wp in non_deg_wps:
            wp_work_type, _ = classify_deliverable_work_type(wp.title or "")
            if wp_work_type != "Test" and d_work_type == "Test":
                wp_work_type = "Test"
            wp_toks = tokenize_v2(wp.title or "")
            corpus = all_deliv_toks + [wp_toks]
            idf_dict = compute_idf(corpus)
            N = len(corpus)
            for other_idx, other_d in enumerate(filtered_deliverables):
                if other_d.id != d_item.id:
                    other_gate, _, _ = deliv_mapping.get(other_d.id, (None, "", False))
                    other_work_type, _ = classify_deliverable_work_type(other_d.name or other_d.description or "")
                    
                    # MAP-07: Do not add Covered by / Also covers between Test-type WP and Build/Integration deliverable (or vice versa)
                    if (wp_work_type == "Test" and other_work_type in ("Build", "Integration")) or (other_work_type == "Test" and wp_work_type in ("Build", "Integration")):
                        continue

                    # MAP-07: Only within the same gate
                    if d_gate and other_gate and d_gate.id == other_gate.id:
                        score = compute_score(wp_toks, all_deliv_toks[other_idx], idf_dict, N)
                        shared_toks = set(wp_toks) & set(all_deliv_toks[other_idx])
                        has_distinctive = any(idf_dict.get(t, 0.0) >= math.log(2.0) for t in shared_toks)
                        if score >= 0.45 and has_distinctive:
                            wp_also_covers.setdefault(wp.id, []).append(other_d.id)
                            deliv_covered_by.setdefault(other_d.id, []).append(f"{wp.id} ({d_item.id})")

    # Map milestone ID to its Schedule WBS Code (e.g. "1.1", "2.1")
    ms_wbs_code_map: Dict[str, str] = {}
    deliv_wbs_code_map: Dict[str, str] = {}

    acceptance_mode = check_acceptance_mode(baseline)
    has_uat = any("uat" in (f"{m.description or ''} {' '.join(m.critical_path_assumptions or [])} {r.description or ''}").lower()
                  for m in (baseline.milestones or []) for r in (baseline.raid_items or []))

    # Find per-milestone comms item (v3 A6)
    per_ms_comm_item: Optional[CommunicationsPlanItem] = None
    for c in comms:
        c_text = f"{c.name or ''} {c.cadence or ''} {getattr(c, 'delivery_day', '') or ''}"
        if PER_MILESTONE_COMM_REGEX.search(c_text):
            per_ms_comm_item = c
            break

    # Calculate WBS numbers
    current_ws_idx = 0

    for ws_name, ms_list in workstream_groups:
        current_ws_idx += 1
        ws_wbs_code = str(current_ws_idx)

        # Workstream Level 1 row in WBS (v3 A1: exactly one per SOW phase)
        wbs_rows.append(WBSRow(
            wbs_code=ws_wbs_code,
            level=1,
            element_type="Workstream",
            name=ws_name,
            workstream=ws_name,
            milestone_id="",
            deliverable_id="",
            source_id="",
            sow_stories="",
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
            sow_stories="",
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
            ms_owner = m.owner or "Delivery Manager"

            m_delivs = delivs_by_ms[m.id]
            deliv_ids_str = ", ".join(d.id for d in m_delivs)

            # SOW Stories for Milestone (v5 A22)
            ms_stories: List[str] = []
            for d in m_delivs:
                for s in extract_story_ids_for_deliverable(d):
                    if s not in ms_stories:
                        ms_stories.append(s)
            ms_sow_stories_str = ", ".join(ms_stories)

            # Filter out schedule links from client prerequisites (v3 A3)
            raw_deps = m.key_dependencies or []
            sched_links = ms_schedule_links.get(m.id, set())
            client_prereq_deps = [clean_text_v2(dep) for dep in raw_deps if dep not in sched_links and clean_text_v2(dep)]
            client_prereqs_str = "; ".join(client_prereq_deps)

            cp_assumptions_str = "; ".join(clean_text_v2(cpa) for cpa in (m.critical_path_assumptions or []) if clean_text_v2(cpa))

            all_ms_notes = list(ms_notes.get(m.id, []))
            final_ms_notes = deduplicate_notes(all_ms_notes)

            preds_list = ms_predecessors.get(m.id, [])
            preds_str = ", ".join(preds_list)

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
                predecessor=preds_str,
                client_prerequisites=client_prereqs_str,
                critical_path_assumptions=cp_assumptions_str,
                linked_deliverables=deliv_ids_str,
                sow_stories=ms_sow_stories_str,
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
                sow_stories="",
                owner=ms_owner,
                planned_start=ms_planned_start.get(m.id),
                planned_finish=ms_planned_finish.get(m.id),
                milestone_date=m.external_date or ms_planned_finish.get(m.id),
                status="Not Started",
                cadence="",
                predecessors=preds_str,
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

            # Milestone date calculations for task timing (v3 A10)
            m_start = ms_planned_start.get(m.id)
            m_finish = ms_planned_finish.get(m.id)
            is_multi_week = bool(m_start and m_finish and (m_finish - m_start).days >= 10)

            # Dates for Client Prerequisites (v3 A10)
            prereq_start = proj_start_date
            if m == sorted_milestones[0]:
                prereq_finish = proj_start_date
            else:
                prereq_finish = last_working_day_before(m_start) if m_start else proj_start_date

            # Dates for Deliverables & Other work (v3 A10)
            deliv_start = m_start
            if m.internal_buffer_date:
                deliv_finish = m.internal_buffer_date
            elif is_multi_week and m_finish:
                deliv_finish = m_finish - timedelta(days=7)
            else:
                deliv_finish = m_finish

            # Dates for Milestone Acceptance (v3 A10)
            if is_multi_week and m_finish:
                accept_start = m_finish - timedelta(days=4)
            else:
                accept_start = m_start
            accept_finish = m_finish

            # 7.2 Client Prerequisites (when milestone has any)
            if client_prereq_deps:
                current_l3_idx += 1
                prereq_wbs_code = f"{ms_wbs_code}.{current_l3_idx}"

                wbs_rows.append(WBSRow(
                    wbs_code=prereq_wbs_code,
                    level=3,
                    element_type="Work Package",
                    name="Client Prerequisites",
                    workstream=ws_name,
                    milestone_id=m.id,
                    deliverable_id="",
                    source_id="",
                    sow_stories="",
                    owner="Talent PM",
                    planned_start=prereq_start,
                    planned_finish=prereq_finish,
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
                        sow_stories="",
                        owner="Talent PM",  # v3 A5: role owner
                        planned_start=prereq_start,
                        planned_finish=prereq_finish,
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
                d_owner, d_owner_note = normalize_owner_v2(d.owner or "Talent PM")
                _, mapping_basis_str, _ = deliv_mapping[d.id]

                # SOW stories on deliverable (v5 A22)
                d_story_ids = extract_story_ids_for_deliverable(d)
                d_sow_stories_str = ", ".join(d_story_ids)

                matched_wps = matched_wps_by_deliv.get(d.id, [])
                non_degen_wps = [wp for wp in matched_wps if wp.id not in degenerate_wp_ids]
                degen_wps = [wp for wp in matched_wps if wp.id in degenerate_wp_ids]
                d_source_id = ", ".join(wp.id for wp in degen_wps) if degen_wps else ""

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
                if d.id in evidence_flags_map:
                    _, flag_note = evidence_flags_map[d.id]
                    deliv_notes.append(flag_note)

                # Missing evidence note (v5 A26)
                ev_raw = d.evidence_required or ""
                is_missing_ev = (not ev_raw.strip()) or ("[CONFIRMATION REQUIRED]" in ev_raw) or (ev_raw.strip().lower() in ("placeholder", "none", "tbd"))
                if is_missing_ev:
                    deliv_notes.append("Evidence not defined in baseline - agree with the client")

                # Multi-deliverable coverage on deliverable row (v6 A30)
                if d.id in deliv_covered_by:
                    deliv_notes.append(f"Covered by {', '.join(deliv_covered_by[d.id])}")

                # Deliverable Level 3 row in WBS
                wbs_rows.append(WBSRow(
                    wbs_code=deliv_wbs_code,
                    level=3,
                    element_type="Deliverable",
                    name=d_name,
                    workstream=ws_name,
                    milestone_id=m.id,
                    deliverable_id=d.id,
                    source_id=d_source_id,
                    sow_stories=d_sow_stories_str,
                    owner=d_owner,
                    planned_start=deliv_start,
                    planned_finish=deliv_finish,
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
                task_rows_to_add: List[Tuple[str, str, str, str, str, str, Optional[str], str]] = []
                # (name, owner, source, source_id, criteria, mapping_basis, note, sow_stories)

                # Work type tasks (v5 A21)
                for tmpl in task_templates:
                    if tmpl.is_core:
                        if non_degen_wps:
                            # Option 1: Non-degenerate work packages
                            for wp in non_degen_wps:
                                wp_raw_owner = wp.owner or ""
                                if wp_raw_owner and not any(ph in wp_raw_owner for ph in ("[UNASSIGNED", "[TBD", "TBD")) and "UNASSIGNED" not in wp_raw_owner.upper():
                                    wp_owner = clean_text_v2(wp_raw_owner)
                                else:
                                    wp_owner = "Toptal Delivery Team"
                                wp_title = strip_work_package_prefix(clean_text_v2(wp.title))
                                verb = get_work_type_verb(work_type)
                                if ":" in wp_title:
                                    parts = wp_title.split(":", 1)
                                    ref_prefix = parts[0].strip()
                                    rest = parts[1].strip()
                                    if extract_sow_references(ref_prefix):
                                        t_name = f"{verb} {ref_prefix}: {rest}"
                                    else:
                                        t_name = wp_title
                                else:
                                    t_name = wp_title

                                wp_note_parts = []
                                if not is_backlog_phase_order_detected:
                                    if wp.parent_deliverable_id and wp.parent_deliverable_id != d.id:
                                        wp_note_parts.append(f"Baseline backlog lists parent {wp.parent_deliverable_id}")
                                if wp.id in wp_also_covers:
                                    wp_note_parts.append(f"Also covers {', '.join(wp_also_covers[wp.id])}")
                                wp_note = " | ".join(wp_note_parts) if wp_note_parts else None
                                wp_refs = extract_sow_references(f"{wp.sow_reference or ''} {wp.title or ''}")
                                wp_sow_str = ", ".join(wp_refs) if wp_refs else (wp.sow_reference or "")
                                task_rows_to_add.append((t_name, wp_owner, "Baseline - Backlog", wp.id, "", "", wp_note, wp_sow_str))
                        elif d_story_ids:
                            # Option 2: SOW work items (TXT-04)
                            verb = get_work_type_verb(work_type)
                            for s_id in d_story_ids:
                                s_title = story_catalogue_titles.get(s_id, "")
                                t_name = f"{verb} {s_id}: {s_title}" if s_title else f"{verb} {s_id}"
                                task_rows_to_add.append((t_name, "Toptal Delivery Team", "Baseline - SOW Work Items", s_id, "", "", None, s_id))
                        else:
                            # Option 3: Template core task
                            tmpl_owner = tmpl.owner_role
                            task_rows_to_add.append((tmpl.name, tmpl_owner, "PM Best Practice", "", "", "", None, ""))
                    else:
                        tmpl_owner = tmpl.owner_role  # v3 A5: role string directly
                        task_rows_to_add.append((tmpl.name, tmpl_owner, "PM Best Practice", "", "", "", None, ""))

                # Assemble acceptance evidence (v3 A1, v5 A26)
                ev_task_note = "Evidence not defined in baseline - agree with the client" if is_missing_ev else None
                task_rows_to_add.append(("Assemble acceptance evidence", "Talent PM", "PM Best Practice", "", ev_text, "", ev_task_note, ""))

                # Internal quality review against acceptance criteria (v3 A1)
                task_rows_to_add.append(("Internal quality review against acceptance criteria", "Talent PM", "PM Best Practice", "", "", "", None, ""))

                # Per-deliverable acceptance mode only
                if acceptance_mode == "per-deliverable":
                    task_rows_to_add.append(("Submit for client review", "Delivery Manager", "PM Best Practice", "", "", "", None, ""))
                    task_rows_to_add.append(("Address client feedback and rework", "Talent PM", "PM Best Practice", "", "", "", None, ""))
                    task_rows_to_add.append(("Obtain written client acceptance", "Delivery Manager", "PM Best Practice", "", "", "", None, ""))

                prev_task_wbs = ""
                for t_idx, (t_name, t_owner, t_src, t_src_id, t_crit, t_mb, t_note, t_sow_stories) in enumerate(task_rows_to_add, 1):
                    t_wbs = f"{deliv_wbs_code}.{t_idx}"
                    t_name_trunc, name_note = truncate_task_name(t_name)
                    all_t_notes = deduplicate_notes([t_note, name_note])

                    # First task depends on last client prerequisites task if one exists
                    if t_idx == 1:
                        task_pred = last_prereq_wbs_code or ""
                    else:
                        task_pred = prev_task_wbs

                    wbs_rows.append(WBSRow(
                        wbs_code=t_wbs,
                        level=4,
                        element_type="Task",
                        name=t_name_trunc,
                        workstream=ws_name,
                        milestone_id=m.id,
                        deliverable_id=d.id,
                        source_id=t_src_id,
                        sow_stories=t_sow_stories,
                        owner=t_owner,
                        planned_start=deliv_start,
                        planned_finish=deliv_finish,
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

                wbs_rows.append(WBSRow(
                    wbs_code=other_wbs_code,
                    level=3,
                    element_type="Work Package",
                    name=f"Other {ws_name} work",
                    workstream=ws_name,
                    milestone_id=m.id,
                    deliverable_id="",
                    source_id="",
                    sow_stories="",
                    owner="Talent PM",
                    planned_start=deliv_start,
                    planned_finish=deliv_finish,
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
                    owp_raw_owner = owp.owner or ""
                    if owp_raw_owner and not any(ph in owp_raw_owner for ph in ("[UNASSIGNED", "[TBD", "TBD")) and "UNASSIGNED" not in owp_raw_owner.upper():
                        owp_owner = clean_text_v2(owp_raw_owner)
                    else:
                        owp_owner = "Toptal Delivery Team"
                    owp_title = strip_work_package_prefix(clean_text_v2(owp.title))
                    owp_note = None
                    if owp.parent_deliverable_id:
                        owp_note = f"Baseline backlog lists parent {owp.parent_deliverable_id}"
                    owp_title_trunc, title_note = truncate_task_name(owp_title)

                    task_pred = (last_prereq_wbs_code or "") if owp_idx == 1 else prev_task_wbs

                    owp_refs = extract_sow_references(f"{owp.sow_reference or ''} {owp.title or ''}")
                    owp_sow_str = ", ".join(owp_refs) if owp_refs else (owp.sow_reference or "")

                    wbs_rows.append(WBSRow(
                        wbs_code=owp_wbs,
                        level=4,
                        element_type="Task",
                        name=owp_title_trunc,
                        workstream=ws_name,
                        milestone_id=m.id,
                        deliverable_id="",
                        source_id=owp.id,
                        sow_stories=owp_sow_str,
                        owner=owp_owner,
                        planned_start=deliv_start,
                        planned_finish=deliv_finish,
                        milestone_date=None,
                        status="Not Started",
                        cadence="",
                        predecessors=task_pred,
                        acceptance_criteria="",
                        linked_raid_ids="",
                        source="Baseline - Backlog",
                        mapping_basis="",
                        notes=deduplicate_notes([owp_note, title_note]),
                        outline_level=3,
                    ))
                    prev_task_wbs = owp_wbs

            # 7.4 Milestone Acceptance Package (v3 A1: exactly 6 tasks in milestone-level mode)
            current_l3_idx += 1
            accept_pkg_wbs_code = f"{ms_wbs_code}.{current_l3_idx}"

            wbs_rows.append(WBSRow(
                wbs_code=accept_pkg_wbs_code,
                level=3,
                element_type="Work Package",
                name=f"{m.id} Milestone Acceptance",
                workstream=ws_name,
                milestone_id=m.id,
                deliverable_id="",
                source_id="",
                sow_stories="",
                owner="Delivery Manager",
                planned_start=accept_start,
                planned_finish=accept_finish,
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

            if acceptance_mode == "milestone-level":
                accept_tasks.append(("Prepare milestone acceptance package and evidence", "Talent PM", "PM Best Practice", ""))
                accept_tasks.append(("Support client user acceptance testing", "Delivery Manager", "PM Best Practice", ""))
                
                # Review task (v3 A6)
                if per_ms_comm_item:
                    c_name = clean_text_v2(per_ms_comm_item.name)
                    c_aud = clean_text_v2(per_ms_comm_item.audience)
                    t_name = f"{c_name} for {c_aud}" if c_aud else c_name
                    accept_tasks.append((t_name, "Delivery Manager", "Baseline - Communications Plan", per_ms_comm_item.id or ""))
                else:
                    accept_tasks.append(("Hold milestone acceptance review with client approvers", "Delivery Manager", "PM Best Practice", ""))
                
                accept_tasks.append(("Triage and address client review feedback", "Talent PM", "PM Best Practice", ""))
                accept_tasks.append(("Obtain formal milestone acceptance and sign-off", "Delivery Manager", "PM Best Practice", ""))
                accept_tasks.append(("Update schedule and RAID Log after acceptance", "Delivery Manager", "PM Best Practice", ""))
            else:
                # Per-deliverable mode
                if has_uat:
                    accept_tasks.append((f"Support client UAT for {m.id}", "Delivery Manager", "PM Best Practice", ""))
                accept_tasks.append((f"Confirm all {m.id} deliverables are accepted", "Delivery Manager", "PM Best Practice", ""))
                accept_tasks.append(("Update schedule and RAID Log after acceptance", "Delivery Manager", "PM Best Practice", ""))

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
                    sow_stories="",
                    owner=a_owner,  # v3 A5: role owner
                    planned_start=accept_start,
                    planned_finish=accept_finish,
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

    # 6. Build RAID Log (v3 A4, A7, A8, A11, v4 A16, A17, A18, A19, v5 A23, A25)
    raid_rows: List[RAIDRow] = []
    all_raw_raid: List[Union[RiskAssumption, DependencyAssumptionItem, ContractAmbiguityItem]] = (
        list(filtered_raid_items) + list(filtered_deps) + list(filtered_ambiguities)
    )

    default_fill_ms = detect_default_filled_milestone(all_raw_raid)
    default_fill_deliv = detect_default_filled_deliverable(all_raw_raid)

    raid_counter = 0
    raid_links_by_ms: Dict[str, List[str]] = {m.id: [] for m in sorted_milestones}
    ms_by_id: Dict[str, Milestone] = {m.id: m for m in sorted_milestones}

    # Decision linking helper (v4 A19)
    decisions = baseline.decisions or []
    dec_tokens_list = [tokenize_v2(f"{d.decision_text or ''} {d.rationale or ''}") for d in decisions]
    dec_idf_dict = compute_idf(dec_tokens_list) if decisions else {}
    N_dec = len(decisions)

    def link_decisions_for_row(row_desc: str, row_ref: str, raw_decision: str) -> str:
        if raw_decision and raw_decision.strip():
            return raw_decision.strip()
        if not decisions:
            return ""
        row_stories = set(extract_sow_references(f"{row_desc} {row_ref}"))
        candidates: List[Tuple[float, str]] = []
        row_tokens = tokenize_v2(row_desc)
        for d_idx, dec in enumerate(decisions):
            dec_text = f"{dec.decision_text or ''} {dec.rationale or ''}"
            dec_stories = set(extract_sow_references(dec_text))
            if row_stories and (row_stories & dec_stories):
                candidates.append((2.0, dec.id))
            else:
                score = compute_score(row_tokens, dec_tokens_list[d_idx], dec_idf_dict, N_dec)
                if score >= 0.50:
                    candidates.append((score, dec.id))
        if not candidates:
            return ""
        candidates.sort(key=lambda c: (-c[0], natural_sort_key(c[1])))
        top_ids = [c[1] for c in candidates[:3]]
        return ", ".join(top_ids)

    def link_deliverables_and_stories(
        item_text_for_stories: str,
        current_linked_ms: str,
        current_linked_wbs: str,
        current_ws: str,
        raid_id: str,
    ) -> Tuple[str, str, str, str]:
        """Find matching deliverables via story index (v4 A17) and link milestone(s) (v5 A23)."""
        matched_deliv_ids = match_item_to_deliverables_by_reference(item_text_for_stories, story_to_deliv_ids)
        sorted_deliv_ids = sorted(list(matched_deliv_ids), key=natural_sort_key)
        linked_deliv_str = ", ".join(sorted_deliv_ids)

        new_linked_ms = current_linked_ms
        new_linked_wbs = current_linked_wbs
        new_ws = current_ws

        if linked_deliv_str:
            ms_for_matched: Set[str] = set()
            for d_id in sorted_deliv_ids:
                if d_id in deliv_mapping:
                    m_obj, _, _ = deliv_mapping[d_id]
                    if m_obj and m_obj.id in ms_by_id:
                        ms_for_matched.add(m_obj.id)

            if current_linked_ms:
                for m_id_part in [p.strip() for p in current_linked_ms.split(",") if p.strip()]:
                    if m_id_part in ms_by_id:
                        ms_for_matched.add(m_id_part)

            all_linked_ms = sorted(
                [ms_by_id[m_id] for m_id in ms_for_matched if m_id in ms_by_id],
                key=lambda m: natural_sort_key(m.id)
            )
            if len(all_linked_ms) == 1:
                single_m = all_linked_ms[0]
                new_linked_ms = single_m.id
                p_m = parsed_phases.get(single_m.id)
                new_ws = p_m.workstream_name if p_m else "Build & Configuration"
            elif len(all_linked_ms) > 1:
                new_linked_ms = ", ".join(m.id for m in all_linked_ms)
                new_ws = "Multiple phases"
            else:
                new_linked_ms = ""
                new_ws = "Cross-phase"

            linked_wbs_codes = [deliv_wbs_code_map[d_id] for d_id in sorted_deliv_ids if d_id in deliv_wbs_code_map]
            if linked_wbs_codes:
                new_linked_wbs = ", ".join(linked_wbs_codes)

        for d_id in sorted_deliv_ids:
            if d_id in deliv_to_linked_raid_ids:
                deliv_to_linked_raid_ids[d_id].append(raid_id)

        return linked_deliv_str, new_linked_ms, new_linked_wbs, new_ws

    # Group 1: Risks and Issues (Baseline RAID Log)
    for r_item in filtered_raid_items:
        raid_counter += 1
        raid_id = f"RAID-{raid_counter:02d}"
        item_type = clean_text_v2(r_item.type or "Risk")
        category = clean_text_v2(getattr(r_item, "category", "") or "Delivery Risk")
        desc = clean_text_v2(getattr(r_item, "description", "") or getattr(r_item, "risk_description", "") or "")
        src_val = "Baseline - RAID Log"
        src_id = getattr(r_item, "id", "") or getattr(r_item, "item_id", "") or ""
        owner_val, owner_n = normalize_owner_v2(getattr(r_item, "owner", "") or "Talent PM")
        prob, p_n = _normalize_rating_v2(getattr(r_item, "probability", None))
        imp, i_n = _normalize_rating_v2(getattr(r_item, "impact", None))
        
        raw_sev = getattr(r_item, "severity", "") or ""
        sev_val = ""
        sev_note = None
        if raw_sev and raw_sev.strip().lower() != "medium":
            sev_val = raw_sev.strip()
            sev_note = "Rating from baseline"

        trig = clean_text_v2(getattr(r_item, "trigger", "") or "")
        mitig = clean_text_v2(getattr(r_item, "mitigation", "") or "")
        due_d = getattr(r_item, "due_date", None)
        status_val, status_n = _normalize_status_v2(r_item.status)
        raw_decision_val = clean_text_v2(getattr(r_item, "linked_decision", "") or "")
        decision_val = link_decisions_for_row(desc, "", raw_decision_val)
        dep_val = clean_text_v2(getattr(r_item, "linked_dependency", "") or getattr(r_item, "linked_dependency_or_assumption", "") or "")
        r_notes = deduplicate_notes([p_n, i_n, status_n, sev_note, owner_n])

        ws_label, linked_ms_str, linked_wbs_str, link_note = link_raid_item_v2(
            r_item, sorted_milestones, deliv_mapping, parsed_phases, ms_wbs_code_map,
            default_fill_ms, default_fill_deliv
        )

        linked_deliv_str, linked_ms_str, linked_wbs_str, ws_label = link_deliverables_and_stories(
            f"{desc} {getattr(r_item, 'category', '')}",
            linked_ms_str, linked_wbs_str, ws_label, raid_id
        )

        all_r_notes = deduplicate_notes([r_notes, link_note])

        if linked_ms_str:
            for ms_id_part in [p.strip() for p in linked_ms_str.split(",")]:
                if ms_id_part in raid_links_by_ms:
                    raid_links_by_ms[ms_id_part].append(raid_id)

        raid_rows.append(RAIDRow(
            raid_id=raid_id,
            type=item_type,
            description=desc,
            contract_reference="",
            category=category,
            workstream=ws_label,
            linked_milestone=linked_ms_str,
            linked_wbs_code=linked_wbs_str,
            linked_deliverables=linked_deliv_str,
            owner=owner_val,
            probability=prob,
            impact=imp,
            severity=sev_val,
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

    # Group 2: Dependencies and Assumptions (Baseline Dependency Log)
    for dep_item in filtered_deps:
        raid_counter += 1
        raid_id = f"RAID-{raid_counter:02d}"
        item_type = clean_text_v2(dep_item.type or "Dependency")
        category = clean_text_v2(getattr(dep_item, "category", "") or "Technical Dependency")
        desc = clean_text_v2(dep_item.description or "")
        src_val = "Baseline - Dependency Log"
        src_id = dep_item.id or ""
        owner_val, owner_n = normalize_owner_v2(getattr(dep_item, "owner", "") or "Talent PM")
        prob, imp, sev_val = "", "", ""
        trig = ""
        mitig = ""
        due_d = getattr(dep_item, "target_date", None)
        status_val, status_n = _normalize_status_v2(dep_item.status)
        raw_decision_val = ""
        decision_val = link_decisions_for_row(desc, "", raw_decision_val)
        dep_val = ""
        r_notes = deduplicate_notes([status_n, owner_n])

        ws_label, linked_ms_str, linked_wbs_str, link_note = link_raid_item_v2(
            dep_item, sorted_milestones, deliv_mapping, parsed_phases, ms_wbs_code_map,
            default_fill_ms, default_fill_deliv
        )

        linked_deliv_str, linked_ms_str, linked_wbs_str, ws_label = link_deliverables_and_stories(
            f"{desc} {getattr(dep_item, 'category', '')}",
            linked_ms_str, linked_wbs_str, ws_label, raid_id
        )

        all_r_notes = deduplicate_notes([r_notes, link_note])

        if linked_ms_str:
            for ms_id_part in [p.strip() for p in linked_ms_str.split(",")]:
                if ms_id_part in raid_links_by_ms:
                    raid_links_by_ms[ms_id_part].append(raid_id)

        raid_rows.append(RAIDRow(
            raid_id=raid_id,
            type=item_type,
            description=desc,
            contract_reference="",
            category=category,
            workstream=ws_label,
            linked_milestone=linked_ms_str,
            linked_wbs_code=linked_wbs_str,
            linked_deliverables=linked_deliv_str,
            owner=owner_val,
            probability=prob,
            impact=imp,
            severity=sev_val,
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

    # Group 3: Contract Clarifications (v3 A7, v4 A16)
    for amb_item in filtered_ambiguities:
        raid_counter += 1
        raid_id = f"RAID-{raid_counter:02d}"
        item_type = "Issue"
        category = "Contract Clarification"
        
        # Parse conflicting_clauses with extract_contract_reference
        conf_clauses = amb_item.conflicting_clauses or ""
        match = CITATION_FMT1_REGEX.match(conf_clauses)
        if match:
            doc_str = match.group("doc").strip()
            ref_str = match.group("ref").strip()
            text_str = match.group("text").strip()
            contract_ref = f"{doc_str}, {ref_str}" if ref_str else doc_str
            desc_text = f"{amb_item.category}: {text_str}" if amb_item.category else text_str
            ref_note = None
        else:
            contract_ref, ref_note = extract_contract_reference(conf_clauses)
            clean_clause_text = re.sub(r'^\s*(?:\[V\d+\]\s*[^:]*:\s*|Exhibit\s+[A-Z0-9]+[^:]*:\s*)', '', conf_clauses, flags=re.IGNORECASE)
            desc_text = f"{amb_item.category}: {clean_clause_text}" if amb_item.category else clean_clause_text

        desc = clean_contract_text(desc_text)
        src_val = "Baseline - Contract Clarifications"
        src_id = amb_item.anomaly_id or getattr(amb_item, "id", "") or ""
        owner_val, owner_n = normalize_owner_v2(getattr(amb_item, "owner", "") or "Talent PM")
        prob, imp, sev_val = "", "", ""
        trig = ""
        mitig = clean_contract_text(amb_item.recommended_clarification or "")
        due_d = None
        status_val = "Open"
        raw_decision_val = ""
        decision_val = link_decisions_for_row(desc, contract_ref, raw_decision_val)
        dep_val = ""

        ws_label, linked_ms_str, linked_wbs_str, link_note = link_raid_item_v2(
            amb_item, sorted_milestones, deliv_mapping, parsed_phases, ms_wbs_code_map,
            default_fill_ms, default_fill_deliv
        )

        linked_deliv_str, linked_ms_str, linked_wbs_str, ws_label = link_deliverables_and_stories(
            f"{desc} {contract_ref} {conf_clauses} {getattr(amb_item, 'recommended_clarification', '') or ''}",
            linked_ms_str, linked_wbs_str, ws_label, raid_id
        )

        all_r_notes = deduplicate_notes([link_note, ref_note, owner_n])

        if linked_ms_str:
            for ms_id_part in [p.strip() for p in linked_ms_str.split(",")]:
                if ms_id_part in raid_links_by_ms:
                    raid_links_by_ms[ms_id_part].append(raid_id)

        raid_rows.append(RAIDRow(
            raid_id=raid_id,
            type=item_type,
            description=desc,
            contract_reference=contract_ref,
            category=category,
            workstream=ws_label,
            linked_milestone=linked_ms_str,
            linked_wbs_code=linked_wbs_str,
            linked_deliverables=linked_deliv_str,
            owner=owner_val,
            probability=prob,
            impact=imp,
            severity=sev_val,
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

    # Group 4: Open Questions (v3 A8, v4 A16, TXT-01)
    valid_open_questions: List[Tuple[int, str]] = []
    for q_idx, q_text in enumerate(baseline.open_questions or [], 1):
        if not q_text or not q_text.strip():
            continue
        clean_q = clean_contract_text(q_text)
        if is_defensive_excluded(clean_q) or re.search(r"\brole is unassigned\b", clean_q, re.IGNORECASE):
            continue
        valid_open_questions.append((q_idx, clean_q))

    for orig_q_idx, q_str in valid_open_questions:
        raid_counter += 1
        raid_id = f"RAID-{raid_counter:02d}"
        item_type = "Issue"
        category = "Open Question"
        desc = q_str
        src_val = "Baseline - Open Questions"
        src_id = f"Q-{orig_q_idx:02d}"
        owner_val, owner_n = normalize_owner_v2("Talent PM")
        prob, imp, sev_val = "", "", ""
        trig = ""
        mitig = ""
        due_d = None
        status_val = "Open"
        
        contract_ref, _ = extract_contract_reference(q_str)

        raw_decision_val = ""
        decision_val = link_decisions_for_row(desc, contract_ref, raw_decision_val)
        dep_val = ""

        # Dummy item for linking
        dummy_q_item = RiskAssumption(
            id=src_id,
            type="Issue",
            description=q_str,
            category=category,
            owner=owner_val,
            status="Open",
        )

        ws_label, linked_ms_str, linked_wbs_str, link_note = link_raid_item_v2(
            dummy_q_item, sorted_milestones, deliv_mapping, parsed_phases, ms_wbs_code_map,
            default_fill_ms, default_fill_deliv
        )

        linked_deliv_str, linked_ms_str, linked_wbs_str, ws_label = link_deliverables_and_stories(
            f"{desc} {contract_ref}",
            linked_ms_str, linked_wbs_str, ws_label, raid_id
        )

        all_r_notes = deduplicate_notes([link_note, owner_n])

        if linked_ms_str:
            for ms_id_part in [p.strip() for p in linked_ms_str.split(",")]:
                if ms_id_part in raid_links_by_ms:
                    raid_links_by_ms[ms_id_part].append(raid_id)

        raid_rows.append(RAIDRow(
            raid_id=raid_id,
            type=item_type,
            description=desc,
            contract_reference=contract_ref,
            category=category,
            workstream=ws_label,
            linked_milestone=linked_ms_str,
            linked_wbs_code=linked_wbs_str,
            linked_deliverables=linked_deliv_str,
            owner=owner_val,
            probability=prob,
            impact=imp,
            severity=sev_val,
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
                sow_stories=s.sow_stories,
                linked_raid_ids=r_ids,
                source=s.source,
                notes=s.notes,
                outline_level=s.outline_level,
                child_row_range=s.child_row_range,
            ))
        else:
            updated_schedule_rows.append(s)

    # Update WBSRow linked_raid_ids for Deliverables (v4 A17)
    updated_wbs_rows: List[WBSRow] = []
    for w in wbs_rows:
        if w.element_type == "Deliverable" and w.deliverable_id in deliv_to_linked_raid_ids and deliv_to_linked_raid_ids[w.deliverable_id]:
            r_ids = ", ".join(sorted(list(set(deliv_to_linked_raid_ids[w.deliverable_id])), key=natural_sort_key))
            updated_wbs_rows.append(WBSRow(
                wbs_code=w.wbs_code,
                level=w.level,
                element_type=w.element_type,
                name=w.name,
                workstream=w.workstream,
                milestone_id=w.milestone_id,
                deliverable_id=w.deliverable_id,
                source_id=w.source_id,
                sow_stories=w.sow_stories,
                owner=w.owner,
                planned_start=w.planned_start,
                planned_finish=w.planned_finish,
                milestone_date=w.milestone_date,
                status=w.status,
                cadence=w.cadence,
                predecessors=w.predecessors,
                acceptance_criteria=w.acceptance_criteria,
                linked_raid_ids=r_ids,
                source=w.source,
                mapping_basis=w.mapping_basis,
                notes=w.notes,
                outline_level=w.outline_level,
                child_row_range=w.child_row_range,
            ))
        else:
            updated_wbs_rows.append(w)

    # 7. Timeline columns
    all_valid_dates = [proj_start_date]
    for s in updated_schedule_rows:
        if s.planned_start:
            all_valid_dates.append(s.planned_start)
        if s.planned_finish:
            all_valid_dates.append(s.planned_finish)
        if s.internal_buffer_date:
            all_valid_dates.append(s.internal_buffer_date)
        if s.external_date:
            all_valid_dates.append(s.external_date)

    min_proj_date = min(all_valid_dates)
    max_proj_date = max(all_valid_dates)

    # First Monday on or before min_proj_date
    start_monday = min_proj_date - timedelta(days=min_proj_date.weekday())
    end_monday = max_proj_date - timedelta(days=max_proj_date.weekday())

    timeline_weeks: List[date] = []
    cur_week = start_monday
    timeline_truncated = False

    while cur_week <= end_monday:
        timeline_weeks.append(cur_week)
        if len(timeline_weeks) >= 52:
            timeline_truncated = True
            break
        cur_week += timedelta(days=7)

    # 8. Traceability self-check (v3 A13, v5 A22)
    wb_ms_ids = {s.milestone_id for s in updated_schedule_rows if s.row_type == "Milestone" and s.milestone_id}
    base_ms_ids = {m.id for m in filtered_milestones}
    missing_ms = sorted(base_ms_ids - wb_ms_ids, key=natural_sort_key)

    wb_deliv_ids = {w.deliverable_id for w in updated_wbs_rows if w.level == 3 and w.element_type == "Deliverable" and w.deliverable_id}
    base_deliv_ids = {d.id for d in filtered_deliverables}
    missing_delivs = sorted(base_deliv_ids - wb_deliv_ids, key=natural_sort_key)

    wb_wp_ids = set()
    for w in updated_wbs_rows:
        if w.source_id and (w.source == "Baseline - Backlog" or w.element_type in ("Deliverable", "Work Package")):
            for p in w.source_id.split(","):
                if p.strip():
                    wb_wp_ids.add(p.strip())
    base_wp_ids = {wp.id for wp in filtered_backlog}
    missing_wps = sorted(base_wp_ids - wb_wp_ids, key=natural_sort_key)

    wb_raid_src_ids = {r.source_id for r in raid_rows if r.source_id}
    base_raid_ids = {getattr(r, "id", "") or getattr(r, "item_id", "") for r in filtered_raid_items if getattr(r, "id", "") or getattr(r, "item_id", "")}
    base_dep_ids = {dep.id for dep in filtered_deps if dep.id}
    base_amb_ids = {amb.anomaly_id for amb in filtered_ambiguities if amb.anomaly_id}
    base_q_ids = {f"Q-{q_idx:02d}" for q_idx, _ in valid_open_questions}
    all_base_raid_ids = base_raid_ids | base_dep_ids | base_amb_ids | base_q_ids
    missing_raid = sorted(all_base_raid_ids - wb_raid_src_ids, key=natural_sort_key)

    base_story_ids: Set[str] = set()
    for d in filtered_deliverables:
        for s in extract_story_ids_for_deliverable(d):
            base_story_ids.add(s)
    if hasattr(baseline, "sow_stories_catalogue") and baseline.sow_stories_catalogue:
        for st in baseline.sow_stories_catalogue:
            ref_val = getattr(st, "reference", None) or getattr(st, "id", None)
            if ref_val:
                base_story_ids.add(ref_val)

    wb_story_ids: Set[str] = set()
    for w in updated_wbs_rows:
        if w.sow_stories:
            for s in extract_sow_references(w.sow_stories):
                wb_story_ids.add(s)
    missing_stories = sorted(base_story_ids - wb_story_ids, key=natural_sort_key)

    has_synthetic = any(
        detect_sow_reference_kind(s) == "Synthetic" or s.startswith("SOW-")
        for s in (base_story_ids | wb_story_ids)
    )

    if missing_ms:
        logger.warning("Traceability check: Missing Milestones in workbook: %s", missing_ms)
    if missing_delivs:
        logger.warning("Traceability check: Missing Deliverables in workbook: %s", missing_delivs)
    if missing_wps:
        logger.warning("Traceability check: Missing Work Packages in workbook: %s", missing_wps)
    if missing_raid:
        logger.warning("Traceability check: Missing RAID items in workbook: %s", missing_raid)
    if missing_stories:
        logger.warning("Traceability check: Missing SOW References in workbook: %s", missing_stories)
    if not base_story_ids and not wb_story_ids:
        logger.warning("No SOW work items identified in baseline.")

    traceability_dict: Dict[str, Dict[str, Any]] = {
        "Milestones": {
            "in_baseline": len(base_ms_ids),
            "in_workbook": len(wb_ms_ids),
            "missing_ids": missing_ms,
        },
        "Deliverables": {
            "in_baseline": len(base_deliv_ids),
            "in_workbook": len(wb_deliv_ids),
            "missing_ids": missing_delivs,
        },
        "Work packages": {
            "in_baseline": len(base_wp_ids),
            "in_workbook": len(wb_wp_ids),
            "missing_ids": missing_wps,
        },
        "RAID items": {
            "in_baseline": len(all_base_raid_ids),
            "in_workbook": len(raid_rows),
            "missing_ids": missing_raid,
        },
        "SOW References": {
            "in_baseline": len(base_story_ids),
            "in_workbook": len(wb_story_ids),
            "missing_ids": missing_stories,
            "synthetic": has_synthetic,
            "empty": len(base_story_ids) == 0,
        },
    }
    traceability_dict["SOW Stories"] = traceability_dict["SOW References"]

    evidence_flags_list = sorted(list(flagged_deliv_ids), key=natural_sort_key)

    return WorkbookModel(
        project_name=baseline.project_name or "Project",
        client_name=client_name,
        contract_type=contract_type,
        talent_pm=talent_pm,
        delivery_manager=delivery_manager,
        start_date=proj_start_date,
        start_date_basis=start_date_basis,
        generation_date=today,
        schedule_rows=updated_schedule_rows,
        wbs_rows=updated_wbs_rows,
        raid_rows=raid_rows,
        unmapped_deliverables_count=unmapped_count,
        has_synthetic_sow_references=has_synthetic,
        timeline_weeks=timeline_weeks,
        timeline_truncated=timeline_truncated,
        excluded_items_count=excluded_items,
        evidence_flags_count=len(evidence_flags_list),
        evidence_flags=evidence_flags_list,
        flagged_evidence_deliverables=flagged_deliv_ids,
        traceability=traceability_dict,
    )
