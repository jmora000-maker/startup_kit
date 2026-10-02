"""Unit tests for CLI Readiness Telemetry Reporter."""

import io
import sys
from pathlib import Path
import pytest

from src.core.models import (
    StartupKitBaseline,
    GateDecision,
    ActionRequiredItem,
    GovernanceContext,
)
from src.scoring.cli_reporter import (
    format_readiness_cli_summary,
    print_readiness_cli_summary,
    format_deck_export_summary,
    print_deck_export_summary,
)
from src.generators.onboarding_deck import OnboardingDeckResult


@pytest.fixture
def sample_baseline() -> StartupKitBaseline:
    return StartupKitBaseline(
        project_name="Pfizer Clinical Analytics",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        governance_context=GovernanceContext(
            project_name="Pfizer Clinical Analytics",
            client_name="Pfizer Inc.",
            governance_tier="Partnered",
            contract_type="Time and Materials",
            delivery_manager="Jane Doe",
            talent_pm="John Smith",
            pmo_lead="Sarah Connor",
            executive_summary="Modernization of clinical analytics data pipelines.",
        ),
        readiness_score=74.2,
        readiness_breakdown={
            "D1_Mandatory_Controls": 72.0,
            "D2_Deliverables_Rigor": 68.0,
            "D3_Talent_Staffing": 80.0,
            "D4_Commercial_Risk": 78.0,
        },
        gate_decision=GateDecision(
            decision_status="Approved with Exception",
            target_mobilize_date="2026-10-01",
            tier_description="Partnered",
            readiness_score=74.2,
            author_name="Sarah Connor",
        ),
        action_required_items=[
            ActionRequiredItem(
                action_id="ACT-01",
                item_type="Open Exception",
                checklist_id="G01-03",
                related_artifact="Deliverables and Acceptance Matrix",
                finding_description="Deliverable DEL-01 missing owner",
                required_action="Assign named owner",
                owner="Talent PM",
                score_recovery_delta=3.5,
            ),
            ActionRequiredItem(
                action_id="ACT-02",
                item_type="Open Clarification",
                checklist_id="G01-04",
                related_artifact="Milestone Delivery Plan",
                finding_description="Milestone M01 date unconfirmed",
                required_action="Confirm date with client",
                owner="Delivery Manager",
                score_recovery_delta=3.0,
            ),
        ],
        sla_met=True,
    )


def test_cli_summary_formatting(sample_baseline: StartupKitBaseline):
    """Verify formatted CLI output contains expected headers, score, breakdown, and recovery potential."""
    output_path = Path("output/Pfizer_Startup_Kit.docx")
    summary = format_readiness_cli_summary(sample_baseline, output_path, use_color=False)

    assert "TOPTAL PMO STARTUP READINESS GATEWAY (G-01) SUMMARY" in summary
    assert "Project Name             : Pfizer Clinical Analytics" in summary
    assert "Client Sponsor           : Pfizer Inc." in summary
    assert "COMPOSITE READINESS SCORE: 74.2% [CONDITIONAL / EXCEPTION REQUIRED - AMBER]" in summary
    assert "GATE DECISION STATUS     : Approved with Exception" in summary
    assert "Mandatory Controls   (D1 - 40% Weight): 72.0%" in summary
    assert "Deliverables Rigor   (D2 - 25% Weight): 68.0%" in summary
    assert "Open Exceptions      : 1 item(s) (G01-03)" in summary
    assert "Open Clarifications  : 1 item(s) (G01-04)" in summary
    assert "Total Score Recovery : +6.5% -> Achievable Target: 80.7% (AMBER)" in summary
    assert "output\\Pfizer_Startup_Kit.docx" in summary or "output/Pfizer_Startup_Kit.docx" in summary


def test_cli_summary_color_coding(sample_baseline: StartupKitBaseline):
    """Verify ANSI color codes for Green, Amber, and Red score thresholds."""
    output_path = Path("output/Doc.docx")

    # Amber (74.2%)
    summary_amber = format_readiness_cli_summary(sample_baseline, output_path, use_color=True)
    assert "\033[93m" in summary_amber  # Amber code

    # Green (90.0%)
    sample_baseline.readiness_score = 90.0
    summary_green = format_readiness_cli_summary(sample_baseline, output_path, use_color=True)
    assert "\033[92m" in summary_green  # Green code

    # Red (60.0%)
    sample_baseline.readiness_score = 60.0
    summary_red = format_readiness_cli_summary(sample_baseline, output_path, use_color=True)
    assert "\033[91m" in summary_red  # Red code


def test_cli_summary_plain_fallback(sample_baseline: StartupKitBaseline, capsys):
    """Verify print_readiness_cli_summary prints clean output without ANSI escape codes when use_color=False."""
    output_path = Path("output/Doc.docx")
    print_readiness_cli_summary(sample_baseline, output_path, use_color=False)

    captured = capsys.readouterr().out
    assert "\033[" not in captured
    assert "COMPOSITE READINESS SCORE: 74.2%" in captured


def test_deck_cli_summary_formatting():
    """Verify format_deck_export_summary output contains expected headers, slide count, and trace elements (DECK-16)."""
    res = OnboardingDeckResult(
        file_path=Path("output/ARC_Talent_Onboarding_Deck.pptx"),
        manifest_path=Path("output/ARC_Talent_Onboarding_Deck.trace.json"),
        slides_count=6,
        trace_entries_count=42,
        project_name="ARC Genomics",
    )
    summary = format_deck_export_summary(res, use_color=False)
    assert "TALENT ONBOARDING DECK" in summary
    assert "6 slides" in summary
    assert "42 elements" in summary
    assert "100% (42/42 elements traced)" in summary
    assert "ARC_Talent_Onboarding_Deck.pptx" in summary
