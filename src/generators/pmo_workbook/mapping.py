"""Deliverable-to-milestone and RAID-to-milestone mapping rules for PMO Delivery Alignment Spec v2."""

import re
import math
import logging
from datetime import date
from typing import List, Dict, Optional, Tuple, Sequence, Set, Union
from src.config import sanitize_report_text
from src.core.models import (
    Milestone,
    Deliverable,
    WorkPackageSeed,
    RiskAssumption,
    DependencyAssumptionItem,
    ContractAmbiguityItem,
)
from src.generators.pmo_workbook.workstreams import (
    parse_milestone_phase,
    ParsedMilestonePhase,
)

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "the", "and", "for", "with", "of", "to", "a", "an", "in", "on", "at", "by", "from", "or", "as", "is",
    "are", "be", "phase", "phases", "milestone", "milestones", "deliverable", "deliverables",
    "delivery", "project", "client", "built", "toptal", "accepted", "completed", "complete",
    "est", "week", "weeks", "related", "output", "outputs", "result", "results", "report", "reports", "work",
    "delivered", "estimated", "plus"
}


def natural_sort_key(s: str) -> List:
    """Natural sort key for IDs like MS-2 before MS-10, DEL-01, WP-01."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s or ""))]


def stem_token(token: str) -> str:
    """Strip trailing 'ing' if len > 5, then strip trailing plural s (and ies to y)."""
    t = token
    if t.endswith("ing") and len(t) > 5:
        t = t[:-3]
    if t.endswith("ies") and len(t) > 3:
        return t[:-3] + "y"
    elif t.endswith("s") and not t.endswith("ss") and len(t) > 3:
        return t[:-1]
    return t


def tokenize_v2(text: str) -> List[str]:
    """Tokenize text into lowercase stemmed terms according to spec v3 section A2."""
    if not text:
        return []
    # Lowercase and replace / with space
    t = text.lower().replace("/", " ")
    # Split on anything other than letters, digits, and hyphens
    raw_tokens = re.findall(r"[a-z0-9\-]+", t)
    tokens: List[str] = []

    def process_and_add(tok: str):
        tok = tok.strip("-")
        if not tok or tok.isdigit():
            return
        stemmed = stem_token(tok)
        if len(stemmed) < 3:
            return
        if stemmed in STOP_WORDS or tok in STOP_WORDS:
            return
        tokens.append(stemmed)

    for tok in raw_tokens:
        tok = tok.strip("-")
        if not tok:
            continue
        if "-" in tok:
            # v3 A2: Split hyphenated words into their parts only; do not also keep the whole compound
            for part in tok.split("-"):
                process_and_add(part)
        else:
            process_and_add(tok)

    return tokens


def compute_idf(corpus_tokens_list: Sequence[Sequence[str]]) -> Dict[str, float]:
    """Compute IDF weights: ln((N + 1) / df) for each token across the document corpus."""
    N = len(corpus_tokens_list)
    df_counts: Dict[str, int] = {}
    for doc_tokens in corpus_tokens_list:
        unique_tokens = set(doc_tokens)
        for t in unique_tokens:
            df_counts[t] = df_counts.get(t, 0) + 1

    idf_dict: Dict[str, float] = {}
    for t, df in df_counts.items():
        idf_dict[t] = math.log((N + 1) / df)
    return idf_dict


def compute_score(item_tokens: Sequence[str], target_tokens: Sequence[str], idf_dict: Dict[str, float], N: int = 0) -> float:
    """Compute weighted overlap score(item, target) = sum(IDF of shared) / sum(IDF of item tokens)."""
    item_unique = set(item_tokens)
    target_unique = set(target_tokens)
    if not item_unique:
        return 0.0

    denom = sum(idf_dict.get(t, 0.0) for t in item_unique)
    if denom == 0.0:
        return 0.0
    num = sum(idf_dict.get(t, 0.0) for t in item_unique if t in target_unique)
    return num / denom


def build_milestone_scope_text_for_scoring(
    milestones: Sequence[Milestone],
    parsed_phases: Dict[str, ParsedMilestonePhase],
    contracted_deliverables: Optional[Sequence[str]] = None,
) -> Dict[str, str]:
    """Build milestone scope text for scoring according to v3 A2.
    
    Milestone scope text for scoring = the milestone name (e.g. 'P2a Services and Data accepted'),
    plus its scope, plus every sow_interpretation.contracted_deliverables entry for that phase.
    An entry belongs to a phase when it starts with that phase code (e.g. 'P2a testing: ...').
    Entries with no phase code inherit the code of the entry before them.
    """
    contracted_by_phase: Dict[str, List[str]] = {}
    current_phase_code: Optional[str] = None

    if contracted_deliverables:
        phase_prefix_regex = re.compile(r"^\s*(?P<code>P\d+[a-z]?)\b", re.IGNORECASE)
        for entry in contracted_deliverables:
            if not entry:
                continue
            m = phase_prefix_regex.match(entry)
            if m:
                current_phase_code = m.group("code").upper()
            if current_phase_code:
                contracted_by_phase.setdefault(current_phase_code, []).append(entry)

    scope_texts: Dict[str, str] = {}
    for m in milestones:
        phase = parsed_phases.get(m.id)
        if phase:
            name = phase.milestone_name or ""
            scope = phase.milestone_scope or ""
            phase_code = phase.phase_code.upper() if phase.phase_code else ""
            extra_entries = contracted_by_phase.get(phase_code, []) if phase_code else []
            full_scope = f"{name} {scope} " + " ".join(extra_entries)
        else:
            full_scope = m.description or ""
        scope_texts[m.id] = full_scope.strip()

    return scope_texts


def _extract_phase_codes_from_text(text: str) -> List[str]:
    """Extract phase codes like P1, P2a, P2b, P3 from text."""
    if not text:
        return []
    matches = re.findall(r"\b(P\d+[a-z]?)\b", text, re.IGNORECASE)
    return [m.upper() for m in matches]


def _extract_milestone_n_from_text(text: str) -> List[int]:
    """Extract Milestone N numbers from text like 'Milestone 3' or 'Milestone 1'."""
    if not text:
        return []
    matches = re.findall(r"\bMilestone\s+(\d+)\b", text, re.IGNORECASE)
    return [int(m) for m in matches]


def map_work_packages_to_milestones(
    work_packages: Sequence[WorkPackageSeed],
    milestones: Sequence[Milestone],
    parsed_phases: Dict[str, ParsedMilestonePhase],
    contracted_deliverables: Optional[Sequence[str]] = None,
) -> Dict[str, Milestone]:
    """Map each work package to a milestone using rules 1, 2, and 3."""
    wp_to_ms: Dict[str, Milestone] = {}
    if not milestones:
        return wp_to_ms

    fallback_ms = milestones[-1]
    ms_by_id = {m.id: m for m in milestones}
    ms_by_phase: Dict[str, Milestone] = {}
    for m in milestones:
        phase = parsed_phases.get(m.id)
        if phase and phase.phase_code:
            ms_by_phase[phase.phase_code.upper()] = m

    # Pre-tokenize milestone scopes using v3 enhanced scope text
    ms_scope_dict = build_milestone_scope_text_for_scoring(milestones, parsed_phases, contracted_deliverables)
    ms_scopes = [ms_scope_dict[m.id] for m in milestones]
    ms_tokens_list = [tokenize_v2(s) for s in ms_scopes]
    idf_dict = compute_idf(ms_tokens_list)
    N = len(milestones)

    for wp in work_packages:
        mapped: Optional[Milestone] = None
        wp_title = wp.title or ""

        # Rule 1: Phase code in title
        phase_codes = _extract_phase_codes_from_text(wp_title)
        for pc in phase_codes:
            if pc in ms_by_phase:
                mapped = ms_by_phase[pc]
                break

        # Rule 2: ID mention in milestone description / deps / assumptions
        if mapped is None:
            wp_id_pat = re.compile(r"\b" + re.escape(wp.id) + r"\b", re.IGNORECASE)
            for m in milestones:
                text_block = f"{m.description or ''} {' '.join(m.key_dependencies or [])} {' '.join(m.critical_path_assumptions or [])}"
                if wp_id_pat.search(text_block):
                    mapped = m
                    break

        # Rule 3: Scope match (score >= 0.20)
        if mapped is None:
            wp_tokens = tokenize_v2(wp_title)
            best_score = 0.0
            best_ms = None
            for idx, m in enumerate(milestones):
                score = compute_score(wp_tokens, ms_tokens_list[idx], idf_dict, N)
                if score >= 0.199 and score > best_score:
                    best_score = score
                    best_ms = m
            if best_ms is not None:
                mapped = best_ms

        wp_to_ms[wp.id] = mapped if mapped is not None else fallback_ms

    return wp_to_ms


def map_deliverables_to_milestones_v2(
    deliverables: Sequence[Deliverable],
    milestones: Sequence[Milestone],
    work_packages: Sequence[WorkPackageSeed],
    parsed_phases: Dict[str, ParsedMilestonePhase],
    contracted_deliverables: Optional[Sequence[str]] = None,
) -> Tuple[Dict[str, Tuple[Milestone, str, bool]], Dict[str, Milestone], Dict[str, str]]:
    """Map deliverables to milestones according to Section 6 of v2 spec as amended by v3 A2.
    
    Returns:
      - deliv_mapping: Dict[deliv_id, (milestone, basis, is_unmapped)]
      - wp_to_ms: Dict[wp_id, milestone]
      - deliv_to_matched_wp: Dict[deliv_id, wp_id] for backlog matches
    """
    deliv_mapping: Dict[str, Tuple[Milestone, str, bool]] = {}
    deliv_to_matched_wp: Dict[str, str] = {}

    if not milestones:
        placeholder = Milestone(
            id="MS-TBC",
            description="Delivery milestones to be confirmed",
            external_date=None,
            internal_buffer_date=None,
            owner="PMO Lead"
        )
        for d in deliverables:
            deliv_mapping[d.id] = (placeholder, "Fallback - MS-TBC", True)
        return deliv_mapping, {}, {}

    fallback_ms = milestones[-1]
    ms_by_id = {m.id: m for m in milestones}
    ms_by_phase: Dict[str, Milestone] = {}
    ms_by_num: Dict[int, Milestone] = {}
    for m in milestones:
        phase = parsed_phases.get(m.id)
        if phase and phase.phase_code:
            ms_by_phase[phase.phase_code.upper()] = m
        num_match = re.search(r"\d+", m.id)
        if num_match:
            ms_by_num[int(num_match.group(0))] = m

    # 1. Map work packages to milestones first
    wp_to_ms = map_work_packages_to_milestones(work_packages, milestones, parsed_phases, contracted_deliverables)

    # 2. Pre-compute IDF for milestone scopes using v3 enhanced scope text
    ms_scope_dict = build_milestone_scope_text_for_scoring(milestones, parsed_phases, contracted_deliverables)
    ms_scopes = [ms_scope_dict[m.id] for m in milestones]
    ms_tokens_list = [tokenize_v2(s) for s in ms_scopes]
    ms_idf_dict = compute_idf(ms_tokens_list)
    N_ms = len(milestones)

    # 3. Pre-compute IDF across work packages
    wp_titles = [wp.title or "" for wp in work_packages]
    wp_tokens_list = [tokenize_v2(t) for t in wp_titles]
    wp_idf_dict = compute_idf(wp_tokens_list)
    N_wp = len(work_packages)

    for d in deliverables:
        d_name = d.name or d.description or ""
        mapped: Optional[Milestone] = None
        basis: Optional[str] = None
        is_unmapped = False

        # Rule 1: Phase code (P2b or Milestone N)
        phase_codes = _extract_phase_codes_from_text(d_name)
        for pc in phase_codes:
            if pc in ms_by_phase:
                mapped = ms_by_phase[pc]
                basis = "Phase code"
                break

        if mapped is None:
            ms_nums = _extract_milestone_n_from_text(d_name)
            for num in ms_nums:
                if num in ms_by_num:
                    mapped = ms_by_num[num]
                    basis = "Phase code"
                    break

        # Rule 2: ID mention in milestone description / deps / assumptions
        if mapped is None:
            d_id_pat = re.compile(r"\b" + re.escape(d.id) + r"\b", re.IGNORECASE)
            for m in milestones:
                text_block = f"{m.description or ''} {' '.join(m.key_dependencies or [])} {' '.join(m.critical_path_assumptions or [])}"
                if d_id_pat.search(text_block):
                    mapped = m
                    basis = "Referenced by milestone"
                    break

        # Rule 3: Scope match (score >= 0.20, ties to earlier milestone)
        if mapped is None:
            d_tokens = tokenize_v2(d_name)
            best_score = 0.0
            best_ms = None
            for idx, m in enumerate(milestones):
                score = compute_score(d_tokens, ms_tokens_list[idx], ms_idf_dict, N_ms)
                if score >= 0.199 and score > best_score:
                    best_score = score
                    best_ms = m
            if best_ms is not None:
                mapped = best_ms
                basis = "Scope match"

        # Rule 4: Backlog text match (score >= 0.30 against work package titles)
        if mapped is None and work_packages:
            d_tokens = tokenize_v2(d_name)
            best_wp_score = 0.0
            best_wp: Optional[WorkPackageSeed] = None
            for idx, wp in enumerate(work_packages):
                score = compute_score(d_tokens, wp_tokens_list[idx], wp_idf_dict, N_wp)
                if score >= 0.299 and score > best_wp_score:
                    best_wp_score = score
                    best_wp = wp
            if best_wp is not None:
                mapped = wp_to_ms.get(best_wp.id, fallback_ms)
                basis = "Backlog match"
                deliv_to_matched_wp[d.id] = best_wp.id

        # Rule 5: Submission date
        if mapped is None and getattr(d, "submission_target_date", None):
            sub_date = d.submission_target_date
            candidates = [m for m in milestones if m.external_date and m.external_date >= sub_date]
            if candidates:
                candidates.sort(key=lambda m: (m.external_date, natural_sort_key(m.id)))
                mapped = candidates[0]
                basis = "Submission date"
            else:
                dated = [m for m in milestones if m.external_date]
                if dated:
                    dated.sort(key=lambda m: (m.external_date, natural_sort_key(m.id)), reverse=True)
                    mapped = dated[0]
                    basis = "Submission date"

        # Rule 6: Fallback
        if mapped is None:
            mapped = fallback_ms
            basis = "Unmapped - confirm milestone"
            is_unmapped = True

        deliv_mapping[d.id] = (mapped, basis, is_unmapped)

    return deliv_mapping, wp_to_ms, deliv_to_matched_wp


def map_work_packages_to_deliverables(
    work_packages: Sequence[WorkPackageSeed],
    deliverables_in_milestone: Sequence[Deliverable],
) -> Tuple[Dict[str, List[WorkPackageSeed]], List[WorkPackageSeed]]:
    """Map work packages within a milestone to its mapped deliverables.
    
    Corpus = deliverable names in this milestone + this work package title.
    If best score >= 0.25, assigns to that deliverable (ties go to lower deliverable ID).
    Otherwise, returns as other_work_packages.
    """
    matched_by_deliv: Dict[str, List[WorkPackageSeed]] = {d.id: [] for d in deliverables_in_milestone}
    other_wps: List[WorkPackageSeed] = []

    if not deliverables_in_milestone:
        return matched_by_deliv, list(work_packages)

    deliv_names = [d.name or d.description or "" for d in deliverables_in_milestone]

    for wp in work_packages:
        wp_title = wp.title or ""
        wp_tokens = tokenize_v2(wp_title)

        # Corpus = deliverable names + this WP title
        corpus = [tokenize_v2(name) for name in deliv_names] + [wp_tokens]
        idf_dict = compute_idf(corpus)
        N = len(corpus)

        best_score = 0.0
        best_deliv: Optional[Deliverable] = None

        for idx, d in enumerate(deliverables_in_milestone):
            d_tokens = corpus[idx]
            score = compute_score(wp_tokens, d_tokens, idf_dict, N)
            if score >= 0.249:
                if score > best_score:
                    best_score = score
                    best_deliv = d
                elif score == best_score and best_deliv is not None:
                    # Tie break by natural sort of deliverable ID
                    if natural_sort_key(d.id) < natural_sort_key(best_deliv.id):
                        best_deliv = d

        if best_deliv is not None:
            matched_by_deliv[best_deliv.id].append(wp)
        else:
            other_wps.append(wp)

    # Sort matched WPs by preliminary_sequence or natural sort of WP ID
    for d_id, wps in matched_by_deliv.items():
        wps.sort(key=lambda wp: (getattr(wp, "preliminary_sequence", 0) or 0, natural_sort_key(wp.id)))

    other_wps.sort(key=lambda wp: (getattr(wp, "preliminary_sequence", 0) or 0, natural_sort_key(wp.id)))
    return matched_by_deliv, other_wps


def detect_default_filled_milestone(
    raid_items: Sequence[Union[RiskAssumption, DependencyAssumptionItem, ContractAmbiguityItem]]
) -> Optional[str]:
    """Detect if at least 4 items have linked_milestone and >= 75% share one value."""
    ms_values = []
    for item in raid_items:
        lm = getattr(item, "linked_milestone", None)
        if lm and lm.strip():
            ms_values.append(lm.strip())

    if len(ms_values) >= 4:
        counts: Dict[str, int] = {}
        for v in ms_values:
            counts[v] = counts.get(v, 0) + 1
        for val, count in counts.items():
            if (count / len(ms_values)) >= 0.75:
                logger.info("Detected default-filled RAID linked_milestone '%s' (%d/%d items). Ignoring default fill.", val, count, len(ms_values))
                return val
    return None


def detect_default_filled_deliverable(
    raid_items: Sequence[Union[RiskAssumption, DependencyAssumptionItem, ContractAmbiguityItem]]
) -> Optional[str]:
    """Detect if at least 4 items have linked_deliverable and >= 75% share one value (v3 A4)."""
    deliv_values = []
    for item in raid_items:
        ld = getattr(item, "linked_deliverable", None)
        if ld and ld.strip():
            deliv_values.append(ld.strip())

    if len(deliv_values) >= 4:
        counts: Dict[str, int] = {}
        for v in deliv_values:
            counts[v] = counts.get(v, 0) + 1
        for val, count in counts.items():
            if (count / len(deliv_values)) >= 0.75:
                logger.info("Detected default-filled RAID linked_deliverable '%s' (%d/%d items). Ignoring default fill.", val, count, len(deliv_values))
                return val
    return None


def link_raid_item_v2(
    item: Union[RiskAssumption, DependencyAssumptionItem, ContractAmbiguityItem],
    milestones: Sequence[Milestone],
    deliv_mapping: Dict[str, Tuple[Milestone, str, bool]],
    parsed_phases: Dict[str, ParsedMilestonePhase],
    wbs_code_map: Dict[str, str],
    default_fill_milestone: Optional[str] = None,
    default_fill_deliverable: Optional[str] = None,
) -> Tuple[str, str, str, Optional[str]]:
    """Link a RAID item to milestone(s) and WBS code(s) according to Section 8 as amended by v3 A4.
    
    New linking order (A4):
      1. Phase codes, phase names, and Milestone N mentions in item text
      2. Milestone or deliverable IDs mentioned in the text
      3. Non-default linked_milestone
      4. Non-default linked_deliverable (adds 'Linked via deliverable ...' note)
      5. Otherwise none (Cross-phase)
      
    Returns: (workstream, linked_milestones_str, linked_wbs_codes_str, note)
    """
    desc = getattr(item, "description", "") or getattr(item, "risk_description", "") or getattr(item, "conflicting_clauses", "") or ""
    item_type = getattr(item, "type", "")
    linked_ms_raw = getattr(item, "linked_milestone", None)
    linked_deliv_raw = getattr(item, "linked_deliverable", None)

    ms_by_id = {m.id: m for m in milestones}
    ms_by_phase: Dict[str, Milestone] = {}
    ms_by_num: Dict[int, Milestone] = {}
    for m in milestones:
        phase = parsed_phases.get(m.id)
        if phase and phase.phase_code:
            ms_by_phase[phase.phase_code.upper()] = m
        num_match = re.search(r"\d+", m.id)
        if num_match:
            ms_by_num[int(num_match.group(0))] = m

    linked_milestone_objs: List[Milestone] = []
    note: Optional[str] = None
    text_to_search = f"{desc} {getattr(item, 'category', '')} {getattr(item, 'linked_decision', '')} {getattr(item, 'linked_dependency_or_assumption', '')}"

    # Rule 1: Phase codes, phase names, and Milestone N mentions in the item text
    if re.search(r"\b(all\s+phases|across\s+all\s+phases)\b", text_to_search, re.IGNORECASE):
        for m in milestones:
            if m not in linked_milestone_objs:
                linked_milestone_objs.append(m)
    else:
        phase_codes = _extract_phase_codes_from_text(text_to_search)
        for pc in phase_codes:
            if pc in ms_by_phase:
                m_obj = ms_by_phase[pc]
                if m_obj not in linked_milestone_objs:
                    linked_milestone_objs.append(m_obj)

        ms_nums = _extract_milestone_n_from_text(text_to_search)
        for num in ms_nums:
            if num in ms_by_num:
                m_obj = ms_by_num[num]
                if m_obj not in linked_milestone_objs:
                    linked_milestone_objs.append(m_obj)

        for m in milestones:
            phase = parsed_phases.get(m.id)
            if phase and phase.milestone_name:
                name_clean = phase.milestone_name.strip()
                if len(name_clean) >= 4 and re.search(r"\b" + re.escape(name_clean) + r"\b", text_to_search, re.IGNORECASE):
                    if m not in linked_milestone_objs:
                        linked_milestone_objs.append(m)

    # Rule 2: Milestone or deliverable IDs mentioned in the text
    if not linked_milestone_objs:
        for m in milestones:
            if re.search(r"\b" + re.escape(m.id) + r"\b", text_to_search, re.IGNORECASE):
                if m not in linked_milestone_objs:
                    linked_milestone_objs.append(m)

        for d_id, (m_obj, _, _) in deliv_mapping.items():
            if re.search(r"\b" + re.escape(d_id) + r"\b", text_to_search, re.IGNORECASE):
                if m_obj in ms_by_id.values() and m_obj not in linked_milestone_objs:
                    linked_milestone_objs.append(m_obj)

    # Rule 3: Non-default linked_milestone
    if not linked_milestone_objs and linked_ms_raw and linked_ms_raw.strip():
        val = linked_ms_raw.strip()
        if val != default_fill_milestone:
            parts = [p.strip() for p in val.split(",")]
            for p in parts:
                if p in ms_by_id and ms_by_id[p] not in linked_milestone_objs:
                    linked_milestone_objs.append(ms_by_id[p])

    # Rule 4: Non-default linked_deliverable
    if not linked_milestone_objs and linked_deliv_raw and linked_deliv_raw.strip():
        d_val = linked_deliv_raw.strip()
        if d_val != default_fill_deliverable:
            if d_val in deliv_mapping:
                m_obj, _, _ = deliv_mapping[d_val]
                if m_obj in ms_by_id.values() and m_obj not in linked_milestone_objs:
                    linked_milestone_objs.append(m_obj)
                    note = f"Linked via deliverable {d_val}"

    # Sort linked milestones by natural sort of ID
    linked_milestone_objs.sort(key=lambda m: natural_sort_key(m.id))

    if len(linked_milestone_objs) == 1:
        m = linked_milestone_objs[0]
        phase = parsed_phases.get(m.id)
        workstream = phase.workstream_name if phase else "Cross-phase"
        linked_ms_str = m.id
        linked_wbs_str = wbs_code_map.get(m.id, "")
    elif len(linked_milestone_objs) > 1:
        workstream = "Multiple phases"
        linked_ms_str = ", ".join(m.id for m in linked_milestone_objs)
        linked_wbs_str = ", ".join(wbs_code_map.get(m.id, "") for m in linked_milestone_objs if wbs_code_map.get(m.id))
    else:
        workstream = "Cross-phase"
        linked_ms_str = ""
        linked_wbs_str = ""

    return workstream, linked_ms_str, linked_wbs_str, note


def score_evidence_consistency(
    deliverables: Sequence[Deliverable]
) -> Dict[str, Tuple[str, str]]:
    """Score evidence text against every deliverable's name + acceptance_criteria according to v3 A9.
    
    If own_score < 0.10, best_score >= 0.35, and best_d != d:
      returns dict of deliv_id -> (best_deliv_id, note)
    """
    flagged: Dict[str, Tuple[str, str]] = {}
    if not deliverables:
        return flagged

    target_texts = [
        f"{d.name or ''} {d.acceptance_criteria or ''}".strip()
        for d in deliverables
    ]
    target_tokens_list = [tokenize_v2(t) for t in target_texts]
    idf_dict = compute_idf(target_tokens_list)
    N = len(deliverables)

    for idx, d in enumerate(deliverables):
        ev = d.evidence_required
        if not ev or not ev.strip():
            continue
        # Check for placeholders
        if any(ph in ev for ph in ("[CONFIRMATION REQUIRED]", "[TBD]", "TBD", "[UNASSIGNED - TO BE CONFIRMED]")) or "UNASSIGNED" in ev.upper():
            continue

        ev_tokens = tokenize_v2(ev)
        if not ev_tokens:
            continue

        own_score = compute_score(ev_tokens, target_tokens_list[idx], idf_dict, N)

        best_score = 0.0
        best_idx = idx
        for i in range(N):
            s = compute_score(ev_tokens, target_tokens_list[i], idf_dict, N)
            if s > best_score:
                best_score = s
                best_idx = i

        if own_score < 0.10 and best_score >= 0.35 and best_idx != idx:
            best_d = deliverables[best_idx]
            note = f"Evidence may belong to {best_d.id} - verify against the SOW"
            flagged[d.id] = (best_d.id, note)

    return flagged
