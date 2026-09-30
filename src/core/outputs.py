"""Output selection and execution result dataclasses."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.generators.pmo_workbook import PMOWorkbookResult


@dataclass(frozen=True)
class OutputSelection:
    kit: bool = False
    checklist: bool = False
    workbook: bool = True

    @classmethod
    def from_flags(cls, *, all_: bool, kit: bool, checklist: bool, export_tools: bool) -> "OutputSelection":
        if all_:
            return cls(kit=True, checklist=True, workbook=True)
        if not (kit or checklist or export_tools):
            return cls()  # default: workbook only
        return cls(kit=kit, checklist=checklist, workbook=export_tools)


@dataclass(frozen=True)
class RunResult:
    kit_path: Optional[Path] = None
    checklist_path: Optional[Path] = None
    workbook: Optional["PMOWorkbookResult"] = None
    readiness_score: float = 0.0
