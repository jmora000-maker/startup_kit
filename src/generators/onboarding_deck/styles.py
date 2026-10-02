"""Presentation and layout style tokens for Talent Team Onboarding Deck (Appendix K.1, DECK-13)."""

from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

# Slide Dimensions (16:9 widescreen)
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)

# Color Palette (Appendix K.1)
COLOR_DEEP_NAVY = RGBColor(0x0F, 0x17, 0x2A)  # #0F172A
COLOR_SLATE = RGBColor(0x47, 0x55, 0x69)      # #475569
COLOR_ACCENT_BLUE = RGBColor(0x20, 0x4E, 0xCF)# #204ECF
COLOR_MUTED_GRAY = RGBColor(0x64, 0x74, 0x8B) # #64748B
COLOR_LIGHT_GRAY = RGBColor(0xF8, 0xFA, 0xFC) # #F8FAFC
COLOR_BORDER_GRAY = RGBColor(0xE2, 0xE8, 0xF0)# #E2E8F0
COLOR_WHITE = RGBColor(0xFF, 0xFF, 0xFF)       # #FFFFFF

# RAG Status Colors (Appendix K.1, K.2)
COLOR_RED_TEXT = RGBColor(0x99, 0x1B, 0x1B)   # #991B1B
COLOR_RED_BG = RGBColor(0xFE, 0xE2, 0xE2)     # #FEE2E2

COLOR_AMBER_TEXT = RGBColor(0x92, 0x40, 0x0E) # #92400E
COLOR_AMBER_BG = RGBColor(0xFE, 0xF3, 0xC7)   # #FEF3C7

COLOR_GREEN_TEXT = RGBColor(0x16, 0x65, 0x34) # #166534
COLOR_GREEN_BG = RGBColor(0xDC, 0xFC, 0xE7)   # #DCFCE7

# Typography Settings (DECK-13, Appendix K.1)
FONT_TITLE = "Proxima Nova"
FONT_BODY = "Calibri"

FONT_SIZE_TITLE = Pt(28)
FONT_SIZE_KICKER = Pt(11)
FONT_SIZE_CARD_HEADER = Pt(16)
FONT_SIZE_CARD_SUBHEADER = Pt(11)
FONT_SIZE_BODY = Pt(11)
FONT_SIZE_TABLE_HEADER = Pt(12)
FONT_SIZE_TABLE_BODY = Pt(10)
FONT_SIZE_SOURCES = Pt(8)
