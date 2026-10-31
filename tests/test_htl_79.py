"""HTL-79: Targeted regression and coverage tests closing high-priority generator gaps.

Covers:
1. Slide 15 single-page table rendering path (governance_deck/writer.py:314, total_pages=1).
2. Client Kickoff Deck workstream layout thresholds for 1-3, 4-5, and 6+ workstreams (client_deck/writer.py:509-512, 519-522).
3. Change Order regex scrubbing fallback on risk mitigations (client_deck/builder.py:314-321).
"""

from pathlib import Path
import pptx
from pptx.util import Pt
import pytest

from tests.deck_bundle import load_baseline
from tests.test_htl_62 import _build_pge_baseline
from src.core.models import (
    StartupKitBaseline,
    Deliverable,
    RiskAssumption,
    SOWInterpretationSummary,
)
from src.generators.governance_deck import (
    export_governance_deck,
    build_governance_deck_model,
)
from src.generators.governance_deck.writer import (
    write_slide15_acceptance_criteria,
)
from src.generators.client_deck import (
    export_client_deck,
    build_client_deck_model,
)
from src.generators.client_deck.builder import (
    build_slide12_model,
)
from src.generators.client_deck.spec import (
    ClientDeckModel,
    Slide1Model,
    Slide5Model,
    Slide6Model,
    Slide12Model,
    Slide15Model,
    WorkstreamBlock,
)
from src.config import CLIENT_DECK_TEMPLATE_PATH
from src.generators.client_deck.writer import (
    write_slide6,
)


# =========================================================================
# 1. Slide 15 Single-Page Table Path (Governance Deck)
# =========================================================================

def test_governance_deck_slide15_single_page_path(tmp_path):
    """HTL-79 (Gap 1): Baseline with <=6 deliverables renders a single Slide 15 without pagination label."""
    pge_baseline = _build_pge_baseline()
    assert len(pge_baseline.deliverables) <= 6

    res = export_governance_deck(pge_baseline, tmp_path / "gov_pge")
    assert res.file_path.exists()
    assert res.slides_count == 19

    prs = pptx.Presentation(str(res.file_path))

    # Slide 15 is index 14
    slide15 = prs.slides[14]

    # Verify subtitle does NOT contain "Part X of Y" or "(Part"
    subtitle_shapes = [
        s.text_frame.text.strip()
        for s in slide15.shapes
        if s.has_text_frame and not s.has_table and "Contractual criteria" in s.text_frame.text
    ]
    assert len(subtitle_shapes) == 1
    subtitle_text = subtitle_shapes[0]
    assert "Part" not in subtitle_text
    assert subtitle_text == "Contractual criteria and verification requirements mapped to milestone gates."

    # Verify table has header + 6 data rows
    table_shapes = [s for s in slide15.shapes if s.has_table]
    assert len(table_shapes) == 1
    tbl = table_shapes[0].table
    assert len(tbl.rows) == 7

    rendered_ids = [tbl.rows[i].cells[0].text.strip().split("\n")[0] for i in range(1, len(tbl.rows))]
    expected_ids = [d.id for d in pge_baseline.deliverables]
    assert rendered_ids == expected_ids

    # Also directly exercise write_slide15_acceptance_criteria standalone entrypoint
    gov_model = build_governance_deck_model(pge_baseline)
    s_direct = prs.slides.add_slide(prs.slide_layouts[14])
    write_slide15_acceptance_criteria(s_direct, gov_model)
    direct_tables = [s for s in s_direct.shapes if s.has_table]
    assert len(direct_tables) == 1
    assert len(direct_tables[0].table.rows) == 7


# =========================================================================
# 2. Client Kickoff Deck Workstream Layout Thresholds
# =========================================================================

def _create_deck_with_n_workstreams(n_ws: int) -> ClientDeckModel:
    """Helper creating a ClientDeckModel with N workstreams and short titles/deliverables."""
    workstreams = [
        WorkstreamBlock(
            title=f"Workstream {i+1} Core",
            deliverables=[f"DEL-{i+1:02d}.1 Feature A", f"DEL-{i+1:02d}.2 Feature B"],
            overflow_count=0,
        )
        for i in range(n_ws)
    ]
    return ClientDeckModel(
        project_name=f"Project with {n_ws} Workstreams",
        slide1=Slide1Model(client_name="Test Client", project_name=f"Project with {n_ws} Workstreams"),
        slide5=Slide5Model(
            why_are_we_doing_this="Why text",
            what_problem_are_we_solving="Problem text",
            what_does_success_look_like="Success text",
        ),
        slide6=Slide6Model(
            workstreams=workstreams,
            solution_overview="Standard solution overview text.",
            out_of_scope=["Out of scope item 1"],
        ),
        slide12=Slide12Model(risks=[]),
        slide15=Slide15Model(next_steps=[]),
    )


