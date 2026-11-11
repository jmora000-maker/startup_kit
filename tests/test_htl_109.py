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


def test_htl_109_slide11_unified_text_frame_and_pill_anchoring(tmp_path: Path):
    """HTL-109: Verify Slide 11 cards use a single unified text frame for Sections 1 & 2 and anchor Section 3 pill to bottom."""
    baseline = _build_pge_baseline()
    res = export_governance_deck(baseline, tmp_path / "gov_s11_unified")
    prs = pptx.Presentation(str(res.file_path))
    slide11 = prs.slides[10]

    # Find the 4 main card textboxes and 4 pill textboxes
    # Card X positions: ~0.67in, ~2.88in, ~5.08in, ~7.29in
    left_positions = [610350, 2629344, 4648338, 6667332]

    for c_left in left_positions:
        sec1_left = c_left + 109728
        card_tbs = [s for s in slide11.shapes if s.has_text_frame and abs(s.left - sec1_left) < 5000]
        # Should have exactly 2 textboxes per card: 1 unified body textbox (Sec 1+2), 1 pill textbox (Sec 3)
        assert len(card_tbs) == 2, f"Expected 2 textboxes at left={sec1_left}, got {len(card_tbs)}"

        # Find body textbox (higher up, top ~1.78in) and pill textbox (lower, top ~3.67in)
        body_tb = min(card_tbs, key=lambda s: s.top)
        pill_tb = max(card_tbs, key=lambda s: s.top)

        # 1. Verify unified body textbox has 4 distinct paragraphs
        tf_body = body_tb.text_frame
        assert len(tf_body.paragraphs) == 4, f"Expected 4 paragraphs in body textbox, got {len(tf_body.paragraphs)}"

        # Para 0: Title (11pt bold)
        p0 = tf_body.paragraphs[0]
        assert len(p0.runs) >= 1
        assert p0.runs[0].font.size == pptx.util.Pt(11.0)
        assert p0.runs[0].font.bold is True

        # Para 1: Characteristics (8.5pt regular)
        p1 = tf_body.paragraphs[1]
        assert len(p1.runs) >= 1
        assert p1.runs[0].font.size == pptx.util.Pt(8.5)
        assert p1.runs[0].font.bold is False

        # Para 2: "WHAT IT MEANS" label (8.5pt bold)
        p2 = tf_body.paragraphs[2]
        assert len(p2.runs) >= 1
        assert p2.runs[0].text == "WHAT IT MEANS"
        assert p2.runs[0].font.size == pptx.util.Pt(8.5)
        assert p2.runs[0].font.bold is True

        # Para 3: Impact (8.5pt regular)
        p3 = tf_body.paragraphs[3]
        assert len(p3.runs) >= 1
        assert p3.runs[0].font.size == pptx.util.Pt(8.5)
        assert p3.runs[0].font.bold is False

        # 2. Verify pill textbox is anchored to bottom
        pill_top_in = pill_tb.top / 914400.0
        assert 3.60 <= pill_top_in <= 3.75, f"Pill top outside expected range: {pill_top_in}in"
        assert "Authority:" in pill_tb.text_frame.text


def test_htl_109_table4_character_budget_compliance():
    """HTL-109: Verify all Table 4 classification guide rows strictly obey 110/70/75 character budgets."""
    from src.generators.scope_baseline.templates import build_table4_classification_guide_rows

    for variant in ["Fixed Bid", "Time and Materials"]:
        rows = build_table4_classification_guide_rows(None, variant)
        assert len(rows) == 4
        for r in rows:
            assert len(r.operational_characteristics) <= 110, (
                f"[{variant}] {r.classification} operational_characteristics exceeds 110 chars: "
                f"len={len(r.operational_characteristics)} ({r.operational_characteristics})"
            )
            assert len(r.budget_milestone_impact) <= 70, (
                f"[{variant}] {r.classification} budget_milestone_impact exceeds 70 chars: "
                f"len={len(r.budget_milestone_impact)} ({r.budget_milestone_impact})"
            )
            assert len(r.approval_pathway) <= 75, (
                f"[{variant}] {r.classification} approval_pathway exceeds 75 chars: "
                f"len={len(r.approval_pathway)} ({r.approval_pathway})"
            )


