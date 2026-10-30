"""PS Governance Kickoff Deck export package (HTL-72)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.core.models import StartupKitBaseline
from src.generators.formatting import sanitize_filename
from src.generators.governance_deck.builder import build_governance_deck_model
from src.generators.governance_deck.spec import GovernanceDeckModel
from src.generators.governance_deck.trace import GovernanceDeckTraceManifest, TraceRef
from src.generators.governance_deck.writer import write_governance_deck
from src.generators.governance_deck.validator import check_governance_deck_traceability


@dataclass(frozen=True)
class GovernanceDeckResult:
    """Result summary of PS Governance Kickoff Deck generation."""
    file_path: Path
    manifest_path: Path
    slides_count: int
    trace_entries_count: int
    project_name: str


def export_governance_deck(
    baseline: StartupKitBaseline,
    output_dir: Path,
    template_path: Optional[Path] = None,
    client_template_path: Optional[Path] = None,
) -> GovernanceDeckResult:
    """Build and save {Project_Name}_PS_Governance_Kickoff.pptx and trace manifest into output_dir (HTL-72)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_name = sanitize_filename(baseline.project_name)
    target_path = output_dir / f"{clean_name}_PS_Governance_Kickoff.pptx"

    model = build_governance_deck_model(baseline)
    saved_path = write_governance_deck(
        model,
        target_path,
        template_path=template_path,
        client_template_path=client_template_path,
    )
    manifest_path = target_path.with_name(f"{clean_name}_PS_Governance_Kickoff.trace.json")

    return GovernanceDeckResult(
        file_path=saved_path,
        manifest_path=manifest_path,
        slides_count=19,
        trace_entries_count=len(model.manifest.entries),
        project_name=baseline.project_name,
    )


__all__ = [
    "export_governance_deck",
    "build_governance_deck_model",
    "write_governance_deck",
    "check_governance_deck_traceability",
    "GovernanceDeckResult",
    "GovernanceDeckModel",
    "TraceRef",
    "GovernanceDeckTraceManifest",
]
