"""Output selection and execution result dataclasses."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.generators.pmo_workbook import PMOWorkbookResult
    from src.generators.onboarding_deck import OnboardingDeckResult
    from src.core.models import StartupKitBaseline, ValidationReport


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
    # HTL-24: structured fields so both front ends can render their own presentation from the
    # same underlying data, instead of only being able to read it off stdout/logs. The CLI's
    # own formatted text (src/scoring/cli_reporter.py) stays CLI-specific presentation built
    # from these fields; a future UI renders its own widgets from the same fields.
    baseline: Optional["StartupKitBaseline"] = None
    validation_report: Optional["ValidationReport"] = None
    summary_text: Optional[str] = None
    fallback_domains: List[str] = field(default_factory=list)
    primary_provider: Optional[str] = None
    # HTL-29 / HTL-02: pause-for-review run result fields
    paused: bool = False
    run_id: Optional[str] = None
