"""Fixed workstream taxonomy and milestone classification logic."""

import re
from dataclasses import dataclass
from typing import List, Tuple, Optional, Sequence, Union
from src.config import sanitize_report_text
from src.core.models import Milestone, Deliverable

# Fixed 7-workstream taxonomy (used for keyword fallback and deliverable template selection)
TAXONOMY: List[Tuple[str, str, List[str]]] = [
    (
        "DIS",
        "Discovery & Requirements",
        [
            "discovery", "requirement", "workshop", "assessment",
            "current state", "as-is", "analysis", "research", "audit", "scoping"
        ]
    ),
    (
        "DES",
        "Design & Architecture",
        [
            "design", "architect", "blueprint", "prototype", "wireframe",
            "mockup", "mock-up", "specification", "ux", "ui"
        ]
    ),
    (
        "BLD",
        "Build & Configuration",
        [
            "build", "develop", "implement", "configur", "sprint",
            "mvp", "feature", "code", "module", "iteration"
        ]
    ),
    (
        "DAT",
        "Data & Integration",
        [
            "data", "migrat", "integrat", "interface", "api",
            "etl", "pipeline", "reconcil"
        ]
    ),
    (
        "TST",
        "Testing & Quality Assurance",
        [
            "test", "uat", "qa", "quality", "sit", "validat", "defect"
        ]
    ),
    (
        "DEP",
        "Deployment & Release",
        [
            "deploy", "go-live", "go live", "launch", "release",
            "cutover", "cut-over", "production", "rollout", "roll-out"
        ]
    ),
    (
        "TRN",
        "Transition & Hypercare",
        [
            "hypercare", "handover", "hand-over", "transition",
            "knowledge transfer", "training", "runbook", "warranty", "stabiliz"
        ]
    ),
]

SHORT_KEYWORDS = {"ux", "ui", "qa", "sit", "uat", "api", "etl", "mvp", "data", "code", "test", "gate"}

WORKSTREAM_NAMES = {code: name for code, name, _ in TAXONOMY}
WORKSTREAM_CODES = [code for code, _, _ in TAXONOMY]

PHASE_LABEL_REGEX = re.compile(
    r"^\s*(?P<code>P\d+[a-z]?)\s+(?P<name>[^:]*?)\s*(?:accepted|completed|complete|approved|sign[- ]?off)?\s*:\s*(?P<scope>.+)$",
    re.IGNORECASE
)


@dataclass(frozen=True)
class ParsedMilestonePhase:
    phase_code: Optional[str]
    workstream_name: str
    milestone_name: str
    milestone_scope: str
    milestone_scope_clean: str
    has_phase_label: bool
    note: Optional[str] = None


def strip_week_range_parenthetical(text: str) -> str:
    """Strip week-range parenthetical like (est. weeks 1–6) from milestone scope text."""
    if not text:
        return ""
    cleaned = re.sub(r"\s*\(\s*(?:est\.?\s*)?weeks?\s+\d+[^)]*\)", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+\.", ".", cleaned)
    return cleaned.strip()


def parse_milestone_phase(milestone: Union[Milestone, str]) -> ParsedMilestonePhase:
    """Parse milestone description to extract phase code, workstream name, milestone name, and scope."""
    desc = milestone.description if isinstance(milestone, Milestone) else str(milestone or "")
    clean_desc = sanitize_report_text(desc)

    match = PHASE_LABEL_REGEX.match(clean_desc)
    if match:
        code = match.group("code")
        raw_name = match.group("name").strip()
        workstream = f"{code} {raw_name}" if raw_name else code
        milestone_name = clean_desc.split(":", 1)[0].strip()
        scope = match.group("scope").strip()
        scope_clean = strip_week_range_parenthetical(scope)
        return ParsedMilestonePhase(
            phase_code=code,
            workstream_name=workstream,
            milestone_name=milestone_name,
            milestone_scope=scope,
            milestone_scope_clean=scope_clean,
            has_phase_label=True,
            note=None
        )

    # Fallback to keyword classifier
    ws_code, _ = classify_milestone(milestone)
    ws_name = WORKSTREAM_NAMES.get(ws_code, "Build & Configuration")
    scope_clean = strip_week_range_parenthetical(clean_desc)
    return ParsedMilestonePhase(
        phase_code=None,
        workstream_name=ws_name,
        milestone_name=clean_desc,
        milestone_scope=clean_desc,
        milestone_scope_clean=scope_clean,
        has_phase_label=False,
        note="Workstream inferred from keywords - confirm"
    )


def _build_keyword_regex(kw: str) -> re.Pattern:
    """Build regex pattern for keyword matching according to taxonomy rules."""
    kw_lower = kw.lower()
    if kw_lower in SHORT_KEYWORDS or len(kw_lower) <= 4:
        # Whole word match only
        pattern = r"\b" + re.escape(kw_lower) + r"\b"
    elif " " in kw_lower:
        # Multi-word match: word start on first token, flexible whitespace
        tokens = kw_lower.split()
        escaped_tokens = [re.escape(t) for t in tokens]
        pattern = r"\b" + r"\s+".join(escaped_tokens[:-1] + [escaped_tokens[-1] + r"\w*"])
    elif "-" in kw_lower:
        pattern = r"\b" + re.escape(kw_lower) + r"\w*"
    else:
        # Word-start match
        pattern = r"\b" + re.escape(kw_lower) + r"\w*"
    return re.compile(pattern, re.IGNORECASE)


KEYWORD_PATTERNS = {
    code: [(kw, _build_keyword_regex(kw)) for kw in kws]
    for code, _, kws in TAXONOMY
}


def _match_keywords(text: str, code: str) -> List[str]:
    """Find all distinct keywords for a workstream code in the given text."""
    matched = []
    for kw, pattern in KEYWORD_PATTERNS[code]:
        if pattern.search(text):
            matched.append(kw)
    return matched


def classify_milestone(
    milestone: Union[Milestone, str],
    mapped_deliverables: Optional[Sequence[Union[Deliverable, str]]] = None
) -> Tuple[str, str]:
    """Classify a milestone into a workstream code and provide the classification basis.
    
    Returns (workstream_code, basis).
    """
    desc = milestone.description if isinstance(milestone, Milestone) else str(milestone or "")
    clean_desc = sanitize_report_text(desc)

    # 1. Score description
    best_code = None
    best_score = 0
    best_keywords: List[str] = []

    for code, _, _ in TAXONOMY:
        matched = _match_keywords(clean_desc, code)
        score = len(matched)
        if score > 0:
            if score >= best_score:  # >= handles tie-break: later in taxonomy order wins
                best_score = score
                best_code = code
                best_keywords = matched

    if best_code is not None:
        basis = f"Keyword: {', '.join(best_keywords)}"
        return best_code, basis

    # 2. Score mapped deliverables if description had no match
    if mapped_deliverables:
        deliv_texts = []
        for d in mapped_deliverables:
            name = d.name if isinstance(d, Deliverable) else str(d)
            deliv_texts.append(sanitize_report_text(name))
        combined_deliv_text = " ".join(deliv_texts)

        for code, _, _ in TAXONOMY:
            matched = _match_keywords(combined_deliv_text, code)
            score = len(matched)
            if score > 0:
                if score >= best_score:
                    best_score = score
                    best_code = code
                    best_keywords = matched

        if best_code is not None:
            basis = f"Deliverable keyword: {', '.join(best_keywords)}"
            return best_code, basis

    # 3. Default to BLD
    return "BLD", "Default - confirm workstream"
