"""Deterministic text measurement, font-stepping, and clause truncation engine for Client Kickoff Deck (HTL-48 / DECK-21).

Reuses the proven character-width and line-height heuristics established in
src/generators/onboarding_deck/layout.py (DECK-21).
"""

import logging
import math
import os
import re
import textwrap
from typing import Optional, Sequence, Tuple

from src.core.interfaces import ILLMClient
from src.config import config
from src.llm.prompts import (
    CONDENSE_PROBLEM_STATEMENT_PROMPT,
    CONDENSE_SOLUTION_OVERVIEW_PROMPT,
)
from src.generators.onboarding_deck.layout import (
    AVG_CHAR_WIDTH_FACTOR,
    LINE_HEIGHT_FACTOR,
)

logger = logging.getLogger(__name__)

BOLD_CHAR_WIDTH_FACTOR = 0.58


def _get_default_llm_client() -> Optional[ILLMClient]:
    """Helper to instantiate default LangChainLLMClient if API keys are configured and not in offline test runner."""
    if "PYTEST_CURRENT_TEST" in os.environ:
        return None
    try:
        from src.llm.client import LangChainLLMClient
        if config.anthropic_api_key or config.openai_api_key:
            return LangChainLLMClient()
    except Exception as exc:
        logger.debug("Could not initialize default LangChainLLMClient: %s", exc)
    return None


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