def test_htl_109_geometric_margin_and_worst_case():
    """HTL-109: Rigorous geometric calculation verifying positive margin and zero overlap for all cards and worst-case text."""
    from src.generators.scope_baseline.templates import build_table4_classification_guide_rows
    from src.generators.client_deck.fit import wrap_lines

    usable_sec12_pt = (3.6665 - 1.7795 - 0.057) * 72.0  # 131.76 pt
    usable_pill_pt = 0.5627 * 72.0  # 40.51 pt

    for variant in ["Fixed Bid", "Time and Materials"]:
        rows = build_table4_classification_guide_rows(None, variant)
        for r in rows:
            title_lines = wrap_lines(r.classification, 1.8, 11.0, 0.60)
            title_pt = (title_lines * 11.0 * 1.15) + 2.0

            char_lines = wrap_lines(r.operational_characteristics, 1.8, 8.5, 0.50)
            char_pt = (char_lines * 8.5 * 1.15) + 6.0

            lbl_lines = wrap_lines("WHAT IT MEANS", 1.8, 8.5, 0.60)
            lbl_pt = (lbl_lines * 8.5 * 1.15) + 2.0

            imp_lines = wrap_lines(r.budget_milestone_impact, 1.8, 8.5, 0.50)
            imp_pt = (imp_lines * 8.5 * 1.15)

            total_sec12_pt = title_pt + char_pt + lbl_pt + imp_pt
            sec12_margin_pt = usable_sec12_pt - total_sec12_pt

            path_text = "Authority: " + r.approval_pathway
            path_lines = wrap_lines(path_text, 1.8, 8.5, 0.50)
            path_pt = path_lines * 8.5 * 1.15
            pill_margin_pt = usable_pill_pt - path_pt

            assert sec12_margin_pt >= 20.0, f"Insufficient margin on [{variant}] {r.classification}: {sec12_margin_pt}pt"
            assert pill_margin_pt >= 5.0, f"Insufficient pill margin on [{variant}] {r.classification}: {pill_margin_pt}pt"

    # Worst case (110 chars char / 70 chars imp / 75 chars path with wide letters)
    wc_title_pt = (2 * 11.0 * 1.15) + 2.0
    wc_char_lines = wrap_lines("W" * 110, 1.8, 8.5, 0.60)
    wc_char_pt = (wc_char_lines * 8.5 * 1.15) + 6.0
    wc_lbl_pt = (1 * 8.5 * 1.15) + 2.0
    wc_imp_lines = wrap_lines("W" * 70, 1.8, 8.5, 0.60)
    wc_imp_pt = (wc_imp_lines * 8.5 * 1.15)
    wc_total_sec12_pt = wc_title_pt + wc_char_pt + wc_lbl_pt + wc_imp_pt
    assert usable_sec12_pt > wc_total_sec12_pt

    wc_path_lines = wrap_lines("Authority: " + ("W" * 75), 1.8, 8.5, 0.60)
    wc_path_pt = wc_path_lines * 8.5 * 1.15
    assert usable_pill_pt > wc_path_pt


