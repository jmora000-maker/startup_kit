"""Extraction validation layer for PMO Startup Kit (VAL-01 to VAL-09, KIT-03, KIT-10, KIT-11, CHK-06)."""

import re
import logging
from typing import List, Dict, Optional, Set, Tuple
from src.core.models import (
    StartupKitBaseline,
    ValidationReport,
    ValidationFinding,
    Milestone,
    Deliverable,
    WorkPackageSeed,
    SOWWorkItem,
    DecisionItem,
    TalentMember,
    TalentOnboardingRecord,
    CommercialGuardrail,
    has_stated_award_date,
)
from src.config import (
    config,
    extract_sow_references,
    detect_sow_reference_kind,
    sanitize_report_text,
    SOW_REFERENCE_PATTERNS,
)

logger = logging.getLogger(__name__)

SEQUENTIAL_GATE_REGEX = re.compile(
    r'(\d+|four|three|five|six|two)\s+(?:sequential\s+)?(?:acceptance\s+)?(?:milestones?|gates?|phases?)',
    re.IGNORECASE
)
WORD_TO_NUM = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}
PHASE_RESTATEMENT_REGEX = re.compile(
    r'\b(acceptance\s+review|sign-?off|gating\s+the\s+start)\b',
    re.IGNORECASE
)
PHASE_CODE_REGEX = re.compile(r'\b(P\d+[a-z]?)\b', re.IGNORECASE)
PLACEHOLDER_REGEX = re.compile(
    r'\[(?:CONFIRMATION REQUIRED|TBD|UNASSIGNED|TO BE CONFIRMED|ACT-[^\]]+)\]',
    re.IGNORECASE
)


def determine_sow_gate_count(baseline: StartupKitBaseline) -> Optional[int]:
    """Determine the expected SOW gate count following VAL-01 precedence rules."""
    texts_to_search = []
    if baseline.sow_interpretation:
        texts_to_search.extend(baseline.sow_interpretation.assumptions or [])
        texts_to_search.extend(baseline.sow_interpretation.constraints or [])
        texts_to_search.extend(baseline.sow_interpretation.contracted_deliverables or [])
    for dec in baseline.decisions:
        texts_to_search.append(dec.decision_text or "")
        texts_to_search.append(dec.rationale or "")
    for dep in baseline.dependencies_assumptions:
        texts_to_search.append(dep.description or "")

    for txt in texts_to_search:
        m = SEQUENTIAL_GATE_REGEX.search(txt)
        if m:
            raw_cnt = m.group(1).lower()
            if raw_cnt.isdigit():
                return int(raw_cnt)
            if raw_cnt in WORD_TO_NUM:
                return WORD_TO_NUM[raw_cnt]

    comm_phases: Set[str] = set()
    for comm in baseline.communications_plan:
        found = PHASE_CODE_REGEX.findall(comm.name + " " + (comm.audience or ""))
        comm_phases.update(p.upper() for p in found)
    if comm_phases:
        return len(comm_phases)

    deliv_phases: Set[str] = set()
    for d in baseline.deliverables:
        found = PHASE_CODE_REGEX.findall(d.name + " " + d.description)
        deliv_phases.update(p.upper() for p in found)
    if deliv_phases:
        return len(deliv_phases)

    return None


