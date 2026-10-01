"""Deliverable-to-milestone and RAID-to-milestone mapping rules for PMO Delivery Alignment Spec v2."""

import re
import math
import logging
from datetime import date
from typing import List, Dict, Optional, Tuple, Sequence, Set, Union
from src.config import sanitize_report_text, extract_sow_references, detect_sow_reference_kind
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

    default_idf = math.log(N + 1) if N > 0 else 1.0
    denom = sum(idf_dict.get(t, default_idf) for t in item_unique)
    if denom == 0.0:
        return 0.0
    num = sum(idf_dict.get(t, default_idf) for t in item_unique if t in target_unique)
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


def strip_work_package_prefix(title: Optional[str]) -> str:
    """Always strip a leading 'Work Package:' (case-insensitive) from work package titles (v5 A24)."""
    if not title:
        return ""
    return re.sub(r"^\s*work\s+package\s*:\s*", "", title, flags=re.IGNORECASE).strip()


def detect_degenerate_work_packages(
    work_packages: Sequence[WorkPackageSeed],
    deliverables: Sequence[Deliverable],
) -> Set[str]:
    """Detect degenerate work packages according to spec v5 A24 and Rev 2 MAP-06.
    
    A work package is degenerate when:
      - Every deliverable has exactly one work package, OR
      - Its title, after removing leading 'Work Package:', scores >= 0.80 against
        its parent deliverable's name (v2 weighted overlap), OR
      - Its title is its parent's name plus generic filler ('implementation task', 'task', 'work package', 'deliverable'), OR
      - Two or more work packages share its title.
    """
    if not work_packages:
        return set()

    degenerate_ids: Set[str] = set()

    # Condition 1: Every deliverable has exactly one work package
    if deliverables and len(work_packages) == len(deliverables) and len(deliverables) > 0:
        return {wp.id for wp in work_packages}

    # Track duplicate titles
    title_counts: Dict[str, List[str]] = {}
    for wp in work_packages:
        clean_t = strip_work_package_prefix(wp.title).lower()
        title_counts.setdefault(clean_t, []).append(wp.id)
    for clean_t, wp_ids in title_counts.items():
        if len(wp_ids) > 1 and clean_t:
            for wid in wp_ids:
                degenerate_ids.add(wid)

    deliv_by_id = {d.id: d for d in deliverables} if deliverables else {}
    for wp in work_packages:
        p_id = wp.parent_deliverable_id.strip() if wp.parent_deliverable_id else ""
        parent = deliv_by_id.get(p_id)
        if parent:
            clean_wp_title = strip_work_package_prefix(wp.title)
            p_name = parent.name or parent.description or ""
            
            # Check generic filler
            clean_filler = re.sub(r'\b(?:implementation\s+task|task|work\s+package|deliverable)\b', '', clean_wp_title, flags=re.IGNORECASE).strip(" :-")
            if clean_filler.lower() == p_name.lower():
                degenerate_ids.add(wp.id)
                continue

            wp_toks = tokenize_v2(clean_wp_title)
            p_toks = tokenize_v2(p_name)
            if not wp_toks or not p_toks:
                continue
            corpus = [wp_toks, p_toks]
            idf = compute_idf(corpus)
            score = compute_score(wp_toks, p_toks, idf, len(corpus))
            if score >= 0.799:
                degenerate_ids.add(wp.id)

    return degenerate_ids


