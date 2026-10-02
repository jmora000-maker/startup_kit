"""Tests for the talking points and SOURCES lines (DECK-09, Appendix K.3)."""

import inspect
import json
import re

import pytest

from src.generators.onboarding_deck import fixed_text as FT
from src.generators.onboarding_deck import talking_points as TP
from src.tools.deck_checks import FILLER_REGEX
from tests.deck_bundle import FIXTURES, build_bundle, notes_points


def _manifest_points(bundle):
    entries = json.loads(bundle["manifest_path"].read_text(encoding="utf-8"))["entries"]
    return [e for e in entries if e["element"].startswith("Talking point")]


def test_every_talking_point_on_slides_2_to_6_has_a_manifest_entry_and_a_traced_value(arc_bundle):
    entries = _manifest_points(arc_bundle)
    for idx in range(2, 7):
        slide = arc_bundle["prs"].slides[idx - 1]
        points = notes_points(slide)
        assert 3 <= len(points) <= 6
        listed = {e["displayed_value"] for e in entries if e["slide"] == idx}
        assert set(points) <= listed, f"slide {idx}: talking points without a manifest entry"
        for e in entries:
            if e["slide"] == idx:
                assert e["traces"] and e["values"], "a talking point carries traced values"
                assert all(v.lower() in e["displayed_value"].lower() for v in e["values"])


def test_cover_and_project_kit_slides_have_two_to_four_points(arc_bundle):
    for idx in (1, 7):
        assert 2 <= len(notes_points(arc_bundle["prs"].slides[idx - 1])) <= 4


def test_fixed_guidance_only_on_cover_and_project_kit(arc_bundle):
    fixed = set(TP.COVER_GUIDANCE) | set(TP.KIT_SLIDE_GUIDANCE)
    for idx in range(2, 7):
        assert not (set(notes_points(arc_bundle["prs"].slides[idx - 1])) & fixed)


def test_no_filler_untraced_claims_or_doubled_punctuation(arc_bundle):
    for idx, slide in enumerate(arc_bundle["prs"].slides, start=1):
        for p in notes_points(slide):
            assert not FILLER_REGEX.search(p), p
            assert ".." not in p and ",," not in p, p
            assert len(p.split()) <= 30, p
            assert "are assigned" not in p
    assert "mitigations" not in " ".join(p.lower() for p in notes_points(arc_bundle["prs"].slides[4]))


def test_placeholders_read_naturally(arc_bundle):
    points = notes_points(arc_bundle["prs"].slides[1])
    leads = next(p for p in points if p.startswith("Delivery Manager:"))
    assert leads == "Delivery Manager: to be confirmed; Talent PM: to be confirmed; PMO Lead: to be confirmed."
    assert not any("To be confirmed," in p or "To be confirmed." in p for p in points)


def test_sources_line_names_each_section_and_sheet_used(arc_bundle):
    for idx in range(1, 8):
        notes = arc_bundle["prs"].slides[idx - 1].notes_slide.notes_text_frame.text
        assert "TALKING POINTS:" in notes and "SOURCES:" in notes
    s5 = arc_bundle["prs"].slides[4].notes_slide.notes_text_frame.text
    assert "SOURCES: Startup Kit · Project Startup Charter; Project Delivery Workbook · RAID Log" in s5
    s4 = arc_bundle["prs"].slides[3].notes_slide.notes_text_frame.text
    assert "SOW Interpretation Summary" in s4 and "Deliverables and Acceptance Matrix" in s4 and "WBS" in s4


def test_slide_5_early_warning_comes_from_the_workbook_trigger(arc_bundle):
    points = notes_points(arc_bundle["prs"].slides[4])
    assert "Early warning for RAID-01: Missed p95 targets in benchmarks or load tests." in points


def test_templates_are_plain_sentences_without_project_data():
    """P-08: templates hold no project, client, or SOW names; K.3 templates read as specified."""
    source = inspect.getsource(TP)
    for forbidden in ("ARC", "Syngenta", "Pfizer", "HS-4", "Toptal", "Genomics"):
        assert forbidden not in source
    assert TP.phases_and_span(4, "2026-10-05", "2027-04-02") == "The project runs in 4 phases, from 2026-10-05 to 2027-04-02."
    assert TP.gate_due("M2", "P2a", "2027-01-22", "M1") == "M2 (P2a) is due 2027-01-22; it starts after M1 is accepted."
    assert TP.gate_due("M1", "P1", "2026-11-13", None) == "M1 (P1) is due 2026-11-13."


def test_sentence_never_doubles_punctuation():
    assert TP.sentence("Apex Global Retail Inc.") == "Apex Global Retail Inc."
    assert TP.sentence("Escalate to the PMO Lead") == "Escalate to the PMO Lead."
    assert TP.spoken("To be confirmed", True) == "to be confirmed" and TP.spoken("Jane Doe", False) == "Jane Doe"


@pytest.mark.parametrize("name", FIXTURES)
def test_talking_point_counts_hold_on_every_fixture(name, tmp_path):
    bundle = build_bundle(tmp_path, name)
    for idx, slide in enumerate(bundle["prs"].slides, start=1):
        n = len(notes_points(slide))
        assert (2 <= n <= 4) if idx in (1, 7) else (3 <= n <= 6), (name, idx, n)
