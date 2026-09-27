"""Core configuration and settings."""

import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AppConfig:
    inputs_dir: Path = Path(os.getenv("INPUTS_DIR", "inputs"))
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "output"))
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.0"))
    default_governance_tier: str = os.getenv("DEFAULT_GOVERNANCE_TIER", "Partnered")
    default_contract_type: str = os.getenv("DEFAULT_CONTRACT_TYPE", "Time and Materials")


config = AppConfig()
