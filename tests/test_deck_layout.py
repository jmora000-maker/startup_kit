"""DECK-21 (layout and alignment) and INV-32: broken-input unit tests on synthetic decks."""

import pytest
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.util import Inches, Pt

from src.tools import deck_checks
from tests.deck_fixtures import add_card, add_table, add_text, blank_deck


def _inv32(prs):
    return [str(v) for v in deck_checks.check_inv32(prs) if v.inv_id == "INV-32"]


def _good_card_deck():
    prs, slides = blank_deck(2)
    s = slides[1]
    add_card(s, 0.83, 1.70, 3.71, 4.58)
    add_text(s, 1.03, 1.90, 3.31, 4.18, [("Client roles", 16.0), ("Client Approver: signs each milestone.", 11.0)], name="Card text")
    return prs, s


def test_inv32_passes_on_a_well_formed_card_and_table():
    prs, s = _good_card_deck()
    add_table(s, 4.81, 1.70, [0.80, 6.00, 0.89], [["ID", "Acceptance Criteria", "Gate"], ["DEL-01", "Shell load P50 < 1.5s.", "M1"]])
    assert _inv32(prs) == []


def test_inv32_fails_on_a_table_that_runs_off_the_slide():
    """L4: a long overflow row in a narrow column wraps past the slide bottom."""
    prs, s = _good_card_deck()
    rows = [["ID", "Acceptance Criteria", "Gate"]] + [["DEL-%02d" % i, "Criteria text", "M1"] for i in range(1, 14)]
    rows.append(["+6 more: DEL-14, DEL-15, DEL-16, DEL-17, DEL-18, DEL-19 (see Startup Kit · Deliverables and Acceptance Matrix)", "", ""])
    add_table(s, 4.81, 1.70, [0.80, 6.00, 0.89], rows)
    msgs = _inv32(prs)
    assert any("outside the content area" in m and "Table" in m for m in msgs), msgs


def test_inv32_fails_when_text_overflows_its_frame():
    prs, slides = blank_deck(2)
    add_card(slides[1], 0.83, 1.70, 3.71, 4.58)
    add_text(slides[1], 1.03, 1.90, 3.31, 4.18, [("Client roles", 16.0)] + [("A long bullet about delivery scope and the client approver for each milestone gate " * 3, 11.0)] * 8, name="Card text")
    assert any("fit estimate" in m for m in _inv32(prs))


@pytest.mark.parametrize("size", [9.5, 10.0])
def test_inv32_fails_on_body_text_below_the_minimum(size):
    prs, slides = blank_deck(2)
    add_card(slides[1], 0.83, 1.70, 3.71, 4.58)
    add_text(slides[1], 1.03, 1.90, 3.31, 4.18, [("Working rhythm", 16.0), ("Kickoff Call: One-time", size)], name="Card text")
    assert any("below the 10.5 pt minimum" in m for m in _inv32(prs))


def test_inv32_fails_on_table_text_below_ten_points():
    prs, slides = blank_deck(3)
    add_table(slides[1], 0.83, 1.70, [1.35, 1.96], [["Client Sponsor", "Acme"]], size=9.5)
    assert any("below the 10 pt minimum" in m for m in _inv32(prs))


def test_inv32_allows_nine_points_only_in_the_slide_3_deliverables_column():
    prs, slides = blank_deck(3)
    header = ["Workstream", "Milestone", "Dates", "Deliverables"]
    shape = add_table(slides[2], 0.83, 1.70, [2.0, 2.6, 1.9, 5.17], [header, ["P1", "M1", "2026-10-05", "DEL-01 Shell"]], size=10.0)
    shape.table.cell(1, 3).text_frame.paragraphs[0].runs[0].font.size = Pt(9)
    assert _inv32(prs) == []
    shape.table.cell(1, 1).text_frame.paragraphs[0].runs[0].font.size = Pt(9)
    assert any("R1C1" in m and "below the 10 pt minimum" in m for m in _inv32(prs))


def test_inv32_fails_on_shapes_outside_the_content_area():
    prs, slides = blank_deck(2)
    add_card(slides[1], 0.30, 1.70, 3.71, 4.58)
    add_card(slides[1], 4.81, 1.70, 3.71, 5.40)
    msgs = _inv32(prs)
    assert sum("outside the content area" in m for m in msgs) == 2


def test_inv32_fails_on_overlapping_content_shapes():
    """L1/L3: a heading text frame that covers the table inside its card."""
    prs, slides = blank_deck(2)
    s = slides[1]
    add_card(s, 0.83, 1.70, 3.71, 4.58)
    add_text(s, 1.03, 1.90, 3.31, 4.18, [("Key facts", 16.0)], name="Card text")
    add_table(s, 1.03, 2.40, [1.35, 1.96], [["Client Sponsor", "Acme"]])
    assert any("overlap" in m for m in _inv32(prs))


def test_inv32_card_text_frame_must_be_inset_and_heading_one_line():
    prs, slides = blank_deck(2)
    add_card(slides[1], 0.83, 1.70, 3.71, 4.58)
    add_text(slides[1], 0.95, 1.80, 3.47, 4.38, [("A very long card heading that cannot fit on one line", 16.0)], name="Card text")
    msgs = _inv32(prs)
    assert any("not inset" in m for m in msgs)
    assert any("wraps to more than one line" in m for m in msgs)


def test_inv32_card_text_frame_must_not_autofit():
    prs, slides = blank_deck(2)
    add_card(slides[1], 0.83, 1.70, 3.71, 4.58)
    box = add_text(slides[1], 1.03, 1.90, 3.31, 4.18, [("Heading", 16.0)], name="Card text")
    box.text_frame.auto_size = MSO_AUTO_SIZE.SHAPE_TO_FIT_TEXT
    assert any("autofit off" in m for m in _inv32(prs))


def test_inv32_flags_runs_without_an_explicit_font_size():
    prs, slides = blank_deck(2)
    b = slides[1].shapes.add_textbox(Inches(0.83), Inches(1.7), Inches(3), Inches(1))
    b.text_frame.text = "Text with no explicit size"
    assert any("no explicit font size" in m for m in _inv32(prs))
