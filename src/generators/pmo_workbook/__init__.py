"""Project Delivery Workbook export package (v2 spec)."""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional, Dict, Any
from src.core.models import StartupKitBaseline, ValidationReport
from src.generators.formatting import sanitize_filename
from src.generators.pmo_workbook.builder import build_workbook_model
from src.generators.pmo_workbook.writer import write_workbook


@dataclass(frozen=True)
class PMOWorkbookResult:
    file_path: Path
    schedule_rows: int
    wbs_rows: int
    task_rows: int
    raid_rows: int
    unmapped_deliverables: int
    workstreams_count: int = 0
    milestones_count: int = 0
    checkpoints_count: int = 0
    excluded_items: int = 0
    evidence_flags: int = 0
    traceability: Dict[str, Any] = field(default_factory=dict)
    validation: Optional[ValidationReport] = None


def export_pmo_workbook(
    baseline: StartupKitBaseline,
    output_dir: Path,
    start_date: Optional[date] = None,
) -> PMOWorkbookResult:
    """Build and save {Project}_Project_Delivery_Workbook.xlsx into output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_name = sanitize_filename(baseline.project_name)
    target_path = output_dir / f"{clean_name}_Project_Delivery_Workbook.xlsx"

    model = build_workbook_model(baseline, start_date=start_date)
    saved_path = write_workbook(model, target_path)

    task_count = sum(1 for w in model.wbs_rows if w.level == 4)
    num_ws = sum(1 for s in model.schedule_rows if s.row_type == "Workstream")
    num_ms = sum(1 for s in model.schedule_rows if s.row_type == "Milestone")
    num_cp = sum(1 for s in model.schedule_rows if s.row_type == "Checkpoint")

    return PMOWorkbookResult(
        file_path=saved_path,
        schedule_rows=len(model.schedule_rows),
        wbs_rows=len(model.wbs_rows),
        task_rows=task_count,
        raid_rows=len(model.raid_rows),
        unmapped_deliverables=model.unmapped_deliverables_count,
        workstreams_count=num_ws,
        milestones_count=num_ms,
        checkpoints_count=num_cp,
        excluded_items=model.excluded_items_count,
        evidence_flags=model.evidence_flags_count,
        traceability=model.traceability,
        validation=getattr(baseline, "validation_report", None),
    )


__all__ = [
    "export_pmo_workbook",
    "PMOWorkbookResult",
]
