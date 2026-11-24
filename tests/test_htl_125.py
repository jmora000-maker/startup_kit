"""HTL-125: Regression test for Governance Kickoff Deck Slide 2 Agenda item font formatting.

Verifies that all agenda items on Slide 2, particularly the last item under PART 2 ("Next steps"),
have explicit formatting: font=Proxima Nova, size=11.0, bold=False.
"""

from pathlib import Path
import pptx
from src.core.models import (
    StartupKitBaseline,
    ProjectStartupCharter,
    SOWInterpretationSummary,
    Milestone,
    Deliverable,
    DependencyAssumptionItem,
    CommercialGuardrail,
    Stakeholder,
)
from src.generators.governance_deck import export_governance_deck


def test_htl_125_agenda_slide2_next_steps_font_formatting(tmp_path: Path):
    """HTL-125: Verify all agenda items on Slide 2 have explicit font=Proxima Nova, size=11.0, bold=False."""
    milestones = [
        Milestone(id="M-01", description="Sprint 1", external_date="2026-11-01", phase="Sprint 1"),
    ]
    charter = ProjectStartupCharter(
        project_name="HTL-125 Test Project",
        client_name="Carrier Smart Home",
        contract_type="Programmatic",
        governance_tier="Partnered",
        delivery_model="Toptal Talent Team (Agile Sprints)",
        project_purpose="Deliver smart home cloud connectivity through agile sprint backlogs.",
        problem_statement="Legacy IoT backend requires modern agile team capacity.",
        high_level_scope=["IoT Cloud", "Mobile SDK"],
        exclusions=["Hardware Firmware Manufacturing"],
        key_deliverables_summary=["DEL-01: Sprint Backlog Features"],
        milestones=milestones,
    )
    sow_int = SOWInterpretationSummary(
        contracted_deliverables=["Sprint Backlog Features"],
        out_of_scope_items=["Hardware Firmware"],
        platform_environment_commitments=["AWS IoT Core"],
        dependencies=["Client API Specifications (2 sprints ready backlog)"],
    )
    delivs = [Deliverable(id="DEL-01", name="Sprint Backlog Features", description="Two-week agile sprint backlog delivery")]
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

    baseline = StartupKitBaseline(
        project_name="HTL-125 Test Project",
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

    out_dir = tmp_path / "gov_deck_htl_125"
    res = export_governance_deck(baseline, out_dir)
    prs = pptx.Presentation(str(res.file_path))

    s2 = prs.slides[1]

    # Verify unnumbered topics and "Next steps" replacement
    expected_agenda_items = {
        107: "Who you represent",
        110: "Roles and responsibilities",
        113: "Sprint lifecycle",
        116: "Decision rights and boundaries",
        122: "Your team",
        125: "Who does what",
        128: "The two-week sprint",
        131: "Next steps",
    }

    for shape_id, expected_text in expected_agenda_items.items():
        matching_shapes = [shp for shp in s2.shapes if shp.has_text_frame and shp.shape_id == shape_id]
        assert len(matching_shapes) == 1, f"Shape id={shape_id} not found on Slide 2"
        shp = matching_shapes[0]
        assert shp.text_frame.text.strip() == expected_text, f"Shape {shape_id} text mismatch: {shp.text_frame.text.strip()!r} != {expected_text!r}"

        runs = [r for p in shp.text_frame.paragraphs for r in p.runs]
        assert len(runs) >= 1, f"Shape {shape_id} has no runs"
        for r in runs:
            assert r.font.name == "Proxima Nova", f"Shape {shape_id} ({shp.text_frame.text!r}) font is {r.font.name}"
            assert r.font.size is not None and r.font.size.pt == 11.0, f"Shape {shape_id} ({shp.text_frame.text!r}) size is {r.font.size}"
            assert r.font.bold is False, f"Shape {shape_id} ({shp.text_frame.text!r}) bold is {r.font.bold}"
