"""Tests for Deck talking points generator and sources lines (DECK-09, Appendix K.3)."""

from src.generators.onboarding_deck.talking_points import (
    build_slide1_talking_points,
    build_slide2_talking_points,
    build_slide3_talking_points,
    build_slide4_talking_points,
    build_slide5_talking_points,
    build_slide6_talking_points,
)


def test_talking_points_formatting_and_sources():
    """Verify that talking points for all 6 slides have bullets and SOURCES line."""
    tp1 = build_slide1_talking_points("Client A", "2026-10-05", "Provided")
    assert "TALKING POINTS:" in tp1
    assert "SOURCES: Startup Kit · Project Charter" in tp1
    assert len([l for l in tp1.splitlines() if l.startswith("•")]) in range(2, 5)

    tp2 = build_slide2_talking_points("Fixed Bid", "Partnered", "Lead", "DM", "TPM", "Purpose", "Escalation", 3, "2026-10-05", "2027-01-01")
    assert "TALKING POINTS:" in tp2
    assert "SOURCES: Startup Kit · Project Charter" in tp2
    assert len([l for l in tp2.splitlines() if l.startswith("•")]) in range(3, 7)

    tp3 = build_slide3_talking_points(3, "2026-10-05", "2027-01-01", 3, 2, 3, 10, "SOW")
    assert "TALKING POINTS:" in tp3
    assert "SOURCES: Project Delivery Workbook · Project Schedule" in tp3
    assert len([l for l in tp3.splitlines() if l.startswith("•")]) in range(3, 7)

    tp4 = build_slide4_talking_points("10 days", "Approver", 10)
    assert "TALKING POINTS:" in tp4
    assert "SOURCES: Project Delivery Workbook · WBS" in tp4
    assert len([l for l in tp4.splitlines() if l.startswith("•")]) in range(3, 7)

    tp5 = build_slide5_talking_points(2, "RAID-01", "Latency risk")
    assert "TALKING POINTS:" in tp5
    assert "SOURCES: Project Delivery Workbook · RAID Log" in tp5
    assert len([l for l in tp5.splitlines() if l.startswith("•")]) in range(3, 7)

    tp6 = build_slide6_talking_points(4, 5, "M1", "Prereq")
    assert "TALKING POINTS:" in tp6
    assert "SOURCES: Startup Kit · Stakeholder and Responsibility Model" in tp6
    assert len([l for l in tp6.splitlines() if l.startswith("•")]) in range(3, 7)