def detect_backlog_phase_order(
    work_packages: Sequence[WorkPackageSeed],
    milestones: Sequence[Milestone],
    deliverables: Optional[Sequence[Deliverable]] = None,
) -> Tuple[bool, List[str]]:
    """Detect if backlog parent IDs encode phases according to spec v4 A14.
    
    Conditions:
      1. Number of distinct parent IDs equals the number of milestones.
      2. Ordered by preliminary_sequence, parent IDs never decrease.
      3. Parent IDs are exactly the first N deliverable IDs in natural order.
      
    Returns: (is_detected, distinct_parents)
    """
    if not work_packages or not milestones:
        return False, []

    num_ms = len(milestones)
    # Sort work packages by preliminary_sequence (treating None as 999999)
    sorted_wps = sorted(
        work_packages,
        key=lambda wp: (getattr(wp, "preliminary_sequence", None) if getattr(wp, "preliminary_sequence", None) is not None else 999999, natural_sort_key(wp.id))
    )

    parents = [wp.parent_deliverable_id.strip() for wp in sorted_wps if wp.parent_deliverable_id and wp.parent_deliverable_id.strip()]
    if not parents:
        return False, []

    distinct_parents: List[str] = []
    for p in parents:
        if p not in distinct_parents:
            distinct_parents.append(p)

    # Condition 1: distinct parents count == number of milestones
    if len(distinct_parents) != num_ms:
        return False, []

    # Condition 2: non-decreasing order
    parent_indices = [distinct_parents.index(p) for p in parents]
    for i in range(len(parent_indices) - 1):
        if parent_indices[i] > parent_indices[i + 1]:
            return False, []

    # Condition 3: the parent IDs are exactly the first N deliverable IDs in natural order
    if deliverables:
        sorted_delivs = sorted(deliverables, key=lambda d: natural_sort_key(d.id))
        expected_parents = [d.id for d in sorted_delivs[:num_ms]]
    else:
        expected_parents = [f"DEL-{i:02d}" for i in range(1, num_ms + 1)]

    if distinct_parents != expected_parents:
        # Also check 1-digit format if applicable e.g. DEL-1, DEL-2...
        expected_1digit = [f"DEL-{i}" for i in range(1, num_ms + 1)]
        if distinct_parents != expected_1digit:
            return False, []

    return True, distinct_parents


def get_reference_phase(ref: str) -> Optional[str]:
    """Helper to detect phase code for a SOW reference."""
    if not ref:
        return None
    ref_clean = ref.strip()
    # Check numbered deliverable e.g. Deliverable 1.2 -> P1, Deliverable 2.1 -> P2
    num_m = re.search(r'Deliverable\s+(\d+)\.', ref_clean, re.IGNORECASE)
    if num_m:
        return f"P{num_m.group(1)}"
    pm = re.search(r'\b(P\d+[a-z]?)\b', ref_clean, re.IGNORECASE)
    if pm:
        return pm.group(1)
    return None


def map_work_packages_to_milestones(
    work_packages: Sequence[WorkPackageSeed],
    milestones: Sequence[Milestone],
    parsed_phases: Dict[str, ParsedMilestonePhase],
    contracted_deliverables: Optional[Sequence[str]] = None,
    deliverables: Optional[Sequence[Deliverable]] = None,
    sow_catalogue: Optional[Sequence[SOWWorkItem]] = None,
) -> Tuple[Dict[str, Milestone], Dict[str, str], bool]:
    """Map each work package to a milestone using MAP-04 precedence rules.
    
    Returns: (wp_to_ms, wp_to_basis, is_phase_order_detected)
    """
    wp_to_ms: Dict[str, Milestone] = {}
    wp_to_basis: Dict[str, str] = {}
    if not milestones:
        return wp_to_ms, wp_to_basis, False

    is_phase_order, distinct_parents = detect_backlog_phase_order(work_packages, milestones, deliverables)
    if is_phase_order:
        logger.info("Backlog parents encode phases, not deliverables; using them as phase order.")
        for wp in work_packages:
            p_id = wp.parent_deliverable_id.strip() if wp.parent_deliverable_id else ""
            if p_id in distinct_parents:
                idx = distinct_parents.index(p_id)
                ms = milestones[idx]
                wp_to_ms[wp.id] = ms
                wp_to_basis[wp.id] = "Backlog phase order"
            else:
                wp_to_ms[wp.id] = milestones[-1]
                wp_to_basis[wp.id] = "Fallback"
        return wp_to_ms, wp_to_basis, True

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

    deliv_by_id = {d.id: d for d in deliverables} if deliverables else {}

    # Build catalogue ref to phase lookup
    cat_ref_phase: Dict[str, str] = {}
    if sow_catalogue:
        for it in sow_catalogue:
            if it.reference and it.phase:
                cat_ref_phase[it.reference] = it.phase.upper()

    for wp in work_packages:
        mapped: Optional[Milestone] = None
        basis: Optional[str] = None
        wp_title = wp.title or ""

        # Rule 1: Work item phase (MAP-04: first!)
        wp_refs = extract_sow_references(f"{wp.sow_reference or ''} {wp.title or ''} {wp.description or ''}")
        ref_phases = {cat_ref_phase[r] for r in wp_refs if r in cat_ref_phase}
        if len(ref_phases) == 1:
            p_code = list(ref_phases)[0]
            if p_code in ms_by_phase:
                mapped = ms_by_phase[p_code]
                basis = "Work item phase"

        # Rule 2: Backlog link from linked_milestones on real parent deliverable (v5 A24)
        if mapped is None:
            p_id = wp.parent_deliverable_id.strip() if wp.parent_deliverable_id else ""
            if p_id in deliv_by_id and wp.linked_milestones:
                for lm in wp.linked_milestones:
                    if lm in ms_by_id:
                        mapped = ms_by_id[lm]
                        basis = "Backlog link"
                        break
                    elif lm.upper() in ms_by_phase:
                        mapped = ms_by_phase[lm.upper()]
                        basis = "Backlog link"
                        break

        # Rule 3: Phase code in title
        if mapped is None:
            phase_codes = _extract_phase_codes_from_text(wp_title)
            for pc in phase_codes:
                if pc in ms_by_phase:
                    mapped = ms_by_phase[pc]
                    basis = "Phase code"
                    break

        # Rule 4: ID mention in milestone description / deps / assumptions
        if mapped is None:
            wp_id_pat = re.compile(r"\b" + re.escape(wp.id) + r"\b", re.IGNORECASE)
            for m in milestones:
                text_block = f"{m.description or ''} {' '.join(m.key_dependencies or [])} {' '.join(m.critical_path_assumptions or [])}"
                if wp_id_pat.search(text_block):
                    mapped = m
                    basis = "Referenced by milestone"
                    break

        # Rule 5: Scope match (score >= 0.20)
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
                basis = "Scope match"

        wp_to_ms[wp.id] = mapped if mapped is not None else fallback_ms
        wp_to_basis[wp.id] = basis if basis is not None else "Fallback"

    return wp_to_ms, wp_to_basis, False