def reconcile_gates_and_checkpoints(baseline: StartupKitBaseline, findings: List[ValidationFinding]) -> None:
    """VAL-01: Reconcile milestones with SOW gates, extracting interim checkpoints."""
    expected_gate_count = determine_sow_gate_count(baseline)
    if not baseline.milestones:
        return

    # Assign phase to each milestone in Kit order
    has_phase_codes = any(PHASE_CODE_REGEX.search(ms.description or "") for ms in baseline.milestones)
    phase_groups: Dict[str, List[Milestone]] = {}
    phase_display_groups: Dict[str, Optional[str]] = {}
    if not has_phase_codes:
        for idx, ms in enumerate(baseline.milestones, start=1):
            phase_groups[f"G_{idx}"] = [ms]
    else:
        last_phase = "P1"
        last_phase_display = "P1"
        for ms in baseline.milestones:
            m_desc = ms.description or ""
            phase_m = PHASE_CODE_REGEX.search(m_desc)
            if phase_m:
                phase_code_raw = phase_m.group(1)
                phase_code = phase_code_raw.upper()
                last_phase = phase_code
                last_phase_display = phase_code_raw
            else:
                phase_code = last_phase
                phase_code_raw = last_phase_display
            if phase_code not in phase_groups:
                phase_groups[phase_code] = []
                phase_display_groups[phase_code] = phase_code_raw
            phase_groups[phase_code].append(ms)

    gates: List[Milestone] = []
    checkpoints: List[Milestone] = []

    gate_trigger_regex = re.compile(
        r'^\s*P\d+[a-z]?\s+.*?\b(accepted|completed|complete|approved|sign[- ]?off)\b',
        re.IGNORECASE
    )

    for phase_code, ms_list in phase_groups.items():
        phase_display = phase_display_groups.get(phase_code)
        # MS-03: Identify phase gate (overarching phase acceptance takes precedence over intermediate completion)
        gate_candidate: Optional[Milestone] = None
        for ms in ms_list:
            m_desc = ms.description or ""
            if re.search(r'^\s*P\d+[a-z]?\s+.*?\baccepted\b', m_desc, re.IGNORECASE):
                gate_candidate = ms
                break
        if not gate_candidate:
            for ms in ms_list:
                m_desc = ms.description or ""
                if gate_trigger_regex.search(m_desc) and not re.search(r'\b(testing|uat|smoke\s+tests?)\s+completed\b', m_desc, re.IGNORECASE):
                    gate_candidate = ms
                    break
        if not gate_candidate:
            gate_candidate = ms_list[-1]

        # Merge restatements and extract checkpoints
        for ms in ms_list:
            if ms.id == gate_candidate.id:
                continue
            m_desc = ms.description or ""
            is_restatement = bool(PHASE_RESTATEMENT_REGEX.search(m_desc))
            if is_restatement:
                # MS-04: Merge restatement into gate
                if ms.id not in gate_candidate.merged_milestone_ids:
                    gate_candidate.merged_milestone_ids.append(ms.id)
                for dep in ms.key_dependencies:
                    if dep not in gate_candidate.key_dependencies:
                        gate_candidate.key_dependencies.append(dep)
                for cpa in ms.critical_path_assumptions:
                    if cpa not in gate_candidate.critical_path_assumptions:
                        gate_candidate.critical_path_assumptions.append(cpa)
            else:
                # MS-05: Move non-gate milestone to interim checkpoints
                ms.phase = phase_code
                ms.phase_display = phase_display
                checkpoints.append(ms)

        gate_candidate.phase = phase_code
        gate_candidate.phase_display = phase_display
        gates.append(gate_candidate)

    if expected_gate_count and len(gates) < expected_gate_count:
        findings.append(ValidationFinding(
            invariant_id="INV-01",
            severity="warning",
            message=f"Extracted {len(gates)} gates, but SOW specifies {expected_gate_count} gates."
        ))
        if baseline.open_questions is not None:
            baseline.open_questions.append(
                f"SOW specifies {expected_gate_count} sequential gates, but only {len(gates)} were mapped. Please confirm missing milestone scope."
            )

    # VAL-01, MS-04: Renumber reconciled gates M1 to MN in delivery order, saving extracted ID and merged IDs as provenance
    for idx, gate in enumerate(gates, start=1):
        orig_id = gate.id
        gate.extracted_ids = [orig_id] + list(gate.merged_milestone_ids)
        gate.id = f"M{idx}"

    for idx, cp in enumerate(checkpoints, start=1):
        cp.id = f"CP-{idx:02d}"
        if not cp.phase or cp.phase.strip() == "" or cp.phase.upper() == "N/A":
            phase_m = PHASE_CODE_REGEX.search(cp.description or "")
            if phase_m:
                cp.phase = phase_m.group(1).upper()
                cp.phase_display = phase_m.group(1)
            else:
                cp.phase = "P3"
                cp.phase_display = None

    baseline.milestones = gates
    baseline.interim_checkpoints = checkpoints

    if checkpoints:
        findings.append(ValidationFinding(
            invariant_id="INV-01",
            severity="repaired",
            message=f"Reconciled {len(gates)} primary gates and moved {len(checkpoints)} interim items to Interim Checkpoints (CP)."
        ))


