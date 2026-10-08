"""CLI Telemetry Reporter for Startup Readiness Scores and G-01 Gate Decisions."""

import os
import sys
from pathlib import Path
from typing import Optional, Union, Sequence
from src.core.models import StartupKitBaseline
from src.generators.pmo_workbook import PMOWorkbookResult
from src.generators.onboarding_deck import OnboardingDeckResult


def format_readiness_cli_summary(
    baseline: StartupKitBaseline,
    output_path: Union[Path, Sequence[Path]],
    use_color: Optional[bool] = None
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
        if baseline.governance_context and baseline.governance_context.client_name
        else (
            getattr(baseline.charter, "client_name", None)
            or getattr(baseline.charter, "client_sponsor", None)
            or "[Client Sponsor]"
        )
    )

    sep_double = "=" * 80
    sep_single = "-" * 80

    if isinstance(output_path, (str, Path)):
        paths = [output_path]
    else:
        paths = list(output_path)

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
        " REPORT ARTIFACTS:" if len(paths) > 1 else " REPORT ARTIFACT:",
    ]

    for p in paths:
        res_p = p.resolve() if hasattr(p, "resolve") else p
        lines.append(f"   • Output File Path     : {res_p}")

    lines.append(sep_double)

    return "\n".join(lines)


def print_readiness_cli_summary(
    baseline: StartupKitBaseline,
    output_path: Union[Path, Sequence[Path]],
    use_color: Optional[bool] = None
) -> None:
    """Print the formatted readiness CLI summary to standard output."""
    summary_text = format_readiness_cli_summary(baseline, output_path, use_color=use_color)
    print(summary_text)


def format_workbook_export_summary(
    result: PMOWorkbookResult,
    use_color: Optional[bool] = None
) -> str:
    """Format an executive CLI summary of the Project Delivery Workbook export."""
    if use_color is None:
        if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
            use_color = False
        else:
            use_color = True

    if use_color:
        COLOR_AMBER = "\033[93m"
        COLOR_CYAN = "\033[96m"
        COLOR_BOLD = "\033[1m"
        COLOR_RESET = "\033[0m"
    else:
        COLOR_AMBER = ""
        COLOR_CYAN = ""
        COLOR_BOLD = ""
        COLOR_RESET = ""

    sep_double = "=" * 80
    sep_single = "-" * 80

    ws_count = result.workstreams_count if result.workstreams_count else 0
    ms_count = result.milestones_count if result.milestones_count else result.schedule_rows
    cp_count = getattr(result, "checkpoints_count", 0)
    cp_str = f" (+{cp_count} checkpoints)" if cp_count > 0 else ""

    lines = [
        sep_double,
        f"{COLOR_BOLD}{COLOR_CYAN}                     PROJECT DELIVERY WORKBOOK{COLOR_RESET}",
        sep_single,
        f"   • Project Schedule     : {ws_count} workstreams, {ms_count} milestones{cp_str}",
        f"   • WBS                  : {result.wbs_rows} elements ({result.task_rows} tasks)",
        f"   • RAID Log             : {result.raid_rows} items",
    ]

    if result.evidence_flags > 0:
        lines.append(f"   • Evidence flags       : {result.evidence_flags} deliverable(s) flagged with potential misattached evidence (v3 A9)")

    if result.excluded_items > 0:
        lines.append(f"   • Excluded readiness   : {result.excluded_items} item(s) dropped by defensive filter")

    if result.unmapped_deliverables > 0:
        unmapped_str = f"   • Unmapped deliverables: {result.unmapped_deliverables} (placed under final milestone - review)"
        if use_color:
            unmapped_str = f"{COLOR_AMBER}{unmapped_str}{COLOR_RESET}"
        lines.append(unmapped_str)

    # Validation findings summary (OUT-09)
    if result.validation and result.validation.findings:
        repaired_n = len(result.validation.repaired)
        warn_n = len(result.validation.warnings)
        err_n = len(result.validation.errors)
        lines.append(sep_single)
        lines.append(f"   {COLOR_BOLD}EXTRACTION VALIDATION (Section 4):{COLOR_RESET}")
        lines.append(f"   • Findings             : {repaired_n} repaired, {warn_n} warning(s), {err_n} error(s)")
        for f in result.validation.findings[:5]:
            lines.append(f"     - [{f.invariant_id}] ({f.severity.upper()}): {f.message}")

    # Traceability Self-Check (v3 A13, v5 A22, v6 Section 1.1)
    if result.traceability:
        lines.append(sep_single)
        lines.append(f"   {COLOR_BOLD}TRACEABILITY SELF-CHECK (v3 A13):{COLOR_RESET}")
        for elem, data in result.traceability.items():
            if elem == "SOW Stories" and "SOW References" in result.traceability:
                continue
            if elem in ("SOW References", "SOW Stories"):
                if data.get("empty"):
                    lines.append(f"   • {elem:<20}: No SOW work items identified")
                    continue
                base_n = data.get("in_baseline", 0)
                wb_n = data.get("in_workbook", 0)
                missing = data.get("missing_ids", [])
                missing_str = ", ".join(missing) if missing else "None"
                syn_note = " (SOW has no item IDs; synthetic references used)" if data.get("synthetic") else ""
                lines.append(f"   • {elem:<20}: {base_n} in baseline -> {wb_n} in workbook (Missing: {missing_str}){syn_note}")
            else:
                base_n = data.get("in_baseline", 0)
                wb_n = data.get("in_workbook", 0)
                missing = data.get("missing_ids", [])
                missing_str = ", ".join(missing) if missing else "None"
                lines.append(f"   • {elem:<20}: {base_n} in baseline -> {wb_n} in workbook (Missing: {missing_str})")

    res_path = result.file_path.resolve() if hasattr(result.file_path, "resolve") else result.file_path
    lines.append(sep_single)
    lines.append(f"   • Output File Path     : {res_path}")
    lines.append(sep_double)

    return "\n".join(lines)


