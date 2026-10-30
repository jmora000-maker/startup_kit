"""HTL-72: Automated test suite for PS Governance Kickoff Deck (Phase 1).

Verifies:
1. Module scaffolding and exports in src/generators/governance_deck/
2. Template fallback path resolution for PS_Governance Kickoff_TEMPLATE.pptx
3. Slide 1 title substitution ('Governance Kickoff') and fixed subtitle ('Aligning on outcomes, team, and how we'll deliver.')
4. Cross-artifact consistency between PS Governance Kickoff Deck and Client Kickoff Deck across lifted slides (13, 14, 18, 19)
5. 19-slide presentation structure and companion trace manifest generation
"""

from pathlib import Path
import pptx
import pytest

from src.generators.governance_deck import (
    GovernanceDeckModel,
    GovernanceDeckResult,
    GovernanceDeckTraceManifest,
    TraceRef,
    build_governance_deck_model,
    check_governance_deck_traceability,
    export_governance_deck,
    write_governance_deck,
)
from src.generators.governance_deck.writer import (
    resolve_client_deck_template_path,
    resolve_governance_deck_template_path,
)
from src.generators.client_deck import build_client_deck_model, export_client_deck
from tests.deck_bundle import load_baseline
from tests.test_htl_62 import _build_pge_baseline


def test_htl_72_module_scaffolding_and_exports():
    """HTL-72: Verify all expected symbols and classes are exported from src.generators.governance_deck."""
    import src.generators.governance_deck as gd

    assert hasattr(gd, "export_governance_deck")
    assert hasattr(gd, "build_governance_deck_model")
    assert hasattr(gd, "write_governance_deck")
    assert hasattr(gd, "check_governance_deck_traceability")
    assert hasattr(gd, "GovernanceDeckResult")
    assert hasattr(gd, "GovernanceDeckModel")
    assert hasattr(gd, "TraceRef")
    assert hasattr(gd, "GovernanceDeckTraceManifest")


def test_htl_72_template_resolution():
    """HTL-72: Verify template path resolution handles real on-disk filenames and fallback."""
    gov_path = resolve_governance_deck_template_path()
    assert gov_path.exists(), f"Governance deck template not found at {gov_path}"
    assert "PS_Governance" in gov_path.name

    client_path = resolve_client_deck_template_path()
    assert client_path.exists(), f"Client deck template not found at {client_path}"
    assert "Project_Kickoff_Deck_TEMPLATE.pptx" in client_path.name


def test_htl_72_slide1_title_and_subtitle_rendering(tmp_path):
    """HTL-72: Verify Slide 1 renders 'Governance Kickoff' substitution and fixed subtitle."""
    baseline = _build_pge_baseline()
    out_dir = tmp_path / "slide1_test"
    result = export_governance_deck(baseline, out_dir)

    assert result.file_path.exists()
    prs = pptx.Presentation(str(result.file_path))
    slide1 = prs.slides[0]

    s1_text = " ".join([s.text_frame.text for s in slide1.shapes if s.has_text_frame])
    assert "Governance Kickoff" in s1_text
    assert "Portland General Electric Company" in s1_text
    assert "Aligning on outcomes, team, and how we'll deliver." in s1_text
    assert "[Client Name]" not in s1_text
    assert "[Project Name]" not in s1_text
    assert "Onboarding for Project Managers staffed on" not in s1_text


