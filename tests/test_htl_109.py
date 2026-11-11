"""HTL-109: Comprehensive test suite for Governance Deck Slide 11 (Change Decision Matrix) and Truncation Elimination across both decks.

Verifies:
1. Part 1: Slide 11 Change Decision Matrix layout, 4-card structure, contract_type variant wiring (Fixed Bid vs T&M), header formatting, and footer banner.
2. Part 1: Slide renumbering / insertion right after Slide 10, pushing Project Details and subsequent slides down by one.
3. Part 2: Content condensation for problem_statement and solution_overview in both Governance Deck and Client Deck, eliminating mechanical '...' truncation while preserving complete meaning.
4. Box height and typography fitting validation at target 10.0pt font size.
"""

from pathlib import Path
import pptx
import pytest

from src.core.models import StartupKitBaseline
from src.generators.governance_deck import (
    GovernanceDeckModel,
    build_governance_deck_model,
    export_governance_deck,
    check_governance_deck_traceability,
)
from src.generators.client_deck import (
    ClientDeckModel,
    build_client_deck_model,
    export_client_deck,
)
from src.generators.client_deck.fit import (
    condense_problem_statement,
    condense_solution_overview,
    estimate_text_height,
)
from tests.deck_bundle import load_baseline
from tests.test_htl_62 import _build_pge_baseline


def test_htl_109_slide11_change_decision_matrix_structure_and_geometry(tmp_path: Path):
    """HTL-109: Verify Slide 11 (Change Decision Matrix) is inserted at index 10 with exact 4-card layout, headers, and footer banner."""
    baseline = _build_pge_baseline()
    res = export_governance_deck(baseline, tmp_path / "gov_s11_test")
    prs = pptx.Presentation(str(res.file_path))

    # Slide 11 is at index 10 (0-indexed)
    slide11 = prs.slides[10]

    # 1. Header validations
    textboxes = [s.text_frame.text.strip() for s in slide11.shapes if s.has_text_frame]
    assert "DECISION RIGHTS IN PRACTICE" in textboxes
    assert "Change Decision Matrix" in textboxes

    # 2. Card validations (4 cards: Clarification, Reprioritization, Expansion, Dependency Impact)
    all_text = " ".join(textboxes)
    assert "Clarification" in all_text
    assert "Reprioritization" in all_text
    assert "Expansion" in all_text
    assert "Dependency Impact" in all_text
    assert "WHAT IT MEANS" in all_text
    assert "Authority:" in all_text

    # 3. Footer Banner validation
    assert any("To keep commitments consistent, please work with your DM and PMO" in t for t in textboxes)

    # 4. Card count & positioning
    # Total shapes includes: header shapes, 4 card backgrounds, 4 title boxes, 4 impact boxes, 4 pill backgrounds, 4 pill textboxes, 1 footer bg, 1 footer accent, 1 footer text
    auto_shapes = [s for s in slide11.shapes if s.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.AUTO_SHAPE]
    assert len(auto_shapes) >= 4

    # Card horizontal distribution check
    card_bgs = [s for s in slide11.shapes if abs((s.top / 914400.0) - 1.668) < 0.1 and abs((s.height / 914400.0) - 2.71) < 0.1]
    assert len(card_bgs) == 4
    left_coords_in = sorted([s.left / 914400.0 for s in card_bgs])
    assert abs(left_coords_in[0] - 0.6675) < 0.05
    assert abs(left_coords_in[1] - 2.8755) < 0.05
    assert abs(left_coords_in[2] - 5.0835) < 0.05
    assert abs(left_coords_in[3] - 7.2915) < 0.05


def test_htl_109_contract_type_variant_wiring(tmp_path: Path):
    """HTL-109: Verify Slide 11 content strictly adapts to Fixed Bid vs Time and Materials commercial model."""
    # 1. Fixed Bid Baseline (e.g. ARC)
    arc_baseline = load_baseline("arc_application_implementation")
    arc_res = export_governance_deck(arc_baseline, tmp_path / "arc_s11_variant")
    arc_prs = pptx.Presentation(str(arc_res.file_path))
    arc_s11_text = " ".join([s.text_frame.text.strip() for s in arc_prs.slides[10].shapes if s.has_text_frame])

    assert "Increases fixed contract price" in arc_s11_text
    assert "fixed contract price" in arc_s11_text.lower() or "fixed" in arc_s11_text.lower()
    assert "No cost impact ($0)" in arc_s11_text

    # 2. Time & Materials Baseline (e.g. PGE)
    pge_baseline = _build_pge_baseline()
    pge_baseline.contract_type = "Time and Materials"
    pge_res = export_governance_deck(pge_baseline, tmp_path / "pge_s11_variant")
    pge_prs = pptx.Presentation(str(pge_res.file_path))
    pge_s11_text = " ".join([s.text_frame.text.strip() for s in pge_prs.slides[10].shapes if s.has_text_frame])

    assert "NTE" in pge_s11_text
    assert "Consumes planned weekly hours" in pge_s11_text or "burn rate" in pge_s11_text


