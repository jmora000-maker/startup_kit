"""HTL-92: Test suite covering all error-detection branches and guards in the client_deck validator.

Verifies that check_client_deck_traceability and check_boilerplate_slides_unchanged catch:
1. File system & presentation existence errors (missing deck file, missing template file)
2. Slide index out of bounds and truncated presentation errors
3. Template with fewer slides than standard boilerplate indices (bounds guard)
4. Modified boilerplate slide text errors (table cells and text frames)
5. Companion trace manifest missing on disk (default and custom path)
6. Happy path with valid presentation and manifest returning zero errors/findings
"""

from pathlib import Path
import pptx
import pytest

from src.core.models import StartupKitBaseline, ValidationFinding
from src.generators.client_deck import (
    check_client_deck_traceability,
    export_client_deck,
)
from src.generators.client_deck.validator import (
    _extract_slide_text,
    check_boilerplate_slides_unchanged,
)
from tests.test_htl_62 import _build_pge_baseline


def _create_valid_deck_and_baseline(tmp_path: Path, name: str = "valid_client_deck"):
    """Helper to generate a clean client deck presentation and baseline for mutation testing."""
    baseline = _build_pge_baseline()
    out_dir = tmp_path / name
    result = export_client_deck(baseline, out_dir)
    return baseline, result.file_path, result.manifest_path


# --- Group A: File System and Presentation Existence Invariants ---


def test_validator_missing_deck_file(tmp_path):
    """Branch 1: Catch non-existent presentation file path emitting INV-29 finding."""
    baseline = _build_pge_baseline()
    missing_deck = tmp_path / "does_not_exist_client_deck.pptx"

    findings = check_client_deck_traceability(baseline, missing_deck)
    assert len(findings) == 1
    assert findings[0].invariant_id == "INV-29"
    assert findings[0].severity == "error"
    assert f"Client Kickoff Deck file not found at {missing_deck}" in findings[0].message


def test_validator_missing_template_file(tmp_path):
    """Branch 2: Catch non-existent template file path in boilerplate and traceability checks."""
    baseline, deck_path, manifest_path = _create_valid_deck_and_baseline(tmp_path, "missing_tpl")
    prs = pptx.Presentation(str(deck_path))
    missing_template = tmp_path / "missing_template.pptx"

    # 1. Direct check_boilerplate_slides_unchanged check
    is_ok, bp_errors = check_boilerplate_slides_unchanged(prs, template_path=missing_template)
    assert is_ok is False
    assert len(bp_errors) == 1
    assert f"Template not found at {missing_template}" in bp_errors[0]

    # 2. check_client_deck_traceability forwarding check
    findings = check_client_deck_traceability(
        baseline,
        deck_path,
        manifest_path=manifest_path,
        template_path=missing_template,
    )
    assert any(
        f.invariant_id == "INV-29" and f"Template not found at {missing_template}" in f.message
        for f in findings
    )


# --- Group B: Slide Count and Index Bounds Invariants ---


def test_validator_slide_index_out_of_bounds(tmp_path):
    """Branch 3: Catch truncated presentation where generated slide count is fewer than boilerplate indices."""
    baseline, deck_path, manifest_path = _create_valid_deck_and_baseline(tmp_path, "truncated_deck")

    # Create a truncated presentation with only 2 slides
    trunc_prs = pptx.Presentation()
    blank_layout = trunc_prs.slide_layouts[6]
    trunc_prs.slides.add_slide(blank_layout)
    trunc_prs.slides.add_slide(blank_layout)
    trunc_path = tmp_path / "truncated_deck" / "truncated.pptx"
    trunc_prs.save(str(trunc_path))

    # 1. Direct check_boilerplate_slides_unchanged check
    is_ok, bp_errors = check_boilerplate_slides_unchanged(trunc_prs)
    assert is_ok is False
    assert any("out of bounds" in err for err in bp_errors)

    # 2. check_client_deck_traceability forwarding check
    findings = check_client_deck_traceability(baseline, trunc_path, manifest_path=manifest_path)
    assert any(f.invariant_id == "INV-29" and "out of bounds" in f.message for f in findings)


def test_validator_template_fewer_slides_than_boilerplate_indices(tmp_path):
    """Branch 4 (defensive guard): Handle template with fewer slides than standard boilerplate indices."""
    baseline, deck_path, manifest_path = _create_valid_deck_and_baseline(tmp_path, "short_tpl")
    prs = pptx.Presentation(str(deck_path))

    # Create a short template with only 2 slides
    short_tpl_prs = pptx.Presentation()
    blank_layout = short_tpl_prs.slide_layouts[6]
    short_tpl_prs.slides.add_slide(blank_layout)
    short_tpl_prs.slides.add_slide(blank_layout)
    short_tpl_path = tmp_path / "short_tpl.pptx"
    short_tpl_prs.save(str(short_tpl_path))

    # tmpl_idx >= len(tmpl_prs.slides) will trigger 'continue' for indices > 1
    is_ok, bp_errors = check_boilerplate_slides_unchanged(prs, template_path=short_tpl_path)
    # The first boilerplate index is 1 (Slide 2). Because slide 2 text won't match blank slide, it reports mismatch rather than crashing
    assert isinstance(is_ok, bool)
    assert isinstance(bp_errors, list)


