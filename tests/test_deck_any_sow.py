"""Tests that the Onboarding Deck builds for every fixture and for SOWs with missing sections (DECK-15)."""

import pytest

from src.tools.check_artifacts import check_artifacts_directory
from tests.deck_bundle import FIXTURES, build_bundle, load_baseline, slide_text


@pytest.mark.parametrize("name", FIXTURES)
def test_deck_builds_and_passes_all_checks_for_every_fixture(name, tmp_path):
    bundle = build_bundle(tmp_path, name)
    assert bundle["deck_path"].exists() and bundle["manifest_path"].exists()
    assert bundle["result"].slides_count == 7
    assert [str(v) for v in check_artifacts_directory(tmp_path)] == []


def _without(attr):
    baseline = load_baseline("arc_genomics")
    setattr(baseline, attr, [])
    return baseline


@pytest.mark.parametrize("attr", ["stakeholders", "communications_plan", "raid_items", "deliverables", "dependencies_assumptions"])
def test_deck_builds_when_a_section_is_empty(attr, tmp_path):
    bundle = build_bundle(tmp_path, baseline=_without(attr))
    assert bundle["result"].slides_count == 7
    violations = [str(v) for v in check_artifacts_directory(tmp_path) if v.inv_id in ("INV-26", "INV-27", "INV-29", "INV-31", "INV-32")]
    assert violations == []


def test_empty_sections_show_one_fixed_line(tmp_path):
    bundle = build_bundle(tmp_path / "a", baseline=_without("stakeholders"))
    assert "None recorded in the Startup Kit" in slide_text(bundle["prs"].slides[5])
    bundle = build_bundle(tmp_path / "b", baseline=_without("communications_plan"))
    assert "None recorded in the Startup Kit" in slide_text(bundle["prs"].slides[5])


def test_deck_builds_with_no_charter_and_no_sow_summary(tmp_path):
    baseline = load_baseline("arc_genomics")
    baseline.charter = None
    baseline.sow_interpretation = None
    bundle = build_bundle(tmp_path, baseline=baseline)
    assert bundle["result"].slides_count == 7
    assert [str(v) for v in check_artifacts_directory(tmp_path) if v.inv_id in ("INV-26", "INV-31", "INV-32")] == []
