"""HTL-116: Comprehensive test suite for Programmatic UAT defects and Client Deck Sprint Cadence.

Verifies:
1. Filename Bug: Scope Baseline document export filename produces `..._Scope_Baseline_Programmatic.docx`.
2. Table 1 Residual Label: Table 1 Row 6 Governance Tier parenthetical is model-neutral (`Governance Tier: {tier}.`) across all models.
3. Slide 5 Residual Text: Fallback placeholders use 'Engagement Overview' for Programmatic contracts.
4. Slides 8-9 Approach & Cadence: Client Kickoff Deck renders Sprint Cadence lifecycle on Slide 8 and Agile Operating Rhythm on Slide 9 for Programmatic models.
5. Slide 6 Focus Rows & Completion Filter: Workstreams reflect backlog themes without milestone completion phrases across all models.
"""

from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
import pptx
import pytest

from src.core.models import (
    StartupKitBaseline,
    ProjectStartupCharter,
    SOWInterpretationSummary,
    Deliverable,
    Milestone,
    DependencyAssumptionItem,
    CommercialGuardrail,
    Stakeholder,
)
from src.generators.scope_baseline import export_scope_baseline
from src.generators.scope_baseline.templates import build_table1_summary_rows
from src.generators.client_deck.builder import build_slide5_model, build_slide6_model, build_client_deck_model
from src.generators.client_deck import export_client_deck
from tests.deck_bundle import load_baseline
from tests.test_htl_62 import _build_pge_baseline


def _create_programmatic_mock_baseline() -> StartupKitBaseline:
    milestones = [
        Milestone(id="M-01", name="Sprint 1", target_date="2026-11-01", phase="Sprint 1", deliverable_id="DEL-01", description="Sprint deliverables accepted following demonstration."),
        Milestone(id="M-02", name="Final Sprint", target_date="2026-12-01", phase="Sprint N", deliverable_id="DEL-02", description="Final sprint concludes and the engagement's service period ends."),
    ]
    charter = ProjectStartupCharter(
        project_name="Carrier Smart Home",
        client_name="Carrier",
        contract_type="Programmatic",
        governance_tier="Partnered",
        delivery_model="Toptal Talent Team (Agile Sprints)",
        project_purpose="Deliver smart home cloud connectivity through agile sprint backlogs.",
        problem_statement="",  # Triggers fallback
        high_level_scope=["IoT Cloud Platform", "Mobile SDK", "Quality Engineering"],
        exclusions=["Hardware Firmware Manufacturing"],
        key_deliverables_summary=["DEL-01: Feature development", "DEL-02: Security and reliability", "DEL-03: Quality engineering"],
        milestones=milestones,
    )
    sow_int = SOWInterpretationSummary(
        contracted_deliverables=["Feature development", "Security and reliability", "Quality engineering"],
        out_of_scope_items=["Hardware Firmware"],
        platform_environment_commitments=["AWS IoT Core"],
        dependencies=["Client API Specifications (2 sprints ready backlog)"],
    )
    delivs = [
        Deliverable(id="DEL-01", name="Feature development", description="Core cloud device pairing and telemetry pipeline"),
        Deliverable(id="DEL-02", name="Security and reliability", description="End-to-end device encryption and cert rotation"),
        Deliverable(id="DEL-03", name="Quality engineering", description="Automated regression suite and load testing"),
    ]
    deps = [DependencyAssumptionItem(id="DEP-01", type="Dependency", description="Client API Specifications", impact_if_unmet="Idle team capacity risk")]
    guardrails = CommercialGuardrail(
        contract_type_implication="Programmatic flat weekly fee with team capacity ceiling.",
        approved_work_rule="Work defined fresh per sprint backlog in accordance with agreed roadmap.",
        non_approved_work_rule="Out-of-roadmap capabilities require SOW Amendment or added team capacity.",
    )
    stakeholders = [
        Stakeholder(name="Jane Doe", role="Client Product Owner", organization="Client"),
        Stakeholder(name="John Smith", role="Product Manager", organization="Toptal"),
    ]

    return StartupKitBaseline(
        project_name="Carrier Smart Home",
        contract_type="Programmatic",
        governance_tier="Partnered",
        charter=charter,
        sow_interpretation=sow_int,
        deliverables=delivs,
        milestones=milestones,
        dependencies_assumptions=deps,
        commercial_guardrails=guardrails,
        stakeholders=stakeholders,
    )


