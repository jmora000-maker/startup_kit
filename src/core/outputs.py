"""Output selection and execution result dataclasses."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.generators.pmo_workbook import PMOWorkbookResult
    from src.generators.onboarding_deck import OnboardingDeckResult


@dataclass(frozen=True)
class OutputSelection:
    kit: bool = False
    checklist: bool = False
    workbook: bool = True
    slides: bool = False

    @classmethod
    def from_flags(
        cls,
        *,
        all_: bool = False,
        kit: bool = False,
        checklist: bool = False,
        export_tools: bool = False,
        slides: bool = False,
    ) -> "OutputSelection":
        if all_:
            return cls(kit=True, checklist=True, workbook=True, slides=True)
        if slides:
            # DECK-02: --slides implies writing Kit and Workbook as deck sources
            return cls(kit=True, checklist=checklist, workbook=True, slides=True)
        if not (kit or checklist or export_tools or slides):
            return cls()  # default: workbook only
        return cls(kit=kit, checklist=checklist, workbook=export_tools, slides=slides)


@dataclass(frozen=True)
class RunResult:
    kit_path: Optional[Path] = None
    checklist_path: Optional[Path] = None
    workbook: Optional["PMOWorkbookResult"] = None
    slides: Optional["OnboardingDeckResult"] = None
    slides_path: Optional[Path] = None
    readiness_score: float = 0.0
