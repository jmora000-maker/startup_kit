"""OUT-11: one file-name rule. All outputs of a run share one sanitized project-name prefix, and only one
sanitize_filename exists in src\\."""

import ast
from pathlib import Path

import pytest

from src.generators.docx_generator import DocxGenerator
from tests.deck_bundle import FIXTURES, build_bundle

SRC = Path(__file__).resolve().parent.parent / "src"
SUFFIXES = (
    "_Startup_Readiness_Checklist.docx",
    "_Startup_Kit.docx",
    "_Project_Delivery_Workbook.xlsx",
    "_Talent_Onboarding_Deck.trace.json",
    "_Talent_Onboarding_Deck.pptx",
)


def _prefix(name: str) -> str:
    for suffix in SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    raise AssertionError(f"unrecognised output file name: {name}")


def _run_outputs(out_dir: Path, fixture: str) -> list:
    """Kit, Checklist, Workbook, deck, and trace manifest for one run."""
    bundle = build_bundle(out_dir, fixture)
    DocxGenerator(generated_date="2026-10-01").write_checklist_docx(bundle["baseline"], out_dir)
    return sorted(p.name for p in out_dir.iterdir() if p.is_file())


@pytest.mark.parametrize("fixture", FIXTURES)
def test_all_outputs_of_one_run_share_one_prefix(fixture, tmp_path):
    names = _run_outputs(tmp_path, fixture)
    assert len(names) == 5, names
    prefixes = {_prefix(n) for n in names}
    assert len(prefixes) == 1, f"outputs of one run use different project-name prefixes: {names}"


@pytest.mark.parametrize("fixture", FIXTURES)
def test_output_names_have_no_double_underscore(fixture, tmp_path):
    bad = [n for n in _run_outputs(tmp_path, fixture) if "__" in n]
    assert bad == [], f"runs of spaces and underscores must collapse to one underscore: {bad}"


def test_only_one_sanitize_filename_exists_in_src():
    found = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found.extend(f"{path.relative_to(SRC.parent)}:{n.lineno} {n.name}" for n in ast.walk(tree)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and "sanitize_filename" in n.name)
    assert len(found) == 1, f"expected exactly one sanitize_filename in src\\, found {len(found)}: {found}"
