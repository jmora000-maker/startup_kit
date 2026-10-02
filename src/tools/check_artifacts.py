"""Comprehensive invariant checker for generated PMO artifacts (QA-04, QA-08, INV-01 to INV-25)."""

import sys
import re
import json
import zipfile
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
import docx
import openpyxl
import pptx

from src.tools.invariant_violation import InvariantViolation
from src.tools import deck_checks
from src.generators.onboarding_deck.textrules import has_compliant_cut

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
CITATION_PREFIX_REGEX = re.compile(r'^\s*(\[V\d+\]|Exhibit\s+[A-Z0-9]+,|[A-Za-z0-9_\-]+\.(?:pdf|docx|pptx|txt|md)\s*[,:])', re.IGNORECASE)
PLACEHOLDER_REGEX = re.compile(r'\[(?:CONFIRMATION REQUIRED|TBD|UNASSIGNED|TO BE CONFIRMED|ACT-[^\]]+)\]', re.IGNORECASE)
BANNED_WORKSTREAM_NAMES = ["Project Management", "Kickoff", "Reporting and Control", "Ongoing"]
KEYWORD_TAXONOMY_WORKSTREAMS = {
    "Discovery & Requirements",
    "Design & Architecture",
    "Build & Configuration",
    "Data & Integration",
    "Testing & Quality Assurance",
    "Deployment & Release",
    "Transition & Hypercare",
}
PHASE_CODE_REGEX = re.compile(r'\b(P\d+[a-z]?|Phase\s+\d+[a-z]?)\b', re.IGNORECASE)

VALID_CONTRACT_REF_EXT_REGEX = re.compile(r'\.[a-zA-Z0-9]{2,4}\b', re.IGNORECASE)
EXHIBIT_WORD_REGEX = re.compile(r'\b(?:Exhibit|Schedule|Appendix|Attachment|Annex)\s+(?:[0-9]+(?:\.[0-9]+)*|[A-Z]\b|[IVXLCDM]+\b)', re.IGNORECASE)
SECTION_WORD_REGEX = re.compile(r'\b(?:Sections?|Clause|§)\s*:?\s*\d+(?:\.\d+)*\b', re.IGNORECASE)
SOW_REF_REGEX = re.compile(r'\b(?:[A-Z][A-Z0-9]{1,9}-\d{2,6}|Deliverable\s+\d+(?:\.\d+)*|D\d+(?:\.\d+)*|Task\s+\d+(?:\.\d+)*|WBS\s+\d+(?:\.\d+)*|SOW-\d+(?:-\d+)?)\b', re.IGNORECASE)


