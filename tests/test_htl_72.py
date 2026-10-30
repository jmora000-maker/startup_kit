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


def test_htl_72_slide12_template_placeholders_and_images_intact(tmp_path):
    """HTL-72: Verify Slide 12 is a direct unmodified lift of Project Kickoff Deck page 3 placeholders and icon images (left for human editing)."""
    baseline = _build_pge_baseline()
    baseline.charter.delivery_manager = "Yulia Ainley"
    baseline.charter.talent_pm = "Jane Doe"
    baseline.charter.pmo_lead = "Alex PMO"

    res = export_governance_deck(baseline, tmp_path / "roster_check")
    prs = pptx.Presentation(str(res.file_path))

    slide12 = prs.slides[11]  # 0-indexed slide 12
    s12_texts = [s.text_frame.text.strip() for s in slide12.shapes if s.has_text_frame and s.text_frame.text.strip()]

    # 1. Must contain exact Project Kickoff Deck page 3 template placeholders
    assert "YOUR TEAM" in s12_texts
    assert "The people delivering your project" in s12_texts
    assert "Name" in s12_texts
    assert "Role" in s12_texts
    assert "Location" in s12_texts

    # 2. Must NOT populate real baseline leadership names or roles
    assert "Yulia Ainley" not in s12_texts
    assert "Jane Doe" not in s12_texts
    assert "Alex PMO" not in s12_texts
    assert "[UNASSIGNED - TO BE CONFIRMED]" not in s12_texts

    # 3. Image relationships must point to generic GIF/PNG placeholder icons, NOT real JPEG photographs
    image_targets = [rel.target_ref for rel in slide12.part.rels.values() if "image" in rel.reltype]
    assert len(image_targets) >= 3
    for target in image_targets:
        assert not target.lower().endswith(".jpg"), f"Slide 12 must not contain real JPEG photos: {target}"
        assert not target.lower().endswith(".jpeg"), f"Slide 12 must not contain real JPEG photos: {target}"
        assert target.lower().endswith(".png") or target.lower().endswith(".gif")


def test_htl_72_slide1_title_rendering_and_clearance_regression(tmp_path):
    """HTL-72: Verify Slide 1 font-fitting scales dynamically to prevent overflow and guarantees positive clearance above divider line."""
    baseline = _build_pge_baseline()
    client_name = "Portland General Electric Company"
    project_name = "Cloud Migration Assessment – Operational Compliance Program (OCP)"
    baseline.charter.client_name = client_name
    baseline.governance_context.client_name = client_name
    baseline.project_name = project_name

    res = export_governance_deck(baseline, tmp_path / "pge_title_clearance")
    prs = pptx.Presentation(str(res.file_path))
    s1 = prs.slides[0]

    title_shape = [s for s in s1.shapes if s.has_text_frame and "Governance Kickoff" in s.text_frame.text][0]
    runs = [r for p in title_shape.text_frame.paragraphs for r in p.runs]
    assert len(runs) > 0

    # 1. Chosen font size must scale down to <= 12.0 pt for long PGE title
    chosen_sz = runs[0].font.size.pt
    assert chosen_sz <= 12.0, f"Chosen font size {chosen_sz} pt must be <= 12.0 pt to prevent title overflow"

    # 2. Text height measurement and clearance verification
    composite_title = f"{client_name}\n{project_name} Governance Kickoff"
    from src.generators.client_deck.fit import estimate_text_height, wrap_lines
    est_height_pt = estimate_text_height(composite_title, width_in=3.30, size_pt=chosen_sz, is_bold=True)
    est_height_in = est_height_pt / 72.0
    title_top_in = title_shape.top / 914400.0  # ~2.966 in
    title_bottom_in = title_top_in + est_height_in

    divider_line_top_in = 4.423  # Layout divider line at 4.423 in (4,044,275 EMUs)
    subtitle_top_in = 4.542      # Subtitle at 4.542 in (4,153,150 EMUs)

    clearance_above_divider = divider_line_top_in - title_bottom_in
    assert clearance_above_divider >= 0.35, f"Clearance above divider line must be >= 0.35 in, got {clearance_above_divider:.3f} in"
    assert title_bottom_in < subtitle_top_in - 0.40, f"Title bottom ({title_bottom_in:.3f} in) must not overlap subtitle ({subtitle_top_in:.3f} in)"

    # 3. Content verification
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


