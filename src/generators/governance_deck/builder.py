"""Pure builder module transforming StartupKitBaseline into GovernanceDeckModel (HTL-72)."""

from typing import List, Optional
from src.core.models import StartupKitBaseline
from src.generators.kit_values import kit_header_values
from src.generators.client_deck.builder import (
    build_slide1_model as client_build_slide1_model,
    build_slide5_model as client_build_slide5_model,
    build_slide6_model as client_build_slide6_model,
    build_slide12_model as client_build_slide12_model,
    build_slide15_model as client_build_slide15_model,
)
from src.generators.governance_deck.spec import (
    GovernanceDeckModel,
    NextStepItem,
    RiskItem,
    Slide1Model,
    Slide13WhyModel,
    Slide14DeliverModel,
    Slide18RisksModel,
    Slide19NextStepsModel,
    WorkstreamBlock,
)
from src.generators.governance_deck.trace import GovernanceDeckTraceManifest, TraceRef


def build_slide1_model(baseline: StartupKitBaseline) -> Slide1Model:
    """Build Slide 1 model with client sponsor and project name sourced from kit_header_values (HTL-49 / HTL-72)."""
    client_m = client_build_slide1_model(baseline)
    return Slide1Model(client_name=client_m.client_name, project_name=client_m.project_name)


def build_slide13_model(baseline: StartupKitBaseline) -> Slide13WhyModel:
    """Build Slide 13 model (Why We're Here) reusing client deck slide 5 extraction (HTL-72)."""
    s5 = client_build_slide5_model(baseline)
    return Slide13WhyModel(
        why_are_we_doing_this=s5.why_are_we_doing_this,
        what_problem_are_we_solving=s5.what_problem_are_we_solving,
        what_does_success_look_like=s5.what_does_success_look_like,
    )


def build_slide14_model(baseline: StartupKitBaseline) -> Slide14DeliverModel:
    """Build Slide 14 model (What We Will Deliver) reusing client deck slide 6 extraction (HTL-72)."""
    s6 = client_build_slide6_model(baseline)
    ws_blocks = [
        WorkstreamBlock(
            title=ws.title,
            deliverables=list(ws.deliverables),
            overflow_count=ws.overflow_count,
        )
        for ws in s6.workstreams
    ]
    return Slide14DeliverModel(
        workstreams=ws_blocks,
        solution_overview=s6.solution_overview,
        out_of_scope=list(s6.out_of_scope),
    )


def build_slide18_model(baseline: StartupKitBaseline) -> Slide18RisksModel:
    """Build Slide 18 model (Initial Risk Register) reusing client deck slide 12 extraction (HTL-72)."""
    s12 = client_build_slide12_model(baseline)
    risk_items = [
        RiskItem(
            id=r.id,
            description=r.description,
            prob_impact=r.prob_impact,
            mitigation=r.mitigation,
            target_date=r.target_date,
            severity_score=r.severity_score,
        )
        for r in s12.risks
    ]
    return Slide18RisksModel(risks=risk_items)


def build_slide19_model(baseline: StartupKitBaseline) -> Slide19NextStepsModel:
    """Build Slide 19 model (Next Steps) reusing client deck slide 15 extraction (HTL-72)."""
    s15 = client_build_slide15_model(baseline)
    step_items = [
        NextStepItem(
            owner=st.owner,
            action=st.action,
            due=st.due,
        )
        for st in s15.next_steps
    ]
    return Slide19NextStepsModel(next_steps=step_items)


