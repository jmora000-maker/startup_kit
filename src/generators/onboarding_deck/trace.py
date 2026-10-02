"""Traceability models and manifest utilities for Talent Team Onboarding Deck (DECK-04, DECK-05)."""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import json
from pathlib import Path


@dataclass
class TraceRef:
    """Trace reference linking a deck element back to a source artifact (DECK-04)."""
    artifact: str  # "Startup Kit" | "Project Delivery Workbook"
    locator: str   # Table name or Sheet name
    key: str       # Row key, ID, or item label
    field: str     # Field or column name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact": self.artifact,
            "locator": self.locator,
            "key": self.key,
            "field": self.field,
        }


@dataclass
class TraceManifestEntry:
    """Entry in the deck trace manifest for a displayed element."""
    slide: int
    element: str
    displayed_value: str
    trace: TraceRef

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slide": self.slide,
            "element": self.element,
            "displayed_value": self.displayed_value,
            "trace": self.trace.to_dict(),
        }


@dataclass
class DeckTraceManifest:
    """Full trace manifest written beside the deck as {project}_Talent_Onboarding_Deck.trace.json."""
    project_name: str
    entries: List[TraceManifestEntry] = field(default_factory=list)

    def add_entry(self, slide: int, element: str, displayed_value: str, trace: Optional[TraceRef]) -> None:
        if trace is not None and displayed_value != "":
            self.entries.append(
                TraceManifestEntry(
                    slide=slide,
                    element=element,
                    displayed_value=displayed_value,
                    trace=trace,
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
