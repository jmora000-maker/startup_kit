"""PPTX Presentation writer and dynamic shape tree engine for PS Governance Kickoff Deck (HTL-72)."""

import copy
import os
from pathlib import Path
from typing import List, Optional, Tuple
import pptx
from pptx.util import Length, Pt
from pptx.dml.color import RGBColor

from src.config import CLIENT_DECK_TEMPLATE_PATH, GOVERNANCE_DECK_TEMPLATE_PATH
from src.generators.client_deck.fit import (
    estimate_text_height,
    fit_deliverables_for_block,
    select_fitting_font_size,
    truncate_at_clause,
)
from src.generators.client_deck.spec import (
    ClientDeckModel,
    Slide1Model as ClientSlide1Model,
    Slide5Model as ClientSlide5Model,
    Slide6Model as ClientSlide6Model,
    Slide12Model as ClientSlide12Model,
    Slide15Model as ClientSlide15Model,
    RiskItem as ClientRiskItem,
    NextStepItem as ClientNextStepItem,
    WorkstreamBlock as ClientWorkstreamBlock,
)
from src.generators.client_deck.writer import (
    _format_table_cell,
    _replace_shape_text,
    _set_header_paragraph_format,
    _set_paragraph_bullet_format,
    _populate_deliverables_box,
    write_slide5,
    write_slide6,
    write_slide12,
    write_slide15,
)
from src.generators.governance_deck.spec import GovernanceDeckModel


