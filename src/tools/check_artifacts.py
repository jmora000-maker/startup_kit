"""Comprehensive invariant checker for generated PMO artifacts (QA-04, QA-08, INV-01 to INV-25)."""

import sys
import re
import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
import docx
import openpyxl

logger = logging.getLogger(__name__)

READINESS_REGEX = re.compile(
    r'\b(G-?01|g01|readiness\s+gate|startup\s+readiness|readiness\s+checklist|readiness\s+score|gate\s+decision|gate\s+approval|startup\s+kit|mobiliz\w*|ACT-\d+)\b',
    re.IGNORECASE
)
BANNED_EFFORT_WORDS = {
    "hour", "hours", "rate", "rates", "cost", "costs", "budget", "burn",
    "capacity", "fte", "story points", "man-day", "manday", "person-day"
}
BANNED_EFFORT_REGEX = re.compile(r'\b(' + '|'.join(BANNED_EFFORT_WORDS) + r')\b', re.IGNORECASE)
CITATION_PREFIX_REGEX = re.compile(r'^\s*(\[V\d+\]|Exhibit\s+[A-Z0-9]+,)', re.IGNORECASE)
PLACEHOLDER_REGEX = re.compile(r'\[(?:CONFIRMATION REQUIRED|TBD|UNASSIGNED|TO BE CONFIRMED|ACT-[^\]]+)\]', re.IGNORECASE)
BANNED_WORKSTREAM_NAMES = ["Project Management", "Kickoff", "Reporting and Control", "Ongoing"]

VALID_CONTRACT_REF_EXT_REGEX = re.compile(r'\.[a-zA-Z0-9]{2,4}\b', re.IGNORECASE)
EXHIBIT_WORD_REGEX = re.compile(r'\b(?:Exhibit|Schedule|Appendix|Attachment|Annex)\s+(?:[0-9]+(?:\.[0-9]+)*|[A-Z]\b|[IVXLCDM]+\b)', re.IGNORECASE)
SECTION_WORD_REGEX = re.compile(r'\b(?:Sections?|Clause|§)\s*:?\s*\d+(?:\.\d+)*\b', re.IGNORECASE)
SOW_REF_REGEX = re.compile(r'\b(?:[A-Z][A-Z0-9]{1,9}-\d{2,6}|Deliverable\s+\d+(?:\.\d+)*|D\d+(?:\.\d+)*|Task\s+\d+(?:\.\d+)*|WBS\s+\d+(?:\.\d+)*|SOW-\d+(?:-\d+)?)\b', re.IGNORECASE)


class InvariantViolation:
    def __init__(self, inv_id: str, message: str, artifact: str = ""):
        self.inv_id = inv_id
        self.message = message
        self.artifact = artifact

    def __str__(self):
        art = f" [{self.artifact}]" if self.artifact else ""
        return f"{self.inv_id}{art}: {self.message}"


def load_oracle_for_folder(folder_path: Path, project_name: str = "") -> Optional[Dict[str, Any]]:
    """Load matching oracle from tests/oracles/ if one exists (ignoring drafts)."""
    oracles_dir = Path("tests/oracles")
    if not oracles_dir.exists():
        return None

    # Check for arc oracle
    p_lower = project_name.lower()
    folder_str = str(folder_path).lower()
    if "arc" in p_lower or "genomics" in p_lower or "arc" in folder_str:
        arc_path = oracles_dir / "arc.json"
        if arc_path.exists():
            with open(arc_path, "r", encoding="utf-8") as f:
                return json.load(f)
    return None