def print_workbook_export_summary(
    result: PMOWorkbookResult,
    use_color: Optional[bool] = None
) -> None:
    """Print the formatted Project Delivery Workbook export summary to standard output."""
    summary_text = format_workbook_export_summary(result, use_color=use_color)
    print(summary_text)


def format_deck_export_summary(
    result: OnboardingDeckResult,
    use_color: Optional[bool] = None
) -> str:
    """Format an executive CLI summary of the Talent Onboarding Deck export (DECK-16)."""
    if use_color is None:
        if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
            use_color = False
        else:
            use_color = True

    if use_color:
        COLOR_CYAN = "\033[96m"
        COLOR_BOLD = "\033[1m"
        COLOR_RESET = "\033[0m"
    else:
        COLOR_CYAN = ""
        COLOR_BOLD = ""
        COLOR_RESET = ""

    sep_double = "=" * 80
    sep_single = "-" * 80

    res_path = result.file_path.resolve() if hasattr(result.file_path, "resolve") else result.file_path
    man_path = result.manifest_path.resolve() if hasattr(result.manifest_path, "resolve") else result.manifest_path

    total = result.elements_total or result.trace_entries_count
    traced = result.elements_traced if result.elements_total else result.trace_entries_count
    pct = f"{100.0 * traced / total:.0f}" if total else "100"

    lines = [
        sep_double,
        f"{COLOR_BOLD}{COLOR_CYAN}                     TALENT ONBOARDING DECK{COLOR_RESET}",
        sep_single,
        f"   • Slides               : {result.slides_count} slides (Cover, Charter, Schedule, Acceptance, Risks, Collaboration, Your Project Kit)",
        f"   • Content elements     : {total} elements",
        f"   • Elements traced      : {pct}% ({traced}/{total} elements traced)",
        f"   • Omitted-ID rows used : {result.overflow_rows}",
        f"   • Trace Manifest       : {man_path}",
        sep_single,
        f"   • Output File Path     : {res_path}",
        sep_double,
    ]

    return "\n".join(lines)


def print_deck_export_summary(
    result: OnboardingDeckResult,
    use_color: Optional[bool] = None
) -> None:
    """Print the formatted Talent Onboarding Deck export summary to standard output."""
    summary_text = format_deck_export_summary(result, use_color=use_color)
    print(summary_text)
