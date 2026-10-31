"""Unit tests for financial sanitization helper (HTL-77)."""

import pytest
import re
from src.config import sanitize_financial_text


def test_positive_financial_examples():
    """Verify dollar amounts and financial figures are properly scrubbed and readable."""
    cases = [
        (
            "$19,650 fee billed upon formal client acceptance.",
            "Fee billed upon formal client acceptance.",
        ),
        (
            "Planned for weeks 1-6 from the start date; Fee of $26,808 is invoiced on acceptance; Client sign-off by Mike Magwire and Satya after UAT",
            "Planned for weeks 1-6 from the start date; Fee is invoiced on acceptance; Client sign-off by Mike Magwire and Satya after UAT",
        ),
        (
            "Planned for weeks 7-16 from the start date; Fee of $60,356 is invoiced on acceptance; UAT is limited to two runs per milestone",
            "Planned for weeks 7-16 from the start date; Fee is invoiced on acceptance; UAT is limited to two runs per milestone",
        ),
        (
            "Planned for weeks 17-21 from the start date; Fee of $68,210 is invoiced on acceptance; Further design-system components or changes are handled by Change Order",
            "Planned for weeks 17-21 from the start date; Fee is invoiced on acceptance; Further design-system components or changes are handled by Change Order",
        ),
        (
            "Planned for weeks 22-26 from the start date; this is the final project completion date; Fee of $44,991 is invoiced on acceptance; No holiday breaks or stoppages are assumed in the schedule",
            "Planned for weeks 22-26 from the start date; this is the final project completion date; Fee is invoiced on acceptance; No holiday breaks or stoppages are assumed in the schedule",
        ),
        (
            "Total fixed fee of $150,000 for deliverables across all phases.",
            "Total fixed fee for deliverables across all phases.",
        ),
        (
            "Rate of $150/hr capped at 40 hours per week.",
            "Rate capped at 40 hours per week.",
        ),
        (
            "Invoiced at 120 USD / hour upon completion.",
            "Invoiced upon completion.",
        ),
        (
            "Milestone payment of $25,000.00 subject to client sign-off.",
            "Milestone payment subject to client sign-off.",
        ),
    ]

    for raw, expected in cases:
        result = sanitize_financial_text(raw)
        assert result == expected, f"Failed on raw: {raw!r}\nGot: {result!r}\nExpected: {expected!r}"


def test_negative_legitimate_numeric_content_preservation():
    """Verify that all legitimate non-financial numbers remain completely untouched."""
    legitimate_samples = [
        # Dates
        "2026-11-18",
        "Planned completion date is 2026-10-26",
        "Signoff deadline: 11/18/2026",
        "Revision 160 · October 21, 2026",
        # Percentages / Thresholds
        "0%",
        "100%",
        "Target SLA ≥ 95% of in-scope workloads",
        "Recovery delta (+2.0% Recovery)",
        "System availability 99.99% required",
        # Durations, Intervals & Counts
        "18",
        "20",
        "=INT(I7-TODAY())",
        "Review window: 5 business days",
        "Remediation within 3 business days",
        "3-hour compliance intervals",
        "Planned for weeks 1-6 from the start date",
        "UAT is limited to two runs per milestone",
        "3 repeated attempts before escalation",
        "10-day buffer applied",
        # Identifiers & Codes
        "1.0",
        "1.2.1",
        "Deliverable DEL-01",
        "Milestone MS-01",
        "Risk RA-01",
        "Phase P2a Discovery",
        "7 Rs disposition framework",
        "Action G01-04 required",
        "Gate G-01 checklist",
        "Per spec v3 A7 and v4 A16",
        "Rev 2 update",
        # Lowercase bullet lines and criteria without financial content
        "• remote mount P95 < 1s.",
        "• token acquisition P95 < 800ms",
        "remote mount P95 < 1s.",
        "token acquisition P95 < 800ms",
        "• system latency < 50ms under peak load",
        "acceptance criteria line item starting lower-case",
    ]

    for sample in legitimate_samples:
        result = sanitize_financial_text(sample)
        assert result == sample, f"Non-financial sample was modified!\nOriginal: {sample!r}\nResult:   {result!r}"