def test_htl_72_cross_artifact_consistency_pge_baseline(tmp_path):
    """HTL-72: Verify exact cross-artifact consistency between Governance Deck and Client Kickoff Deck on PGE baseline."""
    pge_baseline = _build_pge_baseline()

    # Build both deck models
    gov_model = build_governance_deck_model(pge_baseline)
    client_model = build_client_deck_model(pge_baseline)

    # 1. Slide 1 identity
    assert gov_model.slide1.client_name == client_model.slide1.client_name
    assert gov_model.slide1.project_name == client_model.slide1.project_name

    # 2. Slide 13 (Gov) vs Slide 5 (Client) - Why We're Here
    assert gov_model.slide13.why_are_we_doing_this == client_model.slide5.why_are_we_doing_this
    assert gov_model.slide13.what_problem_are_we_solving == client_model.slide5.what_problem_are_we_solving
    assert gov_model.slide13.what_does_success_look_like == client_model.slide5.what_does_success_look_like

    # 3. Slide 14 (Gov) vs Slide 6 (Client) - What We Will Deliver
    assert gov_model.slide14.solution_overview == client_model.slide6.solution_overview
    assert gov_model.slide14.out_of_scope == client_model.slide6.out_of_scope
    assert len(gov_model.slide14.workstreams) == len(client_model.slide6.workstreams)
    for g_ws, c_ws in zip(gov_model.slide14.workstreams, client_model.slide6.workstreams):
        assert g_ws.title == c_ws.title
        assert g_ws.deliverables == c_ws.deliverables

    # 4. Slide 18 (Gov) vs Slide 12 (Client) - Initial Risk Register
    assert len(gov_model.slide18.risks) == len(client_model.slide12.risks)
    for g_r, c_r in zip(gov_model.slide18.risks, client_model.slide12.risks):
        assert g_r.id == c_r.id
        assert g_r.description == c_r.description
        assert g_r.prob_impact == c_r.prob_impact
        assert g_r.mitigation == c_r.mitigation

    # 5. Slide 19 (Gov) vs Slide 15 (Client) - Next Steps
    assert len(gov_model.slide19.next_steps) == len(client_model.slide15.next_steps)
    for g_s, c_s in zip(gov_model.slide19.next_steps, client_model.slide15.next_steps):
        assert g_s.owner == c_s.owner
        assert g_s.action == c_s.action
        assert g_s.due == c_s.due

    # Export both presentations and verify rendered slide content
    gov_res = export_governance_deck(pge_baseline, tmp_path / "gov_out")
    client_res = export_client_deck(pge_baseline, tmp_path / "client_out")

    gov_prs = pptx.Presentation(str(gov_res.file_path))
    client_prs = pptx.Presentation(str(client_res.file_path))

    # Verify Gov Slide 13 matches Client Slide 5 rendered texts
    s13_texts = [p.text for s in gov_prs.slides[12].shapes if s.has_text_frame for p in s.text_frame.paragraphs if p.text.strip()]
    s5_texts = [p.text for s in client_prs.slides[4].shapes if s.has_text_frame for p in s.text_frame.paragraphs if p.text.strip()]
    assert any("Assessment and cloud migration roadmap" in t for t in s13_texts)
    assert any("aging custom system with recurring production failures" in t for t in s13_texts)

    # Verify Gov Slide 18 table matches Client Slide 12 table
    gov_s18_table = [s.table for s in gov_prs.slides[17].shapes if s.has_table][0]
    client_s12_table = [s.table for s in client_prs.slides[11].shapes if s.has_table][0]
    assert len(gov_s18_table.rows) == len(client_s12_table.rows)
    for r_i in range(len(gov_s18_table.rows)):
        gov_row_txt = [c.text_frame.text.strip() for c in gov_s18_table.rows[r_i].cells]
        client_row_txt = [c.text_frame.text.strip() for c in client_s12_table.rows[r_i].cells]
        assert gov_row_txt == client_row_txt


def test_htl_72_cross_artifact_consistency_arc_baseline(tmp_path):
    """HTL-72: Verify exact cross-artifact consistency on ARC baseline."""
    arc_baseline = load_baseline()

    gov_model = build_governance_deck_model(arc_baseline)
    client_model = build_client_deck_model(arc_baseline)

    assert gov_model.slide1.client_name == "Syngenta"
    assert gov_model.slide1.project_name == "ARC Genomics Platform"
    assert len(gov_model.slide14.workstreams) == len(client_model.slide6.workstreams)
    assert len(gov_model.slide18.risks) == len(client_model.slide12.risks)
    assert len(gov_model.slide19.next_steps) == len(client_model.slide15.next_steps)

    gov_res = export_governance_deck(arc_baseline, tmp_path / "gov_arc")
    assert gov_res.slides_count == 19
    assert gov_res.trace_entries_count >= 10

    errs = check_governance_deck_traceability(gov_model, gov_res.file_path)
    assert errs == []


def test_htl_72_placeholder_eradication(tmp_path):
    """HTL-72: Verify no unreplaced placeholders remain in generated Governance Deck populated slides."""
    baseline = _build_pge_baseline()
    res = export_governance_deck(baseline, tmp_path / "placeholder_check")

    prs = pptx.Presentation(str(res.file_path))
    for idx, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            if shape.has_text_frame:
                txt = shape.text_frame.text
                if idx in (0, 12, 13, 17, 18):  # Populated slides (1, 13, 14, 18, 19)
                    assert "[Client Name]" not in txt
                    assert "[Project Name]" not in txt
                    assert "[Pre-filled:" not in txt
                    assert "[high level summary" not in txt
                    assert "[Workstream or Feature" not in txt