def test_htl_109_slide_sequence_push_down(tmp_path: Path):
    """HTL-109: Verify insertion of Slide 11 pushes current Slide 11 (Project Details) and all subsequent slides down by exactly one."""
    baseline = _build_pge_baseline()
    res = export_governance_deck(baseline, tmp_path / "gov_seq_test")
    prs = pptx.Presentation(str(res.file_path))

    # Slide 9 (idx 8)
    s9_text = " ".join([s.text_frame.text for s in prs.slides[8].shapes if s.has_text_frame])
    assert "Scenarios: requests and blockers" in s9_text

    # Slide 10 (idx 9)
    s10_text = " ".join([s.text_frame.text for s in prs.slides[9].shapes if s.has_text_frame])
    assert "Scenarios: schedule, acceptance and status" in s10_text

    # Slide 11 (idx 10) - NEW SLIDE
    s11_text = " ".join([s.text_frame.text for s in prs.slides[10].shapes if s.has_text_frame])
    assert "Change Decision Matrix" in s11_text

    # Slide 12 (idx 11) - Was Slide 11 (Project Details)
    s12_text = " ".join([s.text_frame.text for s in prs.slides[11].shapes if s.has_text_frame])
    assert "project details" in s12_text.lower()

    # Slide 13 (idx 12) - Was Slide 12 (Team Roster)
    s13_text = " ".join([s.text_frame.text for s in prs.slides[12].shapes if s.has_text_frame])
    assert "The people delivering this project" in s13_text

    # Slide 14 (idx 13) - Was Slide 13 (Why We're Here)
    s14_text = " ".join([s.text_frame.text for s in prs.slides[13].shapes if s.has_text_frame])
    assert "Why are we doing this?" in s14_text or "What problem are we solving?" in s14_text


def test_htl_109_elimination_of_ellipsis_truncation(tmp_path: Path):
    """HTL-109: Verify problem_statement and solution_overview have zero mechanical '...' truncations in both decks."""
    baseline = _build_pge_baseline()

    gov_res = export_governance_deck(baseline, tmp_path / "gov_trunc_test")
    client_res = export_client_deck(baseline, tmp_path / "client_trunc_test")

    gov_prs = pptx.Presentation(str(gov_res.file_path))
    client_prs = pptx.Presentation(str(client_res.file_path))

    # Gov Slide 14 & Client Slide 5 (Why We're Here / Problem Statement)
    gov_s14_texts = [s.text_frame.text.strip() for s in gov_prs.slides[13].shapes if s.has_text_frame]
    client_s5_texts = [s.text_frame.text.strip() for s in client_prs.slides[4].shapes if s.has_text_frame]

    for t in gov_s14_texts:
        assert not t.endswith("..."), f"Governance Slide 14 contains trailing truncation: {t}"
    for t in client_s5_texts:
        assert not t.endswith("..."), f"Client Slide 5 contains trailing truncation: {t}"

    # Gov Slide 15 & Client Slide 6 (Deliverables / Solution Overview)
    gov_s15_texts = [s.text_frame.text.strip() for s in gov_prs.slides[14].shapes if s.has_text_frame]
    client_s6_texts = [s.text_frame.text.strip() for s in client_prs.slides[5].shapes if s.has_text_frame]

    for t in gov_s15_texts:
        assert not t.endswith("..."), f"Governance Slide 15 contains trailing truncation: {t}"
    for t in client_s6_texts:
        assert not t.endswith("..."), f"Client Slide 6 contains trailing truncation: {t}"


from src.llm.client import MockLLMClient


