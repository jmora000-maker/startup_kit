"""Scope Baseline document generator package (HTL-108)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.core.interfaces import ILLMClient
from src.core.models import StartupKitBaseline
from src.generators.formatting import sanitize_filename
from src.generators.scope_baseline.models import (
    ScopeBaselineDocument,
    ScopeBaselineSummaryRow,
    ChangeDecisionMatrixRow,
    DecisionRuleControlRow,
    ClassificationGuideRow,
    PracticalDecisionExample,
)
from src.generators.scope_baseline.builder import build_scope_baseline_document
from src.generators.scope_baseline.writer import write_scope_baseline_docx
from src.generators.scope_baseline.validator import validate_scope_baseline_document


@dataclass(frozen=True)
class ScopeBaselineResult:
    """Result summary of Scope Baseline generation."""
    file_path: Path
    variant: str
    project_name: str
    tables_count: int = 5
    examples_count: int = 4


def export_scope_baseline(
    baseline: StartupKitBaseline,
    output_dir: Path,
    llm_client: Optional[ILLMClient] = None,
) -> ScopeBaselineResult:
    """Build and save {Project}_Scope_Baseline_{ContractType}.docx into output_dir (HTL-108)."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc_model = build_scope_baseline_document(baseline, llm_client=llm_client)
    clean_name = sanitize_filename(doc_model.project_name)
    variant_slug = "Fixed_Bid" if doc_model.contract_variant == "Fixed Bid" else "Time_and_Materials"
    target_path = output_dir / f"{clean_name}_Scope_Baseline_{variant_slug}.docx"

    saved_path = write_scope_baseline_docx(doc_model, target_path)

    return ScopeBaselineResult(
        file_path=saved_path,
        variant=doc_model.contract_variant,
        project_name=doc_model.project_name,
        tables_count=5,
        examples_count=len(doc_model.table5_examples),
    )


__all__ = [
    "export_scope_baseline",
    "build_scope_baseline_document",
    "write_scope_baseline_docx",
    "validate_scope_baseline_document",
    "ScopeBaselineResult",
    "ScopeBaselineDocument",
    "ScopeBaselineSummaryRow",
    "ChangeDecisionMatrixRow",
    "DecisionRuleControlRow",
    "ClassificationGuideRow",
    "PracticalDecisionExample",
]
