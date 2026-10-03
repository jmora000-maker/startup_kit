"""Tests for QA-12 exact-match-first oracle resolution."""

from pathlib import Path
from src.tools.check_artifacts import load_oracle_for_folder
from tests.test_oracles import load_oracle


def test_exact_match_priority_over_substring():
    """QA-12: Exact fixture oracle is loaded even when substring matches other oracles (e.g. 'arc')."""
    # 1. Direct load_oracle by fixture name
    oracle = load_oracle("arc_application_implementation")
    assert oracle is not None
    assert oracle.get("fixture") == "arc_application_implementation"
    assert oracle.get("award_date_stated_in_sow") is True
    assert oracle.get("named_delivery_manager") == "Saadia Iqbal"

    # 2. load_oracle_for_folder by folder name
    oracle_folder = load_oracle_for_folder(Path("output/arc_application_implementation"))
    assert oracle_folder is not None
    assert oracle_folder.get("fixture") == "arc_application_implementation"
    assert oracle_folder.get("award_date_stated_in_sow") is True

    # 3. load_oracle_for_folder by project name
    oracle_proj = load_oracle_for_folder(
        Path("output/some_arbitrary_folder"),
        project_name="ARC Application Implementation",
    )
    assert oracle_proj is not None
    assert oracle_proj.get("fixture") == "arc_application_implementation"
    assert oracle_proj.get("award_date_stated_in_sow") is True

    # 4. load_oracle_for_folder by project name with sanitized slug matching
    oracle_slug = load_oracle_for_folder(
        Path("output/arc_app_clean_rev12"),
        project_name="ARC Application Implementation",
    )
    assert oracle_slug is not None
    assert oracle_slug.get("fixture") == "arc_application_implementation"


def test_alias_fallback_when_no_exact_file_exists():
    """QA-12: Known aliases resolve to arc.json when no exact oracle file exists."""
    for name in ["arc", "arc_genomics", "arc_overextracted", "arc_run1", "arc_run2", "arc_run3", "arc_run4"]:
        oracle = load_oracle(name)
        assert oracle is not None, f"Expected oracle for alias {name}"
        assert oracle.get("gate_count") == 4
        assert oracle.get("award_date_stated_in_sow") is False

    # Check via load_oracle_for_folder
    oracle_genomics = load_oracle_for_folder(Path("output/arc_genomics"))
    assert oracle_genomics is not None
    assert oracle_genomics.get("award_date_stated_in_sow") is False

    oracle_overext = load_oracle_for_folder(Path("output/arc_overextracted"))
    assert oracle_overext is not None
    assert oracle_overext.get("award_date_stated_in_sow") is False


def test_non_matching_fixture_resolves_to_none():
    """QA-12: Unrelated fixtures (even if containing 'arc') resolve to None without false guesses."""
    # Substring 'arc' in unknown fixture names must NOT match arc.json
    assert load_oracle("arc_custom_unrelated") is None
    assert load_oracle("genomics_custom") is None
    assert load_oracle("my_arc_project") is None

    # load_oracle_for_folder on non-aliased folders
    assert load_oracle_for_folder(Path("output/arc_custom_unrelated"), project_name="ARC Unrelated") is None
    assert load_oracle_for_folder(Path("output/mock_sow"), project_name="Pfizer Analytics & Cloud Modernization") is None
    assert load_oracle_for_folder(Path("output/no_story_ids"), project_name="No Story IDs") is None
    assert load_oracle_for_folder(Path("output/numbered_deliverables"), project_name="Numbered Deliverables") is None
