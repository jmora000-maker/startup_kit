"""Tests for Deck presentation styles and typography (DECK-13, Appendix K.1)."""

import pytest
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

from src.generators.onboarding_deck.styles import (
    SLIDE_WIDTH,
    SLIDE_HEIGHT,
    COLOR_DEEP_NAVY,
    COLOR_ACCENT_BLUE,
    COLOR_WHITE,
    COLOR_RED_TEXT,
    COLOR_RED_BG,
    COLOR_AMBER_TEXT,
    COLOR_AMBER_BG,
    COLOR_GREEN_TEXT,
    COLOR_GREEN_BG,
    FONT_TITLE,
    FONT_BODY,
    FONT_SIZE_TITLE,
    FONT_SIZE_TABLE_HEADER,
)


def test_deck_styles_constants():
    """Verify Appendix K.1 style tokens."""
    assert SLIDE_WIDTH == Inches(13.333)
    assert SLIDE_HEIGHT == Inches(7.5)

    assert COLOR_DEEP_NAVY == RGBColor(0x0F, 0x17, 0x2A)
    assert COLOR_ACCENT_BLUE == RGBColor(0x20, 0x4E, 0xCF)
    assert COLOR_WHITE == RGBColor(0xFF, 0xFF, 0xFF)

    assert COLOR_RED_TEXT == RGBColor(0x99, 0x1B, 0x1B)
    assert COLOR_RED_BG == RGBColor(0xFE, 0xE2, 0xE2)
    assert COLOR_AMBER_TEXT == RGBColor(0x92, 0x40, 0x0E)
    assert COLOR_AMBER_BG == RGBColor(0xFE, 0xF3, 0xC7)
    assert COLOR_GREEN_TEXT == RGBColor(0x16, 0x65, 0x34)
    assert COLOR_GREEN_BG == RGBColor(0xDC, 0xFC, 0xE7)

    assert FONT_TITLE == "Proxima Nova"
    assert FONT_BODY == "Calibri"
    assert FONT_SIZE_TITLE == Pt(28)
    assert FONT_SIZE_TABLE_HEADER == Pt(12)
