"""Microsoft Word (.docx) report generator implementing IDocumentWriter with Section 4 Three-Layer structure."""

import re
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX

from src.core.interfaces import IDocumentWriter
from src.core.models import StartupKitBaseline, ActionRequiredItem
from src.config import sanitize_report_text
from src.generators.formatting import (
    add_section_heading,
    add_callout_box,
    style_table,
    set_cell_background,
    set_cell_margins,
    format_cell_text_and_highlight,
    ACTION_TAG_REGEX,
    COLOR_NAVY_HEX,
    COLOR_PRIMARY_BLUE_HEX,
    COLOR_LIGHT_BG_HEX,
    COLOR_WARNING_BG_HEX,
)
from src.generators.checklist import G01ChecklistRenderer

logger = logging.getLogger(__name__)


# Bracketed placeholder tokens only (e.g. [TBD], [TO BE CONFIRMED], [CONFIRMATION REQUIRED]) (v4 B6)
BRACKETED_PLACEHOLDER_REGEX = re.compile(
    r'\[\s*(?:CONFIRMATION\s*REQUIRED|CONFIRMATION_REQUIRED|UNDEFINED|UNASSIGNED(?:\s*-\s*TO\s*BE\s*CONFIRMED)?|TO\s*BE\s*CONFIRMED|TO\s*BE\s*DETERMINED|TBD|NOT\s*STATED|PENDING|NEEDS\s*ALIGNMENT|STAFFING\s*REQUIRED)(?:\s*:[^\]\n]*)?\s*\]',
    re.IGNORECASE
)

# Whole-cell bare placeholder text
WHOLE_CELL_PLACEHOLDER_REGEX = re.compile(
    r'^\s*(?:CONFIRMATION\s*REQUIRED|CONFIRMATION_REQUIRED|UNDEFINED|UNASSIGNED(?:\s*-\s*TO\s*BE\s*CONFIRMED)?|TO\s*BE\s*CONFIRMED|TO\s*BE\s*DETERMINED|TBD|NOT\s*STATED|PENDING|NEEDS\s*ALIGNMENT|STAFFING\s*REQUIRED)\s*$',
    re.IGNORECASE
)

PLACEHOLDER_REGEX = BRACKETED_PLACEHOLDER_REGEX


def is_placeholder_text(text: Optional[str]) -> bool:
    """Check if text contains whole-line or bracketed placeholder tokens (v4 B6)."""
    if not text:
        return False
    lines = str(text).split('\n')
    for line in lines:
        bare = re.sub(r'^\s*(?:[•\-\*]|\d+[\.\)])\s*', '', line).strip()
        if WHOLE_CELL_PLACEHOLDER_REGEX.match(bare) or BRACKETED_PLACEHOLDER_REGEX.search(bare):
            return True
    return False


def strip_trailing_unbalanced_brackets(text: str) -> str:
    """Strip trailing whitespace, colons, dashes, and unbalanced closing brackets/parentheses (v4 B6)."""
    s = text.rstrip()
    while s:
        last_char = s[-1]
        if last_char in " \t\r\n:-—–":
            s = s[:-1].rstrip()
        elif last_char == ')':
            if s.count('(') < s.count(')'):
                s = s[:-1].rstrip()
            else:
                break
        elif last_char == ']':
            if s.count('[') < s.count(']'):
                s = s[:-1].rstrip()
            else:
                break
        else:
            break
    return s


def format_cell_with_action(
    cell,
    text: str,
    action: Optional[Union[ActionRequiredItem, List[ActionRequiredItem]]] = None,
    is_warning: bool = False,
    fallback_checklist_id: Optional[str] = None,
    fallback_action_desc: Optional[str] = None,
    fallback_delta: float = 2.0,
) -> None:
    """Formats cell text, cleanly subsumes raw placeholder tokens, attaches exactly ONE [ACT-XX: Remediation (+Delta%)], and applies amber fill."""
    if text is None:
        text = ""

    raw_text = sanitize_report_text(str(text).strip())
    # Strip any preexisting/corrupted action badges or residual recovery markers
    cleaned_raw = re.sub(r'\[ACT(?:-REQ)?-.*?\+\d+(?:\.\d+)?%\s*Recovery\]', '', raw_text, flags=re.IGNORECASE)
    cleaned_raw = re.sub(r'\[ACT-[^\]]+\]', '', cleaned_raw, flags=re.IGNORECASE)
    cleaned_raw = re.sub(r'\[ACT-REQ-[^\]]+\]', '', cleaned_raw, flags=re.IGNORECASE)
    cleaned_raw = re.sub(r'\(\+\d+(?:\.\d+)?%\s*Recovery\)?\]?', '', cleaned_raw, flags=re.IGNORECASE).strip()

    target_actions: List[ActionRequiredItem] = []
    if isinstance(action, list):
        target_actions = [a for a in action if a is not None]
    elif action is not None:
        target_actions = [action]

    has_bracketed_placeholder = bool(BRACKETED_PLACEHOLDER_REGEX.search(cleaned_raw))
    is_whole_placeholder = bool(WHOLE_CELL_PLACEHOLDER_REGEX.match(cleaned_raw.strip()))
    is_bare_placeholder = (
        is_whole_placeholder
        or cleaned_raw.upper() in (
            "UNASSIGNED", "[UNASSIGNED]", "TBD", "[TBD]", "PENDING", "[UNDEFINED]",
            "CONFIRMATION REQUIRED", "[CONFIRMATION REQUIRED]", "STAFFING REQUIRED",
            "TO BE DETERMINED", "[TO BE DETERMINED]", "TO BE CONFIRMED", "[TO BE CONFIRMED]",
            "NOT STATED", "[NOT STATED]"
        )
    )

    # Clean lines and remove orphaned bullet points, colons, or empty placeholders
    lines = cleaned_raw.split('\n')
    cleaned_lines = []
    for line in lines:
        has_bullet = bool(re.match(r'^\s*(?:[•\-\*]|\d+[\.\)])\s*', line))
        # Strip leading bullet marker first to check whole-line placeholder
        bare_line = re.sub(r'^\s*(?:[•\-\*]|\d+[\.\)])\s*', '', line).strip()
        if WHOLE_CELL_PLACEHOLDER_REGEX.match(bare_line):
            c_line = ""
        else:
            c_line = BRACKETED_PLACEHOLDER_REGEX.sub('', bare_line).strip()
        # Clean leading colons/dashes
        c_line = re.sub(r'^[\s\:\—\(\)\[\]]+', '', c_line).strip()
        c_line = strip_trailing_unbalanced_brackets(c_line)
        if c_line:
            if has_bullet:
                cleaned_lines.append(f"• {c_line}")
            else:
                cleaned_lines.append(c_line)

    cleaned_body = "\n".join(cleaned_lines).strip()

    if target_actions:
        is_warning = True
        act_tags = " ".join(f"[{a.action_id}: {a.required_action} (+{a.score_recovery_delta:.1f}% Recovery)]" for a in target_actions)
        formatted_text = f"{cleaned_body} {act_tags}" if cleaned_body else act_tags
    elif is_bare_placeholder or is_warning:
        is_warning = True
        act_id = f"ACT-REQ-{fallback_checklist_id.replace('G01-', '')}" if fallback_checklist_id else "ACT-REQ"
        action_desc = fallback_action_desc or "Confirm requirement and assign owner prior to kickoff"
        fallback_tag = f"[{act_id}: {action_desc} (+{fallback_delta:.1f}% Recovery)]"
        formatted_text = f"{cleaned_body} {fallback_tag}" if cleaned_body else fallback_tag
    else:
        formatted_text = cleaned_body

    format_cell_text_and_highlight(cell, formatted_text, is_warning=is_warning)


