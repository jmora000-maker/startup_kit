"""Core configuration and settings."""

import os
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


@dataclass
class AppConfig:
    inputs_dir: Path = Path(os.getenv("INPUTS_DIR", "inputs"))
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "output"))
    default_provider: str = os.getenv("LLM_PROVIDER", "anthropic").lower()
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = resolve_anthropic_model(os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"))
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    temperature: float = float(os.getenv("TEMPERATURE", os.getenv("OPENAI_TEMPERATURE", "0.0")))
    default_governance_tier: str = os.getenv("DEFAULT_GOVERNANCE_TIER", "Partnered")
    default_contract_type: str = os.getenv("DEFAULT_CONTRACT_TYPE", "Time and Materials")
    max_tokens: int = int(os.getenv("MAX_TOKENS", "16384"))


config = AppConfig()