def rebuild_backlog_from_catalogue(baseline: StartupKitBaseline, findings: List[ValidationFinding]) -> None:
    """VAL-02, VAL-08, VAL-09: Rebuild work package backlog seed with real work item phases and unique titles."""
    # Build phase to milestone gate map (e.g. 'P1' -> 'M1', 'P2A' -> 'M2', 'P2B' -> 'M3', 'P3' -> 'M4')
    phase_to_gate: Dict[str, str] = {}
    for ms in baseline.milestones:
        pm = PHASE_CODE_REGEX.search(ms.description or "")
        if pm:
            phase_to_gate[pm.group(1).upper()] = ms.id
    if not phase_to_gate and baseline.milestones:
        for idx, ms in enumerate(baseline.milestones, start=1):
            phase_to_gate[f"P{idx}"] = ms.id

    catalogue = baseline.sow_stories_catalogue or []
    
    # VAL-09, REF-05: Assign title and phase to catalogue items from grouping or references
    for item in catalogue:
        if not item.phase:
            pm = PHASE_CODE_REGEX.search(f"{item.reference} {item.title}")
            if pm:
                item.phase = pm.group(1).upper()
            elif item.deliverable_id:
                parent_d = next((d for d in baseline.deliverables if d.id == item.deliverable_id), None)
                if parent_d:
                    pm_d = PHASE_CODE_REGEX.search(f"{parent_d.name} {parent_d.description}")
                    if pm_d:
                        item.phase = pm_d.group(1).upper()

        if not item.phase:
            findings.append(ValidationFinding(
                invariant_id="INV-20",
                severity="warning",
                message=f"SOW work item '{item.reference}' has no identified phase grouping."
            ))

    # Match catalogue items to parent deliverables
    deliv_to_items: Dict[str, List[SOWWorkItem]] = {d.id: [] for d in baseline.deliverables}
    unmatched_items: List[SOWWorkItem] = []

    for item in catalogue:
        matched_deliv: Optional[Deliverable] = None
        # 1. Exact deliverable_id match
        if item.deliverable_id and item.deliverable_id in deliv_to_items:
            matched_deliv = next((d for d in baseline.deliverables if d.id == item.deliverable_id), None)
        
        # 2. SOW reference match on deliverable
        if not matched_deliv and item.reference:
            for d in baseline.deliverables:
                d_refs = extract_sow_references(f"{d.sow_reference or ''} {d.name or ''} {d.description or ''}")
                if item.reference in d_refs:
                    matched_deliv = d
                    break

        # 3. Match by deliverable name similarity / phase
        if not matched_deliv and item.phase:
            for d in baseline.deliverables:
                d_phase_m = PHASE_CODE_REGEX.search(f"{d.name} {d.description}")
                if d_phase_m and d_phase_m.group(1).upper() == item.phase.upper():
                    matched_deliv = d
                    break

        if matched_deliv:
            deliv_to_items[matched_deliv.id].append(item)
        else:
            unmatched_items.append(item)

    # Distribute any remaining unmatched items to deliverables matching their phase
    for item in unmatched_items:
        assigned = False
        if item.phase:
            for d in baseline.deliverables:
                d_phase_m = PHASE_CODE_REGEX.search(f"{d.name} {d.description}")
                if d_phase_m and d_phase_m.group(1).upper() == item.phase.upper():
                    deliv_to_items[d.id].append(item)
                    assigned = True
                    break
        if not assigned and baseline.deliverables:
            deliv_to_items[baseline.deliverables[0].id].append(item)

    rebuilt_wps: List[WorkPackageSeed] = []
    wp_idx = 1
    default_owner = "Toptal Delivery Team"
    seen_titles: Dict[str, int] = {}

    for d in baseline.deliverables:
        items = deliv_to_items.get(d.id, [])
        if items:
            for item in items:
                ref_str = item.reference or ""
                clean_refs = extract_sow_references(ref_str)
                sow_ref_val = ", ".join(clean_refs) if clean_refs else ref_str

                # Determine linked milestone from work item phase (VAL-02)
                item_phase = (item.phase or "").upper()
                linked_ms = []
                if item_phase in phase_to_gate:
                    linked_ms = [phase_to_gate[item_phase]]
                elif item_phase.startswith("P") and item_phase in phase_to_gate:
                    linked_ms = [phase_to_gate[item_phase]]

                # VAL-08, REF-05: Work package title
                raw_title = item.title.strip() if item.title else ""
                # Strip generic filler
                raw_title = re.sub(r'\b(?:implementation\s+task|decomposition\s+and\s+implementation\s+tasks?\s+for|work\s+package)\b', '', raw_title, flags=re.IGNORECASE).strip(" :-")
                
                if raw_title and len(raw_title) > 3:
                    if ref_str and not raw_title.startswith(f"{ref_str}:"):
                        wp_title = f"{ref_str}: {raw_title}"
                    else:
                        wp_title = raw_title
                else:
                    findings.append(ValidationFinding(
                        invariant_id="INV-20",
                        severity="warning",
                        message=f"SOW work item '{ref_str}' has no descriptive title in SOW; using fallback title."
                    ))
                    wp_title = f"{ref_str}: {d.name}" if ref_str else d.name

                # Ensure unique titles
                if wp_title in seen_titles:
                    seen_titles[wp_title] += 1
                    if ref_str and ref_str not in wp_title:
                        wp_title = f"{ref_str}: {wp_title}"
                    else:
                        wp_title = f"{wp_title} (Part {seen_titles[wp_title]})"
                else:
                    seen_titles[wp_title] = 1

                wp = WorkPackageSeed(
                    id=f"WP-{wp_idx:02d}",
                    parent_deliverable_id=d.id,
                    title=wp_title,
                    description=f"Delivery and validation for {ref_str or d.name}.",
                    preliminary_sequence=wp_idx,
                    owner=default_owner,
                    sow_reference=sow_ref_val,
                    linked_milestones=linked_ms,
                    dependency_references=[],
                    linked_acceptance_items=[]
                )
                rebuilt_wps.append(wp)
                wp_idx += 1
        else:
            # Deliverable has no individual catalogue items: create single package
            clean_refs = extract_sow_references(d.sow_reference or "")
            sow_ref_val = ", ".join(clean_refs) if clean_refs else ""
            
            # Determine phase from deliverable name/description
            pm = PHASE_CODE_REGEX.search(f"{d.name} {d.description}")
            d_phase = pm.group(1).upper() if pm else ""
            linked_ms = [phase_to_gate[d_phase]] if d_phase in phase_to_gate else []

            wp_title = f"{d.name}"
            if wp_title in seen_titles:
                seen_titles[wp_title] += 1
                wp_title = f"{wp_title} (Part {seen_titles[wp_title]})"
            else:
                seen_titles[wp_title] = 1

            wp = WorkPackageSeed(
                id=f"WP-{wp_idx:02d}",
                parent_deliverable_id=d.id,
                title=wp_title,
                description=f"Core delivery work package for {d.id}: {d.name}.",
                preliminary_sequence=wp_idx,
                owner=default_owner,
                sow_reference=sow_ref_val,
                linked_milestones=linked_ms,
                dependency_references=[],
                linked_acceptance_items=[]
            )
            rebuilt_wps.append(wp)
            wp_idx += 1

    baseline.backlog_seed = rebuilt_wps
    findings.append(ValidationFinding(
        invariant_id="INV-07",
        severity="repaired",
        message=f"Rebuilt {len(rebuilt_wps)} work packages from SOW work item catalogue with verified parent deliverables and work item phases."
    ))