def find_cell_action(
    baseline: StartupKitBaseline,
    table_title: str,
    column_header: str,
    entity_id: Optional[str] = None,
    linked_action_id: Optional[str] = None,
    used_actions: Optional[set] = None,
) -> Optional[ActionRequiredItem]:
    """Find a single unique ActionRequiredItem targeting a specific cell to enforce strict 1-to-1 traceability without broadcasting."""
    if not baseline.action_required_items:
        return None

    if used_actions is None:
        used_actions = set()

    clean_tbl = (table_title or "").lower().strip()
    clean_col = (column_header or "").lower().strip()
    clean_ent = (entity_id or "").lower().strip()

    # 1. Match by linked_action_id first
    if linked_action_id:
        for a in baseline.action_required_items:
            if a.action_id == linked_action_id and a.action_id not in used_actions:
                act_col = (a.target_column_header or "").lower().strip()
                if not act_col or act_col == "general" or act_col in clean_col or clean_col in act_col:
                    used_actions.add(a.action_id)
                    return a

    # 2. Strict Match by entity_id, table_title, and column_header
    if clean_ent:
        for a in baseline.action_required_items:
            if a.action_id in used_actions:
                continue
            act_ent = (a.target_entity_id or "").lower().strip()
            if not act_ent:
                continue

            ent_match = (act_ent == clean_ent or act_ent in clean_ent or clean_ent in act_ent)
            if not ent_match:
                continue

            act_tbl = (a.target_table_title or "").lower().strip()
            tbl_match = (not act_tbl or act_tbl in clean_tbl or clean_tbl in act_tbl)
            if not tbl_match:
                continue

            act_col = (a.target_column_header or "").lower().strip()
            col_match = (not act_col or act_col == "general" or act_col in clean_col or clean_col in act_col)
            if not col_match:
                continue

            used_actions.add(a.action_id)
            return a

        return None

    # 3. Match for non-entity table cells (table_title and column_header)
    if clean_tbl and clean_col:
        for a in baseline.action_required_items:
            if a.action_id in used_actions:
                continue
            if a.target_entity_id:
                continue

            act_tbl = (a.target_table_title or "").lower().strip()
            tbl_match = (not act_tbl or act_tbl in clean_tbl or clean_tbl in act_tbl)
            if not tbl_match:
                continue

            act_col = (a.target_column_header or "").lower().strip()
            col_match = (not act_col or act_col == "general" or act_col in clean_col or clean_col in act_col)
            if not col_match:
                continue

            used_actions.add(a.action_id)
            return a

        return None

    return None


def find_all_cell_actions(
    baseline: StartupKitBaseline,
    table_title: str,
    column_header: str,
    entity_id: Optional[str] = None,
    linked_action_id: Optional[str] = None,
    used_actions: Optional[set] = None,
) -> List[ActionRequiredItem]:
    """Find all matching ActionRequiredItems for a cell."""
    matched = []
    while True:
        act = find_cell_action(
            baseline,
            table_title=table_title,
            column_header=column_header,
            entity_id=entity_id,
            linked_action_id=linked_action_id if not matched else None,
            used_actions=used_actions
        )
        if act is None:
            break
        matched.append(act)
    return matched


def sanitize_filename(name: str) -> str:
    """Sanitize project name for safe filename creation."""
    s = re.sub(r'[^a-zA-Z0-9_\- ]+', '', name).strip()
    return s.replace(' ', '_') or "Project"