def build_governance_deck_model(baseline: StartupKitBaseline) -> GovernanceDeckModel:
    """Complete builder transforming StartupKitBaseline into GovernanceDeckModel with 19-slide trace manifest (HTL-72)."""
    project_name = baseline.project_name or "Project Baseline"
    manifest = GovernanceDeckTraceManifest(project_name=project_name)

    slide1 = build_slide1_model(baseline)
    slide13 = build_slide13_model(baseline)
    slide14 = build_slide14_model(baseline)
    slide18 = build_slide18_model(baseline)
    slide19 = build_slide19_model(baseline)

    # 1. Slide 1 Traces
    headers = kit_header_values(baseline)
    manifest.add(
        slide=1,
        shape="Google Shape;93;p20",
        element="Title",
        displayed_value=f"{slide1.client_name}\n{slide1.project_name} Governance Kickoff",
        traces=[
            TraceRef(
                artifact="Kit",
                locator="Header table",
                key="client_sponsor",
                field="client_sponsor",
            ),
            TraceRef(
                artifact="Kit",
                locator="Header table",
                key="project_name",
                field="project_name",
            ),
        ],
        values=[headers.get("client_sponsor", "Client"), headers.get("project_name", project_name)],
    )

    # 2. Slide 13 Traces (Lifted Client Slide 5)
    manifest.add(
        slide=13,
        shape="Google Shape;176;p24",
        element="Why are we doing this?",
        displayed_value=slide13.why_are_we_doing_this,
        traces=[
            TraceRef(
                artifact="Kit",
                locator="Charter",
                key="project_purpose",
                field="project_purpose",
            )
        ],
    )
    manifest.add(
        slide=13,
        shape="Google Shape;180;p24",
        element="What problem are we solving?",
        displayed_value=slide13.what_problem_are_we_solving,
        traces=[
            TraceRef(
                artifact="Kit",
                locator="Charter",
                key="problem_statement",
                field="problem_statement",
            )
        ],
    )
    manifest.add(
        slide=13,
        shape="Google Shape;184;p24",
        element="What does success look like?",
        displayed_value=slide13.what_does_success_look_like,
        traces=[
            TraceRef(
                artifact="Kit",
                locator="SOW Interpretation",
                key="success_criteria",
                field="success_criteria",
            )
        ],
    )

    # 3. Slide 14 Traces (Lifted Client Slide 6)
    manifest.add(
        slide=14,
        shape="Google Shape;194;p25",
        element="Solution Overview",
        displayed_value=slide14.solution_overview,
        traces=[
            TraceRef(
                artifact="Kit",
                locator="Charter",
                key="solution_overview",
                field="solution_overview",
            )
        ],
    )
    for ws in slide14.workstreams:
        manifest.add(
            slide=14,
            shape="WorkstreamBlock",
            element=f"Workstream: {ws.title}",
            displayed_value="\n".join(ws.deliverables),
            traces=[
                TraceRef(
                    artifact="Workbook",
                    locator="WBS",
                    key=ws.title,
                    field="deliverables",
                )
            ],
            values=ws.deliverables,
        )
    if slide14.out_of_scope:
        manifest.add(
            slide=14,
            shape="Google Shape;202;p25",
            element="Out of Scope",
            displayed_value="\n".join(slide14.out_of_scope),
            traces=[
                TraceRef(
                    artifact="Kit",
                    locator="Charter",
                    key="out_of_scope",
                    field="out_of_scope",
                )
            ],
            values=slide14.out_of_scope,
        )

    # 4. Slide 18 Traces (Lifted Client Slide 12)
    for risk in slide18.risks:
        manifest.add(
            slide=18,
            shape="Table: Initial Risk Register",
            element=f"Risk: {risk.id}",
            displayed_value=f"{risk.description} | {risk.prob_impact} | {risk.mitigation}",
            traces=[
                TraceRef(
                    artifact="Workbook",
                    locator="RAID Log",
                    key=risk.id,
                    field="description",
                )
            ],
        )

    # 5. Slide 19 Traces (Lifted Client Slide 15)
    for step in slide19.next_steps:
        manifest.add(
            slide=19,
            shape="Table: Next Steps",
            element=f"Next Step: {step.owner}",
            displayed_value=f"{step.owner}: {step.action} (Due: {step.due})",
            traces=[
                TraceRef(
                    artifact="Kit",
                    locator="Next Steps",
                    key=step.owner,
                    field="action",
                )
            ],
        )

    return GovernanceDeckModel(
        project_name=project_name,
        slide1=slide1,
        slide13=slide13,
        slide14=slide14,
        slide18=slide18,
        slide19=slide19,
        manifest=manifest,
    )