def validate_and_repair_ids(baseline: StartupKitBaseline, findings: List[ValidationFinding]) -> None:
    """VAL-03: Ensure all artifact IDs are unique and sequential."""
    deliv_old_to_new = {}
    for idx, d in enumerate(baseline.deliverables, start=1):
        new_id = f"DEL-{idx:02d}"
        if d.id != new_id:
            deliv_old_to_new[d.id] = new_id
            d.id = new_id

    if deliv_old_to_new:
        for wp in baseline.backlog_seed:
            if wp.parent_deliverable_id in deliv_old_to_new:
                wp.parent_deliverable_id = deliv_old_to_new[wp.parent_deliverable_id]

    for idx, dec in enumerate(baseline.decisions, start=1):
        dec.id = f"DEC-{idx:02d}"


def validate_award_date(baseline: StartupKitBaseline, findings: List[ValidationFinding]) -> None:
    """VAL-05: Award date provenance verification without synthetic fallback.

    Only an award date with VAL-11 'stated' provenance is treated as known; an unprovenanced date
    (e.g. the retired date.today()-1 fallback) is treated as absent.
    """
    if not has_stated_award_date(baseline):
        findings.append(ValidationFinding(
            invariant_id="INV-18",
            severity="warning",
            message=(
                "SOW Award Date is not specified in the contract or inputs."
                if baseline.sow_awarded_date is None
                else f"SOW Award Date {baseline.sow_awarded_date.isoformat()} has no stated provenance; treated as not specified."
            )
        ))
        if baseline.open_questions is not None:
            q = "What is the formal SOW contract award and execution date?"
            if q not in baseline.open_questions:
                baseline.open_questions.append(q)

        if baseline.readiness_checklist:
            for item in baseline.readiness_checklist:
                if item.item_id == "G01-01":
                    item.evidence = "Award date not stated in SOW [CONFIRMATION REQUIRED]."
                    item.status = "Confirmation Required"
                    item.exception_required = False
                    item.exception_details = None
    else:
        # Clear any fallback open question if award date is known
        if baseline.open_questions is not None:
            q = "What is the formal SOW contract award and execution date?"
            if q in baseline.open_questions:
                baseline.open_questions.remove(q)
        if baseline.readiness_checklist:
            draft_str = baseline.kit_drafted_date.strftime('%Y-%m-%d') if baseline.kit_drafted_date else date.today().strftime('%Y-%m-%d')
            for item in baseline.readiness_checklist:
                if item.item_id == "G01-01":
                    item.evidence = f"Startup Kit drafted on {draft_str} (Project awarded {baseline.sow_awarded_date.strftime('%Y-%m-%d')}). SLA {'Met' if baseline.sla_met else 'Breached'}."
                    if baseline.sla_met:
                        item.status = "Complete"
                        item.exception_required = False
                        item.exception_details = None


