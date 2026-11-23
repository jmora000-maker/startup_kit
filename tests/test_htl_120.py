"""Tests for HTL-120: Deliverable boilerplate suffix removal and Governance Deck dynamic pagination parity."""

import pytest
from src.config import strip_deliverable_boilerplate
from src.core.models import (
    StartupKitBaseline,
    Deliverable,
    Milestone,
    ProjectStartupCharter,
    SOWInterpretationSummary,
)
from src.generators.client_deck.builder import build_client_deck_model
from src.generators.client_deck.writer import chunk_workstreams_for_deliverables_table, write_client_deck
from src.generators.governance_deck.builder import build_governance_deck_model
from src.generators.governance_deck.writer import write_governance_deck
import pptx
from pathlib import Path


def test_strip_deliverable_boilerplate():
    raw_desc = "Develop multi-user home access, roles, and permissions when committed in an agreed sprint; completion of the entire roadmap is not guaranteed."
    cleaned = strip_deliverable_boilerplate(raw_desc)
    assert cleaned == "Develop multi-user home access, roles, and permissions"
    assert "guaranteed" not in cleaned
    assert "committed in an agreed sprint" not in cleaned

    raw_desc2 = "Deliver connectivity, stale-state, and device-sync recovery (when committed in an agreed sprint; completion of the entire roadmap is not guaranteed)"
    assert strip_deliverable_boilerplate(raw_desc2) == "Deliver connectivity, stale-state, and device-sync recovery"

    raw_desc3 = "Provide defect triage; completion of the entire roadmap is not guaranteed."
    assert strip_deliverable_boilerplate(raw_desc3) == "Provide defect triage"


def test_htl_120_governance_deck_dynamic_pagination(tmp_path: Path):
    deliverables = [
        Deliverable(
            id=f"DEL-{i:02d}",
            name=f"Deliverable Feature {i}",
            description=f"Feature {i} implementation and integration when committed in an agreed sprint; completion of the entire roadmap is not guaranteed.",
            owner="Toptal Engineering",
            acceptance_criteria=["Feature verified against acceptance criteria"],
        )
        for i in range(1, 12)
    ]
    baseline = StartupKitBaseline(
        project_name="Test Smart Home App",
        client_name="Test Client",
        contract_type="Programmatic",
        contract_type_variant="Programmatic",
        charter=ProjectStartupCharter(
            project_name="Test Smart Home App",
            client_name="Test Client",
            contract_type="Programmatic",
            governance_tier="Guided",
            executive_summary="Executive summary test narrative.",
            problem_statement="Problem statement text.",
            solution_overview="Solution overview narrative.",
            success_criteria_summary="Success criteria summary.",
        ),
        sow_interpretation=SOWInterpretationSummary(
            solution_overview="Solution overview narrative for kickoff deck.",
            out_of_scope_items=["Hardware manufacturing", "Third party licensing"],
        ),
        milestones=[
            Milestone(id="M1", description="Sprint Cadence Delivery", external_date="2026-12-01"),
        ],
        deliverables=deliverables,
    )

    client_model = build_client_deck_model(baseline)
    gov_model = build_governance_deck_model(baseline)

    client_path = tmp_path / "client.pptx"
    gov_path = tmp_path / "gov.pptx"

    write_client_deck(client_model, client_path)
    write_governance_deck(gov_model, gov_path)

    cd = pptx.Presentation(client_path)
    gd = pptx.Presentation(gov_path)

    # Confirm deliverable chunks
    chunks_c = chunk_workstreams_for_deliverables_table(client_model.slide6.workstreams)
    num_chunks = len(chunks_c)

    # Client deck should have 16 + (num_chunks - 1) slides
    assert len(cd.slides) == 16 + (num_chunks - 1)
    # Governance deck should have 21 + num_chunks slides
    assert len(gd.slides) == 21 + num_chunks

    # Check that governance deck deliverable slides contain the deliverables
    def extract_slide_text(slide):
        texts = []
        for shp in slide.shapes:
            if shp.has_text_frame:
                texts.append(shp.text)
            if shp.has_table:
                for row in shp.table.rows:
                    for cell in row.cells:
                        texts.append(cell.text)
        return " ".join(texts)

    gov_deliv_text = " ".join([
        extract_slide_text(gd.slides[s_idx])
        for s_idx in range(14, 14 + num_chunks)
    ])

    assert "Feature 1 implementation and integration" in gov_deliv_text
    assert "Feature 11 implementation and integration" in gov_deliv_text
    assert "completion of the entire roadmap is not guaranteed" not in gov_deliv_text