def test_htl_109_no_orphaned_slide_or_notes_parts(tmp_path: Path):
    """HTL-109: Permanent regression test verifying zero orphaned slide, notes, or media parts in generated .pptx packages."""
    import zipfile
    import xml.etree.ElementTree as ET

    baselines = [
        ("fixed_bid", load_baseline("arc_application_implementation")),
        ("time_and_materials", _build_pge_baseline()),
    ]

    for label, baseline in baselines:
        res = export_governance_deck(baseline, tmp_path / f"gov_orphan_check_{label}")
        pptx_path = res.file_path
        prs = pptx.Presentation(str(pptx_path))

        with zipfile.ZipFile(pptx_path, "r") as z:
            names = set(z.namelist())
            pres_xml = z.read("ppt/presentation.xml")
            pres_rels_xml = z.read("ppt/_rels/presentation.xml.rels")

            tree = ET.fromstring(pres_xml)
            rels_tree = ET.fromstring(pres_rels_xml)

            ns = {
                "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
                "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
            }

            r_map = {
                rel.attrib["Id"]: rel.attrib["Target"]
                for rel in rels_tree.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
            }

            active_slide_targets = []
            for sldId in tree.findall(".//p:sldId", ns):
                rId = sldId.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
                active_slide_targets.append(r_map[rId])

            zip_slide_files = [n for n in names if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
            zip_notes_files = [n for n in names if n.startswith("ppt/notesSlides/notesSlide") and n.endswith(".xml")]

            # 1. Exact 1:1 count match: active presentation slide IDs == slide XML files in zip == presentation.slides count
            assert len(zip_slide_files) == len(active_slide_targets) == len(prs.slides), (
                f"[{label}] Slide count mismatch: zip_slides={len(zip_slide_files)}, "
                f"active_targets={len(active_slide_targets)}, prs_slides={len(prs.slides)}"
            )

            # 2. Zero orphaned slide parts in zip
            orphaned_slides = [
                s for s in zip_slide_files
                if s.replace("ppt/", "") not in active_slide_targets and s not in active_slide_targets
            ]
            assert len(orphaned_slides) == 0, f"[{label}] Found orphaned slide files in zip: {orphaned_slides}"

            # 3. Zero orphaned notes slide parts (every notesSlide in zip must be referenced by an active slide)
            active_notes_targets = set()
            for target in active_slide_targets:
                slide_file = "ppt/" + target if not target.startswith("ppt/") else target
                slide_rel_file = slide_file.replace("slides/", "slides/_rels/") + ".rels"
                if slide_rel_file in names:
                    s_rel_tree = ET.fromstring(z.read(slide_rel_file))
                    for rel in s_rel_tree.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"):
                        if "notesSlide" in rel.attrib.get("Type", ""):
                            active_notes_targets.add(rel.attrib["Target"].replace("../notesSlides/", ""))

            orphaned_notes = [
                n for n in zip_notes_files
                if n.replace("ppt/notesSlides/", "") not in active_notes_targets
            ]
            assert len(orphaned_notes) == 0, f"[{label}] Found orphaned notes files in zip: {orphaned_notes}"

            # 4. Zero orphaned slide relationships in presentation.xml.rels
            slide_rels_in_pres = [
                rel.attrib["Id"] for rel in rels_tree.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
                if "slide" in rel.attrib.get("Type", "") and "slideMaster" not in rel.attrib.get("Type", "") and "slideLayout" not in rel.attrib.get("Type", "")
            ]
            active_sld_rids = [
                sldId.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
                for sldId in tree.findall(".//p:sldId", ns)
            ]
            orphaned_rels = set(slide_rels_in_pres) - set(active_sld_rids)
            assert len(orphaned_rels) == 0, f"[{label}] Found orphaned slide relationships in presentation.xml.rels: {orphaned_rels}"

            # 5. Full package reachability graph check: every entry in the .pptx zip is reachable from root rels
            visited = {"[Content_Types].xml", "_rels/.rels"}
            queue = ["_rels/.rels"]
            while queue:
                rel_path = queue.pop(0)
                if rel_path not in names:
                    continue
                base_dir = str(Path(rel_path).parent).replace("\\", "/")
                if base_dir == "_rels":
                    base_target_dir = ""
                elif base_dir.endswith("/_rels"):
                    base_target_dir = base_dir[:-6]
                else:
                    base_target_dir = base_dir

                tree_rel = ET.fromstring(z.read(rel_path))
                for rel in tree_rel.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"):
                    target = rel.attrib["Target"]
                    if target.startswith("/"):
                        resolved = target[1:]
                    elif target.startswith("../"):
                        parts = (base_target_dir + "/" + target).split("/")
                        norm_parts = []
                        for p in parts:
                            if p == "..":
                                if norm_parts:
                                    norm_parts.pop()
                            elif p and p != ".":
                                norm_parts.append(p)
                        resolved = "/".join(norm_parts)
                    else:
                        resolved = f"{base_target_dir}/{target}" if base_target_dir else target

                    if resolved in names and resolved not in visited:
                        visited.add(resolved)
                        r_p = Path(resolved)
                        r_rel_path = str(r_p.parent / "_rels" / (r_p.name + ".rels")).replace("\\", "/")
                        if r_rel_path in names and r_rel_path not in visited:
                            visited.add(r_rel_path)
                            queue.append(r_rel_path)

            unreachable = names - visited
            assert len(unreachable) == 0, f"[{label}] Unreachable package entries in zip: {unreachable}"