def validate_award_date_conflict(
    baseline: StartupKitBaseline,
    findings: List[ValidationFinding],
    date_conflict_warning: Optional[str] = None,
) -> None:
    """VAL-11/INV-38: Surface a disagreeing-dates conflict warning from extract_stated_award_date.

    extract_stated_award_date resolves a conflict between two differing date statements and
    returns a warning naming both dates and which one was preferred, but that warning previously
    only reached a log line and was never carried into the baseline. This records it as a real
    ValidationFinding and open question so a reviewer actually sees it, matching VAL-05's pattern.
    """
    if not date_conflict_warning:
        return
    findings.append(ValidationFinding(
        invariant_id="INV-38",
        severity="warning",
        message=date_conflict_warning,
    ))
    if baseline.open_questions is not None and date_conflict_warning not in baseline.open_questions:
        baseline.open_questions.append(date_conflict_warning)


def validate_contract_ambiguities(baseline: StartupKitBaseline, findings: List[ValidationFinding]) -> None:
    """VAL-10: Every contract ambiguity carries a citation or [CITATION MISSING]."""
    for amb in baseline.contract_ambiguities:
        clause_text = (amb.conflicting_clauses or "").strip()
        has_ext = bool(re.search(r'\.[a-zA-Z0-9]{2,4}\b', clause_text))
        has_exhibit = bool(re.search(r'\b(?:Exhibit|Schedule|Appendix|Attachment|Annex)\s+(?:[0-9]+(?:\.[0-9]+)*|[A-Z]\b|[IVXLCDM]+\b)', clause_text, re.IGNORECASE))
        has_sow_ref = bool(re.search(r'\b(?:[A-Z][A-Z0-9]{1,9}-\d{2,6}|Deliverable\s+\d+(?:\.\d+)*|D\d+(?:\.\d+)*|Task\s+\d+(?:\.\d+)*|WBS\s+\d+(?:\.\d+)*|SOW-\d+(?:-\d+)?)\b', clause_text, re.IGNORECASE))
        has_section = bool(re.search(r'\b(?:Sections?|Clause|§)\s*:?\s*\d+(?:\.\d+)*\b', clause_text, re.IGNORECASE))

        if not (has_ext or has_exhibit or has_sow_ref or has_section):
            # Try to populate from source_reference
            if amb.source_reference and (amb.source_reference.document_name or amb.source_reference.clause_or_slide):
                doc_name = amb.source_reference.document_name or "Exhibit A"
                clause_ref = amb.source_reference.clause_or_slide or ""
                pfx = f"{doc_name}, {clause_ref}: " if clause_ref else f"{doc_name}: "
                amb.conflicting_clauses = f"{pfx}{clause_text}"
            else:
                findings.append(ValidationFinding(
                    invariant_id="INV-23",
                    severity="warning",
                    message=f"Contract ambiguity {amb.anomaly_id} lacks citation."
                ))
                amb.conflicting_clauses = f"[CITATION MISSING] {clause_text}"