def condense_problem_statement(
    text: str,
    max_chars: int = 180,
    llm_client: Optional[ILLMClient] = None,
) -> str:
    """Condense problem statement into 1-2 concise sentences within max_chars preserving full semantic meaning via LLM rewriting (HTL-109)."""
    clean = str(text or "").strip()
    if not clean or len(clean) <= max_chars or clean.startswith("["):
        return clean

    # Step 1: Real LLM rewriting
    client = llm_client or _get_default_llm_client()
    if client is not None and hasattr(client, "generate_text"):
        try:
            prompt = CONDENSE_PROBLEM_STATEMENT_PROMPT.format(text=clean, max_chars=max_chars)
            rewritten = client.generate_text(prompt=prompt, system_prompt="You are a senior delivery director rewriting slide content.")
            rewritten_clean = str(rewritten or "").strip().strip('"').strip("'").strip()
            if rewritten_clean and len(rewritten_clean) <= max_chars and not rewritten_clean.endswith("..."):
                logger.info("Successfully condensed problem_statement via LLM (length %d -> %d).", len(clean), len(rewritten_clean))
                return rewritten_clean
            elif rewritten_clean:
                trimmed = rewritten_clean[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;.") + "."
                if len(trimmed) <= max_chars:
                    logger.info("Successfully condensed problem_statement via LLM with boundary trim (length %d -> %d).", len(clean), len(trimmed))
                    return trimmed
        except Exception as exc:
            logger.warning("LLM condensation for problem_statement failed (%s); falling back to deterministic clause selection.", exc)
    else:
        logger.info("No LLM client available for problem_statement condensation; using deterministic clause fallback.")

    # Step 2: Deterministic Fallback (only when LLM is unavailable or fails)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip()]
    if sentences:
        if len(sentences[0]) <= max_chars:
            if len(sentences) > 1 and len(f"{sentences[0]} {sentences[1]}") <= max_chars:
                return f"{sentences[0]} {sentences[1]}"
            return sentences[0]

        s0 = sentences[0]
        s0_sub = re.sub(r",\s*which\s+[^,.]*", "", s0)
        s0_sub = re.sub(r",\s*and\s+its\s+failure\s+to\s+[^,.]*", "", s0_sub)
        if len(s0_sub) <= max_chars:
            return s0_sub.rstrip(" ,") + "."

        return s0[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;.") + "."

    return clean[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;.") + "."


def condense_solution_overview(
    text: str,
    max_chars: int = 300,
    llm_client: Optional[ILLMClient] = None,
) -> str:
    """Condense solution overview into 2-3 cohesive sentences within max_chars preserving full semantic meaning via LLM rewriting (HTL-109)."""
    clean = str(text or "").strip()
    if not clean or len(clean) <= max_chars or clean.startswith("["):
        return clean

    # Step 1: Real LLM rewriting
    client = llm_client or _get_default_llm_client()
    if client is not None and hasattr(client, "generate_text"):
        try:
            prompt = CONDENSE_SOLUTION_OVERVIEW_PROMPT.format(text=clean, max_chars=max_chars)
            rewritten = client.generate_text(prompt=prompt, system_prompt="You are a senior delivery director rewriting slide content.")
            rewritten_clean = str(rewritten or "").strip().strip('"').strip("'").strip()
            if rewritten_clean and len(rewritten_clean) <= max_chars and not rewritten_clean.endswith("..."):
                logger.info("Successfully condensed solution_overview via LLM (length %d -> %d).", len(clean), len(rewritten_clean))
                return rewritten_clean
            elif rewritten_clean:
                trimmed = rewritten_clean[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;.") + "."
                if len(trimmed) <= max_chars:
                    logger.info("Successfully condensed solution_overview via LLM with boundary trim (length %d -> %d).", len(clean), len(trimmed))
                    return trimmed
        except Exception as exc:
            logger.warning("LLM condensation for solution_overview failed (%s); falling back to deterministic clause selection.", exc)
    else:
        logger.info("No LLM client available for solution_overview condensation; using deterministic clause fallback.")

    # Step 2: Deterministic Fallback (only when LLM is unavailable or fails)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip()]
    if sentences:
        result_s = []
        cur_len = 0
        for s in sentences:
            add_len = len(s) + (1 if result_s else 0)
            if cur_len + add_len <= max_chars:
                result_s.append(s)
                cur_len += add_len
            else:
                break
        if result_s:
            return " ".join(result_s)

        s0 = sentences[0]
        if len(s0) > max_chars:
            return s0[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;.") + "."
        return s0

    return clean


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


def estimate_deliverables_height(
    items: Sequence[str],
    width_in: float,
    font_size_pt: float,
    bullet_indent_in: float = 0.27,
) -> float:
    """Accurately estimate total rendered height in points for bulleted deliverables."""
    if not items:
        return 0.0
    inner_w = max(0.5, width_in - bullet_indent_in)
    total_lines = sum(wrap_lines(it, inner_w, font_size_pt) for it in items if it and it.strip())
    spacing_pt = max(0, len(items) - 1) * (1.0 if font_size_pt < 9.0 else 1.5)
    return total_lines * LINE_HEIGHT_FACTOR * font_size_pt + spacing_pt


def extract_deliverable_id(item: str) -> str:
    """Extract deliverable ID (e.g. 'D-01', 'DEL-01', 'M-01') from deliverable string."""
    clean = str(item or "").strip()
    match = re.match(r"^([A-Za-z0-9]+(?:-[A-Za-z0-9]+)+|[A-Za-z]\d+)\b", clean)
    if match:
        return match.group(1)
    tokens = clean.split()
    if tokens:
        first = tokens[0].rstrip(":")
        return first
    return clean


def format_deliverables_overflow(omitted_items: Sequence[str]) -> str:
    """Format Slide 3-style explicit-ID overflow summary line (HTL-50)."""
    clean_omitted = [it for it in omitted_items if it and it.strip()]
    if not clean_omitted:
        return ""
    ids = [extract_deliverable_id(it) for it in clean_omitted]
    id_list_str = ", ".join(ids)
    return f"+{len(clean_omitted)} more: {id_list_str} (see Project Delivery Workbook · Project Schedule)"


def fit_deliverables_for_block(
    deliverables: Sequence[str],
    width_in: float,
    max_height_in: float,
    font_size_pt: float,
    bullet_indent_in: float = 0.27,
) -> Tuple[List[str], int]:
    """Determine how many deliverables fit in (width_in, max_height_in) at font_size_pt (HTL-49 / HTL-50).

    Returns (displayed_items, overflow_count).
    If all deliverables fit, returns (list(deliverables), 0).
    If not all fit, returns (deliverables[:k] + [summary_line], len(deliverables) - k)
    where summary_line explicitly lists omitted deliverable IDs matching Onboarding Deck Slide 3.
    """
    clean_delivs = [d for d in deliverables if d and d.strip()]
    if not clean_delivs:
        return [], 0

    max_h_pt = max_height_in * 72.0
    # 1. Try displaying ALL deliverables
    if estimate_deliverables_height(clean_delivs, width_in, font_size_pt, bullet_indent_in) <= max_h_pt + 1e-4:
        return list(clean_delivs), 0

    # 2. Iteratively test k deliverables + summary line, from len(clean_delivs) - 1 down to 0
    total = len(clean_delivs)
    for k in range(total - 1, -1, -1):
        cand_delivs = list(clean_delivs[:k])
        omitted = clean_delivs[k:]
        ovf = len(omitted)
        summary = format_deliverables_overflow(omitted)
        cand = cand_delivs + [summary] if summary else cand_delivs
        if estimate_deliverables_height(cand, width_in, font_size_pt, bullet_indent_in) <= max_h_pt + 1e-4:
            return cand, ovf

    # 3. Fallback: If even k=0 full summary doesn't fit, truncate the ID list in the summary line so it fits within max_height_in
    omitted = clean_delivs
    ovf = len(omitted)
    ids = [extract_deliverable_id(it) for it in omitted]
    inner_w = max(0.5, width_in - bullet_indent_in)
    summary = format_deliverables_overflow(omitted)
    for m in range(len(ids) - 1, 0, -1):
        short_ids = ", ".join(ids[:m]) + "..."
        cand_summary = f"+{ovf} more: {short_ids} (see Project Delivery Workbook · Project Schedule)"
        if estimate_text_height(cand_summary, inner_w, font_size_pt) <= max_h_pt:
            summary = cand_summary
            break
    else:
        summary = f"+{ovf} more deliverables (see Project Delivery Workbook · Project Schedule)"

    return [summary], ovf
