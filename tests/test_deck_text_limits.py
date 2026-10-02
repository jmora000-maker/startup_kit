"""Tests for Deck text word limits, titles, and INV-28 (DECK-08, INV-28)."""

import json
from pathlib import Path
import pytest
import pptx
import docx
import openpyxl

from src.core.models import StartupKitBaseline
from src.generators.docx_generator import DocxGenerator
from src.generators.pmo_workbook import export_pmo_workbook
from src.generators.onboarding_deck import export_onboarding_deck
from src.tools.check_artifacts import check_deck_invariants
from src.llm.validation import validate_and_repair_baseline


@pytest.fixture
def arc_baseline():
    fixture_dir = Path("tests/fixtures/sow/arc_genomics")
    with open(fixture_dir / "baseline.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    baseline = StartupKitBaseline.model_validate(data)
    validate_and_repair_baseline(baseline)
    return baseline


def test_inv28_passes_on_arc_deck(arc_baseline, tmp_path):
    """INV-28 passes on valid deck: titles <= 8 words, bullets <= 15 words, notes <= 30 words."""
    kit_path = DocxGenerator().write_kit_docx(arc_baseline, tmp_path)
    wb_res = export_pmo_workbook(arc_baseline, tmp_path)
    deck_res = export_onboarding_deck(arc_baseline, tmp_path)

    kit_doc = docx.Document(str(kit_path))
    wb = openpyxl.load_workbook(str(wb_res.file_path), data_only=False)

    violations = check_deck_invariants(
        deck_res.file_path,
        deck_res.manifest_path,
        kit_doc,
        wb,
    )
    inv28_violations = [v for v in violations if v.inv_id == "INV-28"]
    assert len(inv28_violations) == 0


def test_inv28_fails_when_title_too_long(arc_baseline, tmp_path):
    """INV-28 fails when a slide title exceeds 8 words."""
    deck_res = export_onboarding_deck(arc_baseline, tmp_path)
    prs = pptx.Presentation(str(deck_res.file_path))

    # Make Slide 2 title very long
    prs.slides[1].placeholders[0].text = "This Is A Very Long Title That Definitely Exceeds Eight Words Total"

    broken_deck_path = tmp_path / "long_title.pptx"
    prs.save(str(broken_deck_path))

    kit_path = DocxGenerator().write_kit_docx(arc_baseline, tmp_path)
    wb_res = export_pmo_workbook(arc_baseline, tmp_path)
    kit_doc = docx.Document(str(kit_path))
    wb = openpyxl.load_workbook(str(wb_res.file_path), data_only=False)

    violations = check_deck_invariants(
        broken_deck_path,
        deck_res.manifest_path,
        kit_doc,
        wb,
    )
    inv28_violations = [v for v in violations if v.inv_id == "INV-28"]
    assert len(inv28_violations) > 0
    assert any("title exceeds 8 words" in str(v) or "expected 'Project Charter'" in str(v) for v in inv28_violations)


def test_inv28_fails_when_speaker_note_bullet_too_long(arc_baseline, tmp_path):
    """INV-28 fails when a speaker note talking point exceeds 30 words."""
    deck_res = export_onboarding_deck(arc_baseline, tmp_path)
    prs = pptx.Presentation(str(deck_res.file_path))

    # Add a 35-word bullet to Slide 2 speaker notes
    long_bullet = "• " + " ".join(["word"] * 35) + "."
    prs.slides[1].notes_slide.notes_text_frame.text = f"TALKING POINTS:\n{long_bullet}\n• Short bullet.\n• Another short bullet.\n\nSOURCES: Startup Kit"

    broken_deck_path = tmp_path / "long_notes.pptx"
    prs.save(str(broken_deck_path))

    kit_path = DocxGenerator().write_kit_docx(arc_baseline, tmp_path)
    wb_res = export_pmo_workbook(arc_baseline, tmp_path)
    kit_doc = docx.Document(str(kit_path))
    wb = openpyxl.load_workbook(str(wb_res.file_path), data_only=False)

    violations = check_deck_invariants(
        broken_deck_path,
        deck_res.manifest_path,
        kit_doc,
        wb,
    )
    inv28_violations = [v for v in violations if v.inv_id == "INV-28"]
    assert len(inv28_violations) > 0
    assert any("exceeds 30 words" in str(v) for v in inv28_violations)


def test_inv28_accepts_a_cell_over_15_words_only_when_deck_05_allows_no_shorter_cut(arc_baseline, tmp_path):
    """DECK-05 wins over the 15-word guide: a first clause with no earlier boundary is shown whole, not cut again."""
    deck_res = export_onboarding_deck(arc_baseline, tmp_path)
    prs = pptx.Presentation(str(deck_res.file_path))
    table = [sh for sh in prs.slides[3].shapes if getattr(sh, "has_table", False) and sh.has_table][0].table
    cell_run = table.cell(1, 1).text_frame.paragraphs[0].runs[0]
    # a 20-word text with a boundary after its eighth word: the builder must have used that boundary
    cell_run.text = "Negative tests pass and the scan is clean. Findings in Toptal-built components are remediated; findings in Client-built components are reported to the Client."
    broken = tmp_path / "late_boundary.pptx"
    prs.save(str(broken))
    kit_doc = docx.Document(str(DocxGenerator().write_kit_docx(arc_baseline, tmp_path)))
    wb = openpyxl.load_workbook(str(export_pmo_workbook(arc_baseline, tmp_path).file_path), data_only=False)
    violations = [v for v in check_deck_invariants(broken, deck_res.manifest_path, kit_doc, wb) if v.inv_id == "INV-28"]
    assert any("exceeds 15 words" in str(v) for v in violations)


def test_inv28_expects_the_project_kit_title_and_talking_points_on_slide_7(arc_baseline, tmp_path):
    deck_res = export_onboarding_deck(arc_baseline, tmp_path)
    prs = pptx.Presentation(str(deck_res.file_path))
    prs.slides[6].placeholders[0].text = "Something Else"
    broken = tmp_path / "title7.pptx"
    prs.save(str(broken))
    kit_doc = docx.Document(str(DocxGenerator().write_kit_docx(arc_baseline, tmp_path)))
    wb = openpyxl.load_workbook(str(export_pmo_workbook(arc_baseline, tmp_path).file_path), data_only=False)
    violations = [str(v) for v in check_deck_invariants(broken, deck_res.manifest_path, kit_doc, wb) if v.inv_id == "INV-28"]
    assert any("expected 'Your Project Kit'" in v for v in violations)
