"""Core configuration and settings."""

import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load .env explicitly from the project root directory
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    load_dotenv(dotenv_path=_env_file, override=True)
else:
    load_dotenv(override=True)


# Model ID alias mapping to automatically replace retired/legacy Claude model IDs
ANTHROPIC_MODEL_ALIASES: dict[str, str] = {
    "claude-3-5-sonnet-20240620": "claude-sonnet-5-5",
    "claude-3-7-sonnet-20250219": "claude-sonnet-5-5",
    "claude-3-5-sonnet-20241022": "claude-sonnet-5-5",
    "claude-3-5-sonnet-latest": "claude-sonnet-5-5",
    "claude-3-haiku-20240307": "claude-haiku-4-5-20251001",
    "claude-3-5-haiku-20241022": "claude-haiku-4-5-20251001",
    "claude-3-5-haiku-latest": "claude-haiku-4-5-20251001",
}


def resolve_anthropic_model(model_name: Optional[str]) -> str:
    """Resolve legacy/retired model IDs or aliases to supported active model IDs."""
    if not model_name:
        return "claude-sonnet-5-5"
    cleaned = model_name.strip()
    return ANTHROPIC_MODEL_ALIASES.get(cleaned, cleaned)


def normalize_person_name(name: Optional[str], default: str = "[UNASSIGNED - TO BE CONFIRMED]") -> str:
    """Normalize user-entered person name, correcting inverted caps-lock (e.g., 'jAMES' -> 'James') while preserving valid casing and acronyms."""
    if not name:
        return default
    cleaned = name.strip()
    if not cleaned or cleaned.upper() == default.upper() or "UNASSIGNED" in cleaned.upper():
        return default
    words = cleaned.split()
    normalized_words = []
    for w in words:
        if len(w) > 1 and w[0].islower() and any(c.isupper() for c in w[1:]):
            # Inverted caps lock, e.g. jAMES -> James, tINA -> Tina, jUDY -> Judy
            normalized_words.append(w.title())
        elif w.islower():
            # All lower 'james' -> 'James'
            normalized_words.append(w.capitalize())
        elif w.isupper() and len(w) > 4:
            # Long all-upper name like 'CAROLINA' -> 'Carolina'
            normalized_words.append(w.capitalize())
        else:
            # Preserves title case ('James', 'McCullough', 'O'Connor') and short acronyms ('PMO', 'PM', 'QA')
            normalized_words.append(w)
    return " ".join(normalized_words)


def sanitize_report_text(text: Optional[str]) -> str:
    """Sanitize report text to remove references to SOW, Statement of Work, or external/source documents, making text self-contained, simplified, and concise."""
    if not text:
        return "" if text is None else str(text)

    cleaned = str(text)
    # Remove phrases like 'as stated in the SOW', 'per the SOW', 'in accordance with the SOW', 'detailed in SOW', etc.
    cleaned = re.sub(
        r'\b(?:as\s+(?:stated|defined|specified|referenced|stipulated|outlined|detailed)\s+in|per|in\s+accordance\s+with|according\s+to|based\s+on)\s+(?:the\s+)?(?:SOW|Statement\s+of\s+Work|source\s+documents?|input\s+documents?|contract\s+documents?)\b',
        '',
        cleaned,
        flags=re.IGNORECASE
    )
    # Replace standalone 'Statement of Work' or 'SOW' or 'source documents' with 'baseline' or 'project scope'
    cleaned = re.sub(r'\b(?:the\s+)?Statement\s+of\s+Work\b', 'project baseline', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:the\s+)?SOW\b', 'project baseline', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:the\s+)?(?:source|input)\s+documents?\b', 'project baseline', cleaned, flags=re.IGNORECASE)
    # Remove clause / section / slide / page references if they appear in text (e.g. 'in Section 3.2', 'Slide 4')
    cleaned = re.sub(r'\b(?:in\s+)?(?:Section|Clause|Slide|Page)\s+\d+(?:\.\d+)*\b', '', cleaned, flags=re.IGNORECASE)
    # Clean up double spaces, dangling punctuation
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    cleaned = re.sub(r'\s+([,.:;])', r'\1', cleaned)
    cleaned = re.sub(r'^[,\s.:;-]+', '', cleaned)
    return cleaned.strip()


