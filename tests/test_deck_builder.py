"""Tests for the Deck builder and determinism (DECK-03, DECK-14)."""

import json

from src.generators.onboarding_deck import build_deck_model, export_onboarding_deck
from tests.deck_bundle import load_baseline


def test_deck_builder_model_structure():
    """The DeckModel is pure data: a cover, slides 2 to 7 in order, and a manifest."""
    model = build_deck_model(load_baseline())
    assert model.project_name == "ARC Genomics Platform"
    assert model.cover.title.text == "ARC Genomics Platform"
    assert [s.title for s in model.slides] == [
        "Project Charter",
        "Workstreams, Milestones, Deliverables and Dates",
        "Acceptance Criteria",
        "High-Risk Items",
        "Client Collaboration",
        "Your Project Kit",
    ]
    assert [s.number for s in model.slides] == [2, 3, 4, 5, 6, 7]
    assert model.kit_file_name == "ARC_Genomics_Platform_Startup_Kit.docx"
    assert len(model.manifest.entries) > 0


def test_deck_builder_is_pure_and_deterministic(tmp_path):
    """DECK-14: two builds give an identical model and manifest; two exports give an identical manifest."""
    baseline = load_baseline()
    m1, m2 = build_deck_model(baseline), build_deck_model(baseline)
    assert m1.cover == m2.cover
    assert m1.slides == m2.slides
    assert m1.manifest.to_dict() == m2.manifest.to_dict()

    res1 = export_onboarding_deck(baseline, tmp_path / "run1")
    res2 = export_onboarding_deck(baseline, tmp_path / "run2")
    assert json.loads(res1.manifest_path.read_text(encoding="utf-8")) == json.loads(res2.manifest_path.read_text(encoding="utf-8"))


def test_manifest_has_shape_names_traces_and_talking_points():
    model = build_deck_model(load_baseline())
    entries = model.manifest.entries
    assert all(e.traces for e in entries)
    assert all(e.shape for e in entries)
    for slide_no in range(2, 7):
        assert any(e.slide == slide_no and e.element.startswith("Talking point") for e in entries)