class DocxGenerator(IDocumentWriter):
    """Generates the standardized Toptal PMO Startup Kit Word documents following Section 4 structure."""

    def __init__(self, checklist_renderer: G01ChecklistRenderer = None):
        self.checklist_renderer = checklist_renderer or G01ChecklistRenderer()

    def _resolve_output_paths(self, baseline: StartupKitBaseline, output_path: Path) -> tuple[Path, Path]:
        """Resolve output paths for both the Startup Kit and Startup Readiness Checklist documents."""
        if output_path.suffix.lower() in (".docx", ".doc"):
            kit_file = output_path
            stem = output_path.stem
            suffix = output_path.suffix
            if stem.endswith("_Startup_Kit"):
                cl_stem = stem[:-12] + "_Startup_Readiness_Checklist"
            elif stem == "Startup_Kit":
                cl_stem = "Startup_Readiness_Checklist"
            elif stem.endswith("_Startup_Readiness_Checklist"):
                cl_stem = stem
                kit_stem = stem[:-28] + "_Startup_Kit"
                kit_file = output_path.with_name(f"{kit_stem}{suffix}")
            elif stem == "Startup_Readiness_Checklist":
                cl_stem = stem
                kit_file = output_path.with_name(f"Startup_Kit{suffix}")
            else:
                cl_stem = f"{stem}_Startup_Readiness_Checklist"
            checklist_file = output_path.with_name(f"{cl_stem}{suffix}")
        else:
            clean_name = sanitize_filename(baseline.project_name)
            kit_file = output_path / f"{clean_name}_Startup_Kit.docx"
            checklist_file = output_path / f"{clean_name}_Startup_Readiness_Checklist.docx"
        return kit_file, checklist_file

    def write_checklist_docx(self, baseline: StartupKitBaseline, output_path: Path) -> Path:
        """Render the Executive Readiness Gateway and G-01 Checklist into a standalone Word document."""
        if output_path.suffix.lower() in (".docx", ".doc"):
            if output_path.stem.endswith("_Startup_Kit") or output_path.stem == "Startup_Kit":
                _, target_file = self._resolve_output_paths(baseline, output_path)
            else:
                target_file = output_path
        else:
            _, target_file = self._resolve_output_paths(baseline, output_path)

        target_file.parent.mkdir(parents=True, exist_ok=True)
        doc = docx.Document()

        # Page setup
        for section in doc.sections:
            section.top_margin = Inches(1.0)
            section.bottom_margin = Inches(1.0)
            section.left_margin = Inches(1.0)
            section.right_margin = Inches(1.0)

        self.checklist_renderer.render(doc, baseline)
        doc.save(str(target_file))
        logger.info("Successfully generated Startup Readiness Checklist Word document at: %s", target_file)
        return target_file

    def write_documents(self, baseline: StartupKitBaseline, output_path: Path) -> tuple[Path, Path]:
        """Render both the Section 4 Startup Kit Word document and the second Startup Readiness Checklist document."""
        kit_file, checklist_file = self._resolve_output_paths(baseline, output_path)
        self.write_kit_docx(baseline, kit_file)
        self.write_checklist_docx(baseline, checklist_file)
        return kit_file, checklist_file

    def write_docx(self, baseline: StartupKitBaseline, output_path: Path) -> Path:
        """Render the complete Section 4 Startup Kit Word document and second Startup Readiness Checklist document, writing both to disk."""
        kit_file, checklist_file = self._resolve_output_paths(baseline, output_path)
        self.write_kit_docx(baseline, kit_file)
        self.write_checklist_docx(baseline, checklist_file)
        return kit_file

    def write_kit_docx(self, baseline: StartupKitBaseline, output_path: Path) -> Path:
        """Render the Section 4 Startup Kit Word document without the checklist table."""
        target_file, _ = self._resolve_output_paths(baseline, output_path)
        target_file.parent.mkdir(parents=True, exist_ok=True)

        doc = docx.Document()

        # Page setup
        for section in doc.sections:
            section.top_margin = Inches(1.0)
            section.bottom_margin = Inches(1.0)
            section.left_margin = Inches(1.0)
            section.right_margin = Inches(1.0)

        ctx = baseline.governance_context
        charter = baseline.charter
        talent_rec = baseline.talent_onboarding
        used_actions = set()

        # ==========================================
        # Document Header
        # ==========================================
        title_p = doc.add_paragraph()
        title_p.paragraph_format.space_before = Pt(0)
        title_p.paragraph_format.space_after = Pt(2)
        title_run = title_p.add_run("TOPTAL PMO STARTUP KIT")
        title_run.font.name = "Arial"
        title_run.font.size = Pt(22)
        title_run.bold = True
        title_run.font.color.rgb = RGBColor(15, 33, 55)

        subtitle_p = doc.add_paragraph()
        subtitle_p.paragraph_format.space_after = Pt(14)
        subtitle_run = subtitle_p.add_run(f"Project Baseline: {baseline.project_name}")
        subtitle_run.font.name = "Arial"
        subtitle_run.font.size = Pt(13)
        subtitle_run.font.color.rgb = RGBColor(37, 99, 235)

        # Metadata Header Table
        meta_table = doc.add_table(rows=5, cols=4)
        sla_status_str = "Met (Drafted <= 1 day)" if baseline.sla_met else "Breached (Exception Logged)"
        dm_meta = (ctx.delivery_manager if ctx and ctx.delivery_manager else None) or (charter.delivery_manager if charter and charter.delivery_manager else None) or (talent_rec.delivery_manager if talent_rec and talent_rec.delivery_manager else None) or "[UNASSIGNED - TO BE CONFIRMED]"
        tpm_meta = (ctx.talent_pm if ctx and ctx.talent_pm else None) or (charter.talent_pm if charter and charter.talent_pm else None) or (talent_rec.talent_pm if talent_rec and talent_rec.talent_pm else None) or "[UNASSIGNED - TO BE CONFIRMED]"
        pmo_meta = (ctx.pmo_lead if ctx and ctx.pmo_lead else None) or (charter.pmo_lead if charter and charter.pmo_lead else None) or (talent_rec.pmo_lead if talent_rec and talent_rec.pmo_lead else None) or (baseline.author_name if baseline.author_name else None) or "[UNASSIGNED - TO BE CONFIRMED]"
        client_meta = (ctx.client_name if ctx and ctx.client_name else None) or (charter.client_name if charter and charter.client_name else None) or "N/A"

        meta_data = [
            ("Project Name", baseline.project_name, "Client Sponsor", client_meta),
            ("Governance Tier", baseline.governance_tier, "Contract Type", baseline.contract_type),
            ("Delivery Manager", dm_meta, "Talent PM", tpm_meta),
            ("PMO Lead", pmo_meta, "Generated Date", datetime.now().strftime("%Y-%m-%d")),
            ("1-Day SLA Status", sla_status_str, "Workflow State", baseline.workflow_state),
        ]

        for row_idx, (l1, v1, l2, v2) in enumerate(meta_data):
            row = meta_table.rows[row_idx]
            row.cells[0].text = l1
            row.cells[1].text = v1
            row.cells[2].text = l2
            row.cells[3].text = v2
            for c_idx in (0, 2):
                set_cell_background(row.cells[c_idx], COLOR_LIGHT_BG_HEX)
                p = row.cells[c_idx].paragraphs[0]
                p.runs[0].font.name = "Arial"
                p.runs[0].font.size = Pt(9)
                p.runs[0].bold = True
                p.runs[0].font.color.rgb = RGBColor(15, 33, 55)
            for c_idx in (1, 3):
                p = row.cells[c_idx].paragraphs[0]
                if p.runs:
                    p.runs[0].font.name = "Arial"
                    p.runs[0].font.size = Pt(9)
                    p.runs[0].font.color.rgb = RGBColor(30, 41, 59)
                set_cell_margins(row.cells[c_idx], top=80, bottom=80, left=100, right=100)
            set_cell_margins(row.cells[0], top=80, bottom=80, left=100, right=100)
            set_cell_margins(row.cells[2], top=80, bottom=80, left=100, right=100)

        doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # =========================================================================
        # STARTUP KIT READINESS SCORE & LAYER 1: EXECUTIVE STARTUP PACK
        # =========================================================================
        add_section_heading(doc, f"Startup Kit Readiness Score: {baseline.readiness_score:.1f}%", level=1)
        add_section_heading(doc, "Layer 1: Executive Startup Pack", level=1)

        # 1.1 Project Startup Charter
        add_section_heading(doc, "Project Startup Charter", level=2)
        if charter:
            charter_table = doc.add_table(rows=1, cols=2)
            charter_table.cell(0, 0).text = "Startup Charter Dimension"
            charter_table.cell(0, 1).text = "Charter Commitment & Governance Baseline"

            g01_01_act = find_cell_action(baseline, "Project Startup Charter", "Turnaround SLA & PMO Authorization", used_actions=used_actions) if (not baseline.sla_met or any(a.checklist_id == "G01-01" for a in baseline.action_required_items)) else None
            g01_02_act = find_cell_action(baseline, "Project Startup Charter", "Delivery Model & Governance Tier", used_actions=used_actions)

            sla_val = f"SLA Met ({'Yes' if baseline.sla_met else 'No - Retroactive PMO Waiver Required'})"
            model_val = f"Delivery: {charter.delivery_model} | Governance: {charter.governance_model}"

            charter_rows = [
                ("Project Purpose & Delivery Baseline", charter.project_purpose, g01_02_act if is_placeholder_text(charter.project_purpose) else None, "G01-02", "Confirm project purpose and delivery objectives"),
                ("Delivery Model & Governance Tier", model_val, g01_02_act if not is_placeholder_text(charter.project_purpose) else None, "G01-02", "Confirm governance tier and delivery cadence"),
                ("Turnaround SLA & PMO Authorization", sla_val, g01_01_act, "G01-01", "Log retroactive PMO waiver for SLA"),
                ("Escalation Path & Decision Hierarchy", charter.escalation_path, None, "G01-02", "Confirm escalation path"),
                ("Unresolved Assumptions Status", charter.unresolved_assumptions_status, None, "G01-05", "Review unresolved assumptions"),
            ]

            for dim, val, act, fallback_id, fallback_desc in charter_rows:
                r = charter_table.add_row()
                r.cells[0].text = dim
                is_flagged = bool(act or is_placeholder_text(val))
                format_cell_with_action(r.cells[1], val, action=act, is_warning=is_flagged, fallback_checklist_id=fallback_id, fallback_action_desc=fallback_desc)

            style_table(charter_table, col_widths=[2.4, 4.8])
            doc.add_paragraph().paragraph_format.space_after = Pt(6)

            # Objectives & Scope
            if charter.delivery_objectives:
                doc.add_paragraph().paragraph_format.space_after = Pt(2)
                p_obj = doc.add_paragraph()
                p_obj.add_run("Delivery Objectives & Success Criteria:").bold = True
                for obj in charter.delivery_objectives:
                    clean_obj = re.sub(r'^[•\-\*]\s*', '', obj).strip()
                    doc.add_paragraph(clean_obj, style='List Bullet')
                for sc in charter.success_criteria:
                    clean_sc = re.sub(r'^[•\-\*]\s*', '', sc).strip()
                    if not clean_sc.lower().startswith("success criteria:"):
                        doc.add_paragraph(f"Success Criteria: {clean_sc}", style='List Bullet')
                    else:
                        doc.add_paragraph(clean_sc, style='List Bullet')

            if charter.exclusions:
                doc.add_paragraph().paragraph_format.space_after = Pt(2)
                p_exc = doc.add_paragraph()
                p_exc.add_run("High-Level Scope Exclusions:").bold = True
                for exc in charter.exclusions:
                    clean_exc = re.sub(r'^[•\-\*]\s*', '', exc).strip()
                    doc.add_paragraph(clean_exc, style='List Bullet')

        # 1.2 SOW Interpretation Summary
        add_section_heading(doc, "SOW Interpretation Summary", level=2)
        sow_sum = baseline.sow_interpretation
        if sow_sum:
            sow_table = doc.add_table(rows=1, cols=2)
            sow_table.cell(0, 0).text = "SOW Interpretation Dimension"
            sow_table.cell(0, 1).text = "Contractual Summary & Operational Meaning"

            cust_ob = "\n".join(f"• {re.sub(r'^[•\-\*]\s*', '', c).strip()}" for c in sow_sum.customer_obligations if c.strip()) if sow_sum.customer_obligations else "[CONFIRMATION REQUIRED]"
            amb_notes = "\n".join(f"• {re.sub(r'^[•\-\*]\s*', '', n).strip()}" for n in sow_sum.ambiguity_notes if n.strip()) if sow_sum.ambiguity_notes else "No critical ambiguities"
            plat_commit = "\n".join(f"• {re.sub(r'^[•\-\*]\s*', '', p).strip()}" for p in sow_sum.platform_environment_commitments if p.strip()) if sow_sum.platform_environment_commitments else "[UNDEFINED]"
            approval_exp = sow_sum.approval_expectations or "[CONFIRMATION REQUIRED]"

            g01_07_act = find_cell_action(baseline, "SOW Interpretation Summary", "Customer Obligations & Prerequisites", used_actions=used_actions)
            g01_15_act = find_cell_action(baseline, "SOW Interpretation Summary", "Ambiguities & Clarification Notes", used_actions=used_actions)

            sow_rows = [
                ("Contracted Deliverables", "\n".join(f"• {re.sub(r'^[•\-\*]\s*', '', d).strip()}" for d in sow_sum.contracted_deliverables if d.strip()) if sow_sum.contracted_deliverables else "See Deliverables Matrix", None, "G01-03", "Baseline contracted deliverables"),
                ("Explicit Exclusions & Out-of-Scope", "\n".join(f"• {re.sub(r'^[•\-\*]\s*', '', e).strip()}" for e in sow_sum.out_of_scope_items if e.strip()) if sow_sum.out_of_scope_items else "None documented", None, "G01-02", "Confirm scope boundaries"),
                ("Customer Obligations & Prerequisites", cust_ob, g01_07_act, "G01-07", "Issue access prerequisites list to client sponsor"),
                ("Baseline Assumptions & Constraints", "\n".join(f"• {re.sub(r'^[•\-\*]\s*', '', a).strip()}" for a in sow_sum.assumptions + sow_sum.constraints if a.strip()) if (sow_sum.assumptions or sow_sum.constraints) else "Standard working assumptions", None, "G01-05", "Confirm baseline assumptions"),
                ("Platform & Environment Commitments", plat_commit, None, "G01-07", "Confirm client platform and environment access"),
                ("External Dependencies", "\n".join(f"• {re.sub(r'^[•\-\*]\s*', '', d).strip()}" for d in sow_sum.dependencies if d.strip()) if sow_sum.dependencies else "Logged in Dependency Log", None, "G01-05", "Confirm external dependencies"),
                ("Approval & Acceptance Expectations", approval_exp, None, "G01-03", "Finalize acceptance test criteria and approval expectations"),
                ("Ambiguities & Clarification Notes", amb_notes, g01_15_act, "G01-15", "Resolve open questions and scope clarifications"),
            ]

            if baseline.contract_ambiguities:
                amb_summary = f"{len(baseline.contract_ambiguities)} contractual ambiguities logged (see Checklist for detail)"
                sow_rows.append(("Contract Ambiguities Logged", amb_summary, None, "G01-14", "Review contractual ambiguities and recommended clarifications"))

            for dim, val, act, fallback_id, fallback_desc in sow_rows:
                r = sow_table.add_row()
                r.cells[0].text = dim
                is_placeholder = is_placeholder_text(val)
                is_flagged = bool(
                    act
                    or is_placeholder
                    or (dim == "Ambiguities & Clarification Notes" and bool(baseline.open_questions) and val != "No critical ambiguities" and bool(val.strip()))
                )
                # Contract Ambiguities Logged row carries no action tag (v5 B14)
                if dim == "Contract Ambiguities Logged":
                    r.cells[1].text = val
                else:
                    format_cell_with_action(r.cells[1], val, action=act, is_warning=is_flagged, fallback_checklist_id=fallback_id, fallback_action_desc=fallback_desc)

            style_table(sow_table, col_widths=[2.2, 5.0])
            doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # 1.3 Milestone Delivery Plan
        add_section_heading(doc, "Milestone Delivery Plan", level=2)
        ms_table = doc.add_table(rows=1, cols=6)
        ms_headers = ["Milestone ID", "Description", "External Date", "Internal Buffer Date", "Owner", "Source Reference"]
        for idx, h in enumerate(ms_headers):
            ms_table.cell(0, idx).text = h

        for m in baseline.milestones:
            row = ms_table.add_row()
            ext_str = m.external_date.strftime("%Y-%m-%d") if m.external_date else "[CONFIRMATION REQUIRED]"
            buf_str = m.internal_buffer_date.strftime("%Y-%m-%d") if m.internal_buffer_date else "N/A"
            src_doc = sanitize_report_text(m.source_reference.document_name) if m.source_reference else "Project Baseline"
            if not src_doc or any(k in src_doc.lower() for k in ("input document", "sow")):
                src_doc = "Project Baseline"
            src_str = src_doc

            ext_act = find_cell_action(baseline, "Milestone Delivery Plan", "External Date", entity_id=m.id, linked_action_id=m.linked_action_id, used_actions=used_actions)
            buf_act = find_cell_action(baseline, "Milestone Delivery Plan", "Internal Buffer Date", entity_id=m.id, used_actions=used_actions)
            owner_act = find_cell_action(baseline, "Milestone Delivery Plan", "Owner", entity_id=m.id, used_actions=used_actions)

            row.cells[0].text = m.id
            row.cells[1].text = m.description
            format_cell_with_action(row.cells[2], ext_str, action=ext_act, is_warning=(not m.external_date or bool(ext_act)), fallback_checklist_id="G01-04", fallback_action_desc=f"Lock client milestone date for {m.id}")
            format_cell_with_action(row.cells[3], buf_str, action=buf_act, is_warning=(m.internal_buffer_date is None or bool(buf_act)), fallback_checklist_id="G01-04", fallback_action_desc=f"Log 7-day internal buffer date for {m.id}")
            format_cell_with_action(row.cells[4], m.owner, action=owner_act, is_warning=("UNASSIGNED" in m.owner.upper() or m.owner == "Unassigned" or bool(owner_act)), fallback_checklist_id="G01-04", fallback_action_desc=f"Assign delivery owner for {m.id}")
            row.cells[5].text = src_str

        style_table(ms_table, col_widths=[0.9, 2.2, 1.1, 1.1, 1.0, 1.5])
        doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # =========================================================================
        # LAYER 2: DELIVERY CONTROL PACK
        # =========================================================================
        add_section_heading(doc, "Layer 2: Delivery Control Pack", level=1)

        # 2.1 Scope Decomposition / Backlog Seed (v4 B9, v6 Section 1.1: SOW References column)
        add_section_heading(doc, "Scope Decomposition / Backlog Seed", level=2)
        if baseline.backlog_seed:
            wp_table = doc.add_table(rows=1, cols=7)
            wp_headers = ["WP ID", "Parent Deliv", "Work Package Title", "Seq", "Owner", "SOW References", "Status"]
            for idx, h in enumerate(wp_headers):
                wp_table.cell(0, idx).text = h

            for wp in baseline.backlog_seed:
                row = wp_table.add_row()
                is_unassigned = ("UNASSIGNED" in wp.owner.upper() or wp.owner == "Unassigned")
                act = find_cell_action(baseline, "Scope Decomposition / Backlog Seed", "Owner", entity_id=wp.id, linked_action_id=wp.linked_action_id, used_actions=used_actions)
                sow_stories_str = getattr(wp, "sow_reference", None) or ""

                row.cells[0].text = wp.id
                row.cells[1].text = wp.parent_deliverable_id or ""
                row.cells[2].text = wp.title
                row.cells[3].text = str(wp.preliminary_sequence)
                format_cell_with_action(row.cells[4], wp.owner, action=act, is_warning=is_unassigned or bool(act), fallback_checklist_id="G01-03", fallback_action_desc="Assign work package delivery owner")
                row.cells[5].text = sow_stories_str
                row.cells[6].text = wp.status

            style_table(wp_table, col_widths=[0.7, 0.9, 2.8, 0.5, 1.0, 1.0, 0.7])
            doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # 2.2 Deliverables and Acceptance Matrix (v4 B9, v6 Section 1.1: SOW References column)
        add_section_heading(doc, "Deliverables and Acceptance Matrix", level=2)
        deliv_table = doc.add_table(rows=1, cols=8)
        deliv_headers = ["ID", "Deliverable Name", "Acceptance Criteria", "Evidence Required", "Client Approver", "Owner", "SOW References", "Review Window"]
        for idx, h in enumerate(deliv_headers):
            deliv_table.cell(0, idx).text = h

        for d in baseline.deliverables:
            row = deliv_table.add_row()
            ac_text = d.acceptance_criteria if d.acceptance_criteria else "[CONFIRMATION REQUIRED]"
            owner_text = d.owner if (d.owner and d.owner != "Unassigned") else "[UNASSIGNED]"
            approver_text = d.client_approver if (d.client_approver and "UNASSIGNED" not in d.client_approver.upper()) else "[CONFIRMATION REQUIRED]"
            sow_stories_str = getattr(d, "sow_reference", None) or ""

            is_criteria_unconfirmed = (not d.acceptance_criteria or "[CONFIRMATION REQUIRED]" in d.acceptance_criteria or "UNASSIGNED" in d.acceptance_criteria)
            is_owner_unassigned = (d.owner == "Unassigned" or "UNASSIGNED" in d.owner.upper() or not d.owner)
            is_approver_unassigned = (not d.client_approver or d.client_approver == "[UNASSIGNED - TO BE CONFIRMED]" or "UNASSIGNED" in d.client_approver.upper() or "[CONFIRMATION REQUIRED]" in d.client_approver)

            ac_act = find_cell_action(baseline, "Deliverables and Acceptance Matrix", "Acceptance Criteria", entity_id=d.id, linked_action_id=d.linked_action_id, used_actions=used_actions)
            owner_act = find_cell_action(baseline, "Deliverables and Acceptance Matrix", "Owner", entity_id=d.id, linked_action_id=d.linked_action_id, used_actions=used_actions)
            approver_act = find_cell_action(baseline, "Deliverables and Acceptance Matrix", "Client Approver", entity_id=d.id, linked_action_id=d.linked_action_id, used_actions=used_actions)

            row.cells[0].text = d.id
            row.cells[1].text = d.name or d.description
            format_cell_with_action(row.cells[2], ac_text, action=ac_act, is_warning=is_criteria_unconfirmed or bool(ac_act), fallback_checklist_id="G01-03", fallback_action_desc=f"Finalize acceptance test criteria and evidence expectations for {d.id}")
            format_cell_with_action(row.cells[3], d.evidence_required, action=None, is_warning=("[CONFIRMATION REQUIRED]" in d.evidence_required), fallback_checklist_id="G01-03", fallback_action_desc=f"Finalize deliverable evidence expectations for {d.id}")
            format_cell_with_action(row.cells[4], approver_text, action=approver_act, is_warning=is_approver_unassigned or bool(approver_act), fallback_checklist_id="G01-03", fallback_action_desc=f"Confirm client sign-off approver for {d.id}")
            format_cell_with_action(row.cells[5], owner_text, action=owner_act, is_warning=is_owner_unassigned or bool(owner_act), fallback_checklist_id="G01-03", fallback_action_desc=f"Assign named delivery owner for {d.id}")
            row.cells[6].text = sow_stories_str
            format_cell_with_action(row.cells[7], d.review_window, action=None, is_warning=("[CONFIRMATION REQUIRED]" in d.review_window), fallback_checklist_id="G01-03", fallback_action_desc="Confirm deliverable review window")

        style_table(deliv_table, col_widths=[0.7, 1.6, 1.8, 1.2, 1.0, 0.8, 1.0, 0.8])
        doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # 2.3 Dependency and Assumption Log
        add_section_heading(doc, "Dependency and Assumption Log", level=2)
        if baseline.dependencies_assumptions:
            da_table = doc.add_table(rows=1, cols=6)
            da_headers = ["Item ID", "Type", "Description", "Category", "Owner", "Status"]
            for idx, h in enumerate(da_headers):
                da_table.cell(0, idx).text = h

            for da in baseline.dependencies_assumptions:
                row = da_table.add_row()
                is_unassigned = ("UNASSIGNED" in da.owner.upper() or da.owner == "Unassigned")
                is_open = da.status.lower() in ("open", "pending", "unconfirmed")
                act = find_cell_action(baseline, "Dependency and Assumption Log", "Owner", entity_id=da.id, linked_action_id=da.linked_action_id, used_actions=used_actions) or find_cell_action(baseline, "Dependency and Assumption Log", "Status", entity_id=da.id, linked_action_id=da.linked_action_id, used_actions=used_actions)

                row.cells[0].text = da.id
                row.cells[1].text = da.type
                row.cells[2].text = da.description
                row.cells[3].text = da.category
                format_cell_with_action(row.cells[4], da.owner, action=act if is_unassigned else None, is_warning=is_unassigned, fallback_checklist_id="G01-05", fallback_action_desc="Assign dependency/assumption owner")
                format_cell_with_action(row.cells[5], da.status, action=act if (is_open and not is_unassigned) else None, is_warning=is_open, fallback_checklist_id="G01-05", fallback_action_desc="Confirm dependency status")

            style_table(da_table, col_widths=[0.8, 1.0, 3.2, 1.0, 1.2, 0.8])
            doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # 2.4 RAID Log (v4 B5: ID, Probability, Impact columns)
        add_section_heading(doc, "RAID Log", level=2)
        raid_table = doc.add_table(rows=1, cols=9)
        raid_headers = ["Item ID", "Type", "Description", "Category", "Probability", "Impact", "Owner", "Mitigation / Response", "Status"]
        for idx, h in enumerate(raid_headers):
            raid_table.cell(0, idx).text = h

        risk_count = 0
        issue_count = 0
        for item in baseline.raid_items:
            row = raid_table.add_row()
            item_type = item.type if item.type in ("Risk", "Issue") else "Risk"
            if item_type == "Risk":
                risk_count += 1
                default_id = f"RSK-{risk_count:02d}"
            else:
                issue_count += 1
                default_id = f"ISS-{issue_count:02d}"

            raw_id = getattr(item, "id", None) or getattr(item, "item_id", None) or ""
            if not raw_id or raw_id in ("RSK-01", "ISS-01") or not re.match(r"^(?:RSK|ISS)-\d{2}$", raw_id):
                item_id = default_id
            else:
                item_id = raw_id
            item.id = item_id

            mitigation_text = item.mitigation_or_response if hasattr(item, "mitigation_or_response") and item.mitigation_or_response else "[TBD]"
            is_unowned = ("UNASSIGNED" in item.owner.upper() or item.owner == "Unassigned")
            is_mitigation_missing = ("TBD" in mitigation_text.upper() or not mitigation_text or "[CONFIRMATION REQUIRED]" in mitigation_text)

            owner_act = find_cell_action(baseline, "RAID Log", "Owner", entity_id=item_id, linked_action_id=item.linked_action_id, used_actions=used_actions)
            mit_act = find_cell_action(baseline, "RAID Log", "Mitigation / Response", entity_id=item_id, linked_action_id=item.linked_action_id, used_actions=used_actions)

            row.cells[0].text = item_id
            row.cells[1].text = item_type
            row.cells[2].text = item.description
            row.cells[3].text = item.category if hasattr(item, "category") and item.category else "Delivery Risk"
            row.cells[4].text = item.probability or "Medium"
            row.cells[5].text = item.impact or "Medium"
            format_cell_with_action(row.cells[6], item.owner, action=owner_act, is_warning=is_unowned or bool(owner_act), fallback_checklist_id="G01-05", fallback_action_desc="Assign risk owner")
            format_cell_with_action(row.cells[7], mitigation_text, action=mit_act, is_warning=is_mitigation_missing or bool(mit_act), fallback_checklist_id="G01-05", fallback_action_desc="Document fallback mitigation workflow")
            row.cells[8].text = item.status

        style_table(raid_table, col_widths=[0.8, 0.8, 2.2, 1.0, 0.7, 0.7, 1.1, 1.8, 0.7])
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

        # Decision Log Seed
        if baseline.decisions:
            doc.add_paragraph().paragraph_format.space_after = Pt(2)
            p_dec = doc.add_paragraph()
            p_dec.add_run("Decision Log Seed (Readiness Decisions):").bold = True
            dec_table = doc.add_table(rows=1, cols=4)
            dec_headers = ["Decision ID", "Decision Text", "Owner", "Status"]
            for idx, h in enumerate(dec_headers):
                dec_table.cell(0, idx).text = h

            for dec in baseline.decisions:
                row = dec_table.add_row()
                row.cells[0].text = dec.id
                format_cell_with_action(row.cells[1], dec.decision_text, action=None, is_warning=("[CONFIRMATION REQUIRED]" in dec.decision_text), fallback_checklist_id="G01-10", fallback_action_desc="Confirm decision text")
                format_cell_with_action(row.cells[2], dec.decision_owner, action=None, is_warning=("UNASSIGNED" in dec.decision_owner.upper() or dec.decision_owner == "Unassigned"), fallback_checklist_id="G01-10", fallback_action_desc="Assign decision owner")
                format_cell_with_action(row.cells[3], dec.status, action=None, is_warning=("[CONFIRMATION REQUIRED]" in dec.status), fallback_checklist_id="G01-10", fallback_action_desc="Confirm decision status")

            style_table(dec_table, col_widths=[1.0, 4.4, 1.4, 1.0])
            doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # 2.5 Communications and Reporting Plan (v4 B5: Item ID column)
        add_section_heading(doc, "Communications and Reporting Plan", level=2)
        if baseline.communications_plan:
            com_table = doc.add_table(rows=1, cols=7)
            com_headers = ["Item ID", "Report / Meeting", "Audience", "Owner", "Cadence", "Format", "Delivery Day"]
            for idx, h in enumerate(com_headers):
                com_table.cell(0, idx).text = h

            for com_idx, com in enumerate(baseline.communications_plan, 1):
                row = com_table.add_row()
                com_id = getattr(com, "id", None) or f"COM-{com_idx:02d}"
                if not re.match(r"^COM-\d{2}$", com_id):
                    com_id = f"COM-{com_idx:02d}"
                com.id = com_id

                is_unconfirmed_aud = ("[CONFIRMATION REQUIRED]" in com.audience)
                act = find_cell_action(baseline, "Communications and Reporting Plan", "Audience", entity_id=com_id, linked_action_id=com.linked_action_id, used_actions=used_actions) if is_unconfirmed_aud else None

                row.cells[0].text = com_id
                row.cells[1].text = com.name
                format_cell_with_action(row.cells[2], com.audience, action=act, is_warning=is_unconfirmed_aud, fallback_checklist_id="G01-11", fallback_action_desc="Confirm weekly status distribution list")
                row.cells[3].text = com.content_owner
                row.cells[4].text = com.cadence
                row.cells[5].text = com.format
                row.cells[6].text = com.delivery_day

            style_table(com_table, col_widths=[0.8, 1.8, 1.6, 1.0, 1.0, 1.2, 0.8])
            doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # =========================================================================
        # LAYER 3: ASSURANCE PACK
        # =========================================================================
        add_section_heading(doc, "Layer 3: Assurance Pack", level=1)

        # 3.1 Stakeholder and Responsibility Model
        add_section_heading(doc, "Stakeholder and Responsibility Model", level=2)
        if baseline.stakeholders:
            stk_table = doc.add_table(rows=1, cols=5)
            stk_headers = ["Stakeholder Name", "Role", "Organization", "Decision Rights", "Escalation Path"]
            for idx, h in enumerate(stk_headers):
                stk_table.cell(0, idx).text = h

            for stk in baseline.stakeholders:
                row = stk_table.add_row()
                is_unconfirmed = ("[CONFIRMATION REQUIRED]" in stk.decision_rights or "UNASSIGNED" in stk.name.upper())
                act = find_cell_action(baseline, "Stakeholder and Responsibility Model", "Decision Rights", entity_id=stk.name, linked_action_id=stk.linked_action_id, used_actions=used_actions) if is_unconfirmed else None

                format_cell_with_action(row.cells[0], stk.name, action=None, is_warning=("UNASSIGNED" in stk.name.upper()), fallback_checklist_id="G01-09", fallback_action_desc="Confirm stakeholder named representative")
                format_cell_with_action(row.cells[1], stk.role, action=None, is_warning=("UNASSIGNED" in stk.role.upper() or "[CONFIRMATION REQUIRED]" in stk.role), fallback_checklist_id="G01-09", fallback_action_desc="Confirm stakeholder role")
                format_cell_with_action(row.cells[2], stk.organization, action=None, is_warning=("[CONFIRMATION REQUIRED]" in stk.organization), fallback_checklist_id="G01-09", fallback_action_desc="Confirm stakeholder organization")
                format_cell_with_action(row.cells[3], stk.decision_rights, action=act, is_warning=is_unconfirmed, fallback_checklist_id="G01-09", fallback_action_desc="Confirm client sign-off sponsor authority")
                format_cell_with_action(row.cells[4], stk.escalation_responsibility, action=None, is_warning=("[CONFIRMATION REQUIRED]" in stk.escalation_responsibility), fallback_checklist_id="G01-09", fallback_action_desc="Confirm escalation responsibility")

            style_table(stk_table, col_widths=[1.6, 1.4, 1.0, 2.6, 1.4])
            doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # 3.2 RACI / Decision Rights Matrix
        add_section_heading(doc, "RACI / Decision Rights Matrix", level=2)
        if baseline.raci_matrix:
            raci_table = doc.add_table(rows=1, cols=6)
            raci_headers = ["Startup Control / Decision Activity", "PMO Lead", "Delivery Manager", "Talent PM", "Sales / Accts", "Client"]
            for idx, h in enumerate(raci_headers):
                raci_table.cell(0, idx).text = h

            g01_10_act = find_cell_action(baseline, "RACI / Decision Rights Matrix", "Startup Control / Decision Activity", used_actions=used_actions)
            for r in baseline.raci_matrix:
                row = raci_table.add_row()
                format_cell_with_action(row.cells[0], r.decision_or_activity, action=g01_10_act, is_warning=bool(g01_10_act), fallback_checklist_id="G01-10", fallback_action_desc="Align RACI matrix decision rights with client")
                row.cells[1].text = r.pmo_lead
                row.cells[2].text = r.delivery_manager
                row.cells[3].text = r.talent_pm
                row.cells[4].text = r.sales_accounts
                row.cells[5].text = r.client
                g01_10_act = None  # Attach to first row only

            style_table(raci_table, col_widths=[2.8, 1.0, 1.1, 1.0, 1.0, 0.9])
            doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # 3.3 Talent Onboarding Record
        add_section_heading(doc, "Talent Onboarding Record", level=2)
        talent_rec = baseline.talent_onboarding
        if talent_rec:
            doc.add_paragraph(
                f"Onboarding Leadership: Talent PM: {talent_rec.talent_pm} | "
                f"Delivery Manager: {talent_rec.delivery_manager} | "
                f"PMO Lead: {talent_rec.pmo_lead}"
            )
            if talent_rec.delivery_talent_roster:
                roster_table = doc.add_table(rows=1, cols=4)
                roster_headers = ["Role", "Named Talent", "Required Skills", "Staffing Status"]
                for idx, h in enumerate(roster_headers):
                    roster_table.cell(0, idx).text = h

                for tm in talent_rec.delivery_talent_roster:
                    row = roster_table.add_row()
                    is_unstaffed = (
                        "UNASSIGNED" in tm.name.upper()
                        or tm.status.lower() in ("pending", "needs alignment", "unassigned", "staffing required")
                    )
                    act = find_cell_action(baseline, "Talent Onboarding Record", "Named Talent", entity_id=tm.role, linked_action_id=tm.linked_action_id, used_actions=used_actions)

                    row.cells[0].text = tm.role
                    format_cell_with_action(row.cells[1], tm.name, action=act, is_warning=is_unstaffed or bool(act), fallback_checklist_id="G01-08", fallback_action_desc=f"Complete candidate selection and lock staffing for {tm.role}")
                    row.cells[2].text = tm.required_skills
                    format_cell_with_action(row.cells[3], tm.status, action=None, is_warning=is_unstaffed, fallback_checklist_id="G01-08", fallback_action_desc="Update staffing status to Confirmed")

                style_table(roster_table, col_widths=[1.8, 2.0, 2.8, 1.2])
                doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # Save Startup Kit document (without the checklist table)
        doc.save(str(target_file))
        logger.info("Successfully generated Startup Kit Word document at: %s", target_file)

        return target_file

    def _render_artifact_action_banner(
        self,
        doc: docx.Document,
        baseline: StartupKitBaseline,
        checklist_ids: List[str],
        artifact_name: str,
    ) -> None:
        """Deprecated: Actions are embedded directly into tables."""
        return
