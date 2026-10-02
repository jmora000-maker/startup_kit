"""Shared text rules for the Talent Team Onboarding Deck (DECK-05, DECK-08, INV-26, INV-31).

The builder uses these to cut text only at clause boundaries; the checkers use the same functions to
verify what was written, so the rule is defined once.
"""

import re
from typing import List, Optional

from src.generators.formatting import ACTION_TAG_REGEX

ELLIPSIS_REGEX = re.compile(r"\.\.\.|…")
DOUBLED_PUNCT_REGEX = re.compile(r"\.\.|,,|;;|::|!!|\?\?")
SENTENCE_END_CHARS = ".?!"
BOUNDARY_CHARS = ".?!;:"
BRACKET_PAIRS = {")": "(", "]": "[", "}": "{"}
OPENERS = set(BRACKET_PAIRS.values())


def normalize_text(text: Optional[str]) -> str:
    """DECK-05 (3) normalization: action tags removed, whitespace collapsed."""
    if not text:
        return ""
    return " ".join(ACTION_TAG_REGEX.sub("", str(text)).split())


def source_units(cell_text: Optional[str]) -> List[str]:
    """A source cell and each of its bullet lines, normalized (a deck bullet may show one line of a cell)."""
    units: List[str] = []
    whole = normalize_text(cell_text)
    if whole:
        units.append(whole)
    for line in str(cell_text or "").splitlines():
        line = line.strip()
        if line.startswith("•"):
            line = line[1:]
        norm = normalize_text(line)
        if norm and norm not in units:
            units.append(norm)
    return units


def word_count(text: str) -> int:
    return len(text.split())


def has_ellipsis(text: str) -> bool:
    return bool(ELLIPSIS_REGEX.search(text or ""))


def has_doubled_punctuation(text: str) -> Optional[str]:
    m = DOUBLED_PUNCT_REGEX.search(text or "")
    return m.group(0) if m else None


def is_balanced(text: str) -> bool:
    """True when brackets, parentheses, braces, and double quotation marks are all balanced."""
    stack: List[str] = []
    straight_quotes = 0
    curly_depth = 0
    for ch in text or "":
        if ch in OPENERS:
            stack.append(ch)
        elif ch in BRACKET_PAIRS:
            if not stack or stack[-1] != BRACKET_PAIRS[ch]:
                return False
            stack.pop()
        elif ch == '"':
            straight_quotes += 1
        elif ch == "“":
            curly_depth += 1
        elif ch == "”":
            curly_depth -= 1
            if curly_depth < 0:
                return False
    return not stack and straight_quotes % 2 == 0 and curly_depth == 0


def _boundary_ok(shown: str, rest: str) -> bool:
    """True when a prefix `shown` of a longer text, followed by `rest`, ends at a DECK-05 clause boundary."""
    if not shown or shown.endswith(","):
        return False
    if shown[-1] in BOUNDARY_CHARS and (rest[:1] == " " or rest == ""):
        return True
    if rest[:1] in tuple(BOUNDARY_CHARS) and rest[1:2] in ("", " "):
        return shown[-1] not in ", " and not shown.endswith(" -")
    if rest.startswith(" - "):
        return True
    if shown.endswith(")") and is_balanced(shown) and (rest[:1] == " " or rest[:1] in tuple(BOUNDARY_CHARS)):
        return True
    return False


def prefix_violation(shown: str, source: str) -> Optional[str]:
    """Why `shown` is not an acceptable display of `source` (DECK-05 (3)), or None when it is acceptable.

    Acceptable: equal to the source after normalization, or a prefix of it that ends at a sentence or
    clause boundary, has no ellipsis, and leaves no unbalanced bracket, parenthesis, or quotation mark.
    """
    shown_n = normalize_text(shown)
    source_n = normalize_text(source)
    if not shown_n:
        return "empty text"
    if has_ellipsis(shown_n):
        return "contains an ellipsis"
    if shown_n == source_n:
        return None
    if not source_n.startswith(shown_n):
        return "is not the source text or a prefix of it"
    if not is_balanced(shown_n):
        return "leaves an unbalanced bracket, parenthesis, or quotation mark"
    if shown_n.endswith(","):
        return "ends at a comma"
    if not _boundary_ok(shown_n, source_n[len(shown_n):]):
        return "is cut mid-phrase (not at a sentence or clause boundary)"
    return None


MIN_CLAUSE_WORDS = 3
PLACEHOLDER_TEXT_REGEX = re.compile(
    r"^\[?(?:CONFIRMATION REQUIRED|TBD|UNDEFINED|UNASSIGNED(?: - TO BE CONFIRMED)?|TO BE CONFIRMED)\]?$", re.IGNORECASE
)


def is_placeholder_text(text: Optional[str]) -> bool:
    """DECK-10: empty, or a bare placeholder such as [CONFIRMATION REQUIRED], UNASSIGNED, [TBD] (after tag removal)."""
    clean = normalize_text(text)
    return not clean or PLACEHOLDER_TEXT_REGEX.match(clean) is not None


def _candidates(clean: str):
    """(candidate prefix, strong) for every compliant cut of `clean`, shortest first.

    Strong cuts end at a sentence or clause mark (. ? ! ; :) or before ' - '; weak cuts end at the close
    of a complete parenthetical.
    """
    for i in range(1, len(clean)):
        if clean[i:i + 1] in tuple(SENTENCE_END_CHARS) and clean[i + 1:i + 2] in ("", " "):
            continue  # keep the sentence's own full stop
        head = clean[:i].rstrip()
        candidate = head[:-1].rstrip() if head and head[-1] in ";:" else head
        if not candidate or word_count(candidate) < MIN_CLAUSE_WORDS or prefix_violation(candidate, clean) is not None:
            continue
        strong = candidate[-1] in SENTENCE_END_CHARS or head[-1] in BOUNDARY_CHARS or clean[i:i + 1] in tuple(BOUNDARY_CHARS) or clean[i:i + 3] == " - "
        yield candidate, strong


def clause_prefix(text: str, max_words: int) -> str:
    """The first clause of `text` (DECK-05, DECK-08).

    Text that already fits in `max_words` is returned whole. Otherwise the first sentence or clause is
    returned when it fits; failing that, the longest prefix that ends at the close of a complete
    parenthetical and fits. When no compliant cut fits the limit, the shortest compliant cut is returned
    even though it is longer than the limit: DECK-05 forbids any cut that is not at a boundary, so the
    element is sized by DECK-21 instead of cut again.
    """
    clean = normalize_text(text)
    if not clean or word_count(clean) <= max_words:
        return clean
    weak_best = ""
    for candidate, strong in _candidates(clean):
        if strong:
            # a first clause longer than the limit still beats showing more text: it is the shortest compliant cut
            return candidate if (word_count(candidate) <= max_words or not weak_best) else weak_best
        if word_count(candidate) <= max_words:
            weak_best = candidate
    return weak_best or clean


def first_sentence(text: str) -> str:
    """The first sentence of `text` (whole text when it is a single sentence), per DECK-05."""
    clean = normalize_text(text)
    for candidate, strong in _candidates(clean):
        if strong and candidate[-1] in SENTENCE_END_CHARS:
            return candidate
    return clean


def has_compliant_cut(text: str, max_words: int) -> bool:
    """True when `text` is within `max_words` or has a boundary-ended prefix within the limit."""
    clean = normalize_text(text)
    return word_count(clean) <= max_words or word_count(clause_prefix(clean, max_words)) <= max_words
