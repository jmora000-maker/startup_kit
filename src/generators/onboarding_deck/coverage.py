"""Trace coverage of the written deck (DECK-05 (1), DECK-16): every text on a slide is a traced value or a fixed label.

Used by INV-26 and by the CLI summary, so the percentage the CLI prints is measured on the written file,
not assumed.
"""

import re
from typing import Any, Dict, List, Sequence, Tuple

from src.generators.onboarding_deck import fixed_text as FT
from src.generators.onboarding_deck.textrules import normalize_text

GLUE = re.compile(r"[\s\x00•·:;,()\[\]\-–—/&.+]|->")


def unit_texts(slide: Any, slide_no: int) -> List[Tuple[str, str]]:
    """(shape name, text unit) for every content text on a slide: paragraphs and table cell lines."""
    out: List[Tuple[str, str]] = []
    for sh in slide.shapes:
        if sh.is_placeholder and slide_no > 1:
            continue  # title and kicker are fixed labels
        if sh.has_text_frame:
            for p in sh.text_frame.paragraphs:
                if p.text.strip():
                    out.append((sh.name, p.text.strip()))
        if getattr(sh, "has_table", False) and sh.has_table:
            for r in sh.table.rows:
                for c in r.cells:
                    for line in c.text.splitlines():
                        if line.strip():
                            out.append((sh.name, line.strip()))
    return out


def _residue(text: str, phrases: Sequence[str]) -> str:
    s = FT.OVERFLOW_PATTERN.sub("\x00", text)
    for ph in phrases:
        s = s.replace(ph, "\x00")
    return GLUE.sub("", s)


def coverage(entries: List[Dict[str, Any]], prs: Any) -> Tuple[int, List[Tuple[int, str, str]]]:
    """(content text units, the uncovered ones) over every slide of the deck.

    A unit is covered when removing traced values and fixed labels leaves nothing but punctuation.
    Units made only of fixed labels are not content and are not counted.
    """
    by_slide: Dict[int, set] = {}
    for e in entries:
        if str(e.get("element", "")).startswith("Talking point"):
            continue
        by_slide.setdefault(e.get("slide"), set()).add(normalize_text(e.get("displayed_value")))
    fixed = FT.fixed_phrases()
    content = 0
    uncovered: List[Tuple[int, str, str]] = []
    for idx, slide in enumerate(prs.slides, start=1):
        values = {x for x in by_slide.get(idx, set()) if x}
        phrases = sorted(values | set(fixed), key=len, reverse=True)
        for shape_name, text in unit_texts(slide, idx):
            if not _residue(text, sorted(fixed, key=len, reverse=True)):
                continue  # fixed labels only
            content += 1
            if _residue(text, phrases):
                uncovered.append((idx, shape_name, text))
    return content, uncovered
