"""Microsoft Word (.docx) report generator implementing IDocumentWriter with Section 4 Three-Layer structure."""

import re
import logging
from pathlib import Path
from datetime import datetime
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from src.core.interfaces import IDocumentWriter
from src.core.models import StartupKitBaseline
from src.generators.formatting import (
    add_section_heading,
    add_callout_box,
    style_table,
    set_cell_background,
    set_cell_margins,
    COLOR_NAVY_HEX,
    COLOR_PRIMARY_BLUE_HEX,
    COLOR_LIGHT_BG_HEX,
    COLOR_WARNING_BG_HEX,
)
from src.generators.checklist import G01ChecklistRenderer

logger = logging.getLogger(__name__)


def sanitize_filename(name: str) -> str:
    """Sanitize project name for safe filename creation."""
    s = re.sub(r'[^a-zA-Z0-9_\- ]+', '', name).strip()
    return s.replace(' ', '_') or "Project"


class DocxGenerator(IDocumentWriter):
    """Generates the standardized Toptal PMO Startup Kit Word document following Section 4 structure."""

    def __init__(self, checklist_renderer: G01ChecklistRenderer = None):
        self.checklist_renderer = checklist_renderer or G01ChecklistRenderer()

    def write_docx(self, baseline: StartupKitBaseline, output_path: Path) -> Path:
        """Render the complete Section 4 Startup Kit Word document and write to disk."""
        if output_path.suffix.lower() == ".docx":
            target_file = output_path
        else:
            clean_name = sanitize_filename(baseline.project_name)
            target_file = output_path / f"{clean_name}_Startup_Kit.docx"

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
        meta_data = [
            ("Project Name", baseline.project_name, "Client Sponsor", ctx.client_name if ctx and ctx.client_name else (charter.client_name if charter and charter.client_name else "N/A")),
            ("Governance Tier", baseline.governance_tier, "Contract Type", baseline.contract_type),
            ("Delivery Manager", ctx.delivery_manager if ctx and ctx.delivery_manager else "[UNASSIGNED - TO BE CONFIRMED]", "Talent PM", ctx.talent_pm if ctx and ctx.talent_pm else "[UNASSIGNED - TO BE CONFIRMED]"),
            ("PMO Lead", ctx.pmo_lead if ctx and ctx.pmo_lead else "[UNASSIGNED - TO BE CONFIRMED]", "Generated Date", datetime.now().strftime("%Y-%m-%d")),
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
        # EXECUTIVE READINESS GATEWAY: STARTUP READINESS CHECKLIST (G-01) & GATE DECISION
        # =========================================================================
        self.checklist_renderer.render(doc, baseline)

        # Open Questions Callout Box (if any)
        if baseline.open_questions:
            questions_text = "\n".join(f"• {q}" for q in baseline.open_questions)
            add_callout_box(
                doc,
                text=questions_text,
                title="Action Required: Unresolved Validation Points / Clarifications Pending Mobilize Kickoff:",
                bg_color=COLOR_WARNING_BG_HEX,
                border_color="D97706"
            )

        # =========================================================================
        # LAYER 1: EXECUTIVE STARTUP PACK
        # =========================================================================
        add_section_heading(doc, "Layer 1: Executive Startup Pack", level=1)

        # 1.1 Project Startup Charter
        add_section_heading(doc, "Project Startup Charter", level=2)
        if charter:
            charter_text = (
                f"Project Purpose: {charter.project_purpose}\n\n"
                f"Delivery Model: {charter.delivery_model} | Governance Model: {charter.governance_model}\n"
                f"Escalation Path: {charter.escalation_path}\n"
                f"Unresolved Assumptions Status: {charter.unresolved_assumptions_status}"
            )
            add_callout_box(doc, text=charter_text, title="Startup Charter & Delivery Purpose", bg_color=COLOR_LIGHT_BG_HEX)

            # Objectives & Scope
            if charter.delivery_objectives:
                doc.add_paragraph().paragraph_format.space_after = Pt(2)
                p_obj = doc.add_paragraph()
                p_obj.add_run("Delivery Objectives & Success Criteria:").bold = True
                for obj in charter.delivery_objectives:
                    doc.add_paragraph(f"• {obj}", style='List Bullet')
                for sc in charter.success_criteria:
                    doc.add_paragraph(f"• Success Criteria: {sc}", style='List Bullet')

            if charter.exclusions:
                doc.add_paragraph().paragraph_format.space_after = Pt(2)
                p_exc = doc.add_paragraph()
                p_exc.add_run("High-Level Scope Exclusions:").bold = True
                for exc in charter.exclusions:
                    doc.add_paragraph(f"• {exc}", style='List Bullet')

        # 1.2 SOW Interpretation Summary
        add_section_heading(doc, "SOW Interpretation Summary", level=2)
        sow_sum = baseline.sow_interpretation
        if sow_sum:
            sow_table = doc.add_table(rows=1, cols=2)
            sow_table.cell(0, 0).text = "SOW Interpretation Dimension"
            sow_table.cell(0, 1).text = "Contractual Summary & Operational Meaning"

            sow_rows = [
                ("Contracted Deliverables", "\n".join(f"• {d}" for d in sow_sum.contracted_deliverables) or "See Deliverables Matrix"),
                ("Explicit Exclusions & Out-of-Scope", "\n".join(f"• {e}" for e in sow_sum.out_of_scope_items) or "None documented"),
                ("Customer Obligations & Prerequisites", "\n".join(f"• {c}" for c in sow_sum.customer_obligations) or "[CONFIRMATION REQUIRED]"),
                ("Baseline Assumptions & Constraints", "\n".join(f"• {a}" for a in sow_sum.assumptions + sow_sum.constraints) or "Standard working assumptions"),
                ("Platform & Environment Commitments", "\n".join(f"• {p}" for p in sow_sum.platform_environment_commitments) or "Cloud infrastructure per SOW"),
                ("External Dependencies", "\n".join(f"• {d}" for d in sow_sum.dependencies) or "Logged in Dependency Log"),
                ("Approval & Acceptance Expectations", sow_sum.approval_expectations),
                ("Ambiguities & Clarification Notes", "\n".join(f"• {n}" for n in sow_sum.ambiguity_notes) or "No critical ambiguities")
            ]

            for dim, val in sow_rows:
                r = sow_table.add_row()
                r.cells[0].text = dim
                r.cells[1].text = val

            style_table(sow_table, col_widths=[2.2, 5.0])
            doc.add_paragraph().paragraph_format.space_after = Pt(6)

            # Contractual Ambiguities & Conflicts Table (NFR-02)
            if baseline.contract_ambiguities:
                doc.add_paragraph().paragraph_format.space_after = Pt(2)
                p_amb = doc.add_paragraph()
                p_amb.add_run("Contractual Ambiguities & Conflict Analysis (NFR-02):").bold = True
                amb_table = doc.add_table(rows=1, cols=5)
                amb_headers = ["Anomaly ID", "Category", "Conflicting Clauses / Citations", "Risk Impact Analysis", "Recommended Clarification"]
                for idx, h in enumerate(amb_headers):
                    amb_table.cell(0, idx).text = h

                for amb in baseline.contract_ambiguities:
                    row = amb_table.add_row()
                    row.cells[0].text = amb.anomaly_id
                    row.cells[1].text = amb.category
                    row.cells[2].text = amb.conflicting_clauses
                    row.cells[3].text = amb.risk_impact
                    row.cells[4].text = amb.recommended_clarification
                    set_cell_background(row.cells[0], COLOR_WARNING_BG_HEX)

                style_table(amb_table, col_widths=[1.0, 1.2, 2.0, 1.8, 1.8])
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
            src_str = f"{m.source_reference.document_name} ({m.source_reference.clause_or_slide or 'N/A'})" if m.source_reference else "N/A"

            row.cells[0].text = m.id
            row.cells[1].text = m.description
            row.cells[2].text = ext_str
            row.cells[3].text = buf_str
            row.cells[4].text = m.owner
            row.cells[5].text = src_str

            if not m.external_date:
                set_cell_background(row.cells[2], COLOR_WARNING_BG_HEX)

        style_table(ms_table, col_widths=[0.9, 2.2, 1.1, 1.1, 1.0, 1.5])
        doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # =========================================================================
        # LAYER 2: DELIVERY CONTROL PACK
        # =========================================================================
        add_section_heading(doc, "Layer 2: Delivery Control Pack", level=1)

        # 2.1 Scope Decomposition / Backlog Seed
        add_section_heading(doc, "Scope Decomposition / Backlog Seed", level=2)
        if baseline.backlog_seed:
            wp_table = doc.add_table(rows=1, cols=6)
            wp_headers = ["WP ID", "Parent Deliv", "Work Package Title", "Seq", "Owner", "Status"]
            for idx, h in enumerate(wp_headers):
                wp_table.cell(0, idx).text = h

            for wp in baseline.backlog_seed:
                row = wp_table.add_row()
                row.cells[0].text = wp.id
                row.cells[1].text = wp.parent_deliverable_id
                row.cells[2].text = wp.title
                row.cells[3].text = str(wp.preliminary_sequence)
                row.cells[4].text = wp.owner
                row.cells[5].text = wp.status

            style_table(wp_table, col_widths=[0.8, 1.0, 3.2, 0.6, 1.2, 0.8])
            doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # 2.2 Deliverables and Acceptance Matrix
        add_section_heading(doc, "Deliverables and Acceptance Matrix", level=2)
        deliv_table = doc.add_table(rows=1, cols=7)
        deliv_headers = ["ID", "Deliverable Name", "Acceptance Criteria", "Evidence Required", "Client Approver", "Owner", "Review Window"]
        for idx, h in enumerate(deliv_headers):
            deliv_table.cell(0, idx).text = h

        for d in baseline.deliverables:
            row = deliv_table.add_row()
            ac_text = d.acceptance_criteria if d.acceptance_criteria else "[CONFIRMATION REQUIRED]"
            row.cells[0].text = d.id
            row.cells[1].text = d.name or d.description
            row.cells[2].text = ac_text
            row.cells[3].text = d.evidence_required
            row.cells[4].text = d.client_approver
            row.cells[5].text = d.owner
            row.cells[6].text = d.review_window

            if not d.acceptance_criteria:
                set_cell_background(row.cells[2], COLOR_WARNING_BG_HEX)

        style_table(deliv_table, col_widths=[0.7, 1.8, 2.0, 1.3, 1.1, 0.9, 0.9])
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
                row.cells[0].text = da.id
                row.cells[1].text = da.type
                row.cells[2].text = da.description
                row.cells[3].text = da.category
                row.cells[4].text = da.owner
                row.cells[5].text = da.status

            style_table(da_table, col_widths=[0.8, 1.0, 3.2, 1.0, 1.2, 0.8])
            doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # 2.4 RAID Log
        add_section_heading(doc, "RAID Log", level=2)
        raid_table = doc.add_table(rows=1, cols=6)
        raid_headers = ["Type", "Description", "Category", "Owner", "Mitigation / Response", "Status"]
        for idx, h in enumerate(raid_headers):
            raid_table.cell(0, idx).text = h

        for item in baseline.raid_items:
            row = raid_table.add_row()
            row.cells[0].text = item.type
            row.cells[1].text = item.description
            row.cells[2].text = item.category if hasattr(item, "category") else "Technical"
            row.cells[3].text = item.owner
            row.cells[4].text = item.mitigation_or_response if hasattr(item, "mitigation_or_response") else "Active monitoring"
            row.cells[5].text = item.status

        style_table(raid_table, col_widths=[0.9, 2.6, 1.0, 1.1, 2.2, 0.8])
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
                row.cells[1].text = dec.decision_text
                row.cells[2].text = dec.decision_owner
                row.cells[3].text = dec.status

            style_table(dec_table, col_widths=[1.0, 4.4, 1.4, 1.0])
            doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # 2.5 Communications and Reporting Plan
        add_section_heading(doc, "Communications and Reporting Plan", level=2)
        if baseline.communications_plan:
            com_table = doc.add_table(rows=1, cols=6)
            com_headers = ["Report / Meeting", "Audience", "Owner", "Cadence", "Format", "Delivery Day"]
            for idx, h in enumerate(com_headers):
                com_table.cell(0, idx).text = h

            for com in baseline.communications_plan:
                row = com_table.add_row()
                row.cells[0].text = com.name
                row.cells[1].text = com.audience
                row.cells[2].text = com.content_owner
                row.cells[3].text = com.cadence
                row.cells[4].text = com.format
                row.cells[5].text = com.delivery_day

            style_table(com_table, col_widths=[2.0, 1.8, 1.0, 1.0, 1.4, 1.0])
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
                row.cells[0].text = stk.name
                row.cells[1].text = stk.role
                row.cells[2].text = stk.organization
                row.cells[3].text = stk.decision_rights
                row.cells[4].text = stk.escalation_responsibility

            style_table(stk_table, col_widths=[1.6, 1.4, 1.0, 2.6, 1.4])
            doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # 3.2 RACI / Decision Rights Matrix
        add_section_heading(doc, "RACI / Decision Rights Matrix", level=2)
        if baseline.raci_matrix:
            raci_table = doc.add_table(rows=1, cols=6)
            raci_headers = ["Startup Control / Decision Activity", "PMO Lead", "Delivery Manager", "Talent PM", "Sales / Accts", "Client"]
            for idx, h in enumerate(raci_headers):
                raci_table.cell(0, idx).text = h

            for r in baseline.raci_matrix:
                row = raci_table.add_row()
                row.cells[0].text = r.decision_or_activity
                row.cells[1].text = r.pmo_lead
                row.cells[2].text = r.delivery_manager
                row.cells[3].text = r.talent_pm
                row.cells[4].text = r.sales_accounts
                row.cells[5].text = r.client

            style_table(raci_table, col_widths=[2.8, 1.0, 1.1, 1.0, 1.0, 0.9])
            doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # 3.3 Commercial and Margin Guardrails
        add_section_heading(doc, "Commercial and Margin Guardrails", level=2)
        cg = baseline.commercial_guardrails
        if cg:
            cg_text = (
                f"Contract Implications: {cg.contract_type_implication}\n\n"
                f"• Approved Work Rule: {cg.approved_work_rule}\n"
                f"• Non-Approved Work Rule: {cg.non_approved_work_rule}\n"
                f"• Work-at-Risk Policy: {cg.work_at_risk_rule}\n"
                f"• Change Control Triggers: {cg.change_control_trigger}\n"
                f"• Change Order Route: {cg.change_order_route}\n"
                f"• Budget Baseline: {cg.budget_baseline} | Variance Indicator: {cg.variance_indicator} | Margin Risk: {cg.margin_risk_indicator}\n"
                f"• Escalation Threshold: {cg.escalation_threshold}"
            )
            add_callout_box(doc, text=cg_text, title="Commercial Guardrails & Margin Protection Rules", bg_color=COLOR_LIGHT_BG_HEX)

        # 3.4 Talent Onboarding Record
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
                    row.cells[0].text = tm.role
                    row.cells[1].text = tm.name
                    row.cells[2].text = tm.required_skills
                    row.cells[3].text = tm.status

                style_table(roster_table, col_widths=[1.8, 2.0, 2.8, 1.2])
                doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # Save document
        doc.save(str(target_file))
        logger.info("Successfully generated Startup Kit Word document at: %s", target_file)
        return target_file
