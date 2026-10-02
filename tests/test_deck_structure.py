"""Tests for Deck presentation structure, layout validation, and INV-29 (DECK-12, INV-29)."""

import zipfile
from pathlib import Path
import pytest
import docx
import openpyxl

from src.core.models import StartupKitBaseline
from src.generators.docx_generator import DocxGenerator
from src.generators.pmo_workbook import export_pmo_workbook
from src.generators.onboarding_deck import export_onboarding_deck
from src.tools.check_artifacts import check_deck_invariants
from src.llm.validation import validate_and_repair_baseline
import json


@pytest.fixture
def arc_deck_bundle(tmp_path):
    fixture_dir = Path("tests/fixtures/sow/arc_genomics")
    with open(fixture_dir / "baseline.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    baseline = StartupKitBaseline.model_validate(data)
    validate_and_repair_baseline(baseline)

    kit_path = DocxGenerator().write_kit_docx(baseline, tmp_path)
    wb_res = export_pmo_workbook(baseline, tmp_path)
    deck_res = export_onboarding_deck(baseline, tmp_path)

    return {
        "baseline": baseline,
        "deck_path": deck_res.file_path,
        "manifest_path": deck_res.manifest_path,
        "kit_path": kit_path,
        "wb_path": wb_res.file_path,
    }


def test_deck_structure_slide_count_and_layouts(arc_deck_bundle):
    """Deck contains exactly 6 slide parts and no template leftover slides."""
    deck_path = arc_deck_bundle["deck_path"]
    with zipfile.ZipFile(deck_path, "r") as z:
        slide_parts = [n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
        assert len(slide_parts) == 6, f"Expected 6 slide XML parts, found {len(slide_parts)}"
        for n in z.namelist():
            if n.startswith("ppt/slides/"):
                content = z.read(n).decode("utf-8", errors="ignore")
                assert "DELIVERY GOVERNANCE" not in content


def test_inv29_passes_on_valid_deck(arc_deck_bundle):
    """INV-29 passes on clean deck."""
    kit_doc = docx.Document(str(arc_deck_bundle["kit_path"]))
    wb = openpyxl.load_workbook(str(arc_deck_bundle["wb_path"]), data_only=False)

    violations = check_deck_invariants(
        arc_deck_bundle["deck_path"],
        arc_deck_bundle["manifest_path"],
        kit_doc,
        wb,
    )
    inv29_violations = [v for v in violations if v.inv_id == "INV-29"]
    assert len(inv29_violations) == 0


def test_inv29_fails_when_extra_slide_or_template_text_present(arc_deck_bundle, tmp_path):
    """INV-29 fails when template text or incorrect layout is present."""
    broken_deck_path = tmp_path / "broken_deck.pptx"
    # Copy clean deck and inject leftover template text into slide1.xml
    with zipfile.ZipFile(arc_deck_bundle["deck_path"], "r") as zin:
        with zipfile.ZipFile(broken_deck_path, "w") as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "ppt/slides/slide1.xml":
                    data = data.replace(b"</p:spTree>", b"<a:p><a:r><a:t>DELIVERY GOVERNANCE</a:t></a:r></a:p></p:spTree>")
                zout.writestr(item, data)

    kit_doc = docx.Document(str(arc_deck_bundle["kit_path"]))
    wb = openpyxl.load_workbook(str(arc_deck_bundle["wb_path"]), data_only=False)

    violations = check_deck_invariants(
        broken_deck_path,
        arc_deck_bundle["manifest_path"],
        kit_doc,
        wb,
    )
    inv29_violations = [v for v in violations if v.inv_id == "INV-29"]
    assert len(inv29_violations) > 0
    assert "DELIVERY GOVERNANCE" in str(inv29_violations[0])
