"""Traceability models and manifest utilities for the PS Governance Kickoff Deck (HTL-72)."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class TraceRef:
    """Trace reference linking a deck element to a baseline model field or SOW reference."""
    artifact: str
    locator: str
    key: str
    field: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact": self.artifact,
            "locator": self.locator,
            "key": self.key,
            "field": self.field,
        }


@dataclass
class TraceManifestEntry:
    """One displayed element on a slide with its source provenance."""
    slide: int
    shape: str
    element: str
    displayed_value: str
    traces: List[TraceRef]
    values: Optional[List[str]] = None
    derived: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "slide": self.slide,
            "shape": self.shape,
            "element": self.element,
            "displayed_value": self.displayed_value,
            "traces": [t.to_dict() for t in self.traces],
        }
        if self.values is not None:
            d["values"] = list(self.values)
        if self.derived:
            d["derived"] = self.derived
        return d


@dataclass
class GovernanceDeckTraceManifest:
    """Full trace manifest written beside the deck as {project}_PS_Governance_Kickoff.trace.json."""
    project_name: str
    entries: List[TraceManifestEntry] = field(default_factory=list)

    def add(
        self,
        slide: int,
        shape: str,
        element: str,
        displayed_value: str,
        traces: List[TraceRef],
        values: Optional[List[str]] = None,
        derived: Optional[str] = None,
    ) -> None:
        if traces and displayed_value != "":
            self.entries.append(
                TraceManifestEntry(
                    slide=slide,
                    shape=shape,
                    element=element,
                    displayed_value=displayed_value,
                    traces=list(traces),
                    values=values,
                    derived=derived,
                )
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "entries_count": len(self.entries),
            "entries": [e.to_dict() for e in self.entries],
        }

    def write_json(self, target_path: Path) -> Path:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        return target_path
