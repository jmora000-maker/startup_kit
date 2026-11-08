"""HTL-91: Test suite covering all 20 error-detection branches in the governance_deck validator.

Verifies that check_governance_deck_traceability catches:
1. File system & I/O errors (missing file, corrupted presentation)
2. Slide count mismatches
3. Slide 1 header / subtitle / placeholder errors
4. Slide 12 team title missing / legacy client title errors
5. Slide 13 unreplaced template placeholders
6. Slide 14 deliverables table placeholder text
7. Slide 15 acceptance criteria missing table / title errors
8. Slide 16 milestone acceptance missing title / placeholder text
9. Slide 17 approach missing title / placeholder text
10. Slide 18 risk register missing table error
11. Slide 19 next steps missing table error
12. Companion trace manifest missing file / empty entries errors
"""

from pathlib import Path
import pptx
import pytest

from src.generators.governance_deck import (
    GovernanceDeckModel,
    build_governance_deck_model,
    check_governance_deck_traceability,
    export_governance_deck,
    write_governance_deck,
)
from tests.test_htl_62 import _build_pge_baseline


def _create_valid_deck_and_model(tmp_path: Path, name: str = "valid_deck"):
    """Helper to generate a clean base presentation and model for mutation testing."""
    baseline = _build_pge_baseline()
    out_dir = tmp_path / name
    result = export_governance_deck(baseline, out_dir)
    model = build_governance_deck_model(baseline)
    return model, result.file_path


# --- Group A: File System and I/O Errors ---


def test_validator_branch_1_missing_presentation_file(tmp_path):
    """Branch 1: Catch non-existent presentation file path."""
    baseline = _build_pge_baseline()
    model = build_governance_deck_model(baseline)
    missing_path = tmp_path / "does_not_exist.pptx"

    errors = check_governance_deck_traceability(model, missing_path)
    assert len(errors) == 1
    assert f"Presentation file does not exist: {missing_path}" in errors[0]


def test_validator_branch_2_corrupted_presentation_file(tmp_path):
    """Branch 2: Catch unparseable / corrupt presentation file (e.g. truncated non-zip bytes)."""
    baseline = _build_pge_baseline()
    model = build_governance_deck_model(baseline)
    corrupt_path = tmp_path / "corrupt.pptx"
    corrupt_path.write_bytes(b"NOT_A_VALID_PPTX_OR_ZIP_FILE_DATA")

    errors = check_governance_deck_traceability(model, corrupt_path)
    assert len(errors) == 1
    assert "Failed to open presentation:" in errors[0]


# --- Group B: Slide Count Invariants ---


def test_validator_branch_3_slide_count_mismatch(tmp_path):
    """Branch 3: Catch mismatch between presentation slide count and expected count."""
    model, pptx_path = _create_valid_deck_and_model(tmp_path, "count_mismatch")
    prs = pptx.Presentation(str(pptx_path))

    # Add an unexpected extra slide
    blank_layout = prs.slide_layouts[6]
    prs.slides.add_slide(blank_layout)
    prs.save(str(pptx_path))

    errors = check_governance_deck_traceability(model, pptx_path)
    assert any("Expected exactly 19 slides in Governance Deck, found 20" in e for e in errors)


# --- Group C: Slide 1 Header, Subtitle, and Placeholder Invariants ---


def test_validator_branch_4_slide1_missing_title(tmp_path):
    """Branch 4: Catch Slide 1 missing 'Governance Kickoff' title."""
    model, pptx_path = _create_valid_deck_and_model(tmp_path, "s1_title")
    prs = pptx.Presentation(str(pptx_path))

    s1 = prs.slides[0]
    for shape in s1.shapes:
        if shape.has_text_frame and "Governance Kickoff" in shape.text_frame.text:
            shape.text_frame.text = "Incorrect Deck Title"
    prs.save(str(pptx_path))

    errors = check_governance_deck_traceability(model, pptx_path)
    assert "Slide 1 title is missing 'Governance Kickoff'" in errors


def test_validator_branch_5_slide1_missing_subtitle(tmp_path):
    """Branch 5: Catch Slide 1 missing fixed subtitle."""
    model, pptx_path = _create_valid_deck_and_model(tmp_path, "s1_subtitle")
    prs = pptx.Presentation(str(pptx_path))

    s1 = prs.slides[0]
    for shape in s1.shapes:
        if shape.has_text_frame and "Aligning on governance" in shape.text_frame.text:
            shape.text_frame.text = "Random Subtitle Text"
    prs.save(str(pptx_path))

    errors = check_governance_deck_traceability(model, pptx_path)
    assert "Slide 1 is missing subtitle 'Aligning on governance, outcomes and project plan.'" in errors


def test_validator_branch_6_slide1_unreplaced_placeholders(tmp_path):
    """Branch 6: Catch Slide 1 containing raw [Client Name] or [Project Name] tokens."""
    baseline = _build_pge_baseline()
    model = build_governance_deck_model(baseline)
    model.slide1.client_name = "[Client Name]"
    out_path = tmp_path / "s1_placeholders" / "deck.pptx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_governance_deck(model, out_path)

    errors = check_governance_deck_traceability(model, out_path)
    assert "Slide 1 contains unreplaced [Client Name] or [Project Name] placeholders" in errors