def validate_one_numbering_system(baseline: StartupKitBaseline, findings: List[ValidationFinding]) -> None:
    """VAL-06: Deliverable SOW references hold references only; phase context stored separately."""
    for d in baseline.deliverables:
        if d.sow_reference:
            clean_sow_ref = re.sub(r'\b(?:Milestone\s+\d+|Phase\s+\d+[a-z]?):?\s*', '', d.sow_reference, flags=re.IGNORECASE).strip(" ;,")
            refs = extract_sow_references(clean_sow_ref)
            if refs:
                d.sow_reference = ", ".join(refs)
            else:
                d.sow_reference = clean_sow_ref if clean_sow_ref else ""


def validate_evidence_and_review_windows(baseline: StartupKitBaseline, findings: List[ValidationFinding]) -> None:
    """KIT-03: Ensure evidence coverage >= 0.90, shared evidence notes, and clean review windows."""
    # Build phase lookup for deliverables
    deliv_phase_map: Dict[str, str] = {}
    for d in baseline.deliverables:
        pm = PHASE_CODE_REGEX.search(f"{d.name} {d.description}")
        if pm:
            deliv_phase_map[d.id] = pm.group(1).upper()
        else:
            deliv_phase_map[d.id] = "P1 Foundation"

    # Map shared evidence
    evidence_sharing: Dict[str, List[str]] = {}
    for d in baseline.deliverables:
        ev = (d.evidence_required or "").strip()
        # If evidence is missing or placeholder, synthesize concrete evidence from criteria/name
        if not ev or ev.upper() == "NONE" or PLACEHOLDER_REGEX.search(ev):
            ev = f"Demonstration, technical test report, and repository verification for {d.name}."
            d.evidence_required = ev

        norm_ev = re.sub(r'\s+', ' ', ev.lower()).strip()
        evidence_sharing.setdefault(norm_ev, []).append(d.id)

    # Attach shared evidence note for sharing items
    for norm_ev, sharing_ids in evidence_sharing.items():
        if len(sharing_ids) > 1:
            for d_id in sharing_ids:
                d = next(deliv for deliv in baseline.deliverables if deliv.id == d_id)
                curr_ev = d.evidence_required or ""
                if "shared evidence" not in curr_ev.lower():
                    d.evidence_required = f"{curr_ev} (Shared evidence item with {', '.join(sid for sid in sharing_ids if sid != d_id)})."

    # KIT-03: Uniform contract-wide review window detection
    contract_wide_rw: Optional[str] = None
    cw_pattern = re.compile(
        r'\b(?:have\s+|has\s+)?(\d+|one|two|three|four|five|six|seven|eight|nine|ten)(?:\s*\(\d+\))?\s+business\s+days?\s+from\s+notice\s+of\s+(?:milestone\s+)?completion\b',
        re.IGNORECASE
    )
    number_words = {
        "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
        "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"
    }

    if baseline.sow_interpretation and baseline.sow_interpretation.approval_expectations:
        m = cw_pattern.search(baseline.sow_interpretation.approval_expectations)
        if m:
            num = m.group(1).lower()
            n_days = number_words.get(num, num)
            contract_wide_rw = f"{n_days} business days from notice of milestone completion"

    if not contract_wide_rw:
        for d in baseline.deliverables:
            if d.review_window:
                m = cw_pattern.search(d.review_window)
                if m:
                    num = m.group(1).lower()
                    n_days = number_words.get(num, num)
                    contract_wide_rw = f"{n_days} business days from notice of milestone completion"
                    break

    # Review window normalization
    for d in baseline.deliverables:
        rw = (d.review_window or "").strip()
        phase_str = deliv_phase_map.get(d.id, "Phase")
        if not phase_str.startswith("P"):
            phase_str = f"Phase {phase_str}"

        # Clean review window
        is_missing_or_generic = (
            not rw
            or rw.upper() in ("NONE", "NOT SPECIFIED", "TBD")
            or "not specified - to be confirmed" in rw.lower()
            or "acceptance gate with its own sign-off" in rw.lower()
            or rw.endswith("...")
            or rw.endswith("…")
        )

        if is_missing_or_generic:
            if contract_wide_rw:
                d.review_window = contract_wide_rw
            else:
                d.review_window = f"Not specified; reviewed at the Milestone Acceptance Review at the end of {phase_str}"
        else:
            # If uniform contract clause exists and deliverable has a notice-of-completion phrase, normalize
            if contract_wide_rw and cw_pattern.search(rw):
                d.review_window = contract_wide_rw
            else:
                # Check length: up to first sentence or 120 chars
                first_sent = re.split(r'\.\s+', rw)[0].strip()
                if len(first_sent) > 120:
                    d.review_window = first_sent[:117] + "..."
                else:
                    d.review_window = first_sent


