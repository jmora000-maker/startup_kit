"""Tests for deck traceability, the manifest, and INV-26 (DECK-04, DECK-05, DECK-06, DECK-10, DECK-19, DECK-20, DECK-22, INV-26)."""

import copy
import json

import pytest

from src.tools.check_artifacts import check_artifacts_directory, check_deck_invariants
from tests.deck_bundle import FIXTURES, build_bundle


def _manifest(bundle):
    return json.loads(bundle["manifest_path"].read_text(encoding="utf-8"))


def _check_with(bundle, manifest_data, tmp_path, name="broken.trace.json"):
    path = tmp_path / name
    path.write_text(json.dumps(manifest_data), encoding="utf-8")
    out = check_deck_invariants(bundle["deck_path"], path, bundle["kit"], bundle["wb"])
    return [str(v) for v in out if v.inv_id == "INV-26"]


# --- the written manifest (DECK-04, DECK-06) -----------------------------------------------------
def test_inv26_passes_on_a_valid_deck(arc_bundle):
    assert [str(v) for v in check_deck_invariants(arc_bundle["deck_path"], arc_bundle["manifest_path"], arc_bundle["kit"], arc_bundle["wb"]) if v.inv_id == "INV-26"] == []


@pytest.mark.parametrize("name", FIXTURES)
def test_inv26_passes_on_every_fixture(name, tmp_path):
    bundle = build_bundle(tmp_path, name)
    assert [str(v) for v in check_artifacts_directory(tmp_path) if v.inv_id == "INV-26"] == []


def test_manifest_uses_real_keys_and_the_two_artifact_names(arc_bundle):
    """L10: no invented keys such as 'M1 Step 1' or 'Title Row 3'; artifact is Kit or Workbook."""
    data = _manifest(arc_bundle)
    for e in data["entries"]:
        assert e["shape"] and e["traces"]
        for t in e["traces"]:
            assert t["artifact"] in ("Kit", "Workbook")
            assert not t["key"].startswith(("M1 Step", "Title Row"))
    keys = {t["key"] for e in data["entries"] for t in e["traces"]}
    assert {"M1", "DEL-07", "RAID-01", "COM-03", "1.1.7.1", "Client Sponsor", "Start Date"} <= keys


def test_manifest_lists_every_talking_point_on_slides_2_to_6(arc_bundle):
    data = _manifest(arc_bundle)
    for slide in range(2, 7):
        points = [e for e in data["entries"] if e["slide"] == slide and e["element"].startswith("Talking point")]
        assert 3 <= len(points) <= 6


def test_placeholders_are_traced_to_the_placeholder_in_the_source(arc_bundle):
    """DECK-10: 'To be confirmed' carries its TraceRef and is accepted against the source placeholder."""
    data = _manifest(arc_bundle)
    tbc = [e for e in data["entries"] if e["displayed_value"] == "To be confirmed"]
    assert tbc and all(e["traces"] for e in tbc)


def test_only_displayed_kit_content_is_a_source(arc_bundle):
    """DECK-19: delivery objectives and success criteria are in the model but not displayed by the Kit tables."""
    data = _manifest(arc_bundle)
    assert not any(t["field"] in ("Delivery Objectives", "Success Criteria") for e in data["entries"] for t in e["traces"])


# --- broken manifests --------------------------------------------------------------------------
def test_inv26_fails_when_a_displayed_value_is_altered_by_one_word(arc_bundle, tmp_path):
    data = copy.deepcopy(_manifest(arc_bundle))
    entry = next(e for e in data["entries"] if e["traces"][0]["artifact"] == "Kit" and len(e["displayed_value"]) > 10 and not e["element"].startswith("Talking"))
    entry["displayed_value"] += " ExtraWord"
    assert _check_with(arc_bundle, data, tmp_path)


def test_inv26_fails_when_a_trace_points_to_a_missing_sheet(arc_bundle, tmp_path):
    data = copy.deepcopy(_manifest(arc_bundle))
    next(e for e in data["entries"] if e["traces"][0]["artifact"] == "Workbook")["traces"][0]["locator"] = "NonExistentSheet"
    assert any("NonExistentSheet" in m for m in _check_with(arc_bundle, data, tmp_path))


def test_inv26_fails_when_an_element_has_no_traceref(arc_bundle, tmp_path):
    data = copy.deepcopy(_manifest(arc_bundle))
    data["entries"][0]["traces"] = []
    assert any("has no TraceRef" in m for m in _check_with(arc_bundle, data, tmp_path))


def test_inv26_fails_when_text_is_paraphrased(arc_bundle, tmp_path):
    data = copy.deepcopy(_manifest(arc_bundle))
    next(e for e in data["entries"] if e["element"] == "Purpose")["displayed_value"] = "This project aims to modernize genomic pipelines completely."
    assert _check_with(arc_bundle, data, tmp_path)


def test_inv26_fails_when_the_rating_differs_from_deck_20(arc_bundle, tmp_path):
    data = copy.deepcopy(_manifest(arc_bundle))
    next(e for e in data["entries"] if e["element"] == "Rating")["displayed_value"] = "Low"
    assert any("DECK-20" in m for m in _check_with(arc_bundle, data, tmp_path))


def test_inv26_fails_on_an_invented_key(arc_bundle, tmp_path):
    data = copy.deepcopy(_manifest(arc_bundle))
    next(e for e in data["entries"] if e["element"].startswith("Acceptance step"))["traces"][0]["key"] = "M1 Step 1"
    assert any("M1 Step 1" in m for m in _check_with(arc_bundle, data, tmp_path))


def test_inv26_fails_when_the_manifest_is_missing(arc_bundle, tmp_path):
    out = check_deck_invariants(arc_bundle["deck_path"], tmp_path / "absent.trace.json", arc_bundle["kit"], arc_bundle["wb"])
    assert any(v.inv_id == "INV-26" and "missing" in str(v) for v in out)


def test_inv26_fails_when_a_talking_point_entry_is_removed(arc_bundle, tmp_path):
    data = copy.deepcopy(_manifest(arc_bundle))
    data["entries"] = [e for e in data["entries"] if not (e["slide"] == 3 and e["element"] == "Talking point 1")]
    assert any("talking point has no trace manifest entry" in m for m in _check_with(arc_bundle, data, tmp_path))


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