def test_htl_109_llm_condensation_with_mock_client():
    """HTL-109: Verify LLM-based rewriting mechanism for problem statement and solution overview using MockLLMClient."""
    raw_pge_problem = (
        "The legacy OCP application suffers recurring production failures with no clear root cause, "
        "and no internal staff understand its codebase, which keeps all logic in stored procedures. "
        "Its semi-manual data integrations and its failure to flag manually overridden data points "
        "skew averages and cause missing data at required 3-hour compliance intervals."
    )
    raw_pge_solution = (
        "The team inventories the OCP application, infrastructure, and data stores, maps their dependencies, "
        "and assigns each workload a 7 Rs disposition backed by documented rationale. It then builds on these "
        "findings to recommend a target architecture, model multi-year costs and TCO against the current state, "
        "and group workloads into sequenced migration waves with a roadmap. All outputs are delivered as a "
        "single Cloud Migration Assessment Report over three weeks, with weekly status reporting to the client sponsor."
    )

    mock_llm = MockLLMClient()
    mock_llm.set_text_response(
        "problem statement",
        "Legacy OCP application suffers recurring production failures, stored-procedure codebase gaps, and unflagged manual data overrides skewing 3-hour compliance averages.",
    )
    mock_llm.set_text_response(
        "solution overview",
        "Toptal will inventory OCP workloads, map dependencies, and assign 7 Rs dispositions to recommend a target cloud architecture and multi-year TCO model. Delivery culminates in a sequenced migration roadmap within three weeks.",
    )

    condensed_problem = condense_problem_statement(raw_pge_problem, max_chars=180, llm_client=mock_llm)
    assert not condensed_problem.endswith("...")
    assert len(condensed_problem) <= 180
    assert "OCP" in condensed_problem
    assert "production failures" in condensed_problem

    # Verify LLM was invoked with appropriate prompt
    assert len(mock_llm.call_history) >= 1
    assert "problem statement" in mock_llm.call_history[0]["prompt"].lower()

    condensed_solution = condense_solution_overview(raw_pge_solution, max_chars=300, llm_client=mock_llm)
    assert not condensed_solution.endswith("...")
    assert len(condensed_solution) <= 300
    assert "OCP" in condensed_solution
    assert "7 Rs dispositions" in condensed_solution

    # Verify box height fitting for LLM-rewritten outputs
    h_pt = estimate_text_height(condensed_problem, width_in=7.75, size_pt=10.0)
    assert h_pt <= 0.46 * 72.0 + 1e-4

    h_so = estimate_text_height(condensed_solution, width_in=2.84, size_pt=10.0, char_width_factor=0.55)
    assert h_so <= 140.0 + 1e-4


def test_htl_109_deterministic_fallback_when_llm_unavailable():
    """HTL-109: Verify deterministic fallback preserves complete sentences and fits bounding boxes when LLM is unavailable or fails."""
    raw_pge_problem = (
        "The legacy OCP application suffers recurring production failures with no clear root cause, "
        "and no internal staff understand its codebase, which keeps all logic in stored procedures. "
        "Its semi-manual data integrations and its failure to flag manually overridden data points "
        "skew averages and cause missing data at required 3-hour compliance intervals."
    )
    raw_pge_solution = (
        "The team inventories the OCP application, infrastructure, and data stores, maps their dependencies, "
        "and assigns each workload a 7 Rs disposition backed by documented rationale. It then builds on these "
        "findings to recommend a target architecture, model multi-year costs and TCO against the current state, "
        "and group workloads into sequenced migration waves with a roadmap. All outputs are delivered as a "
        "single Cloud Migration Assessment Report over three weeks, with weekly status reporting to the client sponsor."
    )

    class FailingLLMClient:
        def generate_text(self, prompt, system_prompt=None):
            raise TimeoutError("LLM API timed out")

    # 1. Fallback when LLM raises exception
    failing_client = FailingLLMClient()
    fallback_prob = condense_problem_statement(raw_pge_problem, max_chars=180, llm_client=failing_client)
    assert not fallback_prob.endswith("...")
    assert len(fallback_prob) <= 180
    assert "OCP" in fallback_prob
    h_pt = estimate_text_height(fallback_prob, width_in=7.75, size_pt=10.0)
    assert h_pt <= 0.46 * 72.0 + 1e-4

    fallback_sol = condense_solution_overview(raw_pge_solution, max_chars=300, llm_client=failing_client)
    assert not fallback_sol.endswith("...")
    assert len(fallback_sol) <= 300
    assert "OCP" in fallback_sol
    h_so = estimate_text_height(fallback_sol, width_in=2.84, size_pt=10.0, char_width_factor=0.55)
    assert h_so <= 140.0 + 1e-4