def test_htl_116_item1_scope_baseline_filename_slug(tmp_path: Path):
    """Item 1: Verify Scope Baseline document export filename produces correct variant slug across all 3 models."""
    # 1. Programmatic
    b_prog = _create_programmatic_mock_baseline()
    res_prog = export_scope_baseline(b_prog, tmp_path / "prog")
    assert res_prog.file_path.name == "Carrier_Smart_Home_Scope_Baseline_Programmatic.docx"

    # 2. Fixed Bid
    b_fixed = load_baseline("arc_application_implementation")
    res_fixed = export_scope_baseline(b_fixed, tmp_path / "fixed")
    assert "Fixed_Bid" in res_fixed.file_path.name
    assert "Time_and_Materials" not in res_fixed.file_path.name

    # 3. Time & Materials
    b_tm = _build_pge_baseline()
    b_tm.contract_type = "Time and Materials"
    res_tm = export_scope_baseline(b_tm, tmp_path / "tm")
    assert "Time_and_Materials" in res_tm.file_path.name
    assert "Programmatic" not in res_tm.file_path.name


def test_htl_116_item2_table1_model_neutral_governance_tier():
    """Item 2: Verify Table 1 Row 6 Governance Tier parenthetical is model-neutral across all models."""
    for variant in ["Fixed Bid", "Time and Materials", "Programmatic"]:
        b = _create_programmatic_mock_baseline()
        b.contract_type = variant
        rows = build_table1_summary_rows(b, variant)
        r6 = next(r for r in rows if r.dimension == "Commercial Controls & Governance")
        
        # Must contain "Governance Tier: Partnered." without commercial model names in parenthetical
        assert "Governance Tier: Partnered." in r6.authorized_work
        assert "(Fixed Bid)" not in r6.authorized_work
        assert "(Time & Materials)" not in r6.authorized_work
        assert "(Programmatic)" not in r6.authorized_work


def test_htl_116_item3_client_deck_slide5_engagement_overview_fallbacks(tmp_path: Path):
    """Item 3: Verify Slide 5 fallback placeholders use 'Engagement Overview' for Programmatic and 'Project Success Agreement' for Fixed Bid/T&M."""
    # 1. Programmatic
    b_prog = _create_programmatic_mock_baseline()
    s5_prog = build_slide5_model(b_prog)
    assert "Engagement Overview" in s5_prog.what_problem_are_we_solving
    assert "Project Success Agreement" not in s5_prog.what_problem_are_we_solving

    res_prog = export_client_deck(b_prog, tmp_path / "c_deck_prog")
    prs_prog = pptx.Presentation(str(res_prog.file_path))
    s5_p_text = " ".join(s.text_frame.text for s in prs_prog.slides[4].shapes if s.has_text_frame)
    assert "ENGAGEMENT OVERVIEW" in s5_p_text
    assert "Project Success Agreement" not in s5_p_text

    # 2. Fixed Bid
    b_fixed = load_baseline("arc_application_implementation")
    b_fixed.charter.problem_statement = ""
    s5_fixed = build_slide5_model(b_fixed)
    assert "Project Success Agreement" in s5_fixed.what_problem_are_we_solving


def test_htl_116_item4_client_deck_slides8_9_approach_and_cadence(tmp_path: Path):
    """Item 4: Verify Client Kickoff Deck renders Sprint Cadence on Slide 8 and Agile Operating Rhythm on Slide 9 for Programmatic models."""
    b_prog = _create_programmatic_mock_baseline()
    res = export_client_deck(b_prog, tmp_path / "c_deck_s89")
    prs = pptx.Presentation(str(res.file_path))

    # Slide 8: Strategic Approach / Sprint Cadence
    # With 1 Slide 6 page: Slide 8 index is 4 + 1 + 2 = 7
    s8 = prs.slides[7]
    s8_texts = [s.text_frame.text for s in s8.shapes if s.has_text_frame]
    s8_full = " ".join(s8_texts)

    assert "Mobilize, deliver in two-week sprints, then close" in s8_full
    assert "ENGAGEMENT OVERVIEW" in s8_full
    assert "Mobilize" in s8_full
    assert "Sprint 0" in s8_full
    assert "Sprints 1 to [N]" in s8_full or "Sprints 1 to N" in s8_full or "Sprints 1 to" in s8_full
    assert "Close" in s8_full
    assert "Final sprint" in s8_full
    assert "Product backlog" in s8_full
    assert "Sign-Off" in s8_full

    # Slide 9: Operating Rhythm / Agile Cadence
    s9 = prs.slides[8]
    s9_texts = [s.text_frame.text for s in s9.shapes if s.has_text_frame]
    s9_full = " ".join(s9_texts)

    assert "WAYS OF WORKING" in s9_full
    assert "Our operating rhythm" in s9_full
    assert "DAILY" in s9_full
    assert "SPRINT PLANNING" in s9_full
    assert "SPRINT DEMO & ACCEPTANCE" in s9_full
    assert "GOVERNANCE" in s9_full
    assert "Project team stand-ups" in s9_full
    assert "Backlog Refinement" in s9_full
    assert "Demo & Sprint Sign-Off" in s9_full
    assert "Retrospective & Alignment" in s9_full


