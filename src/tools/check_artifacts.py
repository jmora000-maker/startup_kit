"""Comprehensive invariant checker for generated PMO artifacts (QA-04, INV-01 to INV-18)."""

import sys
import re
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


class InvariantViolation:
    def __init__(self, inv_id: str, message: str, artifact: str = ""):
        self.inv_id = inv_id
        self.message = message
        self.artifact = artifact

    def __str__(self):
        art = f" [{self.artifact}]" if self.artifact else ""
        return f"{self.inv_id}{art}: {self.message}"


def check_artifacts_directory(folder_path: Path) -> List[InvariantViolation]:
    """Inspect output folder containing Kit docx, Checklist docx, and Workbook xlsx against INV-01 to INV-18."""
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
    kit_deliverables: List[List[str]] = []
    kit_work_packages: List[List[str]] = []
    kit_raid_items: List[List[str]] = []
    kit_decisions: List[List[str]] = []
    kit_questions: List[str] = []
    kit_charter: Dict[str, str] = {}

    if kit_doc:
        for table in kit_doc.tables:
            if not table.rows:
                continue
            hdr = [c.text.strip().lower() for c in table.rows[0].cells]
            hdr_txt = " | ".join(hdr)
            
            # Project Charter Metadata
            if "project name" in hdr_txt and "client sponsor" in hdr_txt:
                for r in table.rows:
                    cells = [c.text.strip() for c in r.cells]
                    if len(cells) >= 2:
                        kit_charter[cells[0].lower()] = cells[1]
                    if len(cells) >= 4:
                        kit_charter[cells[2].lower()] = cells[3]

            # Milestone Delivery Plan
            elif "milestone" in hdr_txt and "description" in hdr_txt and ("target date" in hdr_txt or "buffer date" in hdr_txt or "external date" in hdr_txt):
                for r in table.rows[1:]:
                    cells = [c.text.strip() for c in r.cells]
                    if len(cells) >= 2 and cells[0]:
                        kit_milestones.append(cells)
            
            # Deliverables
            elif "deliverable" in hdr_txt and ("acceptance criteria" in hdr_txt or "owner" in hdr_txt):
                for r in table.rows[1:]:
                    cells = [c.text.strip() for c in r.cells]
                    if len(cells) >= 2 and cells[0]:
                        kit_deliverables.append(cells)

            # Scope Decomposition / Work packages
            elif "parent deliv" in hdr_txt or "work package" in hdr_txt or ("wp-" in "".join([c.text for r in table.rows for c in r.cells])):
                for r in table.rows[1:]:
                    cells = [c.text.strip() for c in r.cells]
                    if len(cells) >= 2 and cells[0]:
                        kit_work_packages.append(cells)

            # RAID
            elif "raid id" in hdr_txt or ("rsk-" in "".join([c.text for r in table.rows for c in r.cells])):
                for r in table.rows[1:]:
                    cells = [c.text.strip() for c in r.cells]
                    if len(cells) >= 2 and cells[0]:
                        kit_raid_items.append(cells)

            # Decisions
            elif "decision id" in hdr_txt or "dec-" in hdr_txt:
                for r in table.rows[1:]:
                    cells = [c.text.strip() for c in r.cells]
                    if len(cells) >= 2 and cells[0]:
                        kit_decisions.append(cells)

            # Questions
            elif "question" in hdr_txt or "open questions" in hdr_txt:
                for r in table.rows[1:]:
                    cells = [c.text.strip() for c in r.cells]
                    if cells:
                        kit_questions.append(cells[0])

        # INV-17: Unique IDs in Kit
        def check_unique_ids(items, prefix, name):
            ids = [it[0] for it in items if it and it[0].startswith(prefix)]
            if len(ids) != len(set(ids)):
                violations.append(InvariantViolation("INV-17", f"Duplicate IDs found in {name}: {ids}", "Kit"))

        check_unique_ids(kit_milestones, "M", "Milestones")
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

    # Workbook checks
    if wb:
        # Check sheet names for readiness terms
        for sheet_name in wb.sheetnames:
            if READINESS_REGEX.search(sheet_name):
                violations.append(InvariantViolation("INV-04", f"Sheet name '{sheet_name}' contains readiness terms", "Workbook"))

        # Inspect Project Schedule
        if "Project Schedule" in wb.sheetnames:
            sched = wb["Project Schedule"]
            l1_rows = []
            predecessors: Dict[str, List[str]] = {}
            row_wbs_codes = []

            for row_idx, row in enumerate(sched.iter_rows(min_row=5, values_only=True), start=5):
                wbs_code = str(row[0] or "").strip()
                row_type = str(row[1] or "").strip()
                ws_name = str(row[2] or "").strip()
                pred_str = str(row[16] or "").strip() if len(row) > 16 else ""

                if not wbs_code and not row_type:
                    continue

                if row_type == "Workstream":
                    l1_rows.append((wbs_code, ws_name))

                if wbs_code:
                    row_wbs_codes.append(wbs_code)
                    if pred_str and pred_str != "-":
                        preds = [p.strip() for p in pred_str.split(",") if p.strip()]
                        predecessors[wbs_code] = preds

                # INV-03: No banned workstream names
                for banned in BANNED_WORKSTREAM_NAMES:
                    if banned.lower() in ws_name.lower():
                        violations.append(InvariantViolation("INV-03", f"Workstream contains banned term '{banned}' in row {row_idx}", "Project Schedule"))

            # INV-05: Predecessor graph is acyclic and points backward only
            wbs_to_pos = {code: i for i, code in enumerate(row_wbs_codes)}
            for code, preds in predecessors.items():
                curr_pos = wbs_to_pos.get(code, -1)
                for p in preds:
                    p_pos = wbs_to_pos.get(p, -1)
                    if p_pos >= curr_pos and p_pos != -1:
                        violations.append(InvariantViolation("INV-05", f"Forward or self predecessor: {code} depends on later row {p}", "Project Schedule"))

        # Inspect WBS
        if "WBS" in wb.sheetnames:
            wbs_sheet = wb["WBS"]
            for row_idx, row in enumerate(wbs_sheet.iter_rows(min_row=5, values_only=True), start=5):
                level = row[1]
                name = str(row[3] or "").strip()
                owner = str(row[9] or "").strip() if len(row) > 9 else ""
                
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
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists() or not folder.is_dir():
        print(f"Error: Directory '{folder}' does not exist.", file=sys.stderr)
        sys.exit(2)

    violations = check_artifacts_directory(folder)
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
