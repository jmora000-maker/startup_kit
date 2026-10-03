"""Tests and helper loaders for QA-08 oracles."""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional

from src.config import ORACLE_ALIAS_MAP

ORACLES_DIR = Path("tests/oracles")


def load_oracle(name: str) -> Optional[Dict[str, Any]]:
    """Load an oracle JSON by fixture name from tests/oracles/ (QA-12 exact-match-first, ignoring drafts)."""
    # 1. Exact match candidate first (QA-12)
    exact_path = ORACLES_DIR / f"{name}.json"
    if exact_path.exists():
        with open(exact_path, "r", encoding="utf-8") as f:
            content = f.read()
            cleaned = re.sub(r',\s*([}\]])', r'\1', content)
            return json.loads(cleaned)

    # 2. Narrow explicit alias fallback (QA-12 / QA-08)
    if name in ORACLE_ALIAS_MAP:
        alias_path = ORACLES_DIR / ORACLE_ALIAS_MAP[name]
        if alias_path.exists():
            with open(alias_path, "r", encoding="utf-8") as f:
                content = f.read()
                cleaned = re.sub(r',\s*([}\]])', r'\1', content)
                return json.loads(cleaned)

    return None


def test_arc_oracle_structure():
    """Verify ARC oracle loads and has expected fields."""
    oracle = load_oracle("arc")
    assert oracle is not None
    assert oracle["gate_count"] == 4
    assert len(oracle["phases"]) == 4
    assert len(oracle["sow_reference_phase"]) == 4
    assert "HS-4762" in oracle["sow_reference_phase"]["P1"]
    assert oracle["min_evidence_coverage"] == 0.90
    assert oracle["award_date_stated_in_sow"] is False
