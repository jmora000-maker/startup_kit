"""Talent Team Onboarding Deck export package (DECK-01 to DECK-23, Revision 10)."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional, Dict, Any

import pptx

from src.core.models import StartupKitBaseline
from src.generators.formatting import sanitize_filename
from src.generators.onboarding_deck.builder import build_deck_model
from src.generators.onboarding_deck.coverage import coverage
from src.generators.onboarding_deck.spec import DeckModel
from src.generators.onboarding_deck.writer import write_onboarding_deck
from src.generators.onboarding_deck.trace import TraceRef, DeckTraceManifest


@dataclass(frozen=True)
class OnboardingDeckResult:
    """Result summary of Onboarding Deck generation."""
    file_path: Path
    manifest_path: Path
    slides_count: int
    trace_entries_count: int
    project_name: str
    overflow_rows: int = 0
    elements_total: int = 0
    elements_traced: int = 0


def export_onboarding_deck(
    baseline: StartupKitBaseline,
    output_dir: Path,
    start_date: Optional[date] = None,
    template_path: Optional[Path] = None,
) -> OnboardingDeckResult:
    """Build and save {Project}_Talent_Onboarding_Deck.pptx and trace manifest into output_dir (DECK-01)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_name = sanitize_filename(baseline.project_name)
    target_path = output_dir / f"{clean_name}_Talent_Onboarding_Deck.pptx"

    model = build_deck_model(baseline, start_date=start_date)
    saved_path = write_onboarding_deck(model, target_path, template_path=template_path)
    manifest_path = target_path.with_name(f"{clean_name}_Talent_Onboarding_Deck.trace.json")

    # DECK-16: the traced share is measured on the written deck, not assumed
    entries = [e.to_dict() for e in model.manifest.entries]
    total, uncovered = coverage(entries, pptx.Presentation(str(saved_path)))

    return OnboardingDeckResult(
        file_path=saved_path,
        manifest_path=manifest_path,
        slides_count=1 + len(model.slides),
        trace_entries_count=len(model.manifest.entries),
        project_name=baseline.project_name,
        overflow_rows=model.overflow_rows_used,
        elements_total=total,
        elements_traced=total - len(uncovered),
    )


__all__ = [
    "export_onboarding_deck",
    "build_deck_model",
    "write_onboarding_deck",
    "OnboardingDeckResult",
    "DeckModel",
    "TraceRef",
    "DeckTraceManifest",
]
