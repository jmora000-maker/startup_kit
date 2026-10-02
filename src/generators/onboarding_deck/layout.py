"""Layout constants and the fit estimate for the Talent Team Onboarding Deck (DECK-21, Appendix K.1).

The writer sizes every text frame and table with these functions, and INV-32 re-runs them on the
written file, so a deck is accepted only if the estimate that built it still holds.
"""

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence

# --- Geometry (inches) -------------------------------------------------------------------------
CONTENT_X0 = 0.83
CONTENT_X1 = 12.50
CONTENT_Y0 = 1.70
CONTENT_Y1 = 6.70
CONTENT_WIDTH = round(CONTENT_X1 - CONTENT_X0, 2)
CONTENT_HEIGHT = round(CONTENT_Y1 - CONTENT_Y0, 2)

CARD_INSET = 0.20
CARD_CORNER_ADJ = 6153
CARD_OUTLINE_PT = 1.1
THREE_ACROSS_X = (0.83, 4.81, 8.79)
THREE_ACROSS_W = 3.71
TWO_ACROSS_X = (0.83, 6.75)
TWO_ACROSS_W = 5.75
CARD_H = 4.58  # the template's card height; a card may grow to CONTENT_HEIGHT when its text needs it

# --- Table geometry (inches) -------------------------------------------------------------------
TABLE_HEADER_H = 0.40
TABLE_MIN_ROW_H = 0.30
CELL_MARGIN_LR = 0.06
CELL_MARGIN_TB = 0.04
KEY_FACTS_COLS = (1.35, 1.96)
SCHEDULE_COLS = (2.00, 2.60, 1.90, 5.17)
ACCEPTANCE_COLS = (0.80, 6.00, 0.89)
RISK_COLS = (1.50, 3.70, 0.85, 1.60, 3.00, 1.02)

# --- Typography (points) -----------------------------------------------------------------------
TITLE_PT = 28.0
KICKER_PT = 11.0
CARD_HEADING_PT = 16.0
CARD_HEADING_MIN_PT = 14.0
CARD_SUBHEADING_PT = 11.0
BODY_PT = 11.0
BODY_MIN_PT = 10.5
TABLE_HEADER_PT = 12.0
TABLE_BODY_PT = 10.0
TABLE_BODY_MIN_PT = 10.0
TABLE_DELIVERABLES_MIN_PT = 9.0

HEADING_SPACE_AFTER_PT = 8.0
SUBHEADING_SPACE_BEFORE_PT = 8.0
SUBHEADING_SPACE_AFTER_PT = 2.0
BODY_SPACE_AFTER_PT = 4.0
BULLET_INDENT_IN = 0.17

AVG_CHAR_WIDTH_FACTOR = 0.5
LINE_HEIGHT_FACTOR = 1.2


def wrap_lines(text: str, width_in: float, size_pt: float) -> int:
    """Estimated rendered line count (DECK-21 (5)): characters per line from the frame width at an average
    character width of 0.5 x font size; a paragraph's lines are its characters divided by that, rounded up."""
    chars_per_line = max(1, int((width_in * 72.0) / (AVG_CHAR_WIDTH_FACTOR * size_pt)))
    total = 0
    for raw_line in str(text).splitlines() or [""]:
        total += max(1, math.ceil(len(raw_line.strip()) / chars_per_line))
    return total


def text_height_pt(text: str, width_in: float, size_pt: float) -> float:
    return wrap_lines(text, width_in, size_pt) * LINE_HEIGHT_FACTOR * size_pt


@dataclass(frozen=True)
class Para:
    """One paragraph for the fit estimate."""
    text: str
    size_pt: float
    space_before_pt: float = 0.0
    space_after_pt: float = 0.0
    indent_in: float = 0.0


def frame_height_pt(paras: Sequence[Para], width_in: float) -> float:
    """Estimated rendered height of a text frame of the given inner width."""
    total = 0.0
    for p in paras:
        total += p.space_before_pt + p.space_after_pt
        total += text_height_pt(p.text, width_in - p.indent_in, p.size_pt)
    return total


def frame_fits(paras: Sequence[Para], width_in: float, height_in: float) -> bool:
    return frame_height_pt(paras, width_in) <= height_in * 72.0 + 1e-6


def card_inner(card_w: float = THREE_ACROSS_W, card_h: float = CARD_H) -> tuple:
    """(width, height) of a card's text frame."""
    return round(card_w - 2 * CARD_INSET, 2), round(card_h - 2 * CARD_INSET, 2)


def cell_height_in(text: str, col_w_in: float, size_pt: float) -> float:
    """Estimated height of a table cell, margins included."""
    inner = col_w_in - 2 * CELL_MARGIN_LR
    return text_height_pt(text, inner, size_pt) / 72.0 + 2 * CELL_MARGIN_TB


def row_height_in(cells: Sequence[str], col_widths: Sequence[float], sizes: Sequence[float], min_h: float = TABLE_MIN_ROW_H) -> float:
    h = min_h
    for text, w, s in zip(cells, col_widths, sizes):
        h = max(h, cell_height_in(text, w, s))
    return round(math.ceil(h * 100) / 100.0, 2)