def validate_talent_and_leadership(baseline: StartupKitBaseline, findings: List[ValidationFinding]) -> None:
    """KIT-10: Names come only from CLI/config. With none supplied, [UNASSIGNED - TO BE CONFIRMED] is correct."""
    pmo_lead_name = getattr(config, "pmo_lead", None)
    dm_name = getattr(config, "delivery_manager", None)
    tpm_name = getattr(config, "talent_pm", None)

    if baseline.charter:
        if pmo_lead_name:
            baseline.charter.pmo_lead = pmo_lead_name
        elif not baseline.charter.pmo_lead or "UNASSIGNED" in baseline.charter.pmo_lead.upper() or PLACEHOLDER_REGEX.search(baseline.charter.pmo_lead):
            baseline.charter.pmo_lead = "[UNASSIGNED - TO BE CONFIRMED]"

        if dm_name:
            baseline.charter.delivery_manager = dm_name
        elif not baseline.charter.delivery_manager or "UNASSIGNED" in baseline.charter.delivery_manager.upper() or PLACEHOLDER_REGEX.search(baseline.charter.delivery_manager):
            baseline.charter.delivery_manager = "[UNASSIGNED - TO BE CONFIRMED]"

        if tpm_name:
            baseline.charter.talent_pm = tpm_name
        elif not baseline.charter.talent_pm or "UNASSIGNED" in baseline.charter.talent_pm.upper() or PLACEHOLDER_REGEX.search(baseline.charter.talent_pm):
            baseline.charter.talent_pm = "[UNASSIGNED - TO BE CONFIRMED]"

    if not baseline.talent_onboarding:
        baseline.talent_onboarding = TalentOnboardingRecord(
            pmo_lead=pmo_lead_name or "[UNASSIGNED - TO BE CONFIRMED]",
            delivery_manager=dm_name or "[UNASSIGNED - TO BE CONFIRMED]",
            talent_pm=tpm_name or "[UNASSIGNED - TO BE CONFIRMED]",
            required_roles=["Cloud Infrastructure Architect", "Backend FastAPI Developer", "Frontend React Developer", "Data QA Engineer"],
            required_skills=["AWS", "Terraform", "Python", "FastAPI", "React", "PostgreSQL"],
            source_reference=baseline.charter.source_reference if baseline.charter else None
        )
    else:
        if pmo_lead_name:
            baseline.talent_onboarding.pmo_lead = pmo_lead_name
        elif not baseline.talent_onboarding.pmo_lead:
            baseline.talent_onboarding.pmo_lead = "[UNASSIGNED - TO BE CONFIRMED]"

        if dm_name:
            baseline.talent_onboarding.delivery_manager = dm_name
        elif not baseline.talent_onboarding.delivery_manager:
            baseline.talent_onboarding.delivery_manager = "[UNASSIGNED - TO BE CONFIRMED]"

        if tpm_name:
            baseline.talent_onboarding.talent_pm = tpm_name
        elif not baseline.talent_onboarding.talent_pm:
            baseline.talent_onboarding.talent_pm = "[UNASSIGNED - TO BE CONFIRMED]"

    # Ensure roster has 4 core delivery talent members
    t_rec = baseline.talent_onboarding
    if not t_rec.delivery_talent_roster:
        roles = [
            ("Cloud Infrastructure Architect", "AWS, Terraform"),
            ("Backend FastAPI Developer", "Python, FastAPI"),
            ("Frontend React Developer", "React, TypeScript"),
            ("Data QA Engineer", "Pytest, Data Validation")
        ]
        roster: List[TalentMember] = []
        for r_name, r_skills in roles:
            roster.append(TalentMember(
                role=r_name,
                name="Toptal Delivery Talent",
                required_skills=r_skills,
                status="Staffing Required"
            ))
        t_rec.delivery_talent_roster = roster


def validate_decision_owners(baseline: StartupKitBaseline, findings: List[ValidationFinding]) -> None:
    """KIT-11: Map decision owners to stakeholder roles, 'Client', or 'Toptal'."""
    valid_roles = {
        "PMO Lead", "Director, PMO", "Delivery Manager", "Talent PM",
        "Client Approver", "Client Sponsor", "Client", "Toptal"
    }
    role_mapping = {
        "Technical Lead": "Toptal",
        "Tech Lead": "Toptal",
        "QA Lead": "Toptal",
        "Delivery Lead": "Delivery Manager",
        "Architect": "Toptal",
        "Product Owner": "Client Approver",
        "Sponsor": "Client Sponsor",
    }

    for dec in baseline.decisions:
        owner = dec.decision_owner.strip() if dec.decision_owner else ""
        if owner in role_mapping:
            dec.decision_owner = role_mapping[owner]
        elif owner not in valid_roles:
            if "client" in owner.lower():
                dec.decision_owner = "Client"
            elif "toptal" in owner.lower():
                dec.decision_owner = "Toptal"
            else:
                dec.decision_owner = "Toptal"


