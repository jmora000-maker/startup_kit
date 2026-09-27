"""CLI Telemetry Reporter for Startup Readiness Scores and G-01 Gate Decisions."""

import os
import sys
from pathlib import Path
from typing import Optional
from src.core.models import StartupKitBaseline


def format_readiness_cli_summary(
    baseline: StartupKitBaseline, output_path: Path, use_color: Optional[bool] = None
) -> str:
    """Format an executive CLI summary dashboard for the Startup Readiness Gateway (G-01)."""
    if use_color is None:
        # Check NO_COLOR env var or non-interactive stdout
        if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
            use_color = False
        else:
            use_color = True

    # ANSI Color codes
    if use_color:
        COLOR_GREEN = "\033[92m"
        COLOR_AMBER = "\033[93m"
        COLOR_RED = "\033[91m"
        COLOR_CYAN = "\033[96m"
        COLOR_BOLD = "\033[1m"
        COLOR_RESET = "\033[0m"
    else:
        COLOR_GREEN = ""
        COLOR_AMBER = ""
        COLOR_RED = ""
        COLOR_CYAN = ""
        COLOR_BOLD = ""
        COLOR_RESET = ""

    score = baseline.readiness_score
    if score >= 85.0:
        cat_label = "READY FOR GATE REVIEW"
        cat_color = "GREEN"
        status_ansi = COLOR_GREEN
    elif score >= 70.0:
        cat_label = "CONDITIONAL / EXCEPTION REQUIRED"
        cat_color = "AMBER"
        status_ansi = COLOR_AMBER
    else:
        cat_label = "NOT READY / REWORK REQUIRED"
        cat_color = "RED"
        status_ansi = COLOR_RED

    gate_decision_str = (
        baseline.gate_decision.gate_decision_status
        if baseline.gate_decision and hasattr(baseline.gate_decision, "gate_decision_status")
        else (
            baseline.gate_decision.decision_status
            if baseline.gate_decision and hasattr(baseline.gate_decision, "decision_status")
            else "Pending Review"
        )
    )

    sla_str = (
        "MET (Created within 1 business day)"
        if baseline.sla_met
        else "BREACHED (Drafting exceeded 1-day SLA)"
    )

    # Dimension Breakdown
    breakdown = baseline.readiness_breakdown or {}
    d1 = breakdown.get("mandatory_g01_controls", breakdown.get("D1_Mandatory_Controls", 0.0))
    d2 = breakdown.get("deliverable_acceptance_rigor", breakdown.get("D2_Deliverables_Rigor", 0.0))
    d3 = breakdown.get("talent_staffing_readiness", breakdown.get("D3_Talent_Staffing", 0.0))
    d4 = breakdown.get("commercial_risk_mitigation", breakdown.get("D4_Commercial_Risk", 0.0))

    # Action required summary
    action_items = baseline.action_required_items or []
    exceptions = [a for a in action_items if a.item_type == "Open Exception"]
    clarifications = [a for a in action_items if a.item_type == "Open Clarification"]

    exc_ids_str = (
        f" ({', '.join(a.checklist_id for a in exceptions)})" if exceptions else ""
    )
    cla_ids_str = (
        f" ({', '.join(a.checklist_id for a in clarifications)})" if clarifications else ""
    )

    total_recovery = sum(a.score_recovery_delta for a in action_items)
    target_score = min(100.0, round(score + total_recovery, 1))
    target_cat_color = "GREEN" if target_score >= 85.0 else ("AMBER" if target_score >= 70.0 else "RED")

    client_name = (
        baseline.governance_context.client_name
        if baseline.governance_context
        else (baseline.charter.client_sponsor if baseline.charter else "[Client Sponsor]")
    )

    sep_double = "=" * 80
    sep_single = "-" * 80

    lines = [
        sep_double,
        f"{COLOR_BOLD}{COLOR_CYAN}           TOPTAL PMO STARTUP READINESS GATEWAY (G-01) SUMMARY{COLOR_RESET}",
        sep_double,
        f" Project Name             : {baseline.project_name}",
        f" Client Sponsor           : {client_name}",
        f" Governance Tier          : {baseline.governance_tier} | SLA: {sla_str}",
        sep_single,
        f" COMPOSITE READINESS SCORE: {COLOR_BOLD}{status_ansi}{score:.1f}% [{cat_label} - {cat_color}]{COLOR_RESET}",
        f" GATE DECISION STATUS     : {COLOR_BOLD}{gate_decision_str}{COLOR_RESET}",
        sep_single,
        " SCORE BREAKDOWN:",
        f"   • Mandatory Controls   (D1 - 40% Weight): {d1:.1f}%",
        f"   • Deliverables Rigor   (D2 - 25% Weight): {d2:.1f}%",
        f"   • Talent Staffing      (D3 - 20% Weight): {d3:.1f}%",
        f"   • Commercial & Risk    (D4 - 15% Weight): {d4:.1f}%",
        sep_single,
        " ACTION REQUIRED SUMMARY:",
        f"   • Open Exceptions      : {len(exceptions)} item(s){exc_ids_str}",
        f"   • Open Clarifications  : {len(clarifications)} item(s){cla_ids_str}",
        f"   • Total Score Recovery : +{total_recovery:.1f}% -> Achievable Target: {target_score:.1f}% ({target_cat_color})",
        sep_single,
        " REPORT ARTIFACT:",
        f"   • Output File Path     : {output_path.resolve() if hasattr(output_path, 'resolve') else output_path}",
        sep_double,
    ]

    return "\n".join(lines)


def print_readiness_cli_summary(
    baseline: StartupKitBaseline, output_path: Path, use_color: Optional[bool] = None
) -> None:
    """Print the formatted readiness CLI summary to standard output."""
    summary_text = format_readiness_cli_summary(baseline, output_path, use_color=use_color)
    print(summary_text)