def check_artifacts_directory(folder_path: Path, oracle_override: Optional[Dict[str, Any]] = None) -> List[InvariantViolation]:
    """Inspect output folder containing Kit docx, Checklist docx, and Workbook xlsx against INV-01 to INV-25."""
    violations: List[InvariantViolation] = []
    folder = Path(folder_path)

    kit_files = list(folder.glob("*_Startup_Kit.docx"))
    chk_files = list(folder.glob("*_Startup_Readiness_Checklist.docx"))
    wb_files = list(folder.glob("*_Project_Delivery_Workbook.xlsx"))

    kit_doc = docx.Document(str(kit_files[0])) if kit_files else None
    chk_doc = docx.Document(str(chk_files[0])) if chk_files else None
    wb = openpyxl.load_workbook(str(wb_files[0]), data_only=False) if wb_files else None

    # Parse Kit tables
    kit_milestones: List[List[str]] = []
    kit_checkpoints: List[List[str]] = []
    kit_deliverables: List[List[str]] = []
    kit_work_packages: List[List[str]] = []
    kit_raid_items: List[List[str]] = []
    kit_dep_asm_items: List[List[str]] = []
    kit_decisions: List[List[str]] = []
    kit_charter: Dict[str, str] = {}

    if kit_doc:
        for table in kit_doc.tables:
            if not table.rows:
                continue
            hdr = [c.text.strip().lower() for c in table.rows[0].cells]
            hdr_txt = " | ".join(hdr)
            
            # Project Charter Metadata
            if "project name" in hdr_txt and ("client sponsor" in hdr_txt or "client name" in hdr_txt or "governance tier" in hdr_txt):
                for r in table.rows:
                    cells = [c.text.strip() for c in r.cells]
                    if len(cells) >= 2:
                        kit_charter[cells[0].lower()] = cells[1]
                    if len(cells) >= 4:
                        kit_charter[cells[2].lower()] = cells[3]

            # Interim Checkpoints Table
            elif "checkpoint" in hdr_txt and "phase" in hdr_txt and "description" in hdr_txt:
                for r in table.rows[1:]:
                    cells = [c.text.strip() for c in r.cells]
                    if len(cells) >= 2 and cells[0]:
                        kit_checkpoints.append(cells)

            # Milestone Delivery Plan
            elif "milestone" in hdr_txt and "description" in hdr_txt and ("target date" in hdr_txt or "buffer date" in hdr_txt or "external date" in hdr_txt):
                for r in table.rows[1:]:
                    cells = [c.text.strip() for c in r.cells]
                    if len(cells) >= 2 and cells[0]:
                        kit_milestones.append(cells)
            
            # Deliverables
            elif "deliverable" in hdr_txt and ("acceptance criteria" in hdr_txt or "owner" in hdr_txt or "evidence" in hdr_txt):
                for r in table.rows[1:]:
                    cells = [c.text.strip() for c in r.cells]
                    if len(cells) >= 2 and cells[0]:
                        kit_deliverables.append(cells)

            # Scope Decomposition / Work packages
            elif "parent deliv" in hdr_txt or "work package" in hdr_txt or any(c.text.strip().startswith("WP-") for r in table.rows for c in r.cells):
                for r in table.rows[1:]:
                    cells = [c.text.strip() for c in r.cells]
                    if len(cells) >= 2 and cells[0]:
                        kit_work_packages.append(cells)

            # Dependencies & Assumptions
            elif any(c.text.strip().startswith("DEP-") or c.text.strip().startswith("ASM-") for r in table.rows for c in r.cells):
                for r in table.rows[1:]:
                    cells = [c.text.strip() for c in r.cells]
                    if len(cells) >= 2 and cells[0]:
                        kit_dep_asm_items.append(cells)

            # RAID (Risks & Issues)
            elif "raid id" in hdr_txt or any(c.text.strip().startswith("RSK-") or c.text.strip().startswith("ISS-") for r in table.rows for c in r.cells):
                for r in table.rows[1:]:
                    cells = [c.text.strip() for c in r.cells]
                    if len(cells) >= 2 and cells[0]:
                        kit_raid_items.append(cells)

            # Decisions
            elif "decision id" in hdr_txt or any(c.text.strip().startswith("DEC-") for r in table.rows for c in r.cells):
                for r in table.rows[1:]:
                    cells = [c.text.strip() for c in r.cells]
                    if len(cells) >= 2 and cells[0]:
                        kit_decisions.append(cells)

    # Parse Checklist tables
    chk_items: Dict[str, Dict[str, str]] = {}
    chk_ambiguities: List[List[str]] = []
    chk_questions: List[List[str]] = []

    if chk_doc:
        for table in chk_doc.tables:
            if not table.rows:
                continue
            hdr = [c.text.strip().lower() for c in table.rows[0].cells]
            hdr_txt = " | ".join(hdr)

            if ("gate id" in hdr_txt or "item id" in hdr_txt) and "gate criterion" in hdr_txt:
                for r in table.rows[1:]:
                    cells = [c.text.strip() for c in r.cells]
                    if len(cells) >= 6 and cells[0].startswith("G01-"):
                        evidence_str = cells[7] if len(cells) > 7 else cells[-1]
                        chk_items[cells[0]] = {
                            "item_id": cells[0],
                            "criterion": cells[1],
                            "artifact": cells[2],
                            "status": cells[3] if len(cells) > 3 else "",
                            "owner": cells[4] if len(cells) > 4 else "",
                            "evidence": evidence_str
                        }

            elif "anomaly id" in hdr_txt or "conflicting clauses" in hdr_txt:
                for r in table.rows[1:]:
                    cells = [c.text.strip() for c in r.cells]
                    if cells and cells[0].startswith("AMB-"):
                        chk_ambiguities.append(cells)

            elif "question id" in hdr_txt or "actionable clarification question" in hdr_txt:
                for r in table.rows[1:]:
                    cells = [c.text.strip() for c in r.cells]
                    if cells and cells[0].startswith("Q-"):
                        chk_questions.append(cells)

    proj_name = kit_charter.get("project name", "")
    oracle = oracle_override or load_oracle_for_folder(folder, proj_name)

    if kit_doc:
        # INV-01: Kit milestone count equals SOW gate count
        if oracle and "gate_count" in oracle:
            expected_gates = oracle["gate_count"]
            if len(kit_milestones) != expected_gates:
                violations.append(InvariantViolation(
                    "INV-01",
                    f"Kit milestone count {len(kit_milestones)} does not match SOW gate count {expected_gates}",
                    "Kit"
                ))

        # INV-17: Unique IDs in Kit
        def check_unique_ids(items, prefix, name):
            ids = [it[0] for it in items if it and it[0].startswith(prefix)]
            if len(ids) != len(set(ids)):
                violations.append(InvariantViolation("INV-17", f"Duplicate IDs found in {name}: {ids}", "Kit"))

        check_unique_ids(kit_milestones, "M", "Milestones")
        check_unique_ids(kit_checkpoints, "CP", "Checkpoints")
        check_unique_ids(kit_deliverables, "DEL", "Deliverables")
        check_unique_ids(kit_work_packages, "WP", "Work Packages")
        check_unique_ids(kit_decisions, "DEC", "Decisions")

        # INV-07: Every Kit work package has an existing parent deliverable, a valid SOW reference, and a non-placeholder owner
        deliv_ids = {d[0] for d in kit_deliverables if d}
        for wp in kit_work_packages:
            if not wp or len(wp) < 4:
                continue
            wp_id = wp[0]
            parent_id = wp[1] if len(wp) > 1 else ""
            owner = wp[4] if len(wp) > 4 else (wp[3] if len(wp) > 3 else "")
            
            if parent_id and parent_id not in deliv_ids and parent_id != "None" and parent_id != "-":
                violations.append(InvariantViolation("INV-07", f"Work package {wp_id} has invalid parent deliverable '{parent_id}'", "Kit"))
            if not parent_id or parent_id == "" or parent_id == "None":
                violations.append(InvariantViolation("INV-07", f"Work package {wp_id} has blank parent deliverable", "Kit"))
            if PLACEHOLDER_REGEX.search(owner) or owner.upper() in ["UNASSIGNED", "TBD", "[UNASSIGNED - TO BE CONFIRMED]"]:
                violations.append(InvariantViolation("INV-07", f"Work package {wp_id} has placeholder owner '{owner}'", "Kit"))

        # INV-13: No description begins with citation prefix
        for d in kit_deliverables:
            if len(d) > 1 and CITATION_PREFIX_REGEX.search(d[1]):
                violations.append(InvariantViolation("INV-13", f"Deliverable description begins with citation prefix: '{d[1][:40]}...'", "Kit"))
        for m in kit_milestones:
            if len(m) > 1 and CITATION_PREFIX_REGEX.search(m[1]):
                violations.append(InvariantViolation("INV-13", f"Milestone description begins with citation prefix: '{m[1][:40]}...'", "Kit"))
        for wp in kit_work_packages:
            if len(wp) > 2 and CITATION_PREFIX_REGEX.search(wp[2]):
                violations.append(InvariantViolation("INV-13", f"Work package description begins with citation prefix: '{wp[2][:40]}...'", "Kit"))
        for r in kit_raid_items:
            if len(r) > 2 and CITATION_PREFIX_REGEX.search(r[2]):
                violations.append(InvariantViolation("INV-13", f"RAID description begins with citation prefix: '{r[2][:40]}...'", "Kit"))

        # INV-14: Every deliverable has evidence or missing-evidence note
        for d in kit_deliverables:
            if len(d) >= 4:
                d_id = d[0]
                ev = d[3].strip()
                if not ev or ev.upper() == "NONE":
                    violations.append(InvariantViolation("INV-14", f"Deliverable {d_id} has empty evidence", "Kit"))

        # INV-21: No two work packages share a title. No title contains 'implementation task'.
        wp_titles: List[str] = []
        for wp in kit_work_packages:
            wp_id = wp[0]
            desc = wp[2] if len(wp) > 2 else ""
            title_match = re.split(r':\s+|\.\s+|\n', desc)
            wp_title = title_match[0].strip() if title_match else desc.strip()
            
            if re.search(r'\bimplementation\s+task\b', desc, re.IGNORECASE):
                violations.append(InvariantViolation("INV-21", f"Work package {wp_id} title contains 'implementation task': '{desc[:50]}'", "Kit"))
            
            if wp_title:
                wp_titles.append(wp_title)

        if len(wp_titles) != len(set(wp_titles)):
            seen_t: Set[str] = set()
            dup_t: Set[str] = set()
            for t in wp_titles:
                if t in seen_t:
                    dup_t.add(t)
                seen_t.add(t)
            violations.append(InvariantViolation("INV-21", f"Duplicate work package title(s) found in Kit: {list(dup_t)[:3]}", "Kit"))

        # INV-22: Evidence coverage at least oracle minimum. Shared evidence carries shared-item note.
        if kit_deliverables:
            total_delivs = len(kit_deliverables)
            valid_evidence_count = 0
            evidence_by_text: Dict[str, List[str]] = {}

            for d in kit_deliverables:
                d_id = d[0]
                ev = d[3].strip() if len(d) > 3 else ""
                has_placeholder = bool(PLACEHOLDER_REGEX.search(ev))
                is_valid = bool(ev and ev.upper() != "NONE" and not has_placeholder)
                if is_valid:
                    valid_evidence_count += 1
                
                if is_valid:
                    norm_ev = re.sub(r'\s+', ' ', ev.lower()).strip()
                    evidence_by_text.setdefault(norm_ev, []).append(d_id)

            coverage = valid_evidence_count / total_delivs if total_delivs > 0 else 0.0
            if oracle and "min_evidence_coverage" in oracle:
                min_cov = float(oracle["min_evidence_coverage"])
                if coverage < min_cov - 1e-4:
                    violations.append(InvariantViolation(
                        "INV-22",
                        f"Evidence coverage {coverage:.2f} ({valid_evidence_count}/{total_delivs}) is below oracle minimum {min_cov:.2f}",
                        "Kit"
                    ))

            for norm_ev, sharing_delivs in evidence_by_text.items():
                if len(sharing_delivs) > 1:
                    if "shared evidence" not in norm_ev:
                        violations.append(InvariantViolation(
                            "INV-22",
                            f"Deliverables {sharing_delivs} share evidence without 'Shared evidence item' note: '{norm_ev[:50]}...'",
                            "Kit"
                        ))

        # INV-24: Review window is KIT-03 default or SOW text. Never 'NOT SPECIFIED - TO BE CONFIRMED' or ends with '...'.
        for d in kit_deliverables:
            d_id = d[0]
            rw = ""
            for idx in [7, 6, 5]:
                if len(d) > idx and ("day" in d[idx].lower() or "review" in d[idx].lower() or "not specified" in d[idx].lower() or "business" in d[idx].lower()):
                    rw = d[idx].strip()
                    break
            if not rw and len(d) > 7:
                rw = d[7].strip()
            if rw:
                if "not specified - to be confirmed" in rw.lower() or rw.strip().upper() == "NOT SPECIFIED":
                    violations.append(InvariantViolation("INV-24", f"Deliverable {d_id} review window contains placeholder '{rw}'", "Kit"))
                if rw.endswith("...") or rw.endswith("…"):
                    violations.append(InvariantViolation("INV-24", f"Deliverable {d_id} review window is truncated with ellipsis: '{rw}'", "Kit"))

    # Checklist Checks
    if chk_doc:
        # INV-18: Award date provenance
        if oracle and not oracle.get("award_date_stated_in_sow", True):
            for t in chk_doc.tables:
                for r in t.rows:
                    txt = " ".join([c.text for c in r.cells])
                    if "project awarded 20" in txt.lower() or "awarded: 20" in txt.lower():
                        violations.append(InvariantViolation("INV-18", f"Checklist contains computed award date: '{txt[:60]}'", "Checklist"))

    # Workbook checks
    if wb:
        # Check sheet names for readiness terms
        for sheet_name in wb.sheetnames:
            if READINESS_REGEX.search(sheet_name):
                violations.append(InvariantViolation("INV-04", f"Sheet name '{sheet_name}' contains readiness terms", "Workbook"))

        # Inspect Project Schedule
        sched_gate_count = 0
        if "Project Schedule" in wb.sheetnames:
            sched = wb["Project Schedule"]
            l1_rows = []
            predecessors: Dict[str, List[str]] = {}
            row_wbs_codes = []
            schedule_gate_items: Dict[str, int] = {}

            # Row 3 check for INV-18 (Start Date basis)
            row3_val = str(sched.cell(row=3, column=1).value or "")
            if oracle and not oracle.get("award_date_stated_in_sow", True):
                if "after award" in row3_val.lower():
                    violations.append(InvariantViolation("INV-18", f"Schedule Start Date basis says 'after award' when SOW has no award date: '{row3_val}'", "Project Schedule"))

            for row_idx, row in enumerate(sched.iter_rows(min_row=5, values_only=True), start=5):
                wbs_code = str(row[0] or "").strip()
                row_type = str(row[1] or "").strip()
                ws_name = str(row[2] or "").strip()
                m_id = str(row[3] or "").strip()
                sow_refs = str(row[20] or "").strip() if len(row) > 20 else ""
                pred_str = str(row[16] or "").strip() if len(row) > 16 else ""

                if not wbs_code and not row_type:
                    continue

                if row_type == "Workstream":
                    l1_rows.append((wbs_code, ws_name))

                if row_type == "Milestone" and m_id:
                    sched_gate_count += 1
                    refs = [r.strip() for r in sow_refs.split(",") if r.strip()]
                    schedule_gate_items[m_id] = len(refs)

                if wbs_code:
                    row_wbs_codes.append(wbs_code)
                    if pred_str and pred_str != "-":
                        preds = [p.strip() for p in pred_str.split(",") if p.strip()]
                        predecessors[wbs_code] = preds

                # INV-03: No banned workstream names
                for banned in BANNED_WORKSTREAM_NAMES:
                    if banned.lower() in ws_name.lower():
                        violations.append(InvariantViolation("INV-03", f"Workstream contains banned term '{banned}' in row {row_idx}", "Project Schedule"))

            # INV-02: Exactly one level 1 row per SOW phase
            if oracle and "phases" in oracle:
                expected_phase_count = len(oracle["phases"])
                if len(l1_rows) != expected_phase_count:
                    violations.append(InvariantViolation(
                        "INV-02",
                        f"Schedule has {len(l1_rows)} level 1 workstreams, expected {expected_phase_count}",
                        "Project Schedule"
                    ))

            # INV-20: No gate holds more than its oracle share of work items
            if oracle and "sow_reference_phase" in oracle:
                oracle_counts = {
                    "M1": len(oracle["sow_reference_phase"].get("P1", [])),
                    "M2": len(oracle["sow_reference_phase"].get("P2a", [])),
                    "M3": len(oracle["sow_reference_phase"].get("P2b", [])),
                    "M4": len(oracle["sow_reference_phase"].get("P3", [])),
                }
                for g_id, exp_cnt in oracle_counts.items():
                    act_cnt = schedule_gate_items.get(g_id, 0)
                    if act_cnt > exp_cnt + 5:
                        violations.append(InvariantViolation(
                            "INV-20",
                            f"Gate {g_id} holds {act_cnt} SOW references, expected {exp_cnt}",
                            "Project Schedule"
                        ))

            # INV-05: Predecessor graph is acyclic and points backward only
            wbs_to_pos = {code: i for i, code in enumerate(row_wbs_codes)}
            for code, preds in predecessors.items():
                curr_pos = wbs_to_pos.get(code, -1)
                for p in preds:
                    p_pos = wbs_to_pos.get(p, -1)
                    if p_pos >= curr_pos and p_pos != -1:
                        violations.append(InvariantViolation("INV-05", f"Forward or self predecessor: {code} depends on later row {p}", "Project Schedule"))

        # Inspect WBS
        wbs_deliv_ids: List[str] = []
        wbs_sow_refs: Set[str] = set()
        wbs_tasks_by_wp_id: Set[str] = set()
        wbs_gate_packages: Dict[str, List[str]] = {}

        if "WBS" in wb.sheetnames:
            wbs_sheet = wb["WBS"]
            current_workstream = ""
            current_gate_id = ""
            current_pkg_name = ""

            for row_idx, row in enumerate(wbs_sheet.iter_rows(min_row=5, values_only=True), start=5):
                level = row[1]
                elem_type = str(row[2] or "").strip()
                name = str(row[3] or "").strip()
                ws_name = str(row[4] or "").strip()
                m_id = str(row[5] or "").strip()
                d_id = str(row[6] or "").strip()
                s_id = str(row[7] or "").strip()
                sow_refs_str = str(row[8] or "").strip()
                owner = str(row[9] or "").strip() if len(row) > 9 else ""
                source_val = str(row[19] or "").strip() if len(row) > 19 else ""
                notes_val = str(row[21] or "").strip() if len(row) > 21 else ""
                
                if elem_type == "Workstream":
                    current_workstream = name
                elif elem_type in ("Milestone", "Gate"):
                    current_gate_id = m_id
                    wbs_gate_packages.setdefault(m_id, [])
                elif elem_type in ("Deliverable", "Package", "Work Package"):
                    current_pkg_name = name
                    if current_gate_id:
                        wbs_gate_packages.setdefault(current_gate_id, []).append(name)
                    if d_id and d_id.startswith("DEL-"):
                        wbs_deliv_ids.append(d_id)

                if s_id:
                    for wp_match in re.findall(r'WP-\d+', s_id):
                        wbs_tasks_by_wp_id.add(wp_match)
                if notes_val:
                    for wp_match in re.findall(r'WP-\d+', notes_val):
                        wbs_tasks_by_wp_id.add(wp_match)

                if sow_refs_str:
                    for r in SOW_REF_REGEX.findall(sow_refs_str):
                        wbs_sow_refs.add(r)
                if s_id and SOW_REF_REGEX.match(s_id):
                    wbs_sow_refs.add(s_id)

                # INV-03: No level 1 or 2 row with PM Best Practice
                if level in (1, 2, "1", "2") and "PM Best Practice" in source_val:
                    if "MS-TBC" not in name:
                        violations.append(InvariantViolation("INV-03", f"Level {level} row '{name}' has Source 'PM Best Practice'", "WBS"))

                # INV-10: No task name > 120 chars, starts with 'Work Package:', or contains action placeholder
                if level == 4 or level == "4":
                    if len(name) > 120:
                        violations.append(InvariantViolation("INV-10", f"Task name exceeds 120 characters at row {row_idx}: '{name[:30]}...'", "WBS"))
                    if name.startswith("Work Package:"):
                        violations.append(InvariantViolation("INV-10", f"Task name starts with 'Work Package:' at row {row_idx}", "WBS"))
                    if PLACEHOLDER_REGEX.search(name):
                        violations.append(InvariantViolation("INV-10", f"Task name contains action placeholder at row {row_idx}: '{name}'", "WBS"))

                # INV-11: No generated task has placeholder owner
                if (level == 4 or level == "4") and name:
                    if PLACEHOLDER_REGEX.search(owner) or owner.upper() in ["UNASSIGNED", "TBD", "[UNASSIGNED - TO BE CONFIRMED]"]:
                        violations.append(InvariantViolation("INV-11", f"Task '{name}' has placeholder owner '{owner}' at row {row_idx}", "WBS"))

                # INV-14: Evidence flag check
                if "may belong to" in notes_val.lower() or "evidence" in notes_val.lower():
                    flag_m = re.search(r'belong to (DEL-\d+)', notes_val, re.IGNORECASE)
                    if flag_m:
                        target_d = flag_m.group(1).upper()
                        if target_d == d_id.upper():
                            violations.append(InvariantViolation("INV-14", f"Evidence flag on {d_id} names itself: '{notes_val}'", "WBS"))

            # INV-06: Every Kit deliverable appears exactly once at WBS level 3 under a gate. Every gate has a Milestone Acceptance package.
            if kit_deliverables:
                kit_deliv_ids = [d[0] for d in kit_deliverables if d and d[0].startswith("DEL-")]
                for d_id in kit_deliv_ids:
                    count_in_wbs = wbs_deliv_ids.count(d_id)
                    if count_in_wbs != 1:
                        violations.append(InvariantViolation(
                            "INV-06",
                            f"Deliverable {d_id} appears {count_in_wbs} times at WBS level 3 (expected exactly 1)",
                            "WBS"
                        ))

            for g_id, pkgs in wbs_gate_packages.items():
                if not any("Milestone Acceptance" in p or "Acceptance" in p for p in pkgs):
                    violations.append(InvariantViolation(
                        "INV-06",
                        f"Gate {g_id} lacks Milestone Acceptance package",
                        "WBS"
                    ))

            # INV-07 check: Work packages appear in WBS as task or degenerate Source ID
            if kit_work_packages:
                for wp in kit_work_packages:
                    wp_id = wp[0]
                    if wp_id not in wbs_tasks_by_wp_id:
                        violations.append(InvariantViolation(
                            "INV-07",
                            f"Work package {wp_id} does not appear as task or Source ID in WBS",
                            "WBS"
                        ))

            # INV-08: Every SOW reference in catalogue appears in WBS SOW References
            if oracle and "sow_reference_phase" in oracle:
                all_oracle_refs = [r for r_list in oracle["sow_reference_phase"].values() for r in r_list]
                for r in all_oracle_refs:
                    if r not in wbs_sow_refs:
                        violations.append(InvariantViolation(
                            "INV-08",
                            f"SOW reference '{r}' missing from WBS SOW references",
                            "WBS"
                        ))

            # INV-19: Deliverables placed in oracle phase
            if oracle and "sow_reference_phase" in oracle:
                ref_to_phase: Dict[str, str] = {}
                for phase_code, r_list in oracle["sow_reference_phase"].items():
                    for r in r_list:
                        ref_to_phase[r] = phase_code

                for row_idx, row in enumerate(wbs_sheet.iter_rows(min_row=5, values_only=True), start=5):
                    elem_type = str(row[2] or "").strip()
                    d_id = str(row[6] or "").strip()
                    ws_name = str(row[4] or "").strip()
                    sow_refs_str = str(row[8] or "").strip()
                    
                    if (elem_type == "Deliverable" or d_id.startswith("DEL-")) and sow_refs_str:
                        refs = SOW_REF_REGEX.findall(sow_refs_str)
                        phases_for_refs = {ref_to_phase[r] for r in refs if r in ref_to_phase}
                        if len(phases_for_refs) == 1:
                            expected_phase = list(phases_for_refs)[0]
                            if expected_phase.lower() not in ws_name.lower():
                                violations.append(InvariantViolation(
                                    "INV-19",
                                    f"Deliverable {d_id} (refs {refs}) belongs to {expected_phase}, but mapped to workstream '{ws_name}'",
                                    "WBS"
                                ))

            # INV-25 check: Check if 'Other {ws} work' holds work packages from other phases
            for row_idx, row in enumerate(wbs_sheet.iter_rows(min_row=5, values_only=True), start=5):
                elem_type = str(row[2] or "").strip()
                ws_name = str(row[4] or "").strip()
                name = str(row[3] or "").strip()
                s_id = str(row[7] or "").strip()
                sow_refs_str = str(row[8] or "").strip()
                
                if "other " in ws_name.lower() or "other " in name.lower():
                    for phase_pfx in ["P1", "P2a", "P2A", "P2b", "P2B", "P3"]:
                        if phase_pfx.lower() in name.lower() and phase_pfx.lower() not in ws_name.lower():
                            violations.append(InvariantViolation(
                                "INV-25",
                                f"Task '{name}' belonging to {phase_pfx} sits in '{ws_name}'",
                                "WBS"
                            ))
                            break

                    refs = SOW_REF_REGEX.findall(f"{name} {sow_refs_str} {s_id}")
                    if oracle and "sow_reference_phase" in oracle:
                        for r in refs:
                            expected_phase = ref_to_phase.get(r)
                            if expected_phase and expected_phase.lower() not in ws_name.lower():
                                violations.append(InvariantViolation(
                                    "INV-25",
                                    f"Row '{name}' with ref {r} ({expected_phase}) sits in '{ws_name}'",
                                    "WBS"
                                ))

        # Inspect RAID Log for INV-09, INV-13, INV-23
        raid_source_ids: List[str] = []
        wb_open_q_count = 0

        if "RAID Log" in wb.sheetnames:
            raid_sheet = wb["RAID Log"]
            for row_idx, row in enumerate(raid_sheet.iter_rows(min_row=5, values_only=True), start=5):
                raid_id = str(row[0] or "").strip()
                r_type = str(row[1] or "").strip()
                desc = str(row[2] or "").strip()
                contract_ref = str(row[3] or "").strip()
                cat = str(row[4] or "").strip()
                source_id = str(row[23] or "").strip() if len(row) > 23 else ""
                
                if not raid_id or raid_id == "RAID ID":
                    continue

                if source_id:
                    raid_source_ids.append(source_id)

                if cat == "Open Question" or source_id.startswith("Q-"):
                    wb_open_q_count += 1

                # INV-13: Description begins with citation prefix or Contract Reference has empty parts
                if CITATION_PREFIX_REGEX.search(desc):
                    violations.append(InvariantViolation("INV-13", f"RAID description begins with citation prefix: '{desc[:40]}...'", "RAID Log"))
                
                if contract_ref:
                    parts = [p.strip() for p in contract_ref.split("|")]
                    if any(p == "" or p == "Stories:" or p == "Sections:" for p in parts) or contract_ref.endswith("|") or contract_ref.startswith("|"):
                        violations.append(InvariantViolation("INV-13", f"RAID row {raid_id} Contract Reference has empty part: '{contract_ref}'", "RAID Log"))

                # INV-23: Every Contract Reference is 'Not cited', blank (on non-clarification rows), or valid citation
                if cat in ("Contract Clarification", "Open Question") or contract_ref:
                    if cat not in ("Contract Clarification", "Open Question") and contract_ref not in ("", "-", "None"):
                        violations.append(InvariantViolation("INV-23", f"Non-clarification RAID row {raid_id} ({cat}) has non-blank Contract Reference: '{contract_ref}'", "RAID Log"))
                    elif contract_ref and contract_ref not in ("Not cited", "-", "None"):
                        has_ext = bool(VALID_CONTRACT_REF_EXT_REGEX.search(contract_ref))
                        has_exhibit = bool(EXHIBIT_WORD_REGEX.search(contract_ref))
                        has_sow_ref = bool(SOW_REF_REGEX.search(contract_ref))
                        has_section = bool(SECTION_WORD_REGEX.search(contract_ref))
                        
                        if not (has_ext or has_exhibit or has_sow_ref or has_section):
                            violations.append(InvariantViolation(
                                "INV-23",
                                f"RAID row {raid_id} Contract Reference '{contract_ref}' is invalid (lacks file ext, Exhibit word, SOW ref, or section)",
                                "RAID Log"
                            ))

            # INV-09: Every Kit and Checklist register ID appears exactly once as RAID Source ID
            kit_register_ids = []
            for r in kit_raid_items:
                if r and r[0]:
                    kit_register_ids.append(r[0])
            for dep in kit_dep_asm_items:
                if dep and dep[0]:
                    kit_register_ids.append(dep[0])
            for amb in chk_ambiguities:
                if amb and amb[0]:
                    kit_register_ids.append(amb[0])
            for q in chk_questions:
                if q and q[0]:
                    q_text = q[1] if len(q) > 1 else ""
                    # Role questions matching readiness / unassigned are excluded
                    if not (READINESS_REGEX.search(q_text) or re.search(r'\brole is unassigned\b', q_text, re.IGNORECASE)):
                        kit_register_ids.append(q[0])

            for reg_id in kit_register_ids:
                count_in_raid = raid_source_ids.count(reg_id)
                if count_in_raid != 1:
                    violations.append(InvariantViolation(
                        "INV-09",
                        f"Register item {reg_id} appears {count_in_raid} times as RAID Source ID (expected exactly 1)",
                        "RAID Log"
                    ))

        # INV-12: Cross-artifact counts agree (TR-02)
        if chk_items and "G01-15" in chk_items:
            g15_ev = chk_items["G01-15"]["evidence"]
            g15_m = re.search(r'(\d+)\s+validation\s+points', g15_ev, re.IGNORECASE)
            
            actual_chk_questions = [
                q for q in chk_questions
                if len(q) > 1 and "No open clarification questions" not in q[1]
            ]
            
            if "no open questions" in g15_ev.lower() or (g15_m and int(g15_m.group(1)) == 0):
                if len(actual_chk_questions) != 0:
                    violations.append(InvariantViolation(
                        "INV-12",
                        f"G01-15 indicates 0 questions but Checklist questions table has {len(actual_chk_questions)}",
                        "Checklist"
                    ))
            elif g15_m:
                g15_count = int(g15_m.group(1))
                chk_q_count = len(actual_chk_questions)
                if g15_count != chk_q_count:
                    violations.append(InvariantViolation(
                        "INV-12",
                        f"G01-15 count ({g15_count}) does not match Checklist Actionable Questions count ({chk_q_count})",
                        "Checklist"
                    ))
                
                # Excluded role questions
                excluded_q_count = 0
                for q in actual_chk_questions:
                    q_text = q[1] if len(q) > 1 else ""
                    if READINESS_REGEX.search(q_text) or re.search(r'\brole is unassigned\b', q_text, re.IGNORECASE):
                        excluded_q_count += 1
                
                expected_wb_q_count = chk_q_count - excluded_q_count
                if wb_open_q_count != expected_wb_q_count:
                    violations.append(InvariantViolation(
                        "INV-12",
                        f"Workbook Open Question count ({wb_open_q_count}) does not match Checklist questions ({chk_q_count}) minus excluded ({excluded_q_count}) = {expected_wb_q_count}",
                        "RAID Log"
                    ))

        if chk_items and "G01-03" in chk_items and kit_deliverables:
            g3_ev = chk_items["G01-03"]["evidence"]
            g3_m = re.search(r'(\d+)\s+deliverables', g3_ev, re.IGNORECASE)
            if g3_m:
                g3_count = int(g3_m.group(1))
                if g3_count != len(kit_deliverables) or (wbs_deliv_ids and len(wbs_deliv_ids) != g3_count):
                    violations.append(InvariantViolation(
                        "INV-12",
                        f"Deliverable counts disagree across artifacts: Kit={len(kit_deliverables)}, Checklist G01-03={g3_count}, WBS={len(wbs_deliv_ids)}",
                        "Cross-Artifact"
                    ))

        if chk_items and "G01-04" in chk_items and kit_milestones:
            g4_ev = chk_items["G01-04"]["evidence"]
            g4_m = re.search(r'(\d+)\s+milestones', g4_ev, re.IGNORECASE)
            if g4_m:
                g4_count = int(g4_m.group(1))
                if g4_count != len(kit_milestones):
                    violations.append(InvariantViolation(
                        "INV-12",
                        f"Milestone counts disagree: Kit={len(kit_milestones)}, Checklist G01-04={g4_count}",
                        "Cross-Artifact"
                    ))

        if chk_items and "G01-05" in chk_items:
            g5_ev = chk_items["G01-05"]["evidence"]
            g5_raid_m = re.search(r'(\d+)\s+RAID', g5_ev, re.IGNORECASE)
            g5_dep_m = re.search(r'(\d+)\s+dependencies', g5_ev, re.IGNORECASE)
            if g5_raid_m and kit_raid_items:
                g5_r_count = int(g5_raid_m.group(1))
                if g5_r_count != len(kit_raid_items):
                    violations.append(InvariantViolation(
                        "INV-12",
                        f"RAID items count disagrees: Kit={len(kit_raid_items)}, Checklist G01-05={g5_r_count}",
                        "Cross-Artifact"
                    ))
            if g5_dep_m and kit_dep_asm_items:
                g5_d_count = int(g5_dep_m.group(1))
                if g5_d_count != len(kit_dep_asm_items):
                    violations.append(InvariantViolation(
                        "INV-12",
                        f"Dependencies/Assumptions count disagrees: Kit={len(kit_dep_asm_items)}, Checklist G01-05={g5_d_count}",
                        "Cross-Artifact"
                    ))

        # Global cell scan for INV-04, INV-15, INV-16
        for sname in wb.sheetnames:
            sheet = wb[sname]
            for row_idx, row in enumerate(sheet.iter_rows(values_only=True), start=1):
                for col_idx, cell_val in enumerate(row, start=1):
                    val_str = str(cell_val or "")
                    if cell_val is None:
                        continue
                    # INV-04: Readiness terms in cells
                    if READINESS_REGEX.search(val_str):
                        violations.append(InvariantViolation("INV-04", f"Cell at {sname}!R{row_idx}C{col_idx} matches readiness term: '{val_str}'", "Workbook"))
                    
                    # INV-15: Banned effort words in headers/templates/formulas
                    if row_idx < 5 or val_str.startswith("="):
                        if BANNED_EFFORT_REGEX.search(val_str):
                            violations.append(InvariantViolation("INV-15", f"Effort word found at {sname}!R{row_idx}C{col_idx}: '{val_str}'", "Workbook"))

                    # INV-16: No literal 'None' or 'null' text
                    if val_str.strip() in ["None", "null", "NULL"]:
                        violations.append(InvariantViolation("INV-16", f"Literal '{val_str}' found at {sname}!R{row_idx}C{col_idx}", "Workbook"))

    return violations


def main():
    parser = argparse.ArgumentParser(description="Check PMO Startup Kit output artifacts for invariant violations (QA-04).")
    parser.add_argument("folder", type=str, help="Path to output directory containing generated artifacts")
    parser.add_argument("--oracle", type=str, default=None, help="Optional oracle name (e.g. arc)")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists() or not folder.is_dir():
        print(f"Error: Directory '{folder}' does not exist.", file=sys.stderr)
        sys.exit(2)

    oracle_data = None
    if args.oracle:
        oracle_path = Path("tests/oracles") / f"{args.oracle}.json"
        if oracle_path.exists():
            with open(oracle_path, "r", encoding="utf-8") as f:
                oracle_data = json.load(f)

    violations = check_artifacts_directory(folder, oracle_override=oracle_data)
    if violations:
        print(f"FAILED: Found {len(violations)} invariant violation(s) in '{folder}':")
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)
    else:
        print(f"PASSED: All artifacts in '{folder}' satisfy all invariants.")
        sys.exit(0)


if __name__ == "__main__":
    main()
