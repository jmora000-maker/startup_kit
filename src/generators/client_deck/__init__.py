"""Client Kickoff Deck export package (OUT-14)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.core.models import StartupKitBaseline
from src.generators.formatting import sanitize_filename
from src.generators.client_deck.builder import build_client_deck_model
from src.generators.client_deck.spec import ClientDeckModel
from src.generators.client_deck.trace import ClientDeckTraceManifest, TraceRef
from src.generators.client_deck.writer import write_client_deck
from src.generators.client_deck.validator import check_client_deck_traceability


@dataclass(frozen=True)
class ClientDeckResult:
    """Result summary of Client Kickoff Deck generation."""
    file_path: Path
    manifest_path: Path
    slides_count: int
    trace_entries_count: int
    project_name: str


def export_client_deck(
    baseline: StartupKitBaseline,
    output_dir: Path,
    template_path: Optional[Path] = None,
) -> ClientDeckResult:
    """Build and save {Project_Name}_Client_Kickoff_Deck.pptx and trace manifest into output_dir (OUT-14)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_name = sanitize_filename(baseline.project_name)
    target_path = output_dir / f"{clean_name}_Client_Kickoff_Deck.pptx"

    model = build_client_deck_model(baseline)
    saved_path = write_client_deck(model, target_path, template_path=template_path)
    manifest_path = target_path.with_name(f"{clean_name}_Client_Kickoff_Deck.trace.json")

    return ClientDeckResult(
        file_path=saved_path,
        manifest_path=manifest_path,
        slides_count=16,
        trace_entries_count=len(model.manifest.entries),
        project_name=baseline.project_name,
    )


__all__ = [
    "export_client_deck",
    "build_client_deck_model",
    "write_client_deck",
    "check_client_deck_traceability",
    "ClientDeckResult",
    "ClientDeckModel",
    "TraceRef",
    "ClientDeckTraceManifest",
]