def test_htl_72_slide15_deliverable_acceptance_criteria_pge(tmp_path):
    """HTL-72: Verify Slide 15 renders Deliverable Acceptance Criteria table with 12 countable bullets and gate mapping (HTL-62/64/72)."""
    import json
    baseline = _build_pge_baseline()
    res = export_governance_deck(baseline, tmp_path / "slide15_test")

    prs = pptx.Presentation(str(res.file_path))
    slide15 = prs.slides[14]  # 0-indexed slide 15

    # 1. Header & Textbox validations
    textboxes = [s.text_frame.text.strip() for s in slide15.shapes if s.has_text_frame and not s.has_table]
    assert "PROJECT SUCCESS AGREEMENT" in textboxes
    assert "Deliverable acceptance criteria" in textboxes
    assert any("Contractual criteria and verification requirements mapped to milestone gates." in t for t in textboxes)

    # 2. Table structure validation
    table_shapes = [s for s in slide15.shapes if s.has_table]
    assert len(table_shapes) == 1
    table_shape = table_shapes[0]
    table = table_shape.table
    assert len(table.rows) == 7  # 1 header + 6 deliverables
    assert len(table.columns) == 3

    # Geometry & clearance validation: table must not clip bottom of slide (5.625 in)
    tbl_top_in = table_shape.top / 914400.0
    tbl_height_in = table_shape.height / 914400.0
    tbl_bottom_in = tbl_top_in + tbl_height_in
    assert tbl_top_in <= 1.60
    assert tbl_bottom_in <= 4.50  # Over 1.10 in clearance above slide bottom at 5.625 in

    # 3. Header row
    h0 = table.rows[0].cells[0].text.strip()
    h1 = table.rows[0].cells[1].text.strip()
    h2 = table.rows[0].cells[2].text.strip()
    assert h0 == "Deliverable"
    assert h1 == "Acceptance Criteria"
    assert h2 == "Milestone Gate"

    # 4. Data rows and countable bullet verification (HTL-64 principle: count them, don't just check text)
    expected_ids = ["DEL-01", "DEL-02", "DEL-03", "DEL-04", "DEL-05", "DEL-06"]
    total_criteria_bullets = 0

    for idx, expected_id in enumerate(expected_ids, start=1):
        row = table.rows[idx]
        col0_text = row.cells[0].text.strip()
        col1_text = row.cells[1].text.strip()
        col2_text = row.cells[2].text.strip()

        assert expected_id in col0_text
        assert col2_text == "M1"  # Gated to M1 for PGE

        # Count individual criteria paragraphs in column 1
        crit_paras = [p.text.strip() for p in row.cells[1].text_frame.paragraphs if p.text.strip()]
        assert len(crit_paras) == 2  # Exactly 2 criteria per PGE deliverable
        total_criteria_bullets += len(crit_paras)

        for p_text in crit_paras:
            assert p_text.startswith("• ")

    assert total_criteria_bullets == 12  # All 12 PGE criteria rendered

    # 5. Trace Manifest verification
    manifest_path = res.file_path.with_name(f"{res.file_path.stem}.trace.json")
    assert manifest_path.exists()
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    s15_entries = [e for e in manifest_data["entries"] if e["slide"] == 15]
    assert len(s15_entries) == 6  # 6 deliverable entries

    for entry in s15_entries:
        assert entry["shape"] == "Table: Deliverable Acceptance Criteria"
        trace_fields = [t["field"] for t in entry["traces"]]
        assert "ID" in trace_fields
        assert "Acceptance Criteria" in trace_fields
        assert "Milestone ID" in trace_fields


def test_htl_72_slide15_custom_deliverables_and_placeholders(tmp_path):
    """HTL-72: Verify Slide 15 handles single criterion, empty criteria, and unconfirmed gates."""
    from src.core.models import Deliverable
    baseline = _build_pge_baseline()
    baseline.deliverables = [
        Deliverable(
            id="DEL-01",
            name="Single Criterion Item",
            acceptance_criteria=["Single explicit criterion without bullet prefix."],
        ),
        Deliverable(
            id="DEL-02",
            name="Unassigned Item",
            acceptance_criteria=[],
        ),
    ]

    res = export_governance_deck(baseline, tmp_path / "custom_deliv_test")
    prs = pptx.Presentation(str(res.file_path))
    slide15 = prs.slides[14]

    table_shapes = [s for s in slide15.shapes if s.has_table]
    assert len(table_shapes) == 1
    table = table_shapes[0].table
    assert len(table.rows) == 3  # 1 header + 2 deliverables

    # Row 1: Single criterion rendered without "• " bullet
    r1_col1_paras = [p.text.strip() for p in table.rows[1].cells[1].text_frame.paragraphs if p.text.strip()]
    assert len(r1_col1_paras) == 1
    assert not r1_col1_paras[0].startswith("• ")
    assert "Single explicit criterion" in r1_col1_paras[0]

    # Row 2: Empty criteria rendered as [CONFIRMATION REQUIRED]
    r2_col1_paras = [p.text.strip() for p in table.rows[2].cells[1].text_frame.paragraphs if p.text.strip()]
    assert len(r2_col1_paras) == 1
    assert r2_col1_paras[0] == "[CONFIRMATION REQUIRED]"
