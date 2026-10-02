"""Tests for Deck traceability, manifest generation, and INV-26 verification (DECK-04, DECK-05, DECK-06, DECK-19, DECK-20, INV-26)."""

import json
from pathlib import Path
import pytest
import docx
import openpyxl

from src.core.models import StartupKitBaseline
from src.generators.docx_generator import DocxGenerator
from src.generators.pmo_workbook import export_pmo_workbook
from src.generators.onboarding_deck import export_onboarding_deck, build_deck_model, write_onboarding_deck
from src.generators.onboarding_deck.trace import TraceRef
from src.tools.check_artifacts import check_deck_invariants, check_artifacts_directory
from src.llm.validation import validate_and_repair_baseline


@pytest.fixture
def arc_artifacts(tmp_path):
    """Generate Kit, Workbook, and Deck for ARC Genomics fixture."""
    fixture_dir = Path("tests/fixtures/sow/arc_genomics")
    baseline_file = fixture_dir / "baseline.json"
    with open(baseline_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    baseline = StartupKitBaseline.model_validate(data)
    validate_and_repair_baseline(baseline)

    writer = DocxGenerator()
    kit_path = writer.write_kit_docx(baseline, tmp_path)
    wb_res = export_pmo_workbook(baseline, tmp_path)
    deck_res = export_onboarding_deck(baseline, tmp_path)

    return {
        "baseline": baseline,
        "tmp_path": tmp_path,
        "kit_path": kit_path,
        "wb_path": wb_res.file_path,
        "deck_path": deck_res.file_path,
        "manifest_path": deck_res.manifest_path,
    }


def test_inv26_passes_on_valid_deck(arc_artifacts):
    """INV-26 passes on cleanly generated artifacts."""
    kit_doc = docx.Document(str(arc_artifacts["kit_path"]))
    wb = openpyxl.load_workbook(str(arc_artifacts["wb_path"]), data_only=False)

    violations = check_deck_invariants(
        arc_artifacts["deck_path"],
        arc_artifacts["manifest_path"],
        kit_doc,
        wb,
    )
    inv26_violations = [v for v in violations if v.inv_id == "INV-26"]
    assert len(inv26_violations) == 0, f"Unexpected INV-26 violations: {inv26_violations}"


def test_inv26_fails_when_displayed_value_altered_by_one_word(arc_artifacts, tmp_path):
    """INV-26 fails when a displayed value in the manifest is modified by one word."""
    manifest_path = arc_artifacts["manifest_path"]
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    # Alter one entry's displayed value
    for entry in manifest_data["entries"]:
        if entry["trace"]["artifact"] == "Startup Kit" and len(entry["displayed_value"]) > 10:
            entry["displayed_value"] = entry["displayed_value"] + " ExtraWord"
            break

    broken_manifest_path = tmp_path / "broken_value.trace.json"
    with open(broken_manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)

    kit_doc = docx.Document(str(arc_artifacts["kit_path"]))
    wb = openpyxl.load_workbook(str(arc_artifacts["wb_path"]), data_only=False)

    violations = check_deck_invariants(
        arc_artifacts["deck_path"],
        broken_manifest_path,
        kit_doc,
        wb,
    )
    inv26_violations = [v for v in violations if v.inv_id == "INV-26"]
    assert len(inv26_violations) > 0, "Expected INV-26 violation for altered displayed value"
    assert "not found in Startup Kit" in str(inv26_violations[0])


def test_inv26_fails_when_trace_ref_points_to_missing_sheet(arc_artifacts, tmp_path):
    """INV-26 fails when a TraceRef points to a non-existent sheet/locator."""
    manifest_path = arc_artifacts["manifest_path"]
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    for entry in manifest_data["entries"]:
        if entry["trace"]["artifact"] == "Project Delivery Workbook":
            entry["trace"]["locator"] = "NonExistentSheet"
            break

    broken_manifest_path = tmp_path / "broken_sheet.trace.json"
    with open(broken_manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)

    kit_doc = docx.Document(str(arc_artifacts["kit_path"]))
    wb = openpyxl.load_workbook(str(arc_artifacts["wb_path"]), data_only=False)

    violations = check_deck_invariants(
        arc_artifacts["deck_path"],
        broken_manifest_path,
        kit_doc,
        wb,
    )
    inv26_violations = [v for v in violations if v.inv_id == "INV-26"]
    assert len(inv26_violations) > 0, "Expected INV-26 violation for missing workbook sheet"


def test_inv26_fails_when_element_has_no_trace_ref(arc_artifacts, tmp_path):
    """INV-26 fails when an element entry has an empty/null TraceRef."""
    manifest_path = arc_artifacts["manifest_path"]
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    manifest_data["entries"][0]["trace"] = None

    broken_manifest_path = tmp_path / "missing_ref.trace.json"
    with open(broken_manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)

    kit_doc = docx.Document(str(arc_artifacts["kit_path"]))
    wb = openpyxl.load_workbook(str(arc_artifacts["wb_path"]), data_only=False)

    violations = check_deck_invariants(
        arc_artifacts["deck_path"],
        broken_manifest_path,
        kit_doc,
        wb,
    )
    inv26_violations = [v for v in violations if v.inv_id == "INV-26"]
    assert len(inv26_violations) > 0, "Expected INV-26 violation for missing TraceRef"
    assert "has no TraceRef" in str(inv26_violations[0])


def test_inv26_fails_when_text_is_paraphrased(arc_artifacts, tmp_path):
    """INV-26 fails when text is paraphrased rather than a clause-boundary prefix."""
    manifest_path = arc_artifacts["manifest_path"]
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    for entry in manifest_data["entries"]:
        if entry["trace"]["artifact"] == "Startup Kit" and "Project Purpose" in entry["element"]:
            entry["displayed_value"] = "This project aims to modernize genomic pipelines completely."
            break

    broken_manifest_path = tmp_path / "paraphrased.trace.json"
    with open(broken_manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)

    kit_doc = docx.Document(str(arc_artifacts["kit_path"]))
    wb = openpyxl.load_workbook(str(arc_artifacts["wb_path"]), data_only=False)

    violations = check_deck_invariants(
        arc_artifacts["deck_path"],
        broken_manifest_path,
        kit_doc,
        wb,
    )
    inv26_violations = [v for v in violations if v.inv_id == "INV-26"]
    assert len(inv26_violations) > 0, "Expected INV-26 violation for paraphrased text"


def test_inv26_fails_when_rating_differs_from_deck20(arc_artifacts, tmp_path):
    """INV-26 fails when a displayed rating disagrees with the DECK-20 rule."""
    manifest_path = arc_artifacts["manifest_path"]
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    for entry in manifest_data["entries"]:
        if entry["trace"]["artifact"] == "Project Delivery Workbook" and entry["displayed_value"] == "High":
            entry["displayed_value"] = "Low"  # Falsify rating
            break

    broken_manifest_path = tmp_path / "broken_rating.trace.json"
    with open(broken_manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)

    kit_doc = docx.Document(str(arc_artifacts["kit_path"]))
    wb = openpyxl.load_workbook(str(arc_artifacts["wb_path"]), data_only=False)

    violations = check_deck_invariants(
        arc_artifacts["deck_path"],
        broken_manifest_path,
        kit_doc,
        wb,
    )
    inv26_violations = [v for v in violations if v.inv_id == "INV-26"]
    assert len(inv26_violations) > 0, "Expected INV-26 violation for incorrect DECK-20 rating"
    assert "differs from DECK-20" in str(inv26_violations[0])


# ---------------------------------------------------------------------------------------------
# Rev 10, step 1: INV-26 hardened (DECK-04 real keys, DECK-05 boundary rules, DECK-09 manifest)
# Broken-input unit tests on small synthetic artifacts; each must name INV-26.
# ---------------------------------------------------------------------------------------------
from tests.deck_fixtures import make_kit, make_workbook, blank_deck, add_text, trace, entry
from src.tools import deck_checks


@pytest.fixture
def synthetic(tmp_path):
    kit = make_kit(tmp_path / "kit.docx")
    wb = make_workbook(tmp_path / "wb.xlsx")
    return deck_checks.SourceIndex(kit, wb)


KIT_DEL = ("Kit", "Deliverables and Acceptance Matrix")


def _del_entry(value, key="DEL-01", field="Deliverable Name"):
    return entry(2, "Text", "Name", value, trace(*KIT_DEL, key, field))


def _inv26(entries, index, prs=None):
    return [v for v in deck_checks.check_inv26(entries, index, prs) if v.inv_id == "INV-26"]


def test_inv26_accepts_whole_names_dates_and_clause_prefixes(synthetic):
    name = "Backend Integration/Load Tests and Performance Engineering Spike"
    entries = [
        _del_entry(name),
        entry(2, "Text", "Criteria", "Search P95 < 1s under load.", trace(*KIT_DEL, "DEL-01", "Acceptance Criteria")),
        entry(1, "Text", "Start", "2026-10-05", trace("Workbook", "Project Schedule", "Start Date", "Start Date")),
        entry(3, "Table", "Milestone", "P1 Foundation accepted", trace("Workbook", "Project Schedule", "M1", "Milestone")),
        entry(2, "Text", "Sponsor", "Acme", trace("Kit", "Header table", "Client Sponsor", "Client Sponsor")),
    ]
    assert _inv26(entries, synthetic) == []


def test_inv26_rejects_invented_keys(synthetic):
    """L10: keys such as 'M1 Step 1' and 'Title Row 3' do not appear in the source."""
    bad = [
        entry(4, "Text", "Step", "Anything", trace("Workbook", "WBS", "M1 Step 1", "Name")),
        entry(1, "Text", "Start", "2026-10-05", trace("Workbook", "Project Schedule", "Title Row 3", "Start Date")),
    ]
    msgs = [str(v) for v in _inv26(bad, synthetic)]
    assert any("M1 Step 1" in m for m in msgs) and any("Title Row 3" in m for m in msgs)


def test_inv26_rejects_unknown_field_and_artifact_alias(synthetic):
    msgs = [str(v) for v in _inv26([entry(2, "Text", "X", "Demo Project", trace("Kit", "Header table", "Project Name", "Project Name")),
                                    entry(2, "Text", "Y", "Fixed Bid", trace("Startup Kit", "Header table", "Contract Type", "Contract Type")),
                                    entry(2, "Text", "Z", "Open", trace("Workbook", "RAID Log", "RAID-01", "Probability and Impact"))], synthetic)]
    assert any("must be 'Kit'" in m for m in msgs)
    assert any("Probability and Impact" in m and "not found" in m for m in msgs)


def test_inv26_rejects_comma_cut_ellipsis_unbalanced_and_name_cut(synthetic):
    """L5, L6: boundary rules (DECK-05)."""
    crit = "Search P95 < 1s under load. Targets are defined, and the backlog is triaged."
    cases = {
        "comma cut": entry(2, "Text", "C", "Search P95 < 1s under load. Targets are defined,", trace(*KIT_DEL, "DEL-01", "Acceptance Criteria")),
        "ellipsis": entry(2, "Text", "C", "Search P95 < 1s under load. Targets are...", trace(*KIT_DEL, "DEL-01", "Acceptance Criteria")),
        "mid-phrase": entry(2, "Text", "C", "Search P95 < 1s under load. Targets are defined, and the", trace(*KIT_DEL, "DEL-01", "Acceptance Criteria")),
        "name cut": _del_entry("Backend Integration/Load Tests and Performance Engineering"),
        "name cut at a boundary": _del_entry("Production Smoke Tests and 48-Hour Defect", "DEL-02"),
    }
    assert crit  # the source the cut cases are cut from
    for label, e in cases.items():
        assert _inv26([e], synthetic), f"INV-26 passed a {label}"
    unbalanced = entry(2, "Text", "R", "Use query observability (HS-4942", trace("Workbook", "RAID Log", "RAID-01", "Mitigation / Response"))
    assert any("unbalanced" in str(v) for v in _inv26([unbalanced], synthetic))


def test_inv26_rejects_altered_text_and_placeholder_misuse(synthetic):
    assert _inv26([entry(2, "Text", "S", "Acme Corp", trace("Kit", "Header table", "Client Sponsor", "Client Sponsor"))], synthetic)
    assert _inv26([entry(2, "Text", "S", "To be confirmed", trace("Kit", "Header table", "Client Sponsor", "Client Sponsor"))], synthetic)


def test_inv26_rating_is_recomputed_from_probability_and_impact(synthetic):
    refs = (trace("Workbook", "RAID Log", "RAID-01", "Probability"), trace("Workbook", "RAID Log", "RAID-01", "Impact"))
    assert _inv26([entry(5, "Table", "Rating", "High", *refs, derived="rating")], synthetic) == []
    assert _inv26([entry(5, "Table", "Rating", "Low", *refs, derived="rating")], synthetic)


def test_inv26_talking_points_need_manifest_entries_and_traced_values(synthetic):
    prs, slides = blank_deck(2)
    slides[1].notes_slide.notes_text_frame.text = "TALKING POINTS:\n• The client sponsor is Acme.\n\nSOURCES: Kit"
    assert any("no trace manifest entry" in str(v) for v in _inv26([], synthetic, prs) + deck_checks.check_inv26([entry(2, "Notes", "Heading", "x", trace("Kit", "Header table", "Client Sponsor", "Client Sponsor"))], synthetic, prs))
    tp = entry(2, "Notes", "Talking point 1", "The client sponsor is Acme.", trace("Kit", "Header table", "Client Sponsor", "Client Sponsor"), values=["Acme"])
    ok = [v for v in deck_checks.check_inv26([tp], synthetic, prs) if "talking point" in str(v).lower()]
    assert ok == []
    no_value = dict(tp, values=[])
    assert any("no traced value" in str(v) for v in deck_checks.check_inv26([no_value], synthetic, prs))


def test_inv26_flags_slide_text_without_a_traceref(synthetic):
    prs, slides = blank_deck(2)
    add_text(slides[1], 0.83, 1.7, 3.0, 1.0, ["Acme", "An untraced claim about delivery"])
    entries = [entry(2, "Text", "Sponsor", "Acme", trace("Kit", "Header table", "Client Sponsor", "Client Sponsor"))]
    msgs = [str(v) for v in deck_checks.check_inv26(entries, synthetic, prs)]
    assert any("An untraced claim about delivery" in m and "no TraceRef" in m for m in msgs)
