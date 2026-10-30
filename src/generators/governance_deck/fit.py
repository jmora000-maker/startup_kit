"""Text fitting and typography utilities for PS Governance Kickoff Deck (HTL-72)."""

from src.generators.client_deck.fit import (
    estimate_text_height,
    fit_deliverables_for_block,
    select_fitting_font_size,
    truncate_at_clause,
    wrap_lines,
)

__all__ = [
    "estimate_text_height",
    "fit_deliverables_for_block",
    "select_fitting_font_size",
    "truncate_at_clause",
    "wrap_lines",
]
