"""G-01 On-Board Talent PM / DM Readiness Gate Checklist & Executive Gateway builder."""

from typing import List
import docx
from docx.shared import Inches, Pt, RGBColor
from src.core.models import StartupKitBaseline, ReadinessChecklistItem, ActionRequiredItem
from src.scoring.readiness_engine import ReadinessScoringEngine
from src.generators.formatting import (
    add_section_heading,
    add_callout_box,
    style_table,
    set_cell_background,
    set_cell_margins,
    format_cell_text_and_highlight,
    COLOR_NAVY_HEX,
    COLOR_LIGHT_BG_HEX,
    COLOR_WARNING_BG_HEX,
)


class G01ChecklistRenderer:
    """Renders the standard G-01 Executive Readiness Gateway and Gate Checklist into the Word document."""

    def render(self, doc: docx.Document, baseline: StartupKitBaseline):
        add_section_heading(
            doc,
            "Executive Readiness Gateway: Startup Readiness Checklist (G-01) & Gate Decision",
            level=1
        )

        intro_p = doc.add_paragraph()
        intro_p.paragraph_format.space_after = Pt(6)
        run_intro = intro_p.add_run(
            "Under the PMO No-Mobilize / No-Kickoff governance rule (WR-03), no project may transition "
            "into Mobilize or conduct kickoffs without G-01 gate sign-off or an authorized exception. "
            "This front-loaded gateway establishes delivery assurance, evaluates quantitative readiness, "
            "verifies segregation of duties, and baselines controls across all Section 4 artifacts."
        )
        run_intro.font.name = "Arial"
        run_intro.font.size = Pt(9.5)

        items: List[ReadinessChecklistItem] = baseline.readiness_checklist
        if not items:
            has_unconfirmed_delivs = any(d.acceptance_criteria is None for d in baseline.deliverables)
            has_unconfirmed_dates = any(m.external_date is None for m in baseline.milestones)
            tier = baseline.governance_tier
            pmo_owner = baseline.governance_context.pmo_lead if baseline.governance_context else "PMO Lead"
            dm_owner = baseline.governance_context.delivery_manager if baseline.governance_context else "Delivery Manager"
            tpm_owner = baseline.governance_context.talent_pm if baseline.governance_context else "Talent PM"

            items = [
                ReadinessChecklistItem(
                    item_id="G01-01",
                    gate_criterion="Startup Kit created within 1 day of delivery",
                    related_section4_artifact="Project Startup Charter",
                    owner=pmo_owner,
                    status="Complete",
                    evidence="Startup Kit Word Report",
                    approval_status="Approved"
                ),
                ReadinessChecklistItem(
                    item_id="G01-02",
                    gate_criterion="Governance Tier assigned and cadence established",
                    related_section4_artifact="Project Startup Charter",
                    owner=pmo_owner,
                    status="Complete",
                    evidence=f"Charter / Tier: {tier}",
                    approval_status="Approved"
                ),
                ReadinessChecklistItem(
                    item_id="G01-03",
                    gate_criterion="Deliverables mapped to owners with explicit acceptance routes",
                    related_section4_artifact="Deliverables and Acceptance Matrix",
                    owner=tpm_owner,
                    status="Review Required" if has_unconfirmed_delivs else "Complete",
                    evidence=f"{len(baseline.deliverables)} deliverables mapped",
                    exception_required=has_unconfirmed_delivs,
                    approval_status="Pending Review" if has_unconfirmed_delivs else "Approved"
                ),
                ReadinessChecklistItem(
                    item_id="G01-04",
                    gate_criterion="Milestones committed with external dates and internal buffers",
                    related_section4_artifact="Milestone Delivery Plan",
                    owner=dm_owner,
                    status="Review Required" if has_unconfirmed_dates else "Complete",
                    evidence=f"{len(baseline.milestones)} milestones tracked",
                    exception_required=has_unconfirmed_dates,
                    approval_status="Pending Confirmation" if has_unconfirmed_dates else "Approved"
                ),
                ReadinessChecklistItem(
                    item_id="G01-05",
                    gate_criterion="Risks, Assumptions, Issues, and Dependencies seeded",
                    related_section4_artifact="RAID Log",
                    owner=tpm_owner,
                    status="Complete",
                    evidence=f"{len(baseline.raid_items)} RAID items identified",
                    approval_status="Approved"
                ),
                ReadinessChecklistItem(
                    item_id="G01-06",
                    gate_criterion="Talent PM and DM briefed on governance cadence and KO decks",
                    related_section4_artifact="Talent Onboarding Record",
                    owner=pmo_owner,
                    status="In Progress",
                    evidence="Onboarding Briefing Session",
                    approval_status="Pending Review"
                ),
                ReadinessChecklistItem(
                    item_id="G01-07",
                    gate_criterion="Formal Readiness Gate review: Approved to proceed to Mobilize",
                    related_section4_artifact="Startup Readiness Checklist",
                    owner=pmo_owner,
                    status="Complete",
                    evidence="G-01 Sign-off Record",
                    approval_status="Approved"
                ),
            ]

        gate_dec = baseline.gate_decision

        # 1. Executive Gate Decision & Readiness Score Callout Box
        decision_status = gate_dec.gate_decision_status if gate_dec else "Pending Gate Review"
        score = baseline.readiness_score
        breakdown = baseline.readiness_breakdown or {}

        if score >= 85.0:
            health_cat = "READY FOR GATE REVIEW (Green)"
            box_bg = COLOR_LIGHT_BG_HEX
        elif score >= 70.0:
            health_cat = "CONDITIONAL / EXCEPTION REQUIRED (Amber)"
            box_bg = COLOR_WARNING_BG_HEX
        else:
            health_cat = "NOT READY / REWORK REQUIRED (Red)"
            box_bg = COLOR_WARNING_BG_HEX

        summary_tbl = doc.add_table(rows=1, cols=1)
        cell = summary_tbl.cell(0, 0)
        set_cell_background(cell, box_bg)
        set_cell_margins(cell, top=140, bottom=140, left=160, right=160)

        sp = cell.paragraphs[0]
        sp.paragraph_format.space_before = Pt(0)
        sp.paragraph_format.space_after = Pt(3)

        s_run = sp.add_run(f"G-01 READINESS GATE DECISION: {decision_status.upper()}\n")
        s_run.font.name = "Arial"
        s_run.font.size = Pt(11)
        s_run.bold = True
        s_run.font.color.rgb = RGBColor(15, 33, 55)

        author_str = baseline.author_name or (gate_dec.author_name if gate_dec else "PMO Lead")
        reviewers_str = ", ".join(baseline.reviewer_names or (gate_dec.reviewer_names if gate_dec else ["Delivery Manager", "Technical Lead"]))
        approver_str = baseline.approver_name or (gate_dec.approver_name if gate_dec else "PMO Lead")
        concurring_str = f" | Concurring Approver: {baseline.concurring_approver_name}" if baseline.concurring_approver_name else ""
        sla_str = "Met (Drafted within 1 business day)" if baseline.sla_met else "Breached (Exception Logged)"
        seg_str = "Verified (Author, Reviewers, Approver segregated)" if baseline.segregation_of_duties_verified else "Segregation Warning"
        exceptions_count = len([i for i in items if i.exception_required or i.status == "Exception Required"])

        detail_text = (
            f"Startup Readiness Score: {score:.1f}% — {health_cat}\n"
            f"Score Breakdown: Controls: {breakdown.get('mandatory_g01_controls', 0.0):.1f}% | "
            f"Acceptance Rigor: {breakdown.get('deliverable_acceptance_rigor', 0.0):.1f}% | "
            f"Staffing: {breakdown.get('talent_staffing_readiness', 0.0):.1f}% | "
            f"Commercial/Risk: {breakdown.get('commercial_risk_mitigation', 0.0):.1f}%\n\n"
            f"• Author / Drafter: {author_str} (PMO Lead)\n"
            f"• Independent Reviewers: {reviewers_str}\n"
            f"• Approval Authority: {approver_str}{concurring_str}\n"
            f"• 1-Day Creation SLA Status: {sla_str}\n"
            f"• Role Segregation: {seg_str}\n"
            f"• Open Exceptions: {exceptions_count} | Open Clarifications: {len(baseline.open_questions)}\n"
            f"• Workflow State: {baseline.workflow_state}\n"
            f"• Decision Comments: {gate_dec.decision_comments if gate_dec else 'Readiness baseline reviewed; awaiting mobilization sign-off.'}"
        )
        if gate_dec and gate_dec.bypass_reason:
            detail_text += f"\n• Exception Note: {gate_dec.bypass_reason} (Authority: {gate_dec.bypass_approving_authority})"

        d_run = sp.add_run(detail_text)
        d_run.font.name = "Arial"
        d_run.font.size = Pt(9)
        d_run.font.color.rgb = RGBColor(30, 41, 59)

        doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # Prepare Action Items for in-table linkage in checklist table
        action_items = baseline.action_required_items
        if not action_items and (exceptions_count > 0 or baseline.open_questions):
            action_items = ReadinessScoringEngine.generate_action_required_items(baseline)
            baseline.action_required_items = action_items

        # 2. Mandatory G-01 Checklist Table (Final section of the document)
        add_section_heading(doc, "Startup Readiness Checklist Table (G-01)", level=2)

        table = doc.add_table(rows=1, cols=8)
        headers = [
            "Gate ID",
            "Gate Criterion",
            "Related Section 4 Artifact",
            "Status",
            "Owner",
            "Reviewer",
            "Approver",
            "Evidence & Exceptions"
        ]
        for idx, name in enumerate(headers):
            table.cell(0, idx).text = name

        for item in items:
            row = table.add_row()
            row.cells[0].text = item.item_id
            row.cells[1].text = item.gate_criterion
            row.cells[2].text = item.related_section4_artifact
            row.cells[3].text = item.status
            row.cells[4].text = item.owner
            row.cells[5].text = item.reviewer
            row.cells[6].text = item.approver

            matching_act = next((a for a in action_items if a.checklist_id == item.item_id), None)
            ev_text = item.evidence
            if item.exception_required and item.exception_details:
                ev_text += f"\n[EXCEPTION: {item.exception_details}]"
            if matching_act and f"[{matching_act.action_id}]" not in ev_text:
                ev_text += f" [{matching_act.action_id}]"
            format_cell_text_and_highlight(row.cells[7], ev_text)

        style_table(table, col_widths=[0.7, 2.0, 1.4, 1.1, 0.9, 0.9, 1.0, 1.6])
        doc.add_paragraph().paragraph_format.space_after = Pt(8)

    def render_action_required_table(
        self, doc: docx.Document, baseline: StartupKitBaseline
    ):
        """Render the structured Action Required table with open exceptions, clarifications, and score recovery."""
        action_items = baseline.action_required_items
        if not action_items:
            exceptions_count = len([i for i in baseline.readiness_checklist if i.exception_required or i.status == "Exception Required"])
            if exceptions_count > 0 or baseline.open_questions:
                action_items = ReadinessScoringEngine.generate_action_required_items(baseline)
                baseline.action_required_items = action_items

        if action_items:
            self._render_action_required_table(doc, baseline, action_items)

    def _render_action_required_table(
        self, doc: docx.Document, baseline: StartupKitBaseline, action_items: List[ActionRequiredItem]
    ):
        """Render the structured Action Required table with open exceptions, clarifications, and score recovery."""
        total_recovery = sum(a.score_recovery_delta for a in action_items)
        target_score = min(100.0, round(baseline.readiness_score + total_recovery, 1))
        if target_score >= 85.0:
            target_cat = "READY FOR GATE REVIEW (Green)"
        elif target_score >= 70.0:
            target_cat = "CONDITIONAL / EXCEPTION REQUIRED (Amber)"
        else:
            target_cat = "NOT READY / REWORK REQUIRED (Red)"

        recovery_summary = (
            f"Total Score Recovery Potential: +{total_recovery:.1f}% -> "
            f"Target Achievable Readiness Score: {target_score:.1f}% ({target_cat})\n"
            f"Resolving the {len(action_items)} validation points / clarifications below prior to or during the Mobilize "
            f"kickoff closes all open governance gaps and unblocks full gate clearance."
        )

        add_callout_box(
            doc,
            text=recovery_summary,
            title="Action Required: Unresolved Validation Points / Clarifications Pending Mobilize Kickoff:",
            bg_color=COLOR_WARNING_BG_HEX,
            border_color="D97706",
        )

        table = doc.add_table(rows=1, cols=8)
        headers = [
            "Action ID",
            "Type",
            "Gate ID",
            "Related Artifact",
            "Validation Finding & Required Action",
            "Owner",
            "Deadline",
            "Score Impact",
        ]
        for idx, name in enumerate(headers):
            table.cell(0, idx).text = name

        for item in action_items:
            row = table.add_row()
            row.cells[0].text = item.action_id
            if row.cells[0].paragraphs and row.cells[0].paragraphs[0].runs:
                row.cells[0].paragraphs[0].runs[0].bold = True

            row.cells[1].text = item.item_type
            if item.item_type == "Open Exception":
                set_cell_background(row.cells[1], COLOR_WARNING_BG_HEX)
            else:
                set_cell_background(row.cells[1], COLOR_LIGHT_BG_HEX)

            row.cells[2].text = item.checklist_id
            row.cells[3].text = item.related_artifact
            row.cells[4].text = f"{item.finding_description}\n• Action: {item.required_action}"
            row.cells[5].text = item.owner
            row.cells[6].text = item.resolution_deadline
            row.cells[7].text = f"+{item.score_recovery_delta:.1f}%"

        style_table(table, col_widths=[0.8, 1.1, 0.8, 1.3, 2.5, 1.0, 1.0, 0.8])
        doc.add_paragraph().paragraph_format.space_after = Pt(6)
