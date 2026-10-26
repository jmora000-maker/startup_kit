"""Deterministic text measurement, font-stepping, and clause truncation engine for Client Kickoff Deck (HTL-48 / DECK-21).

Reuses the proven character-width and line-height heuristics established in
src/generators/onboarding_deck/layout.py (DECK-21).
"""

import math
import re
import textwrap
from typing import Sequence, Tuple

from src.generators.onboarding_deck.layout import (
    AVG_CHAR_WIDTH_FACTOR,
    LINE_HEIGHT_FACTOR,
)

BOLD_CHAR_WIDTH_FACTOR = 0.58


def wrap_lines(
    text: str,
    width_in: float,
    size_pt: float,
    char_width_factor: float = AVG_CHAR_WIDTH_FACTOR,
) -> int:
    """Estimated rendered line count with word wrapping and character width factor (HTL-48 / HTL-49)."""
    chars_per_line = max(1, int((width_in * 72.0) / (char_width_factor * size_pt)))
    total = 0
    for raw_line in str(text).splitlines() or [""]:
        clean = raw_line.strip()
        if not clean:
            total += 1
            continue
        wrapped = textwrap.wrap(clean, width=chars_per_line, break_long_words=True)
        total += max(1, len(wrapped))
    return total


def estimate_text_height(
    text: str,
    width_in: float,
    size_pt: float,
    line_height_factor: float = LINE_HEIGHT_FACTOR,
    char_width_factor: float = AVG_CHAR_WIDTH_FACTOR,
    is_bold: bool = False,
) -> float:
    """Estimated rendered text height in points based on font size, box width, and typography weight (DECK-21 / HTL-48 / HTL-49)."""
    if not text:
        return 0.0
    factor = BOLD_CHAR_WIDTH_FACTOR if is_bold else char_width_factor
    num_lines = wrap_lines(text, width_in, size_pt, char_width_factor=factor)
    return num_lines * line_height_factor * size_pt


def truncate_at_clause(
    text: str,
    max_chars: int,
    suffix: str = "...",
) -> str:
    """Truncate text at a natural sentence or clause boundary within max_chars limit."""
    clean = str(text or "").strip()
    if len(clean) <= max_chars:
        return clean

    target_len = max(10, max_chars - len(suffix))
    slice_text = clean[:target_len]

    # Find last natural clause boundary (. , ; :)
    match = re.search(r"([.;:,])\s+[^.;:,]*$", slice_text)
    if match and match.start(1) > int(target_len * 0.5):
        boundary_pos = match.start(1)
        return clean[:boundary_pos].rstrip() + suffix

    # Fallback to last whitespace boundary
    last_space = slice_text.rfind(" ")
    if last_space > int(target_len * 0.5):
        return clean[:last_space].rstrip() + suffix

    return slice_text.rstrip() + suffix


def select_fitting_font_size(
    text: str,
    width_in: float,
    max_height_in: float,
    candidate_sizes: Sequence[float],
    min_font_floor: float = 8.0,
    is_bold: bool = False,
) -> Tuple[float, str]:
    """Select the largest candidate font size that fits within (width_in, max_height_in).

    If the text still does not fit at the minimum candidate font size, returns the smallest
    candidate size and text (or truncated text if caller uses truncation).
    """
    if not text:
        return candidate_sizes[0] if candidate_sizes else 11.0, ""

    max_height_pt = max_height_in * 72.0
    sorted_sizes = sorted(candidate_sizes, reverse=True)

    for sz in sorted_sizes:
        h = estimate_text_height(text, width_in, sz, is_bold=is_bold)
        if h <= max_height_pt + 1e-4:
            return sz, text

    floor_size = sorted_sizes[-1] if sorted_sizes else min_font_floor
    return floor_size, text