def test_htl_116_item6_client_deck_slide6_focus_rows_and_completion_filter():
    """Item 6: Verify Slide 6 Focus rows source backlog themes and exclude milestone completion phrases."""
    b_prog = _create_programmatic_mock_baseline()
    s6_prog = build_slide6_model(b_prog)

    # Workstream titles should be functional themes, NOT milestone completion phrases
    titles = [ws.title for ws in s6_prog.workstreams]
    assert "Feature development" in titles
    assert "Security and reliability" in titles
    assert "Quality engineering" in titles

    for ws in s6_prog.workstreams:
        assert "concludes" not in ws.title.lower()
        assert "service period ends" not in ws.title.lower()
        assert "deliverables accepted following" not in ws.title.lower()
        for d in ws.deliverables:
            assert "concludes" not in d.lower()
            assert "service period ends" not in d.lower()
            assert "deliverables accepted following" not in d.lower()


def test_htl_116_client_deck_package_relationships_and_reachability(tmp_path: Path):
    """HTL-116: Verify generated Programmatic Client Kickoff Deck has zero orphaned relationships, missing targets, or unreferenced parts (mirroring test_htl_109)."""
    baseline = _create_programmatic_mock_baseline()
    res = export_client_deck(baseline, tmp_path / "client_deck_rel_check")
    deck_path = res.file_path

    prs = pptx.Presentation(str(deck_path))

    with zipfile.ZipFile(deck_path, "r") as z:
        names = set(z.namelist())

        # Parse ppt/presentation.xml and ppt/_rels/presentation.xml.rels
        tree = ET.fromstring(z.read("ppt/presentation.xml"))
        rels_tree = ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))

        ns = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main"}
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
            f"Slide count mismatch: zip_slides={len(zip_slide_files)}, "
            f"active_targets={len(active_slide_targets)}, prs_slides={len(prs.slides)}"
        )

        # 2. Zero orphaned slide parts in zip
        orphaned_slides = [
            s for s in zip_slide_files
            if s.replace("ppt/", "") not in active_slide_targets and s not in active_slide_targets
        ]
        assert len(orphaned_slides) == 0, f"Found orphaned slide files in zip: {orphaned_slides}"

        # 3. Zero orphaned notes slide parts
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
        assert len(orphaned_notes) == 0, f"Found orphaned notes files in zip: {orphaned_notes}"

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
        assert len(orphaned_rels) == 0, f"Found orphaned slide relationships in presentation.xml.rels: {orphaned_rels}"

        # 5. Slide 8 specific check: verify slide 8 .rels contains no dangling or missing targets
        s8_target = active_slide_targets[7]  # Slide 8
        s8_rel_file = ("ppt/" + s8_target if not s8_target.startswith("ppt/") else s8_target).replace("slides/", "slides/_rels/") + ".rels"
        if s8_rel_file in names:
            s8_rels_tree = ET.fromstring(z.read(s8_rel_file))
            for rel in s8_rels_tree.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"):
                tgt = rel.attrib["Target"]
                # Resolve relative target from ppt/slides/
                if tgt.startswith("../"):
                    resolved_tgt = "ppt/" + tgt[3:]
                else:
                    resolved_tgt = "ppt/slides/" + tgt
                assert resolved_tgt in names, f"Slide 8 relationship {rel.attrib['Id']} points to missing target {resolved_tgt}"

        # 6. Full package reachability graph check
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
        assert len(unreachable) == 0, f"Unreachable package entries in zip: {unreachable}"