def resolve_governance_deck_template_path(custom_path: Optional[Path] = None) -> Path:
    """Resolve the PS Governance Kickoff Deck template path with fallback resolution (HTL-72)."""
    if custom_path and custom_path.exists():
        return custom_path

    env_path = os.getenv("GOVERNANCE_DECK_TEMPLATE_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    primary_path = Path("templates/PS_Governance Kickoff_TEMPLATE.pptx")
    if primary_path.exists():
        return primary_path

    fallback_path = Path("templates/PS_Governance_Kickoff_TEMPLATE.pptx")
    if fallback_path.exists():
        return fallback_path

    return primary_path


def resolve_client_deck_template_path(custom_path: Optional[Path] = None) -> Path:
    """Resolve the Client Kickoff Deck template path with fallback resolution (HTL-72)."""
    if custom_path and custom_path.exists():
        return custom_path
    if CLIENT_DECK_TEMPLATE_PATH.exists():
        return CLIENT_DECK_TEMPLATE_PATH
    fallback = Path("templates/Project_Kickoff_Deck_TEMPLATE.pptx")
    if fallback.exists():
        return fallback
    return CLIENT_DECK_TEMPLATE_PATH


def write_slide1(slide, model: GovernanceDeckModel) -> None:
    """Populate Slide 1 [Client Name] and [Project Name] placeholders with 'Governance Kickoff' and fixed subtitle (HTL-72)."""
    candidate_sizes = [24.0, 22.0, 20.0, 18.0, 16.0, 14.0, 13.0, 12.0, 11.0, 10.0, 9.5, 9.0]
    client_name = model.slide1.client_name or "Client"
    project_name = model.slide1.project_name or "Project Baseline"

    # Composite text for title line-wrapping and height estimation
    composite_title = f"{client_name}\n{project_name} Governance Kickoff"

    # Slide 1 available geometry:
    # Title box top = 2.966 in (2,712,227 EMUs), Layout divider line top = 4.423 in (4,044,375 EMUs).
    # To guarantee generous visual clearance (>= 0.70 in) above the divider line and subtitle (top = 4.542 in),
    # max_height_in is strictly bounded to 0.70 in (~50.4 pt).
    title_sz, _ = select_fitting_font_size(
        composite_title,
        width_in=3.30,
        max_height_in=0.70,
        candidate_sizes=candidate_sizes,
        is_bold=True,
    )

    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        text = shape.text_frame.text

        # Title Shape
        if "[Client Name]" in text or "[Project Name]" in text or shape.shape_id in (92, 93):
            tf = shape.text_frame
            tf.word_wrap = True
            tf.margin_top = 0
            tf.margin_bottom = 0
            tf.margin_left = 0
            tf.margin_right = 0

            # Strip normAutofit if present and enforce top anchor
            for bpr in shape._element.xpath(".//a:bodyPr"):
                bpr.set("anchor", "t")
                for autofit in list(bpr.xpath("./a:normAutofit")):
                    bpr.remove(autofit)
                if not bpr.xpath("./a:noAutofit"):
                    from lxml import etree
                    ns_a = "http://schemas.openxmlformats.org/drawingml/2006/main"
                    bpr.append(etree.Element(f"{{{ns_a}}}noAutofit"))

            # Clear paragraphs except first
            for p in list(tf.paragraphs[1:]):
                tf._txBody.remove(p._p)

            p0 = tf.paragraphs[0]
            p0.text = f"{client_name}\n{project_name} Governance Kickoff"
            for r in p0.runs:
                r.font.name = "Proxima Nova"
                r.font.size = Pt(title_sz)
                r.font.bold = True

        # Subtitle Shape
        elif "Onboarding for Project Managers" in text or "Aligning on outcomes" in text or shape.shape_id in (93, 94):
            tf = shape.text_frame
            tf.word_wrap = True
            tf.margin_top = 0
            tf.margin_bottom = 0
            tf.margin_left = 0
            tf.margin_right = 0

            for bpr in shape._element.xpath(".//a:bodyPr"):
                bpr.set("anchor", "t")

            for p in list(tf.paragraphs[1:]):
                tf._txBody.remove(p._p)

            p0 = tf.paragraphs[0]
            p0.text = "Aligning on outcomes, team, and how we'll deliver."
            for r in p0.runs:
                r.font.name = "Proxima Nova"
                r.font.size = Pt(11)


def write_governance_deck(
    model: GovernanceDeckModel,
    target_path: Path,
    template_path: Optional[Path] = None,
    client_template_path: Optional[Path] = None,
) -> Path:
    """Load template presentation, assemble 19 slides, populate lifted and new slides, and save output file (HTL-72)."""
    src_template = resolve_governance_deck_template_path(template_path)
    if not src_template.exists():
        raise FileNotFoundError(f"Governance Deck template not found at {src_template}")

    src_client_template = resolve_client_deck_template_path(client_template_path)
    if not src_client_template.exists():
        raise FileNotFoundError(f"Client Deck template not found at {src_client_template}")

    prs_gov = pptx.Presentation(str(src_template))
    prs_client = pptx.Presentation(str(src_client_template))

    layout_default = prs_gov.slide_layouts[14]

    # Add Acceptance Criteria (Slide 15 - Phase 2 placeholder)
    s_acc_crit = prs_gov.slides.add_slide(layout_default)
    for s in list(s_acc_crit.shapes):
        s_acc_crit.shapes._spTree.remove(s._element)

    # Add How Acceptance Works (Slide 16 - Phase 2 placeholder)
    s_acc_works = prs_gov.slides.add_slide(layout_default)
    for s in list(s_acc_works.shapes):
        s_acc_works.shapes._spTree.remove(s._element)

    # Add Risk Register (Slide 18) - Copy shapes from Client Deck Slide 12
    s_risk = prs_gov.slides.add_slide(layout_default)
    for s in list(s_risk.shapes):
        s_risk.shapes._spTree.remove(s._element)
    for shape in prs_client.slides[11].shapes:
        s_risk.shapes._spTree.append(copy.deepcopy(shape._element))

    # Copy Slide 3 shapes (Team Roster placeholders) from Client Deck onto Gov Slide 12 (index 11)
    s_gov_12 = prs_gov.slides[11]
    for s in list(s_gov_12.shapes):
        s_gov_12.shapes._spTree.remove(s._element)
    for s in prs_client.slides[2].shapes:
        s_gov_12.shapes._spTree.append(copy.deepcopy(s._element))

    # Copy Slide 5 shapes (Why We're Here) from Client Deck onto Gov Slide 13 (index 12)
    s_gov_13 = prs_gov.slides[12]
    for s in list(s_gov_13.shapes):
        s_gov_13.shapes._spTree.remove(s._element)
    for s in prs_client.slides[4].shapes:
        s_gov_13.shapes._spTree.append(copy.deepcopy(s._element))

    # Copy Slide 6 shapes (What We Will Deliver) from Client Deck onto Gov Slide 14 (index 13)
    s_gov_14 = prs_gov.slides[13]
    for s in list(s_gov_14.shapes):
        s_gov_14.shapes._spTree.remove(s._element)
    for s in prs_client.slides[5].shapes:
        s_gov_14.shapes._spTree.append(copy.deepcopy(s._element))

    # Reorder slides into exact 19-slide sequence:
    # 0..10: Slides 1..11
    # 11: Slide 12 (Team Roster - index 11)
    # 12: Slide 13 (Why We're Here - index 12)
    # 13: Slide 14 (What We Deliver - index 13)
    # 14: Slide 15 (Acceptance Criteria - index 17)
    # 15: Slide 16 (How Acceptance Works - index 18)
    # 16: Slide 17 (Approach - index 14)
    # 17: Slide 18 (Initial Risk Register - index 19)
    # 18: Slide 19 (Next Steps - index 15)
    desired_indices = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 17, 18, 14, 19, 15]
    sldIdLst = prs_gov.slides._sldIdLst
    all_sld_ids = list(sldIdLst)

    for child in list(sldIdLst):
        sldIdLst.remove(child)

    for idx in desired_indices:
        sldIdLst.append(all_sld_ids[idx])

    # Convert governance deck models to client models for slide writers
    client_deck_adapter = ClientDeckModel(
        project_name=model.project_name,
        slide1=ClientSlide1Model(client_name=model.slide1.client_name, project_name=model.slide1.project_name),
        slide5=ClientSlide5Model(
            why_are_we_doing_this=model.slide13.why_are_we_doing_this,
            what_problem_are_we_solving=model.slide13.what_problem_are_we_solving,
            what_does_success_look_like=model.slide13.what_does_success_look_like,
        ),
        slide6=ClientSlide6Model(
            workstreams=[
                ClientWorkstreamBlock(
                    title=ws.title,
                    deliverables=list(ws.deliverables),
                    overflow_count=ws.overflow_count,
                )
                for ws in model.slide14.workstreams
            ],
            solution_overview=model.slide14.solution_overview,
            out_of_scope=list(model.slide14.out_of_scope),
        ),
        slide12=ClientSlide12Model(
            risks=[
                ClientRiskItem(
                    id=r.id,
                    description=r.description,
                    prob_impact=r.prob_impact,
                    mitigation=r.mitigation,
                    target_date=r.target_date,
                    severity_score=r.severity_score,
                )
                for r in model.slide18.risks
            ]
        ),
        slide15=ClientSlide15Model(
            next_steps=[
                ClientNextStepItem(
                    owner=st.owner,
                    action=st.action,
                    due=st.due,
                )
                for st in model.slide19.next_steps
            ]
        ),
    )

    # Populate slides:
    # Slide 1 (index 0)
    write_slide1(prs_gov.slides[0], model)

    # Slide 13 (index 12): Why We're Here (Client Slide 5)
    write_slide5(prs_gov.slides[12], client_deck_adapter)

    # Slide 14 (index 13): What We Deliver (Client Slide 6)
    write_slide6(prs_gov.slides[13], client_deck_adapter)

    # Slide 18 (index 17): Initial Risk Register (Client Slide 12)
    write_slide12(prs_gov.slides[17], client_deck_adapter)

    # Slide 19 (index 18): Next Steps (Client Slide 15)
    write_slide15(prs_gov.slides[18], client_deck_adapter)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    prs_gov.save(str(target_path))

    # Write companion trace manifest: {project}_PS_Governance_Kickoff.trace.json
    manifest_path = target_path.with_name(f"{target_path.stem}.trace.json")
    model.manifest.write_json(manifest_path)

    return target_path