# --- Group D: Slide 12 Team Roster Title Invariants ---


def test_validator_branch_7_slide12_missing_team_title(tmp_path):
    """Branch 7: Catch Slide 12 missing 'The people delivering this project' title."""
    model, pptx_path = _create_valid_deck_and_model(tmp_path, "s12_missing_title")
    prs = pptx.Presentation(str(pptx_path))

    s12 = prs.slides[11]
    for shape in s12.shapes:
        if shape.has_text_frame and "The people delivering this project" in shape.text_frame.text:
            shape.text_frame.text = "Our Delivery Team Roster"
    prs.save(str(pptx_path))

    errors = check_governance_deck_traceability(model, pptx_path)
    assert "Slide 12 title is missing 'The people delivering this project'" in errors


def test_validator_branch_8_slide12_retains_client_facing_title(tmp_path):
    """Branch 8: Catch Slide 12 retaining legacy client-facing 'The people delivering your project' title."""
    model, pptx_path = _create_valid_deck_and_model(tmp_path, "s12_client_title")
    prs = pptx.Presentation(str(pptx_path))

    s12 = prs.slides[11]
    for shape in s12.shapes:
        if shape.has_text_frame and "The people delivering this project" in shape.text_frame.text:
            shape.text_frame.text = "The people delivering your project"
    prs.save(str(pptx_path))

    errors = check_governance_deck_traceability(model, pptx_path)
    assert "Slide 12 title still contains 'The people delivering your project'" in errors


# --- Group E: Slide 13 Why We're Here Placeholder Invariant ---


def test_validator_branch_9_slide13_unreplaced_placeholders(tmp_path):
    """Branch 9: Catch Slide 13 containing unreplaced '[Pre-filled:' placeholders."""
    baseline = _build_pge_baseline()
    model = build_governance_deck_model(baseline)
    model.slide13.what_problem_are_we_solving = "[Pre-filled: Project Purpose and Core Objectives]"
    out_path = tmp_path / "s13_placeholders" / "deck.pptx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_governance_deck(model, out_path)

    errors = check_governance_deck_traceability(model, out_path)
    assert "Slide 13 contains unreplaced '[Pre-filled:' placeholders" in errors


# --- Group F: Slide 14 Deliverables Table Placeholder Invariant ---


def test_validator_branch_10_slide14_unreplaced_placeholders(tmp_path):
    """Branch 10: Catch Slide 14 containing unreplaced '[high level summary' or '[Workstream or Feature' tokens."""
    baseline = _build_pge_baseline()
    model = build_governance_deck_model(baseline)
    model.slide14.solution_overview = "Deliverables: [high level summary of deliverables and [Workstream or Feature]"
    out_path = tmp_path / "s14_placeholders" / "deck.pptx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_governance_deck(model, out_path)

    errors = check_governance_deck_traceability(model, out_path)
    assert "Slide 14 contains unreplaced placeholder text" in errors


# --- Group G: Slide 15 Acceptance Criteria Table & Title Invariants ---


def test_validator_branch_11_slide15_missing_table(tmp_path):
    """Branch 11: Catch Slide 15 missing Deliverable Acceptance Criteria table."""
    model, pptx_path = _create_valid_deck_and_model(tmp_path, "s15_missing_table")
    prs = pptx.Presentation(str(pptx_path))

    s15 = prs.slides[14]
    # Remove table shape
    for shape in list(s15.shapes):
        if shape.has_table:
            sp_elem = shape._element
            sp_elem.getparent().remove(sp_elem)
    prs.save(str(pptx_path))

    errors = check_governance_deck_traceability(model, pptx_path)
    assert "Slide 15 is missing Deliverable Acceptance Criteria table" in errors


def test_validator_branch_12_slide15_missing_title(tmp_path):
    """Branch 12: Catch Slide 15 missing title 'Deliverable acceptance criteria'."""
    model, pptx_path = _create_valid_deck_and_model(tmp_path, "s15_missing_title")
    prs = pptx.Presentation(str(pptx_path))

    s15 = prs.slides[14]
    for shape in s15.shapes:
        if shape.has_text_frame and "Deliverable acceptance criteria" in shape.text_frame.text:
            shape.text_frame.text = "Other Deliverable Criteria"
    prs.save(str(pptx_path))

    errors = check_governance_deck_traceability(model, pptx_path)
    assert "Slide 15 is missing title 'Deliverable acceptance criteria'" in errors


# --- Group H: Slide 16 How Milestone Acceptance Works Title & Placeholder Invariants ---