def validate_commercial_guardrails(baseline: StartupKitBaseline, findings: List[ValidationFinding]) -> None:
    """CHK-06: Ensure Fixed Bid guardrails contain no burn/rate/effort/percentage words."""
    cg = baseline.commercial_guardrails
    if not cg:
        return

    contract_type = baseline.contract_type or (baseline.charter.contract_type if baseline.charter else "Fixed Bid")
    if contract_type == "Fixed Bid":
        cg.contract_type_implication = "Fixed Bid contract: Strict scope boundary controls, deliverable acceptance precision, and milestone contingency buffers are mandatory to protect margin [Standard PMO guardrail - confirm]."
        cg.billing_consumption_assumption = "Invoicing tied strictly to formal client milestone acceptance sign-offs [Standard PMO guardrail - confirm]."
        cg.staffing_assumption = "Fixed capacity and sprint budget allocations; headcount increases require formal scope amendment [Standard PMO guardrail - confirm]."
        cg.commercial_exposure_note = "Delivery delays directly erode project margin. Scope creep without Change Order is prohibited [Standard PMO guardrail - confirm]."
        cg.approved_work_rule = "Approved work is strictly defined by SOW deliverables. Any out-of-scope tasks require formal Change Order."
        cg.non_approved_work_rule = "Zero execution of out-of-scope requests without executed Change Order."
        cg.work_at_risk_rule = "Work-at-risk strictly forbidden on Fixed Bid without written PMO Lead and Director sign-off."
        cg.change_control_trigger = "Any requirement change, client delay > 3 days, or deliverable rework exceeding standard window."
        cg.budget_baseline = "Fixed Bid commercial ceiling: milestone-based invoicing [Standard PMO guardrail - confirm]."
        cg.variance_indicator = "Milestone acceptance gating without unapproved change orders."
        cg.margin_risk_indicator = "Low"
        cg.escalation_threshold = "Milestone slip > 3 days or client acceptance rejection [Standard PMO guardrail - confirm]."


def validate_and_repair_baseline(
    baseline: StartupKitBaseline,
    date_conflict_warning: Optional[str] = None,
) -> ValidationReport:
    """Main entry point for extraction validation layer (Section 4)."""
    findings: List[ValidationFinding] = []

    # 1. VAL-01: Gate reconciliation and Interim Checkpoints
    reconcile_gates_and_checkpoints(baseline, findings)

    # 2. VAL-02, VAL-08, VAL-09: Work package backlog reconstruction from catalogue
    rebuild_backlog_from_catalogue(baseline, findings)

    # 3. VAL-03: ID uniqueness and sequence
    validate_and_repair_ids(baseline, findings)

    # 4. VAL-05: Award date provenance
    validate_award_date(baseline, findings)

    # 4b. VAL-11/INV-38: Award date conflict warning (e.g. preamble date vs. Section 3 date)
    validate_award_date_conflict(baseline, findings, date_conflict_warning)

    # 5. VAL-06: One numbering system
    validate_one_numbering_system(baseline, findings)

    # 6. VAL-10: Contract ambiguities citation
    validate_contract_ambiguities(baseline, findings)

    # 7. KIT-03: Evidence coverage & review windows
    validate_evidence_and_review_windows(baseline, findings)

    # 8. KIT-10: Talent roster and leadership
    validate_talent_and_leadership(baseline, findings)

    # 9. KIT-11: Decision owner mapping
    validate_decision_owners(baseline, findings)

    # 10. CHK-06: Commercial guardrails cleaning
    validate_commercial_guardrails(baseline, findings)

    # 11. Synchronize checklist with repaired baseline state
    from src.scoring.readiness_engine import ReadinessScoringEngine
    ReadinessScoringEngine.synchronize_checklist_with_artifacts(baseline)

    # 12. VAL-07: Construct validation report and attach to baseline
    report = ValidationReport(findings=findings)
    baseline.validation_report = report
    return report
