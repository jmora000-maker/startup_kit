"""Tests for Deck builder and determinism (DECK-03, DECK-14)."""

import json
from pathlib import Path
import pytest

from src.core.models import StartupKitBaseline
from src.generators.onboarding_deck import build_deck_model, export_onboarding_deck
from src.llm.validation import validate_and_repair_baseline


@pytest.fixture
def arc_baseline():
    fixture_dir = Path("tests/fixtures/sow/arc_genomics")
    with open(fixture_dir / "baseline.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    baseline = StartupKitBaseline.model_validate(data)
    validate_and_repair_baseline(baseline)
    return baseline


def test_deck_builder_model_structure(arc_baseline):
    """DeckModel builds pure data structure with 6 slides and manifest."""
    model = build_deck_model(arc_baseline)
    assert model.project_name == "ARC Genomics Platform"
    assert model.cover_slide.title == "ARC Genomics Platform"
    assert model.charter_slide.title == "Project Charter"
    assert model.schedule_slide.title == "Workstreams, Milestones, Deliverables and Dates"
    assert model.acceptance_slide.title == "Acceptance Criteria"
    assert model.risks_slide.title == "High-Risk Items"
    assert model.collaboration_slide.title == "Client Collaboration"
    assert len(model.manifest.entries) > 0


def test_deck_builder_determinism(arc_baseline, tmp_path):
    """DECK-14: Two independent builds produce identical deck model text and identical manifest."""
    model1 = build_deck_model(arc_baseline)
    model2 = build_deck_model(arc_baseline)

    assert model1.cover_slide == model2.cover_slide
    assert model1.charter_slide == model2.charter_slide
    assert model1.schedule_slide == model2.schedule_slide
    assert model1.acceptance_slide == model2.acceptance_slide
    assert model1.risks_slide == model2.risks_slide
    assert model1.collaboration_slide == model2.collaboration_slide
    assert model1.manifest.to_dict() == model2.manifest.to_dict()

    dir1 = tmp_path / "run1"
    dir2 = tmp_path / "run2"
    res1 = export_onboarding_deck(arc_baseline, dir1)
    res2 = export_onboarding_deck(arc_baseline, dir2)

    with open(res1.manifest_path, "r", encoding="utf-8") as f1, open(res2.manifest_path, "r", encoding="utf-8") as f2:
        assert json.load(f1) == json.load(f2)