# --- Group C: Boilerplate Text Invariance & Corruption Invariants ---


def test_validator_modified_boilerplate_slide_text(tmp_path):
    """Branch 5: Catch modified text in boilerplate slides (e.g. Slide 2 'Who you represent')."""
    baseline, deck_path, manifest_path = _create_valid_deck_and_baseline(tmp_path, "mutated_bp")
    prs = pptx.Presentation(str(deck_path))

    # Mutate text on Slide 2 (index 1 in BOILERPLATE_SLIDE_INDICES)
    slide2 = prs.slides[1]
    for shape in slide2.shapes:
        if shape.has_text_frame:
            shape.text_frame.text = "MUTATED BOILERPLATE CONTENT FOR TESTING"
            break
    prs.save(str(deck_path))

    # 1. Direct check_boilerplate_slides_unchanged check
    is_ok, bp_errors = check_boilerplate_slides_unchanged(prs)
    assert is_ok is False
    assert any("Boilerplate Slide 2 modified" in err for err in bp_errors)

    # 2. check_client_deck_traceability forwarding check
    findings = check_client_deck_traceability(baseline, deck_path, manifest_path=manifest_path)
    assert any(
        f.invariant_id == "INV-29" and "Boilerplate Slide 2 modified" in f.message
        for f in findings
    )


def test_extract_slide_text_helper_with_tables_and_text_frames():
    """Verify _extract_slide_text extracts lines from both text frames and table cells, ignoring blanks."""
    prs = pptx.Presentation()
    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)

    # Add text box shape with text and an empty paragraph
    tb = slide.shapes.add_textbox(0, 0, 1000000, 1000000)
    tb.text_frame.text = "Line 1 in text frame\nLine 2 in text frame"
    p_empty = tb.text_frame.add_paragraph()
    p_empty.text = "   "

    # Add table shape with text cells and an empty/whitespace cell
    tbl_shape = slide.shapes.add_table(2, 2, 0, 2000000, 2000000, 1000000)
    tbl = tbl_shape.table
    tbl.cell(0, 0).text = "Cell (0,0)"
    tbl.cell(0, 1).text = "Cell (0,1)"
    tbl.cell(1, 0).text = "Cell (1,0)"
    tbl.cell(1, 1).text = "   "

    extracted = _extract_slide_text(slide)
    assert "Line 1 in text frame" in extracted
    assert "Line 2 in text frame" in extracted
    assert "Cell (0,0)" in extracted
    assert "Cell (0,1)" in extracted
    assert "Cell (1,0)" in extracted
    assert "   " not in extracted
    assert "" not in extracted


# --- Group D: Companion Trace Manifest Invariants ---


def test_validator_missing_default_companion_manifest(tmp_path):
    """Branch 6: Catch default companion trace manifest file missing on disk (INV-26)."""
    baseline, deck_path, manifest_path = _create_valid_deck_and_baseline(tmp_path, "missing_default_mf")

    # Delete default manifest
    if manifest_path.exists():
        manifest_path.unlink()

    findings = check_client_deck_traceability(baseline, deck_path)
    assert any(
        f.invariant_id == "INV-26" and f"Companion trace manifest missing at {manifest_path}" in f.message
        for f in findings
    )


def test_validator_missing_custom_companion_manifest(tmp_path):
    """Branch 6 (custom path): Catch custom companion trace manifest path missing on disk (INV-26)."""
    baseline, deck_path, manifest_path = _create_valid_deck_and_baseline(tmp_path, "missing_custom_mf")
    custom_mf = tmp_path / "custom_missing_manifest.trace.json"

    findings = check_client_deck_traceability(baseline, deck_path, manifest_path=custom_mf)
    assert any(
        f.invariant_id == "INV-26" and f"Companion trace manifest missing at {custom_mf}" in f.message
        for f in findings
    )


# --- Group E: Control / Happy Path Verification ---


def test_validator_happy_path_returns_zero_findings(tmp_path):
    """Verify that a clean, unmutated valid presentation produces 0 validation findings and passes boilerplate checks."""
    baseline, deck_path, manifest_path = _create_valid_deck_and_baseline(tmp_path, "clean_happy_path")
    prs = pptx.Presentation(str(deck_path))

    # 1. Boilerplate check returns (True, [])
    is_ok, bp_errors = check_boilerplate_slides_unchanged(prs)
    assert is_ok is True
    assert bp_errors == []

    # 2. Traceability audit returns zero findings
    findings = check_client_deck_traceability(baseline, deck_path, manifest_path=manifest_path)
    assert findings == []