def test_htl_72_slide12_template_placeholders_intact(tmp_path):
    """HTL-72: Verify Slide 12 is a direct unmodified lift of Project Kickoff Deck page 3 placeholders (left for human editing)."""
    baseline = _build_pge_baseline()
    baseline.charter.delivery_manager = "Yulia Ainley"
    baseline.charter.talent_pm = "Jane Doe"
    baseline.charter.pmo_lead = "Alex PMO"

    res = export_governance_deck(baseline, tmp_path / "roster_check")
    prs = pptx.Presentation(str(res.file_path))

    slide12 = prs.slides[11]  # 0-indexed slide 12
    s12_texts = [s.text_frame.text.strip() for s in slide12.shapes if s.has_text_frame and s.text_frame.text.strip()]

    # Must contain exact Project Kickoff Deck page 3 template placeholders
    assert "YOUR TEAM" in s12_texts
    assert "The people delivering your project" in s12_texts
    assert "Name" in s12_texts
    assert "Role" in s12_texts
    assert "Location" in s12_texts

    # Must NOT populate real baseline leadership names or roles
    assert "Yulia Ainley" not in s12_texts
    assert "Jane Doe" not in s12_texts
    assert "Alex PMO" not in s12_texts
    assert "[UNASSIGNED - TO BE CONFIRMED]" not in s12_texts


def test_htl_72_slide1_long_title_overflow_regression(tmp_path):
    """HTL-72: Regression test for Slide 1 overflow bug with realistically long client and project names (PGE)."""
    baseline = _build_pge_baseline()
    client_name = "Portland General Electric Company"
    project_name = "Cloud Migration Assessment – Operational Compliance Program (OCP)"
    baseline.charter.client_name = client_name
    baseline.governance_context.client_name = client_name
    baseline.project_name = project_name

    composite_title = f"{client_name}\n{project_name} Governance Kickoff"
    from src.generators.client_deck.fit import estimate_text_height, select_fitting_font_size

    candidate_sizes = [24.0, 22.0, 20.0, 18.0, 16.0, 14.0, 13.0, 12.0, 11.0, 10.0, 9.5, 9.0]
    sz, _ = select_fitting_font_size(
        composite_title,
        width_in=3.30,
        max_height_in=0.70,
        candidate_sizes=candidate_sizes,
        is_bold=True,
    )
    est_height_pt = estimate_text_height(composite_title, width_in=3.30, size_pt=sz, is_bold=True)
    est_height_in = est_height_pt / 72.0

    # Ensure font size scales down appropriately and total text height leaves clean buffer (>= 0.70 in) above divider line (4.423 in)
    assert sz <= 10.0
    assert est_height_in <= 0.70
    title_bottom_in = 2.966 + est_height_in
    assert title_bottom_in < 3.75  # Over 0.65 in margin above divider line at 4.423 in

    # Verify rendered output PPTX
    res = export_governance_deck(baseline, tmp_path / "pge_long_title")
    prs = pptx.Presentation(str(res.file_path))
    s1 = prs.slides[0]

    title_shape = [s for s in s1.shapes if s.has_text_frame and "Governance Kickoff" in s.text_frame.text][0]
    assert title_shape.top / 914400 < 3.0  # Top position unchanged at ~2.97 in
    runs = [r for p in title_shape.text_frame.paragraphs for r in p.runs]
    assert len(runs) > 0
    assert runs[0].font.size.pt <= 10.0
    assert "Portland General Electric Company" in title_shape.text_frame.text
    assert "Governance Kickoff" in title_shape.text_frame.text


def test_htl_72_tier1_customer_outcome_framing(tmp_path):
    """HTL-72: Verify Slides 13 and 14 render Tier 1 customer-outcome framing when synthesis fields are present."""
    baseline = _build_pge_baseline()
    tier1_solution = (
        "The engagement delivers a comprehensive assessment and cloud migration roadmap for "
        "PGE's Operational Compliance Program (OCP) systems. Workstreams inventory in-scope "
        "workloads and map dependencies to establish target architectures and a multi-year TCO model. "
        "Delivery culminates in a 7 Rs disposition register and sequenced migration wave plan aligned "
        "with compliance standards."
    )
    tier1_success = (
        "The client receives a clear, evidence-backed view of their OCP infrastructure and modern "
        "cloud architecture options. They can confidently decide workload disposition and wave sequencing, "
        "supported by an actionable multi-year TCO model and validated migration roadmap."
    )
    baseline.charter.solution_overview = tier1_solution
    baseline.charter.success_criteria_summary = tier1_success

    res = export_governance_deck(baseline, tmp_path / "tier1_out")
    prs = pptx.Presentation(str(res.file_path))

    # Slide 13 (Why We're Here)
    s13_texts = [s.text_frame.text.strip() for s in prs.slides[12].shapes if s.has_text_frame]
    assert any("The client receives a clear, evidence-backed view" in t for t in s13_texts)

    # Slide 14 (What We Deliver)
    s14_texts = [s.text_frame.text.strip() for s in prs.slides[13].shapes if s.has_text_frame]
    assert any("The engagement delivers a comprehensive assessment" in t for t in s14_texts)