def map_deliverables_to_milestones_v2(
    deliverables: Sequence[Deliverable],
    milestones: Sequence[Milestone],
    work_packages: Sequence[WorkPackageSeed],
    parsed_phases: Dict[str, ParsedMilestonePhase],
    contracted_deliverables: Optional[Sequence[str]] = None,
    sow_catalogue: Optional[Sequence[SOWWorkItem]] = None,
) -> Tuple[Dict[str, Tuple[Milestone, str, bool]], Dict[str, Milestone], Dict[str, str]]:
    """Map deliverables to milestones according to MAP-03 precedence rules.
    
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
    wp_to_ms, wp_to_basis, is_phase_order = map_work_packages_to_milestones(
        work_packages, milestones, parsed_phases, contracted_deliverables, deliverables, sow_catalogue
    )

    # 2. Pre-compute IDF for milestone scopes using v3 enhanced scope text
    ms_scope_dict = build_milestone_scope_text_for_scoring(milestones, parsed_phases, contracted_deliverables)
    ms_scopes = [ms_scope_dict[m.id] for m in milestones]
    ms_tokens_list = [tokenize_v2(s) for s in ms_scopes]
    ms_idf_dict = compute_idf(ms_tokens_list)
    N_ms = len(milestones)

    # 3. Detect degenerate work packages and compute IDF across usable work packages (v5 A24)
    degenerate_wp_ids = detect_degenerate_work_packages(work_packages, deliverables)
    usable_work_packages = [wp for wp in work_packages if wp.id not in degenerate_wp_ids]

    wp_titles = [wp.title or "" for wp in usable_work_packages]
    wp_tokens_list = [tokenize_v2(t) for t in wp_titles]
    wp_idf_dict = compute_idf(wp_tokens_list) if wp_tokens_list else {}
    N_wp = len(usable_work_packages)

    # Build catalogue ref to phase lookup
    cat_ref_phase: Dict[str, str] = {}
    deliv_to_cat_phases: Dict[str, Set[str]] = {}
    if sow_catalogue:
        for it in sow_catalogue:
            if it.reference and it.phase:
                cat_ref_phase[it.reference] = it.phase.upper()
                if it.deliverable_id:
                    deliv_to_cat_phases.setdefault(it.deliverable_id, set()).add(it.phase.upper())

    for d in deliverables:
        d_name = d.name or d.description or ""
        mapped: Optional[Milestone] = None
        basis: Optional[str] = None
        is_unmapped = False

        # Rule 1 (MAP-03): Catalogue phase (all SOW references on deliverable are in one phase)
        d_refs = extract_sow_references(f"{d.sow_reference or ''} {d_name}")
        d_ref_phases = {cat_ref_phase[r] for r in d_refs if r in cat_ref_phase}
        if d.id in deliv_to_cat_phases:
            d_ref_phases.update(deliv_to_cat_phases[d.id])

        if len(d_ref_phases) == 1:
            p_code = list(d_ref_phases)[0]
            if p_code in ms_by_phase:
                mapped = ms_by_phase[p_code]
                basis = "Catalogue phase"

        # Rule 2: Phase code (P2b or Milestone N) in name
        if mapped is None:
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

        # Rule 3: ID mention in milestone description / deps / assumptions
        if mapped is None:
            d_id_pat = re.compile(r"\b" + re.escape(d.id) + r"\b", re.IGNORECASE)
            for m in milestones:
                text_block = f"{m.description or ''} {' '.join(m.key_dependencies or [])} {' '.join(m.critical_path_assumptions or [])}"
                if d_id_pat.search(text_block):
                    mapped = m
                    basis = "Referenced by milestone"
                    break

        # Rule 4: Strong backlog match for deliverables (MAP-03: non-degenerate only, gate from work item phase)
        if mapped is None and usable_work_packages:
            d_tokens = tokenize_v2(d_name)
            best_strong_score = 0.0
            best_strong_wp: Optional[WorkPackageSeed] = None
            for idx, wp in enumerate(usable_work_packages):
                wp_basis = wp_to_basis.get(wp.id, "")
                if wp_basis not in ("Fallback", "Fallback - MS-TBC"):
                    score = compute_score(d_tokens, wp_tokens_list[idx], wp_idf_dict, N_wp)
                    if score > best_strong_score:
                        best_strong_score = score
                        best_strong_wp = wp
            if best_strong_score >= 0.75 and best_strong_wp is not None:
                if best_strong_wp.id in wp_to_ms:
                    mapped = wp_to_ms[best_strong_wp.id]
                    basis = f"Backlog match ({best_strong_wp.id})"
                    deliv_to_matched_wp[d.id] = best_strong_wp.id

        # Rule 5: Scope match (score >= 0.20, ties to earlier milestone)
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

        # Rule 6: Backlog text match (score >= 0.30 against work package titles, non-degenerate only)
        if mapped is None and usable_work_packages:
            d_tokens = tokenize_v2(d_name)
            best_wp_score = 0.0
            best_wp: Optional[WorkPackageSeed] = None
            for idx, wp in enumerate(usable_work_packages):
                score = compute_score(d_tokens, wp_tokens_list[idx], wp_idf_dict, N_wp)
                if score >= 0.299 and score > best_wp_score:
                    best_wp_score = score
                    best_wp = wp
            if best_wp is not None:
                mapped = wp_to_ms.get(best_wp.id, fallback_ms)
                basis = "Backlog match"
                deliv_to_matched_wp[d.id] = best_wp.id

        # Rule 7: Submission date
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

        # Rule 8: Fallback
        if mapped is None:
            mapped = fallback_ms
            basis = "Unmapped - confirm milestone"
            is_unmapped = True

        deliv_mapping[d.id] = (mapped, basis, is_unmapped)

    return deliv_mapping, wp_to_ms, deliv_to_matched_wp


def extract_usable_sow_references(text: str) -> List[str]:
    """Extract SOW references from text, excluding Section-kind references (v6 Section 1.1)."""
    return [r for r in extract_sow_references(text) if detect_sow_reference_kind(r) != "Section"]


def match_item_to_deliverables_by_reference(
    item_text_or_refs: Union[str, Sequence[str], Set[str]],
    reference_to_deliv_map: Dict[str, Set[str]],
) -> Set[str]:
    """Match an item to deliverable IDs using a reference-to-deliverable index.

    Rule: Section-kind references, and any reference shared by more than one deliverable,
    must not be used to link items to deliverables or milestones.
    """
    if isinstance(item_text_or_refs, str):
        refs = extract_usable_sow_references(item_text_or_refs)
    else:
        refs = [r for r in item_text_or_refs if detect_sow_reference_kind(r) != "Section"]

    matched_deliv_ids: Set[str] = set()
    for ref in refs:
        deliv_ids = reference_to_deliv_map.get(ref, set())
        if len(deliv_ids) == 1:
            matched_deliv_ids.update(deliv_ids)

    return matched_deliv_ids


def map_work_packages_to_deliverables(
    work_packages: Sequence[WorkPackageSeed],
    deliverables_in_milestone: Sequence[Deliverable],
) -> Tuple[Dict[str, List[WorkPackageSeed]], List[WorkPackageSeed]]:
    """Map work packages within a milestone to its mapped deliverables (MAP-05).
    
    1. Pass 0: Parent link match (if wp.parent_deliverable_id matches a deliverable in this milestone).
    2. Pass 1: Unique work item ID match (excluding non-unique references like Sections).
    3. Pass 2: Best text score >= 0.20 within milestone (ties to lower deliverable ID).
    4. Pass 3 (v6 A29): Distinctive token with IDF >= ln(2) against unassigned deliverables in milestone.
    5. Remaining work packages go to other_wps.
    """
    matched_by_deliv: Dict[str, List[WorkPackageSeed]] = {d.id: [] for d in deliverables_in_milestone}
    other_wps: List[WorkPackageSeed] = []

    if not deliverables_in_milestone:
        return matched_by_deliv, list(work_packages)

    deliv_ids_in_ms = {d.id: d for d in deliverables_in_milestone}
    deliv_names = [d.name or d.description or "" for d in deliverables_in_milestone]

    # Pre-extract unique work item references per deliverable (exclude Section references)
    deliv_ref_index: Dict[str, Set[str]] = {}
    for d in deliverables_in_milestone:
        for ref in extract_usable_sow_references(f"{d.sow_reference or ''}"):
            deliv_ref_index.setdefault(ref, set()).add(d.id)

    unassigned_after_parent: List[WorkPackageSeed] = []
    # Pass 0: Parent link match (a valid parent in the same gate) first, before any text scoring
    for wp in work_packages:
        p_id = wp.parent_deliverable_id.strip() if wp.parent_deliverable_id else ""
        if p_id in deliv_ids_in_ms:
            matched_by_deliv[p_id].append(wp)
        else:
            unassigned_after_parent.append(wp)

    unassigned_wps: List[WorkPackageSeed] = []
    # Pass 1: Match by unique work item ID (e.g. SOW-01)
    for wp in unassigned_after_parent:
        matched_delivs = match_item_to_deliverables_by_reference(
            f"{wp.sow_reference or ''} {wp.title or ''}",
            deliv_ref_index
        )
        if len(matched_delivs) == 1:
            matched_deliv_id = list(matched_delivs)[0]
            matched_by_deliv[matched_deliv_id].append(wp)
        else:
            unassigned_wps.append(wp)

    # Pass 2: Text overlap score >= 0.20
    remaining_unassigned: List[WorkPackageSeed] = []
    for wp in unassigned_wps:
        wp_title = wp.title or ""
        wp_tokens = tokenize_v2(wp_title)

        corpus = [tokenize_v2(name) for name in deliv_names] + [wp_tokens]
        idf_dict = compute_idf(corpus)
        N = len(corpus)

        best_score = 0.0
        best_deliv: Optional[Deliverable] = None

        for idx, d in enumerate(deliverables_in_milestone):
            d_tokens = corpus[idx]
            score = compute_score(wp_tokens, d_tokens, idf_dict, N)
            if score >= 0.199:
                if score > best_score:
                    best_score = score
                    best_deliv = d
                elif score == best_score and best_deliv is not None:
                    if natural_sort_key(d.id) < natural_sort_key(best_deliv.id):
                        best_deliv = d

        if best_deliv is not None:
            matched_by_deliv[best_deliv.id].append(wp)
        else:
            remaining_unassigned.append(wp)

    # Pass 3 (v6 A29): Distinctive shared token with IDF >= ln(2) against empty deliverables in same milestone
    min_idf = math.log(2.0)  # ~0.693147

    ms_corpus = [tokenize_v2(name) for name in deliv_names] + [tokenize_v2(wp.title or "") for wp in work_packages]
    ms_idf = compute_idf(ms_corpus)

    for wp in remaining_unassigned:
        wp_tokens = set(tokenize_v2(wp.title or ""))
        assigned_deliv = None

        for d in deliverables_in_milestone:
            if not matched_by_deliv[d.id]:
                d_tokens = set(tokenize_v2(d.name or d.description or ""))
                shared = wp_tokens & d_tokens
                if any(ms_idf.get(t, 0.0) >= (min_idf - 1e-6) for t in shared):
                    assigned_deliv = d
                    break

        if assigned_deliv is not None:
            matched_by_deliv[assigned_deliv.id].append(wp)
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
            # WBS-09: Require best-matching deliverable to share at least one distinctive token (IDF >= ln 2)
            shared_distinctive = [
                t for t in set(ev_tokens).intersection(target_tokens_list[best_idx])
                if idf_dict.get(t, 0.0) >= math.log(2.0)
            ]
            if shared_distinctive:
                best_d = deliverables[best_idx]
                note = f"Evidence may belong to {best_d.id} - verify against the SOW"
                flagged[d.id] = (best_d.id, note)

    return flagged