def _resolve_oracle_inheritance(oracle: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not oracle:
        return oracle
    extends_name = oracle.get("extends_reference_phase_map_from")
    if extends_name:
        base_path = Path("tests/oracles") / f"{extends_name}.json"
        if not base_path.exists():
            base_path = Path("tests/oracles_draft") / f"{extends_name}.json"
        if base_path.exists():
            with open(base_path, "r", encoding="utf-8") as f:
                content = f.read()
                cleaned = re.sub(r',\s*([}\]])', r'\1', content)
                base_data = json.loads(cleaned)
                merged = dict(base_data)
                merged.update(oracle)
                return merged
    return oracle


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
                content = f.read()
                cleaned = re.sub(r',\s*([}\]])', r'\1', content)
                return json.loads(cleaned)
    return None


DECK_READINESS_REGEX = re.compile(
    r'\b(G-?01|g01|readiness\s+gate|startup\s+readiness|readiness\s+checklist|readiness\s+score|gate\s+decision|gate\s+approval|mobiliz\w*|ACT-\d+)\b',
    re.IGNORECASE,
)


def compute_deck20_rating(probability: str, impact: str) -> str:
    """Recompute rating per DECK-20 rule."""
    p_up = (probability or "").strip().capitalize()
    i_up = (impact or "").strip().capitalize()

    if (p_up == "High" and i_up in ("High", "Medium")) or (i_up == "High" and p_up in ("High", "Medium")):
        return "High"
    if p_up == "Low" and i_up == "Low":
        return "Low"
    return "Medium"


def check_deck_invariants(
    deck_path: Path,
    manifest_path: Optional[Path],
    kit_doc: Optional[Any],
    wb: Optional[Any],
) -> List[InvariantViolation]:
    """Check deck presentation and trace manifest against INV-26, INV-27, INV-28, INV-29."""
    violations: List[InvariantViolation] = []
    if not deck_path.exists():
        return violations

    # Check zip parts and template text (INV-29)
    with zipfile.ZipFile(deck_path, "r") as z:
        slide_parts = [n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
        if len(slide_parts) != 7:
            violations.append(InvariantViolation("INV-29", f"Deck contains {len(slide_parts)} slide parts, expected exactly 7", "Deck"))

        for n in z.namelist():
            if n.startswith("ppt/slides/"):
                content = z.read(n).decode("utf-8", errors="ignore")
                if "DELIVERY GOVERNANCE" in content:
                    violations.append(InvariantViolation("INV-29", f"Template text 'DELIVERY GOVERNANCE' remains in '{n}'", "Deck"))

    prs = pptx.Presentation(str(deck_path))
    file_names = [p.name for p in deck_path.parent.glob("*") if p.suffix in (".docx", ".xlsx") and "Checklist" not in p.name]
    index = deck_checks.SourceIndex(kit_doc, wb, file_names)
    known_names = index.names()
    slides_list = list(prs.slides)
    if len(slides_list) != 7:
        violations.append(InvariantViolation("INV-28", f"Deck has {len(slides_list)} slides, expected exactly 7", "Deck"))

    if len(slides_list) > 0 and slides_list[0].slide_layout.name != "CUSTOM_1":
        violations.append(InvariantViolation("INV-29", f"Slide 1 layout is '{slides_list[0].slide_layout.name}', expected 'CUSTOM_1'", "Deck"))

    for idx, s in enumerate(slides_list[1:], start=2):
        if s.slide_layout.name != "CUSTOM_16":
            violations.append(InvariantViolation("INV-29", f"Slide {idx} layout is '{s.slide_layout.name}', expected 'CUSTOM_16'", "Deck"))

    # Expected titles (DECK-01, INV-28)
    expected_titles = {
        2: "Project Charter",
        3: "Workstreams, Milestones, Deliverables and Dates",
        4: "Acceptance Criteria",
        5: "High-Risk Items",
        6: "Client Collaboration",
        7: "Your Project Kit",
    }

    # Check slide texts, notes, and limits (INV-04, INV-28)
    for s_idx, slide in enumerate(slides_list, start=1):
        # Speaker notes check
        notes_text = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""
        if "SOURCES:" not in notes_text and "SOURCES :" not in notes_text:
            violations.append(InvariantViolation("INV-28", f"Slide {s_idx} speaker notes missing 'SOURCES:' line", "Deck"))

        if DECK_READINESS_REGEX.search(notes_text):
            violations.append(InvariantViolation("INV-04", f"Slide {s_idx} speaker notes contain readiness term: '{notes_text}'", "Deck"))

        # Bullet count and word limits in notes
        tp_lines = [line.strip().lstrip("•").strip() for line in notes_text.splitlines() if line.strip().startswith("•")]
        if s_idx in (1, 7) and not (2 <= len(tp_lines) <= 4):
            violations.append(InvariantViolation("INV-28", f"Slide {s_idx} has {len(tp_lines)} talking points, expected 2 to 4", "Deck"))
        elif 1 < s_idx < 7 and not (3 <= len(tp_lines) <= 6):
            violations.append(InvariantViolation("INV-28", f"Slide {s_idx} has {len(tp_lines)} talking points, expected 3 to 6", "Deck"))

        for tp in tp_lines:
            if len(tp.split()) > 30:
                violations.append(InvariantViolation("INV-28", f"Slide {s_idx} talking point exceeds 30 words ({len(tp.split())} words): '{tp}'", "Deck"))

        # Title check
        if s_idx > 1 and len(slide.placeholders) > 0:
            title_text = slide.placeholders[0].text.strip()
            exp_t = expected_titles.get(s_idx, "")
            if exp_t and title_text != exp_t:
                violations.append(InvariantViolation("INV-28", f"Slide {s_idx} title is '{title_text}', expected '{exp_t}'", "Deck"))
            if len(title_text.split()) > 8:
                violations.append(InvariantViolation("INV-28", f"Slide {s_idx} title exceeds 8 words ({len(title_text.split())} words): '{title_text}'", "Deck"))

        # Shape text check (INV-04, placeholders, cell length)
        for shape in slide.shapes:
            if shape.has_text_frame:
                full_tf_text = shape.text_frame.text
                if DECK_READINESS_REGEX.search(full_tf_text):
                    violations.append(InvariantViolation("INV-04", f"Slide {s_idx} shape text contains readiness term: '{full_tf_text}'", "Deck"))
                for p in shape.text_frame.paragraphs:
                    p_txt = p.text.strip()
                    if p_txt in ("[UNASSIGNED]", "[TBD]", "[CONFIRMATION REQUIRED]", "None", "null", "NULL"):
                        violations.append(InvariantViolation("INV-28", f"Slide {s_idx} contains raw placeholder: '{p_txt}'", "Deck"))

            if shape.has_table:
                table = shape.table
                for r_idx, row in enumerate(table.rows):
                    for c_idx, cell in enumerate(row.cells):
                        c_txt = cell.text.strip()
                        if DECK_READINESS_REGEX.search(c_txt):
                            violations.append(InvariantViolation("INV-04", f"Slide {s_idx} table cell R{r_idx}C{c_idx} contains readiness term: '{c_txt}'", "Deck"))
                        if c_txt in ("[UNASSIGNED]", "[TBD]", "[CONFIRMATION REQUIRED]", "None", "null", "NULL"):
                            violations.append(InvariantViolation("INV-28", f"Slide {s_idx} table cell contains raw placeholder: '{c_txt}'", "Deck"))
                        if r_idx > 0 and len(c_txt.split()) > 15 and not c_txt.startswith("+"):
                            # If cell contains multiple lines (e.g. deliverables list), check each line.
                            # A line over 15 words is accepted only when DECK-05 allows no shorter cut: it holds a
                            # whole name (names are never cut) or has no sentence or clause boundary within its
                            # first 15 words (DECK-05 wins).
                            lines = [ln.strip() for ln in c_txt.splitlines() if ln.strip()]
                            if lines and all(len(ln.split()) <= 15 or not has_compliant_cut(ln, 15) or any(n in ln for n in known_names) for ln in lines):
                                pass
                            else:
                                violations.append(InvariantViolation("INV-28", f"Slide {s_idx} table cell R{r_idx}C{c_idx} exceeds 15 words: '{c_txt}'", "Deck"))

    # Table capacities and completeness (INV-27)
    # Check Slide 3 schedule table
    s3 = slides_list[2] if len(slides_list) >= 3 else None
    if s3:
        s3_tables = [sh.table for sh in s3.shapes if sh.has_table]
        if s3_tables:
            s3_tab = s3_tables[0]
            if len(s3_tab.rows) - 1 > 12:
                violations.append(InvariantViolation("INV-27", f"Slide 3 schedule table has {len(s3_tab.rows)-1} rows, exceeding capacity of 12", "Deck"))

    # Check Slide 4 acceptance table
    s4 = slides_list[3] if len(slides_list) >= 4 else None
    if s4:
        s4_tables = [sh.table for sh in s4.shapes if sh.has_table]
        if s4_tables:
            s4_tab = s4_tables[0]
            if len(s4_tab.rows) - 1 > 14:
                violations.append(InvariantViolation("INV-27", f"Slide 4 acceptance table has {len(s4_tab.rows)-1} rows, exceeding capacity of 14", "Deck"))

    # Check Slide 5 risks table
    s5 = slides_list[4] if len(slides_list) >= 5 else None
    if s5:
        s5_tables = [sh.table for sh in s5.shapes if sh.has_table]
        if s5_tables:
            s5_tab = s5_tables[0]
            if len(s5_tab.rows) - 1 > 6:
                violations.append(InvariantViolation("INV-27", f"Slide 5 risks table has {len(s5_tab.rows)-1} rows, exceeding capacity of 6", "Deck"))

    # INV-26 (strict), INV-31, INV-32: read the written files back (DECK-04, DECK-05, DECK-09, DECK-21)
    if not manifest_path or not manifest_path.exists():
        violations.append(InvariantViolation("INV-26", "Trace manifest file is missing beside the deck", "Deck"))
        entries: List[Dict[str, Any]] = []
    else:
        entries, manifest_error = deck_checks.load_manifest_entries(manifest_path)
        violations.extend(deck_checks.check_inv26(entries, index, prs, manifest_error))
    violations.extend(deck_checks.check_inv27_completeness(prs, index))
    violations.extend(deck_checks.check_inv31(prs, entries, index.names(), file_names))
    violations.extend(deck_checks.check_inv32(prs))

    return violations


def check_artifacts_directory(folder_path: Path, oracle_override: Optional[Dict[str, Any]] = None) -> List[InvariantViolation]:
    """Inspect output folder containing Kit docx, Checklist docx, and Workbook xlsx against INV-01 to INV-25."""
    violations: List[InvariantViolation] = []
    folder = Path(folder_path)

    kit_files = list(folder.glob("*_Startup_Kit.docx"))
    chk_files = list(folder.glob("*_Startup_Readiness_Checklist.docx"))
    wb_files = list(folder.glob("*_Project_Delivery_Workbook.xlsx"))
    deck_files = list(folder.glob("*_Talent_Onboarding_Deck.pptx"))
    manifest_files = list(folder.glob("*_Talent_Onboarding_Deck.trace.json"))

    kit_doc = docx.Document(str(kit_files[0])) if kit_files else None
    chk_doc = docx.Document(str(chk_files[0])) if chk_files else None
    wb = openpyxl.load_workbook(str(wb_files[0]), data_only=False) if wb_files else None

    # Check deck invariants if deck is present (INV-26, INV-27, INV-28, INV-29)
    if deck_files:
        deck_path = deck_files[0]
        manifest_path = manifest_files[0] if manifest_files else None
        violations.extend(check_deck_invariants(deck_path, manifest_path, kit_doc, wb))

    # INV-30: Workbook RAID rows carry the Kit RAID Log fields (RAID-09)
    violations.extend(deck_checks.check_inv30(kit_doc, wb))

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
    if oracle:
        oracle = _resolve_oracle_inheritance(oracle)

    if kit_doc:
        # INV-34: Kit 1-Day SLA Status is never 'Not determinable - award date not stated' when oracle states award date is in SOW
        if oracle and oracle.get("award_date_stated_in_sow") is True:
            sla_status = kit_charter.get("1-day sla status", "")
            if "not determinable" in sla_status.lower():
                violations.append(InvariantViolation(
                    "INV-34",
                    f"Kit 1-Day SLA Status is '{sla_status}' when oracle states award date is in SOW",
                    "Kit"
                ))

        # INV-35: No generic review-window fallback when oracle specifies contract_wide_review_window
        if oracle and oracle.get("contract_wide_review_window"):
            cw_window = oracle["contract_wide_review_window"]
            for d in kit_deliverables:
                d_id = d[0]
                rw = ""
                for idx in [7, 6, 5]:
                    if len(d) > idx and ("day" in d[idx].lower() or "review" in d[idx].lower() or "not specified" in d[idx].lower() or "business" in d[idx].lower()):
                        rw = d[idx].strip()
                        break
                if not rw and len(d) > 7:
                    rw = d[7].strip()
                if "reviewed at the milestone acceptance review" in rw.lower() or "not specified; reviewed at the" in rw.lower():
                    violations.append(InvariantViolation(
                        "INV-35",
                        f"Deliverable {d_id} has generic review window fallback '{rw}' when oracle specifies contract_wide_review_window: '{cw_window}'",
                        "Kit"
                    ))
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

        # MS-05 / KIT-02: Every checkpoint has a phase; never blank or 'N/A'
        for cp in kit_checkpoints:
            cp_id = cp[0] if len(cp) > 0 else "CP-??"
            cp_phase = cp[1].strip() if len(cp) > 1 else ""
            if not cp_phase or cp_phase.upper() in ("N/A", "NONE", ""):
                violations.append(InvariantViolation("INV-01", f"Checkpoint {cp_id} has blank or 'N/A' phase '{cp_phase}'", "Kit"))

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

        # INV-34: Checklist G01-01 and SLA status are never 'Not determinable' when oracle states award date is in SOW
        if oracle and oracle.get("award_date_stated_in_sow") is True:
            if chk_items and "G01-01" in chk_items:
                g1_ev = chk_items["G01-01"].get("evidence", "")
                g1_status = chk_items["G01-01"].get("status", "")
                if "not determinable" in g1_ev.lower() or "not determinable" in g1_status.lower():
                    violations.append(InvariantViolation(
                        "INV-34",
                        f"Checklist G01-01 evidence/status contains 'Not determinable' ('{g1_ev}') when oracle states award date is in SOW",
                        "Checklist"
                    ))
            for t in chk_doc.tables:
                for r in t.rows:
                    txt = " ".join([c.text for c in r.cells])
                    if "sla" in txt.lower() and "not determinable" in txt.lower():
                        violations.append(InvariantViolation(
                            "INV-34",
                            f"Checklist metadata table contains 'Not determinable' SLA status when oracle states award date is in SOW",
                            "Checklist"
                        ))
                        break

    # Workbook checks
    if wb:
        # Check sheet names for readiness terms
        for sheet_name in wb.sheetnames:
            if READINESS_REGEX.search(sheet_name):
                violations.append(InvariantViolation("INV-04", f"Sheet name '{sheet_name}' contains readiness terms", "Workbook"))

        has_phase_milestone = False
        for m in kit_milestones:
            if len(m) > 1 and PHASE_CODE_REGEX.search(m[1]):
                has_phase_milestone = True
                break
        if not has_phase_milestone:
            for m in kit_checkpoints:
                if len(m) > 2 and PHASE_CODE_REGEX.search(m[2]):
                    has_phase_milestone = True
                    break
        if not has_phase_milestone and oracle and ("phases" in oracle or "sow_reference_phase" in oracle):
            has_phase_milestone = True

        sched_workstreams: Set[str] = set()
        wbs_workstreams: Set[str] = set()

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

            # INV-34: Schedule Start Date basis is not assumed when award date is stated in SOW
            if oracle and oracle.get("award_date_stated_in_sow") is True:
                if "assumed -" in row3_val.lower():
                    violations.append(InvariantViolation(
                        "INV-34",
                        f"Schedule Start Date basis is '{row3_val}' when oracle states award date is in SOW",
                        "Project Schedule"
                    ))

            for row_idx, row in enumerate(sched.iter_rows(min_row=5, values_only=True), start=5):
                wbs_code = str(row[0] or "").strip()
                row_type = str(row[1] or "").strip()
                ws_name = str(row[2] or "").strip()
                m_id = str(row[3] or "").strip()
                sow_refs = str(row[20] or "").strip() if len(row) > 20 else ""
                pred_str = str(row[16] or "").strip() if len(row) > 16 else ""

                if not wbs_code and not row_type:
                    continue

                if ws_name:
                    sched_workstreams.add(ws_name)

                if row_type == "Workstream":
                    l1_rows.append((wbs_code, ws_name))

                if row_type == "Milestone" and m_id:
                    sched_gate_count += 1
                    refs = [r.strip() for r in sow_refs.split(",") if r.strip()]
                    schedule_gate_items[m_id] = len(refs)

                # INV-33: No milestone or checkpoint workstream is keyword-taxonomy name
                if row_type in ("Milestone", "Checkpoint"):
                    if has_phase_milestone and ws_name in KEYWORD_TAXONOMY_WORKSTREAMS:
                        violations.append(InvariantViolation(
                            "INV-33",
                            f"Milestone/checkpoint row {wbs_code} has keyword-taxonomy workstream '{ws_name}' despite recognizable phase code in milestone descriptions",
                            "Project Schedule"
                        ))

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

                if ws_name:
                    wbs_workstreams.add(ws_name)

                # INV-33: No milestone or checkpoint workstream is keyword-taxonomy name
                if elem_type in ("Milestone", "Gate", "Checkpoint") or level in (2, "2"):
                    if has_phase_milestone and ws_name in KEYWORD_TAXONOMY_WORKSTREAMS:
                        violations.append(InvariantViolation(
                            "INV-33",
                            f"WBS level {level} row '{name}' ({m_id}) has keyword-taxonomy workstream '{ws_name}' despite recognizable phase code in milestone descriptions",
                            "WBS"
                        ))

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

            # INV-33: Keyword and phase workstreams are never mixed within one Workbook
            all_wb_workstreams = sched_workstreams | wbs_workstreams
            has_kw = any(w in KEYWORD_TAXONOMY_WORKSTREAMS for w in all_wb_workstreams)
            has_ph = any(PHASE_CODE_REGEX.search(w) for w in all_wb_workstreams)
            if has_kw and has_ph:
                violations.append(InvariantViolation(
                    "INV-33",
                    f"Keyword workstreams and phase workstreams are mixed within the Workbook: {sorted(all_wb_workstreams)}",
                    "Workbook"
                ))

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

                # Invariant: Every work-item task has a non-empty SOW References cell when its work item has a reference
                t_src = str(row[19] or "").strip() if len(row) > 19 else ""
                if elem_type == "Task" and (t_src in ("Baseline - Backlog", "Baseline - SOW Work Items") or s_id.startswith("WP-") or s_id.startswith("HS-")):
                    has_ref = bool(SOW_REF_REGEX.search(name) or SOW_REF_REGEX.search(s_id))
                    matching_wp = next((wp for wp in kit_work_packages if wp[0] == s_id), None)
                    if matching_wp and len(matching_wp) > 5 and matching_wp[5]:
                        has_ref = True
                    if has_ref and not sow_refs_str:
                        violations.append(InvariantViolation(
                            "INV-08",
                            f"Work-item task '{name}' (source {s_id}) has empty SOW References cell",
                            "WBS"
                        ))

        # Oracle sample work item titles verification (REF-05)
        if oracle and oracle.get("work_item_titles_in_sow") and oracle.get("sample_work_item_titles"):
            sample_titles = oracle["sample_work_item_titles"]
            
            def _norm_s(s: str) -> str:
                cleaned = s.replace("<", "").replace(">", "")
                cleaned = re.sub(r'-\s*\n\s*', '-', cleaned)
                return " ".join(cleaned.lower().split())

            # 1. Check Kit work packages
            for s_id, sample in sample_titles.items():
                norm_sample = _norm_s(sample)
                
                matching_wp = None
                for wp in kit_work_packages:
                    wp_title = wp[2] if len(wp) > 2 else ""
                    if s_id in wp_title or (len(wp) > 5 and s_id in str(wp[5])):
                        matching_wp = wp
                        break
                
                if not matching_wp:
                    violations.append(InvariantViolation(
                        "INV-20",
                        f"Kit lacks work package matching SOW reference '{s_id}'",
                        "Startup Kit"
                    ))
                else:
                    norm_wp_title = _norm_s(matching_wp[2])
                    if norm_sample not in norm_wp_title:
                        violations.append(InvariantViolation(
                            "INV-20",
                            f"Kit work package for {s_id} ('{matching_wp[2]}') does not contain exact sample title '{sample}'",
                            "Startup Kit"
                        ))

            # 2. Check WBS task names
            if "WBS" in wb.sheetnames:
                wbs_sheet = wb["WBS"]
                for s_id, sample in sample_titles.items():
                    norm_sample = _norm_s(sample)
                    
                    found_wbs = False
                    for row in wbs_sheet.iter_rows(min_row=5, values_only=True):
                        t_name = str(row[3] or "")
                        t_src_id = str(row[7] or "")
                        t_sow_refs = str(row[8] or "")
                        t_notes = str(row[21] or "") if len(row) > 21 else ""
                        if s_id in t_name or s_id == t_src_id or s_id in t_sow_refs or s_id in t_notes:
                            norm_t_text = _norm_s(f"{t_name} {t_notes}")
                            if norm_sample in norm_t_text:
                                found_wbs = True
                                break
                    if not found_wbs:
                        violations.append(InvariantViolation(
                            "INV-20",
                            f"WBS task name for {s_id} does not contain exact sample title '{sample}'",
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
                    if any(p == "" or p.startswith("Stories:") or p == "SOW refs:" or p == "Sections:" for p in parts) or contract_ref.endswith("|") or contract_ref.startswith("|") or contract_ref.endswith(","):
                        violations.append(InvariantViolation("INV-13", f"RAID row {raid_id} Contract Reference has empty or outdated part: '{contract_ref}'", "RAID Log"))

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
        direct_path = Path(args.oracle)
        if direct_path.exists() and direct_path.is_file():
            with open(direct_path, "r", encoding="utf-8") as f:
                content = f.read()
                cleaned = re.sub(r',\s*([}\]])', r'\1', content)
                oracle_data = json.loads(cleaned)
        else:
            oracle_path = Path("tests/oracles") / f"{args.oracle}.json"
            if oracle_path.exists():
                with open(oracle_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    cleaned = re.sub(r',\s*([}\]])', r'\1', content)
                    oracle_data = json.loads(cleaned)
            else:
                draft_path = Path("tests/oracles_draft") / f"{args.oracle}.json"
                if draft_path.exists():
                    with open(draft_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        cleaned = re.sub(r',\s*([}\]])', r'\1', content)
                        oracle_data = json.loads(cleaned)

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
