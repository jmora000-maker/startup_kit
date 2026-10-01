"""Extraction validation layer for PMO Startup Kit (VAL-01 to VAL-07)."""

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
)
from src.config import (
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
    # 1. Explicit statement in decisions, assumptions, or SOW interpretation
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

    # 2. Phases listed in approver decision rights or per-milestone communications
    comm_phases: Set[str] = set()
    for comm in baseline.communications_plan:
        found = PHASE_CODE_REGEX.findall(comm.name + " " + (comm.audience or ""))
        comm_phases.update(p.upper() for p in found)
    if comm_phases:
        return len(comm_phases)

    # 3. Distinct phase codes in contracted deliverables
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

    # Identify true gates vs interim checkpoints or restatements
    gates: List[Milestone] = []
    checkpoints: List[Milestone] = []

    # Check phase groups
    seen_phases: Set[str] = set()
    for ms in baseline.milestones:
        m_desc = ms.description or ""
        phase_m = PHASE_CODE_REGEX.search(m_desc)
        phase_code = phase_m.group(1).upper() if phase_m else ""

        is_restatement = bool(PHASE_RESTATEMENT_REGEX.search(m_desc))
        
        # If this is a main phase gate (first time seeing phase with acceptance or standard gate description)
        if phase_code and phase_code not in seen_phases and not is_restatement:
            seen_phases.add(phase_code)
            gates.append(ms)
        elif not phase_code and len(gates) < (expected_gate_count or 4):
            gates.append(ms)
        else:
            # Move to interim checkpoints
            checkpoints.append(ms)

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

    # Renumber gates M1..MN
    old_to_new_gate: Dict[str, str] = {}
    for idx, g in enumerate(gates, start=1):
        new_id = f"M{idx}"
        old_to_new_gate[g.id] = new_id
        g.id = new_id

    # Renumber checkpoints CP-01..CP-NN
    for idx, cp in enumerate(checkpoints, start=1):
        cp.id = f"CP-{idx:02d}"

    baseline.milestones = gates
    baseline.interim_checkpoints = checkpoints

    if checkpoints:
        findings.append(ValidationFinding(
            invariant_id="INV-01",
            severity="repaired",
            message=f"Reconciled {len(gates)} primary gates and moved {len(checkpoints)} interim items to Interim Checkpoints (CP)."
        ))

    # Update deliverable milestone links
    for d in baseline.deliverables:
        if d.source_reference and hasattr(d, "linked_milestones"):
            pass  # Keep valid


def rebuild_backlog_from_catalogue(baseline: StartupKitBaseline, findings: List[ValidationFinding]) -> None:
    """VAL-02: Rebuild work package backlog seed from SOW work item catalogue."""
    deliv_ids = {d.id: d for d in baseline.deliverables}
    
    # Check if raw backlog seed is invalid
    is_invalid = False
    if not baseline.backlog_seed:
        is_invalid = True
    else:
        for wp in baseline.backlog_seed:
            if not wp.parent_deliverable_id or wp.parent_deliverable_id not in deliv_ids:
                is_invalid = True
                break
            if not wp.owner or PLACEHOLDER_REGEX.search(wp.owner) or wp.owner.upper() in ["UNASSIGNED", "TBD"]:
                is_invalid = True
                break
            # Check for phase names in references
            if wp.sow_reference and any(detect_sow_reference_kind(r) == "Section" for r in extract_sow_references(wp.sow_reference)):
                is_invalid = True
                break

    catalogue = baseline.sow_stories_catalogue or []
    if not catalogue and baseline.deliverables:
        # Check if SOW had scope but catalogue empty
        if len(baseline.deliverables) > 0 and not is_invalid:
            return

    # Build work packages from catalogue items grouped by deliverable
    rebuilt_wps: List[WorkPackageSeed] = []
    
    # Map deliverable -> catalogue work items
    deliv_to_items: Dict[str, List[SOWWorkItem]] = {d.id: [] for d in baseline.deliverables}
    for item in catalogue:
        d_id = item.deliverable_id
        if d_id and d_id in deliv_to_items:
            deliv_to_items[d_id].append(item)
        else:
            # Find best matching deliverable by SOW reference or phase
            matched = False
            for d in baseline.deliverables:
                if d.sow_reference and item.reference and item.reference in d.sow_reference:
                    deliv_to_items[d.id].append(item)
                    matched = True
                    break
            if not matched and baseline.deliverables:
                # Assign to first deliverable
                deliv_to_items[baseline.deliverables[0].id].append(item)

    wp_idx = 1
    default_owner = "Toptal Delivery Team"

    for d in baseline.deliverables:
        items = deliv_to_items.get(d.id, [])
        if items:
            for item in items:
                ref_str = item.reference or ""
                # Extract valid SOW references
                clean_refs = extract_sow_references(ref_str)
                sow_ref_val = ", ".join(clean_refs) if clean_refs else ref_str

                # Determine linked milestone
                linked_ms = []
                for ms in baseline.milestones:
                    if d.id in (ms.description or "") or (item.phase and item.phase in (ms.description or "")):
                        linked_ms.append(ms.id)
                if not linked_ms and baseline.milestones:
                    linked_ms = [baseline.milestones[0].id]

                wp_title = item.title if item.title else f"{d.name} implementation task"
                if len(wp_title) > 120:
                    wp_title = wp_title[:117] + "..."

                wp = WorkPackageSeed(
                    id=f"WP-{wp_idx:02d}",
                    parent_deliverable_id=d.id,
                    title=wp_title,
                    description=f"Delivery and implementation for {item.reference or d.name}.",
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
            # Create a work package for the deliverable itself
            clean_refs = extract_sow_references(d.sow_reference or "")
            sow_ref_val = ", ".join(clean_refs) if clean_refs else ""
            
            linked_ms = [baseline.milestones[0].id] if baseline.milestones else ["M1"]
            wp = WorkPackageSeed(
                id=f"WP-{wp_idx:02d}",
                parent_deliverable_id=d.id,
                title=f"{d.name} implementation package",
                description=f"Core work package for deliverable {d.id}: {d.name}.",
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
        message=f"Rebuilt {len(rebuilt_wps)} work packages from SOW work item catalogue with verified parent deliverables."
    ))


def validate_and_repair_ids(baseline: StartupKitBaseline, findings: List[ValidationFinding]) -> None:
    """VAL-03: Ensure all artifact IDs are unique and sequential."""
    # Deliverables DEL-01..DEL-NN
    deliv_old_to_new = {}
    for idx, d in enumerate(baseline.deliverables, start=1):
        new_id = f"DEL-{idx:02d}"
        if d.id != new_id:
            deliv_old_to_new[d.id] = new_id
            d.id = new_id

    # Update parent IDs on work packages
    if deliv_old_to_new:
        for wp in baseline.backlog_seed:
            if wp.parent_deliverable_id in deliv_old_to_new:
                wp.parent_deliverable_id = deliv_old_to_new[wp.parent_deliverable_id]

    # Decisions DEC-01..DEC-NN
    for idx, dec in enumerate(baseline.decisions, start=1):
        dec.id = f"DEC-{idx:02d}"


def validate_award_date(baseline: StartupKitBaseline, findings: List[ValidationFinding]) -> None:
    """VAL-05: Award date provenance verification without synthetic fallback."""
    if baseline.sow_awarded_date is None:
        findings.append(ValidationFinding(
            invariant_id="INV-18",
            severity="warning",
            message="SOW Award Date is not specified in the contract or inputs."
        ))
        if baseline.open_questions is not None:
            q = "What is the formal SOW contract award and execution date?"
            if q not in baseline.open_questions:
                baseline.open_questions.append(q)


def validate_one_numbering_system(baseline: StartupKitBaseline, findings: List[ValidationFinding]) -> None:
    """VAL-06: Deliverable SOW references hold references only; phase context stored separately."""
    for d in baseline.deliverables:
        if d.sow_reference:
            # Strip Milestone N or Phase annotations, preserving valid SOW references
            clean_sow_ref = re.sub(r'\b(?:Milestone\s+\d+|Phase\s+\d+[a-z]?):?\s*', '', d.sow_reference, flags=re.IGNORECASE).strip(" ;,")
            refs = extract_sow_references(clean_sow_ref)
            if refs:
                d.sow_reference = ", ".join(refs)
            else:
                d.sow_reference = clean_sow_ref if clean_sow_ref else ""


def validate_and_repair_baseline(baseline: StartupKitBaseline) -> ValidationReport:
    """Main entry point for extraction validation layer (Section 4)."""
    findings: List[ValidationFinding] = []

    # 1. VAL-01: Gate reconciliation and Interim Checkpoints
    reconcile_gates_and_checkpoints(baseline, findings)

    # 2. VAL-02: Work package backlog reconstruction from catalogue
    rebuild_backlog_from_catalogue(baseline, findings)

    # 3. VAL-03: ID uniqueness and sequence
    validate_and_repair_ids(baseline, findings)

    # 4. VAL-05: Award date provenance
    validate_award_date(baseline, findings)

    # 5. VAL-06: One numbering system
    validate_one_numbering_system(baseline, findings)

    # 6. VAL-07: Construct validation report and attach to baseline
    report = ValidationReport(findings=findings)
    baseline.validation_report = report
    return report
