"""Tests and helper loaders for QA-08 oracles."""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional

ORACLES_DIR = Path("tests/oracles")


def load_oracle(name: str) -> Optional[Dict[str, Any]]:
    """Load an oracle JSON by fixture name from tests/oracles/ (ignoring drafts)."""
    # Map common aliases
    alias_map = {
        "arc": "arc.json",
        "arc_genomics": "arc.json",
        "arc_run1": "arc.json",
        "arc_run2": "arc.json",
        "arc_run3": "arc.json",
        "arc_run4": "arc.json",
        "arc_overextracted": "arc.json",
    }
    filename = alias_map.get(name, f"{name}.json")
    oracle_path = ORACLES_DIR / filename
    if not oracle_path.exists():
        return None
    with open(oracle_path, "r", encoding="utf-8") as f:
        content = f.read()
        cleaned = re.sub(r',\s*([}\]])', r'\1', content)
        return json.loads(cleaned)


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
