"""Shared, single-source-of-truth value lists for the Streamlit app's screens.

Item 4 of the follow-up UI-correctness pass found that the Generate tab (src/review_ui/generate.py)
and the Fact Review tab (src/review_ui/app.py) each defined their own, inconsistent idea of
"contract type" -- Generate allowed free text while Fact Review rendered contract type as a plain
text field too, with no shared closed set anywhere. This module defines the allowed value sets
once, in one place, so both screens import the same list and show identical normalized values and
identical selected-value display for the same underlying concept.

CONTRACT_TYPES matches the only two contract types the rest of the system already treats as
meaningful: src/llm/prompts.py's own extraction instructions ("Common types include 'Time and
Materials' and 'Fixed Bid'"), src/generators/checklist.py's commercial-guardrail branching
(`if contract_type == "Fixed Bid"` / else), and src/extractors/startup_kit_docx_parser.py's
re-ingestion defaulting all only ever distinguish these two values.

GOVERNANCE_TIERS matches src/core/models.py's own closed-set `GovernanceTier` literal.

MODEL_OPTIONS_BY_PROVIDER lists the known-valid model IDs offered in the admin-gated model
dropdown (item 5): the "current" Anthropic entry matches config.resolve_anthropic_model's own
default; legacy/retired Anthropic IDs are intentionally not offered here, since
config.ANTHROPIC_MODEL_ALIASES already transparently redirects them for anyone who still types one
via the CLI's --model flag.
"""

from typing import Dict, List

GOVERNANCE_TIERS: List[str] = ["Guided", "Partnered", "Elevated"]

CONTRACT_TYPES: List[str] = ["Time and Materials", "Fixed Bid"]

MODEL_OPTIONS_BY_PROVIDER: Dict[str, List[str]] = {
    "anthropic": ["claude-sonnet-5-5", "claude-haiku-4-5-20251001"],
    "openai": ["gpt-4o"],
}

# Sentinel shown in the model dropdown for "use this provider's own default model" (an empty
# string is passed through to build_llm_client, same as today's blank free-text field did).
PROVIDER_DEFAULT_MODEL_LABEL = "(provider default)"


def resolve_select_index(value: str, options: List[str], fallback: str) -> int:
    """Index of `value` in `options`; falls back to `fallback`'s index if `value` isn't a
    recognized option, and to 0 if neither is recognized. Always returns a valid index into
    `options` (never raises), so callers can pass it straight to st.selectbox's `index=`.
    """
    if value in options:
        return options.index(value)
    if isinstance(value, str):
        for opt in options:
            if f"({opt})" in value or value == opt:
                return options.index(opt)
    if fallback in options:
        return options.index(fallback)
    return 0
