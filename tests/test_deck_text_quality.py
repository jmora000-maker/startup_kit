"""INV-31 (text quality, DECK-05, DECK-09): broken-input unit tests and text-rule tests."""

import pytest

from src.generators.onboarding_deck.textrules import (
    clause_prefix,
    has_compliant_cut,
    is_balanced,
    normalize_text,
    prefix_violation,
)
from src.tools import deck_checks
from tests.deck_fixtures import add_text, blank_deck, entry, trace

NAMES = [
    "Backend Integration/Load Tests and Performance Engineering Spike",
    "Production Smoke Tests and 48-Hour Defect Watch",
]


def _inv31(prs, entries=(), names=NAMES, files=()):
    return [str(v) for v in deck_checks.check_inv31(prs, list(entries), names, files) if v.inv_id == "INV-31"]


def _deck_with(text, notes=None):
    prs, slides = blank_deck(3)
    add_text(slides[1], 0.83, 1.7, 5.0, 1.0, [text])
    if notes is not None:
        slides[1].notes_slide.notes_text_frame.text = notes
    return prs


def test_clean_deck_text_passes():
    assert _inv31(_deck_with("DEL-02 Production Smoke Tests and 48-Hour Defect Watch")) == []


@pytest.mark.parametrize("text, needle", [
    ("Client provides design system access by the...", "ellipsis"),
    ("Client provides access…", "ellipsis"),
    ("Latency targets (Snowflake sizing,", "unbalanced"),
    ("Tokens, design files]", "unbalanced"),
    ('He said "ready', "unbalanced"),
    ("Purpose: build the platform..", "doubled punctuation"),
    ("Owners,, dates", "doubled punctuation"),
    ("DEL-07 Backend Integration/Load Tests and Performance Engineering", "shortened name"),
    ("DEL-17 Production Smoke Tests and 48-Hour Defect", "shortened name"),
])
def test_inv31_fails_on_broken_text(text, needle):
    msgs = _inv31(_deck_with(text))
    assert any(needle in m for m in msgs), f"INV-31 did not flag {text!r}: {msgs}"


def test_inv31_applies_to_speaker_notes():
    msgs = _inv31(_deck_with("ok", notes="TALKING POINTS:\n• First client prerequisite is required by M1: access (code library.\n\nSOURCES: Kit"))
    assert any("speaker notes" in m and "unbalanced" in m for m in msgs)


def test_inv31_requires_manifest_entries_for_talking_points():
    prs = _deck_with("ok", notes="TALKING POINTS:\n• The project runs in 4 phases.\n\nSOURCES: Kit")
    assert any("no trace manifest entry" in m for m in _inv31(prs))
    tp = entry(2, "Notes", "Talking point 1", "The project runs in 4 phases.", trace("Workbook", "Project Schedule", "M1", "Milestone"), values=["P1"])
    assert not any("no trace manifest entry" in m for m in _inv31(prs, [tp]))


def test_inv31_flags_filler_words_in_notes():
    prs = _deck_with("ok", notes="TALKING POINTS:\n• Active alignment ensures rapid resolution.\n\nSOURCES: Kit")
    assert any("evaluative filler" in m for m in _inv31(prs))


def test_inv31_flags_shortened_file_names():
    prs = _deck_with("Open ARC_Genomics_Platform_Startup_Kit now")
    msgs = _inv31(prs, files=["ARC_Genomics_Platform_Startup_Kit.docx"])
    assert any("shortened file name" in m for m in msgs)
    assert _inv31(_deck_with("Open ARC_Genomics_Platform_Startup_Kit.docx now"), files=["ARC_Genomics_Platform_Startup_Kit.docx"]) == []


def test_inv31_does_not_flag_a_different_complete_name():
    names = ["P2a Services and Data accepted", "P2a Services and Data"]
    assert _inv31(_deck_with("P2a Services and Data"), names=names) == []


# --- text rules --------------------------------------------------------------------------------
def test_prefix_rules():
    src = "Negative tests pass and the scan is clean. Findings in Toptal-built components are remediated; findings in Client-built components are reported."
    assert prefix_violation(src, src) is None
    assert prefix_violation("Negative tests pass and the scan is clean.", src) is None
    assert prefix_violation("Negative tests pass and the scan is clean. Findings in Toptal-built components are remediated", src) is None
    assert prefix_violation("Negative tests pass and the scan is", src)
    assert prefix_violation("Negative tests pass and the scan is clean. Findings in Toptal-built components are", src)


def test_comma_is_not_a_boundary():
    src = "Targets are referential integrity 100%, representative query patterns validated, controls audited, classification coverage validated."
    assert prefix_violation("Targets are referential integrity 100%,", src)
    assert prefix_violation("Targets are referential integrity 100%", src)


def test_parenthetical_close_is_a_boundary_only_when_complete():
    src = "Use query observability (HS-4942) to attribute misses and report Client-owned causes."
    assert prefix_violation("Use query observability (HS-4942)", src) is None
    assert prefix_violation("Use query observability (HS-4942", src)


def test_clause_prefix_never_cuts_mid_phrase():
    src = "Latency and render-time targets may be missed because they depend on Client-owned components (Snowflake sizing, Azure AD, CloudFront, OneGWAS, network)."
    out = clause_prefix(src, 15)
    assert out == src  # no compliant cut exists, so the text is shown whole and sized by DECK-21
    assert not has_compliant_cut(src, 15)
    two = "Negative tests pass and the scan is clean. Findings in Toptal-built components are remediated; findings in Client-built components are reported."
    assert clause_prefix(two, 15) == "Negative tests pass and the scan is clean."
    assert is_balanced(clause_prefix(two, 15))


def test_normalize_removes_action_tags_and_collapses_whitespace():
    assert normalize_text("Toptal  [ACT-01: Assign named delivery owner for DEL-01. (+2.2% Recovery)]") == "Toptal"