def test_validator_branch_13_slide16_missing_title(tmp_path):
    """Branch 13: Catch Slide 16 missing title 'How milestone acceptance works'."""
    model, pptx_path = _create_valid_deck_and_model(tmp_path, "s16_missing_title")
    prs = pptx.Presentation(str(pptx_path))

    s16 = prs.slides[15]
    for shape in s16.shapes:
        if shape.has_text_frame and "How milestone acceptance works" in shape.text_frame.text:
            shape.text_frame.text = "Acceptance Milestone Process"
    prs.save(str(pptx_path))

    errors = check_governance_deck_traceability(model, pptx_path)
    assert "Slide 16 is missing title 'How milestone acceptance works'" in errors


def test_validator_branch_14_slide16_unreplaced_placeholders(tmp_path):
    """Branch 14: Catch Slide 16 containing '[Pre-filled:' or '[CONFIRMATION REQUIRED]' placeholder text."""
    baseline = _build_pge_baseline()
    model = build_governance_deck_model(baseline)
    model.slide16.cards[0].steps.append(("Review", "[CONFIRMATION REQUIRED] Acceptance review period"))
    out_path = tmp_path / "s16_placeholders" / "deck.pptx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_governance_deck(model, out_path)

    errors = check_governance_deck_traceability(model, out_path)
    assert "Slide 16 contains unreplaced placeholder text" in errors


# --- Group I: Slide 17 Approach Title & Placeholder Invariants ---


def test_validator_branch_15_slide17_missing_title(tmp_path):
    """Branch 15: Catch Slide 17 missing title 'Approach'."""
    baseline = _build_pge_baseline()
    model = build_governance_deck_model(baseline)
    model.slide17.title = "Project Delivery Strategy"
    out_path = tmp_path / "s17_missing_title" / "deck.pptx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_governance_deck(model, out_path)

    errors = check_governance_deck_traceability(model, out_path)
    assert "Slide 17 is missing title 'Approach'" in errors


def test_validator_branch_16_slide17_unreplaced_placeholders(tmp_path):
    """Branch 16: Catch Slide 17 containing '[Pre-filled:' or '[CONFIRMATION REQUIRED]' placeholder text."""
    baseline = _build_pge_baseline()
    model = build_governance_deck_model(baseline)
    model.slide17.cards[0].bullets.append("[Pre-filled: Core Technical Methodology]")
    out_path = tmp_path / "s17_placeholders" / "deck.pptx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_governance_deck(model, out_path)

    errors = check_governance_deck_traceability(model, out_path)
    assert "Slide 17 contains unreplaced placeholder text" in errors


# --- Group J: Slide 18 & 19 Structured Table Invariants ---


def test_validator_branch_17_slide18_missing_risk_table(tmp_path):
    """Branch 17: Catch Slide 18 missing Initial Risk Register table."""
    model, pptx_path = _create_valid_deck_and_model(tmp_path, "s18_missing_table")
    prs = pptx.Presentation(str(pptx_path))

    s18 = prs.slides[17]
    for shape in list(s18.shapes):
        if shape.has_table:
            sp_elem = shape._element
            sp_elem.getparent().remove(sp_elem)
    prs.save(str(pptx_path))

    errors = check_governance_deck_traceability(model, pptx_path)
    assert "Slide 18 is missing Initial Risk Register table" in errors


def test_validator_branch_18_slide19_missing_next_steps_table(tmp_path):
    """Branch 18: Catch Slide 19 missing Next Steps table."""
    model, pptx_path = _create_valid_deck_and_model(tmp_path, "s19_missing_table")
    prs = pptx.Presentation(str(pptx_path))

    s19 = prs.slides[18]
    for shape in list(s19.shapes):
        if shape.has_table:
            sp_elem = shape._element
            sp_elem.getparent().remove(sp_elem)
    prs.save(str(pptx_path))

    errors = check_governance_deck_traceability(model, pptx_path)
    assert "Slide 19 is missing Next Steps table" in errors


# --- Group K: Companion Trace Manifest Invariants ---


def test_validator_branch_19_missing_manifest_file(tmp_path):
    """Branch 19: Catch companion trace manifest file missing on disk."""
    model, pptx_path = _create_valid_deck_and_model(tmp_path, "manifest_missing")
    manifest_path = pptx_path.with_name(f"{pptx_path.stem}.trace.json")

    # Delete manifest file on disk
    if manifest_path.exists():
        manifest_path.unlink()

    errors = check_governance_deck_traceability(model, pptx_path)
    assert any(f"Trace manifest file missing at {manifest_path}" in e for e in errors)


def test_validator_branch_20_empty_manifest_entries(tmp_path):
    """Branch 20: Catch trace manifest with 0 entries."""
    model, pptx_path = _create_valid_deck_and_model(tmp_path, "manifest_empty")

    # Set manifest entries to empty
    model.manifest.entries = []

    errors = check_governance_deck_traceability(model, pptx_path)
    assert "Trace manifest has 0 entries" in errors


# --- Control / Happy Path Verification ---


def test_validator_happy_path_returns_zero_errors(tmp_path):
    """Verify that a clean, unmutated valid presentation produces 0 validation errors."""
    model, pptx_path = _create_valid_deck_and_model(tmp_path, "clean_happy_path")
    errors = check_governance_deck_traceability(model, pptx_path)
    assert errors == []