@pytest.mark.parametrize("n_ws,expected_h_sz,expected_d_sz", [
    (1, 11.0, 10.5),
    (2, 11.0, 10.5),
    (3, 10.5, 10.0),
    (4, 10.0, 9.5),
    (5, 9.0, 8.5),
    (6, 8.0, 7.5),
    (7, 8.0, 7.5),
])
def test_client_deck_workstream_layout_thresholds(n_ws, expected_h_sz, expected_d_sz, tmp_path):
    """HTL-79 (Gap 2): Workstream count thresholds (1-3, 4-5, 6+) select correct font sizes and do not overflow."""
    model = _create_deck_with_n_workstreams(n_ws)

    # Use client deck template
    prs = pptx.Presentation(str(CLIENT_DECK_TEMPLATE_PATH))
    slide6 = prs.slides[5]

    write_slide6(slide6, model)

    # Inspect rendered shapes on slide 6
    # Headers are on left (left ~502750), deliverables on right (left ~2726700), below column header (top >= 1500000)
    h_shapes = [s for s in slide6.shapes if s.has_text_frame and abs(s.left - 502750) < 50000 and s.top >= 1500000 and "Workstream" in s.text_frame.text]
    d_shapes = [s for s in slide6.shapes if s.has_text_frame and abs(s.left - 2726700) < 50000 and s.top >= 1500000 and "DEL-" in s.text_frame.text]

    assert len(h_shapes) == n_ws, f"Expected {n_ws} header shapes, found {len(h_shapes)}"
    assert len(d_shapes) == n_ws, f"Expected {n_ws} deliverable shapes, found {len(d_shapes)}"

    # Verify font sizes
    for h in h_shapes:
        font_sz = h.text_frame.paragraphs[0].runs[0].font.size.pt
        assert font_sz == expected_h_sz, f"At n_ws={n_ws}, expected header font {expected_h_sz}, got {font_sz}"

    for d in d_shapes:
        font_sz = d.text_frame.paragraphs[0].runs[0].font.size.pt
        assert font_sz == expected_d_sz, f"At n_ws={n_ws}, expected deliv font {expected_d_sz}, got {font_sz}"

    # Verify geometry bounding box: bottom of all shapes must not exceed y_end (4873114)
    y_end = 4873114
    for s in h_shapes + d_shapes:
        bottom = s.top + s.height
        assert bottom <= y_end + 10000, f"Shape {s.shape_id} overflowed bottom: {bottom} > {y_end}"


# =========================================================================
# 3. Change Order Regex Scrubbing Fallback (Client Deck Builder)
# =========================================================================

def _build_baseline_with_risk_mitigation(mitigation_text: str) -> StartupKitBaseline:
    """Helper creating a baseline with a single risk whose mitigation is tested."""
    baseline = _build_pge_baseline()
    baseline.raid_items = [
        RiskAssumption(
            id="RAID-01",
            category="Risk",
            description="Scope expansion risk during phase 2 execution.",
            probability="High",
            impact="High",
            mitigation_or_response=mitigation_text,
            status="Open",
        )
    ]
    return baseline


def test_change_order_regex_scrubbing_with_surrounding_clause():
    """HTL-79 (Gap 3a): Risk mitigation with Change Order and non-commercial surrounding clause retains surrounding clause."""
    baseline = _build_baseline_with_risk_mitigation(
        "Track scope changes in weekly governance meetings, and manage a Change Order for out of scope features."
    )
    slide12_model = build_slide12_model(baseline)
    assert len(slide12_model.risks) == 1
    mitigation = slide12_model.risks[0].mitigation
    assert "Change Order" not in mitigation
    assert "Track scope changes in weekly governance meetings" in mitigation


def test_change_order_regex_scrubbing_fallback_when_empty():
    """HTL-79 (Gap 3b): Risk mitigation consisting solely of Change Order action falls back to sensible default text."""
    # Test case without trailing punctuation
    baseline_plain = _build_baseline_with_risk_mitigation("Manage a Change Order")
    model_plain = build_slide12_model(baseline_plain)
    assert model_plain.risks[0].mitigation == "Active monitoring by Delivery Manager and PMO"

    # Test case with defect keyword without trailing period
    baseline_defect = _build_baseline_with_risk_mitigation("Issue a Change Order for defect fixes")
    model_defect = build_slide12_model(baseline_defect)
    assert model_defect.risks[0].mitigation == "Report defects early and agree remediation timelines with Client"

    # Test case with trailing period
    baseline_period = _build_baseline_with_risk_mitigation("Manage a Change Order for out of scope items.")
    model_period = build_slide12_model(baseline_period)
    assert model_period.risks[0].mitigation == "Active monitoring by Delivery Manager and PMO"