@dataclass
class AppConfig:
    inputs_dir: Path = Path(os.getenv("INPUTS_DIR", "inputs"))
    mock_inputs_dir: Path = Path(os.getenv("MOCK_INPUTS_DIR", "inputs/SOWs/Test"))
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "output"))
    mock_output_dir: Path = Path(os.getenv("MOCK_OUTPUT_DIR", "output/Reports/Test"))
    default_provider: str = os.getenv("LLM_PROVIDER", "anthropic").lower()
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = resolve_anthropic_model(os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"))
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    temperature: float = float(os.getenv("TEMPERATURE", os.getenv("OPENAI_TEMPERATURE", "0.0")))
    default_governance_tier: str = os.getenv("DEFAULT_GOVERNANCE_TIER", "Partnered")
    default_contract_type: str = os.getenv("DEFAULT_CONTRACT_TYPE", "Time and Materials")
    max_tokens: int = int(os.getenv("MAX_TOKENS", "16384"))
    llm_cache_mode: str = os.getenv("LLM_CACHE_MODE", "off").lower()
    llm_cache_dir: Path = Path(os.getenv("LLM_CACHE_DIR", "tests/fixtures/llm_cache"))


# Tool reserved prefixes that must never be classified as SOW identifiers (v6 Section 1.1)
TOOL_RESERVED_PREFIXES: set[str] = {
    "DEL", "WP", "RSK", "ISS", "DEP", "ASM", "AMB", "Q", "M", "MS", "CP", "COM", "DEC", "ACT", "ACT-REQ", "RAID", "G01", "G"
}

# Configurable, ordered list of (Kind, Pattern) tuples for SOW reference detection (v6 Section 1.1)
SOW_REFERENCE_PATTERNS: list[tuple[str, str]] = [
    ("Story ID", r"\b[A-Z][A-Z0-9]{1,9}-\d{2,6}\b"),
    ("Deliverable number", r"\b(?:Deliverable\s+\d+(?:\.\d+)*|D\d+(?:\.\d+)*)\b"),
    ("Task or WBS code", r"\b(?:Task|WBS)\s+\d+(?:\.\d+)*\b"),
    ("Section", r"\b(?:Section|Clause|§)\s*\d+(?:\.\d+)*\b"),
]


def is_tool_reserved_id(identifier: str) -> bool:
    """Check if identifier uses one of the internal tool-reserved prefixes (v6 Section 1.1)."""
    if not identifier:
        return False
    ident_upper = identifier.strip().upper()
    parts = ident_upper.split("-")
    if len(parts) >= 2:
        prefix1 = parts[0]
        prefix_full = "-".join(parts[:-1])
        if prefix1 in TOOL_RESERVED_PREFIXES or prefix_full in TOOL_RESERVED_PREFIXES:
            return True
    return False


def detect_sow_reference_kind(ref: str) -> Optional[str]:
    """Detect reference kind for an identifier string using SOW_REFERENCE_PATTERNS (v6 Section 1.1)."""
    if not ref:
        return None
    ref_clean = ref.strip()
    if ref_clean.upper().startswith("SOW-"):
        return "Synthetic"
    for kind, pattern in SOW_REFERENCE_PATTERNS:
        m = re.search(pattern, ref_clean, re.IGNORECASE)
        if m:
            if kind == "Story ID" and is_tool_reserved_id(ref_clean):
                continue
            return kind
    return None


def extract_sow_references_with_kind(text: str) -> list[tuple[str, str]]:
    """Extract all SOW references and their kinds from text in appearance order (v6 Section 1.1)."""
    if not text:
        return []
    results: list[tuple[str, str]] = []
    seen: set[str] = set()

    # Synthetic references pattern: SOW-{phase code or milestone ID}-{nn} or SOW-{nn}
    synthetic_pattern = r"\bSOW-(?:[A-Za-z0-9]+-)?\d{2,4}\b"
    for m in re.finditer(synthetic_pattern, text, re.IGNORECASE):
        val = m.group(0).strip()
        if val.upper() not in seen:
            seen.add(val.upper())
            results.append((val, "Synthetic"))

    for kind, pattern in SOW_REFERENCE_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            val = m.group(0).strip()
            if kind == "Story ID" and is_tool_reserved_id(val):
                continue
            if val.upper() not in seen:
                seen.add(val.upper())
                results.append((val, kind))

    # Sort by appearance position in text
    def _pos(item: tuple[str, str]) -> int:
        idx = text.find(item[0])
        return idx if idx >= 0 else 999999

    results.sort(key=_pos)
    return results


def extract_sow_references(text: str) -> list[str]:
    """Extract unique SOW references from text in appearance order (v6 Section 1.1)."""
    return [ref for ref, _ in extract_sow_references_with_kind(text)]


config = AppConfig()
