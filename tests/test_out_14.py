"""Comprehensive automated tests for OUT-14: Client Kickoff Deck generator and pipeline integration."""

import time
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch
import docx
import pptx
import pytest
from streamlit.testing.v1 import AppTest

from src.core.models import (
    Deliverable,
    DependencyAssumptionItem,
    Milestone,
    ProjectStartupCharter,
    RiskAssumption,
    SOWInterpretationSummary,
    Stakeholder,
    StartupKitBaseline,
)
from src.core.outputs import OutputSelection, RunResult
from src.generators.client_deck import (
    ClientDeckModel,
    ClientDeckResult,
    check_client_deck_traceability,
    export_client_deck,
)
from src.generators.client_deck.builder import (
    build_client_deck_model,
    build_slide1_model,
    build_slide5_model,
    build_slide6_model,
    build_slide12_model,
    build_slide15_model,
    format_success_criteria_prose,
    is_commercial_risk,
    synthesize_problem_statement,
)
from src.generators.client_deck.validator import check_boilerplate_slides_unchanged
from src.generators.client_deck.writer import write_client_deck
from src.orchestrator import StartupKitController
from src.review_ui.generate import (
    validate_generate_inputs,
    validate_output_selection,
    validate_reingest_inputs,
)

APP_FILE = str(Path(__file__).parent.parent / "src" / "review_ui" / "app.py")


@pytest.fixture
def rich_client_deck_baseline():
    """Rich baseline fixture for Client Kickoff Deck generation and testing."""
    return StartupKitBaseline(
        project_name="Apex Enterprise Cloud",
        contract_type="Time and Materials",
        governance_tier="Partnered",
        sow_awarded_date=date(2026, 11, 1),
        charter=ProjectStartupCharter(
            client_name="Apex Global Technologies",
            project_purpose="Modernize customer onboarding pipeline with event-driven cloud microservices.",
            delivery_manager="Jane Doe",
            pmo_lead="Sarah Connor",
            talent_pm="Alex Rivera",
            delivery_objectives=[
                "Deploy microservices architecture on AWS",
                "Integrate real-time identity verification",
            ],
            success_criteria=[
                "Reduce onboarding processing latency from 48 hours to under 15 minutes",
                "Achieve 99.95% service uptime across all regional endpoints",
                "Pass all SOC2 compliance audit checks prior to general availability",
            ],
            high_level_scope=[
                "Core microservices development and API orchestration",
                "Database schema migration from legacy Oracle to PostgreSQL",
            ],
            exclusions=[
                "Legacy mainframe decommissioning and hardware salvage",
                "Third-party credit bureau licensing agreements",
            ],
        ),
        sow_interpretation=SOWInterpretationSummary(
            contracted_deliverables=["Core API Gateway", "Authentication Service", "Reporting Service"],
            out_of_scope_items=["Hardware procurement", "On-premise network reconfiguration"],
            customer_obligations=["Provide AWS IAM root access and staging credentials within 3 business days"],
            constraints=["Must comply with European GDPR data residency constraints"],
            dependencies=["Single Sign-On federation with Okta directory"],
        ),
        milestones=[
            Milestone(id="M1", description="Architecture & Discovery", external_date=date(2026, 12, 1), owner="Jane Doe"),
            Milestone(id="M2", description="Core Microservices Build", external_date=date(2027, 1, 15), owner="Jane Doe"),
            Milestone(id="M3", description="Integration & UAT Testing", external_date=date(2027, 2, 28), owner="Jane Doe"),
            Milestone(id="M4", description="Production Launch & Cutover", external_date=date(2027, 3, 31), owner="Jane Doe"),
        ],
        deliverables=[
            Deliverable(id="DEL-01", name="Architecture Blueprint & Schema Spec", owner="Jane Doe"),
            Deliverable(id="DEL-02", name="API Gateway & Auth Service Implementation", owner="Jane Doe"),
            Deliverable(id="DEL-03", name="Automated Integration & Regression Test Suite", owner="Jane Doe"),
            Deliverable(id="DEL-04", name="Production Deployment Runbook & Release Notes", owner="Jane Doe"),
        ],
        dependencies_assumptions=[
            DependencyAssumptionItem(
                id="ASM-01",
                type="Assumption",
                description="Assumes blended billing rate of $175/hr for senior engineering talent",
                category="Commercial",
                status="Active",
            ),
            DependencyAssumptionItem(
                id="DEP-01",
                type="Dependency",
                description="Client security team sign-off on OAuth2 token exchange architecture",
                category="Technical",
                status="Open",
            ),
        ],
        raid_items=[
            # Commercial risk: MUST BE SCRUBBED from Slide 12
            RiskAssumption(
                id="RSK-01",
                type="Risk",
                description="Budget overrun if total engagement spend exceeds $350,000 fee ceiling",
                category="Financial Risk",
                probability="High",
                impact="High",
                mitigation_or_response="Weekly financial burn review to manage billable hours",
                due_date=date(2026, 12, 15),
            ),
            # Delivery risk 1 (Score: 3*3=9)
            RiskAssumption(
                id="RSK-02",
                type="Risk",
                description="Delay in client IAM credential provisioning blocking sandbox environment setup",
                category="Dependencies",
                probability="High",
                impact="High",
                mitigation_or_response="Escalate access request to Client Sponsor during kickoff meeting",
                due_date=date(2026, 11, 10),
            ),
            # Delivery risk 2 (Score: 3*2=6)
            RiskAssumption(
                id="RSK-03",
                type="Risk",
                description="Legacy database schema complexity extending data migration ETL timeline",
                category="Technical",
                probability="High",
                impact="Medium",
                mitigation_or_response="Conduct early schema profiling sprint in Phase 1",
                due_date=date(2026, 12, 1),
            ),
            # Delivery risk 3 (Score: 2*2=4)
            RiskAssumption(
                id="RSK-04",
                type="Risk",
                description="Third-party payment gateway API rate limiting under peak load",
                category="Operational",
                probability="Medium",
                impact="Medium",
                mitigation_or_response="Implement exponential backoff caching layer",
                due_date=date(2027, 1, 20),
            ),
            # Delivery risk 4 (Score: 1*1=1, should be ranked below top 3)
            RiskAssumption(
                id="RSK-05",
                type="Risk",
                description="Minor UI styling adjustments requested during final UAT demo",
                category="Governance",
                probability="Low",
                impact="Low",
                mitigation_or_response="Manage styling tweaks within standard sprint buffer",
                due_date=date(2027, 2, 15),
            ),
        ],
    )


# =========================================================================
# 1. Slide 1 Replacement Tests
# =========================================================================

def test_slide1_placeholder_replacement(rich_client_deck_baseline, tmp_path):
    """OUT-14.1: Slide 1 fills [Client Name] and [Project Name] placeholders correctly."""
    out_file = tmp_path / "slide1_test.pptx"
    model = build_client_deck_model(rich_client_deck_baseline)
    assert model.slide1.client_name == "Apex Global Technologies"
    assert model.slide1.project_name == "Apex Enterprise Cloud"

    saved_path = write_client_deck(model, out_file)
    prs = pptx.Presentation(str(saved_path))
    slide1 = prs.slides[0]

    title_shape = next(s for s in slide1.shapes if s.has_text_frame and "Kickoff" in s.text_frame.text)
    assert "Apex Global Technologies" in title_shape.text_frame.text
    assert "Apex Enterprise Cloud" in title_shape.text_frame.text
    assert "[Client Name]" not in title_shape.text_frame.text
    assert "[Project Name]" not in title_shape.text_frame.text


def test_slide1_client_name_fallback_to_client(tmp_path):
    """OUT-14.1: Slide 1 falls back to 'Client' when client_name is unstated."""
    baseline = StartupKitBaseline(
        project_name="Generic Cloud Project",
        charter=ProjectStartupCharter(client_name=None, project_purpose="Cloud platform."),
    )
    model = build_slide1_model(baseline)
    assert model.client_name == "Client"
    assert model.project_name == "Generic Cloud Project"


# =========================================================================
# 2. Slide 5 Problem Statement & Success Criteria Synthesis Tests
# =========================================================================

def test_slide5_why_problem_success_synthesis(rich_client_deck_baseline):
    """OUT-14.2: Slide 5 maps project purpose, synthesizes problem statement, and formats prose success criteria."""
    model = build_slide5_model(rich_client_deck_baseline)

    # Why are we doing this?
    assert model.why_are_we_doing_this == "Modernize customer onboarding pipeline with event-driven cloud microservices."

    # What problem are we solving? (deterministic synthesis without LLM)
    assert "Addressing operational bottlenecks and technical limitations" in model.what_problem_are_we_solving
    assert "European GDPR data residency constraints" in model.what_problem_are_we_solving

    # What does success look like? (narrative prose, not bullet list)
    assert model.what_does_success_look_like.startswith("Success is defined across key project milestones:")
    assert "reduce onboarding processing latency" in model.what_does_success_look_like
    assert "99.95% service uptime" in model.what_does_success_look_like
    assert "•" not in model.what_does_success_look_like
    assert "\n" not in model.what_does_success_look_like


def test_format_success_criteria_prose_variations():
    """OUT-14.2: format_success_criteria_prose correctly formats 0, 1, 2, and 3+ criteria."""
    # 0 criteria
    assert "Success will be achieved upon fulfilling all contracted deliverables" in format_success_criteria_prose([])

    # 1 criterion
    c1 = format_success_criteria_prose(["Complete platform deployment on AWS"])
    assert c1 == "Success is defined by complete platform deployment on AWS."

    # 2 criteria
    c2 = format_success_criteria_prose(["Deliver Core API Gateway", "Achieve 99.9% uptime"])
    assert c2 == "Success is defined by deliver Core API Gateway, and achieve 99.9% uptime."

    # 3+ criteria
    c3 = format_success_criteria_prose(["Deliver API", "Deploy database", "Pass security audit"])
    assert c3 == "Success is defined across key project milestones: deliver API; deploy database; and pass security audit."


def test_synthesize_problem_statement_fallbacks():
    """OUT-14.2: synthesize_problem_statement gracefully handles missing purpose or constraints."""
    # Baseline with no constraints or major risks
    b1 = StartupKitBaseline(
        project_name="Simple Project",
        charter=ProjectStartupCharter(project_purpose="Migrate existing databases to cloud."),
    )
    s1 = synthesize_problem_statement(b1)
    assert s1 == "Addressing existing legacy operational and technology challenges by executing: Migrate existing databases to cloud."

    # Baseline with no charter purpose
    b2 = StartupKitBaseline(project_name="Minimal Project")
    s2 = synthesize_problem_statement(b2)
    assert s2 == "Addressing existing operational and technology challenges to establish core platform capabilities."


# =========================================================================
# 3. Slide 6 Dynamic Layout Tests (N=2, N=4, N=6 and Overflow)
# =========================================================================

def test_slide6_dynamic_layout_n4(rich_client_deck_baseline, tmp_path):
    """OUT-14.3: Slide 6 populates exact 4 workstream blocks with proper bullets and title clearance."""
    out_file = tmp_path / "slide6_n4.pptx"
    model = build_client_deck_model(rich_client_deck_baseline)
    assert len(model.slide6.workstreams) == 4

    saved_path = write_client_deck(model, out_file)
    prs = pptx.Presentation(str(saved_path))
    slide6 = prs.slides[5]

    all_text = "\n".join(s.text_frame.text for s in slide6.shapes if s.has_text_frame)
    assert "Architecture & Discovery" in all_text
    assert "Core Microservices Build" in all_text
    assert "Integration & UAT Testing" in all_text
    assert "Production Launch & Cutover" in all_text
    assert "Out of Scope:" in all_text
    assert "Legacy mainframe decommissioning" in all_text

    # Verify Solution Overview title (shape 193) and body (shape 194) clearance and styling
    s193 = next(s for s in slide6.shapes if s.shape_id == 193 or (s.has_text_frame and "Solution Overview" in s.text_frame.text))
    s194 = next(s for s in slide6.shapes if s.shape_id == 194 or (s.has_text_frame and "Modernize customer onboarding" in s.text_frame.text))
    assert s194.top >= s193.top + s193.height
    assert len(s193._element.xpath(".//p:ph")) == 0
    assert s193.text_frame.paragraphs[0].runs[0].font.color.rgb == pptx.dml.color.RGBColor(255, 255, 255)
    assert s194.text_frame.paragraphs[0].runs[0].font.color.rgb == pptx.dml.color.RGBColor(255, 255, 255)

    # Verify deliverable boxes have native bullet formatting on every paragraph
    deliv_shapes = [s for s in slide6.shapes if s.shape_id in (205, 206, 208, 210)]
    for ds in deliv_shapes:
        if ds.has_text_frame:
            for p in ds.text_frame.paragraphs:
                pPr_elements = p._p.xpath("./a:pPr")
                assert len(pPr_elements) > 0, "Paragraph missing pPr bullet formatting"
                buChar = pPr_elements[0].xpath("./a:buChar")
                assert len(buChar) > 0, "Paragraph missing a:buChar bullet definition"


def test_slide6_dynamic_layout_n2(tmp_path):
    """OUT-14.3: Slide 6 dynamically removes surplus shapes and configures divider lines for N=2."""
    baseline = StartupKitBaseline(
        project_name="Two Phase Project",
        milestones=[
            Milestone(id="M1", description="Phase 1: Foundation & Discovery"),
            Milestone(id="M2", description="Phase 2: Core Platform Launch"),
        ],
        deliverables=[
            Deliverable(id="D1", name="Discovery Architecture Report (M1)"),
            Deliverable(id="D2", name="Production Ready Application (M2)"),
        ],
    )
    out_file = tmp_path / "slide6_n2.pptx"
    model = build_client_deck_model(baseline)
    assert len(model.slide6.workstreams) == 2

    saved_path = write_client_deck(model, out_file)
    prs = pptx.Presentation(str(saved_path))
    slide6 = prs.slides[5]

    all_text = "\n".join(s.text_frame.text for s in slide6.shapes if s.has_text_frame)
    assert "Phase 1: Foundation & Discovery" in all_text
    assert "Phase 2: Core Platform Launch" in all_text
    assert "[Workstream or Feature Set 3]" not in all_text
    assert "[Workstream or Feature Set 4]" not in all_text

    # Exactly 3 divider lines (N + 1)
    lines = [s for s in slide6.shapes if s.shape_id in (195, 196, 197, 198, 199) or (not s.has_text_frame and not s.has_table and s.height == 0)]
    assert len(lines) == 3


def test_slide6_dynamic_layout_n6_and_overflow(tmp_path):
    """OUT-14.3: Slide 6 dynamically clones shapes for N=6 workstreams and handles >3 deliverables overflow."""
    many_deliverables = [
        Deliverable(id=f"D1_{i}", name=f"Phase 1 Component Feature Deliverable {i}") for i in range(1, 6)
    ]
    baseline = StartupKitBaseline(
        project_name="Six Phase Platform",
        milestones=[
            Milestone(id="M1", description="Phase 1: Discovery"),
            Milestone(id="M2", description="Phase 2: Architecture"),
            Milestone(id="M3", description="Phase 3: Core API Services"),
            Milestone(id="M4", description="Phase 4: Web Frontend"),
            Milestone(id="M5", description="Phase 5: Performance Testing"),
            Milestone(id="M6", description="Phase 6: Multi-Region Deployment"),
        ],
        deliverables=many_deliverables,
    )
    out_file = tmp_path / "slide6_n6.pptx"
    model = build_client_deck_model(baseline)
    assert len(model.slide6.workstreams) == 6

    # Verify first workstream has overflow pattern (>3 deliverables mapped)
    ws1 = model.slide6.workstreams[0]
    assert len(ws1.deliverables) == 3
    assert ws1.deliverables[2].startswith("+")
    assert "additional deliverables (see Project Delivery Workbook)" in ws1.deliverables[2]

    saved_path = write_client_deck(model, out_file)
    prs = pptx.Presentation(str(saved_path))
    slide6 = prs.slides[5]

    all_text = "\n".join(s.text_frame.text for s in slide6.shapes if s.has_text_frame)
    assert "Phase 1: Discovery" in all_text
    assert "Phase 6: Multi-Region Deployment" in all_text
    assert "+ 3 additional deliverables (see Project Delivery Workbook)" in all_text

    # Exactly 7 divider lines (N + 1)
    lines = [s for s in slide6.shapes if not s.has_text_frame and not s.has_table and s.height == 0]
    assert len(lines) == 7


# =========================================================================
# 4. Slide 12 Risk Filtering & Severity Ranking Tests
# =========================================================================

def test_slide12_commercial_risk_exclusion_and_ranking(rich_client_deck_baseline, tmp_path):
    """OUT-14.4: Slide 12 scrubs financial/commercial risks and ranks top 3 delivery risks by severity."""
    model = build_slide12_model(rich_client_deck_baseline)

    # 1. Commercial risk RSK-01 ($350,000 budget overrun) MUST NOT be present
    risk_ids = [r.id for r in model.risks]
    assert "RSK-01" not in risk_ids
    assert not any("$" in r.description for r in model.risks)

    # 2. Exactly top 3 risks selected in rank order
    assert len(model.risks) == 3
    assert model.risks[0].id == "RSK-02"  # Score: 3*3 = 9
    assert model.risks[1].id == "RSK-03"  # Score: 3*2 = 6
    assert model.risks[2].id == "RSK-04"  # Score: 2*2 = 4
    # RSK-05 (score 1) is ranked 4th and excluded

    # 3. Target resolution date matches risk.due_date
    assert model.risks[0].target_date == "2026-11-10"

    # 4. Write presentation and verify table
    out_file = tmp_path / "slide12_test.pptx"
    full_model = build_client_deck_model(rich_client_deck_baseline)
    saved_path = write_client_deck(full_model, out_file)
    prs = pptx.Presentation(str(saved_path))
    slide12 = prs.slides[11]

    tbl = next(s.table for s in slide12.shapes if s.has_table)
    assert len(tbl.rows) == 4  # Header + 3 risks
    row1_text = " | ".join(c.text for c in tbl.rows[1].cells)
    assert "RSK-02" in row1_text
    assert "High/High" in row1_text
    assert "2026-11-10" in row1_text


def test_slide12_only_commercial_risks_graceful_handling(tmp_path):
    """OUT-14.4: When baseline has only commercial risks, Slide 12 handles empty/fewer risks cleanly."""
    baseline = StartupKitBaseline(
        project_name="Commercial Only",
        raid_items=[
            RiskAssumption(
                id="RSK-C1",
                type="Risk",
                description="Hourly rate billing escalation over $200/hr",
                category="Commercial",
            ),
            RiskAssumption(
                id="RSK-C2",
                type="Risk",
                description="Margin erosion due to subcontractor fee structure",
                category="Financial",
            ),
        ],
    )
    model = build_slide12_model(baseline)
    assert len(model.risks) == 0

    full_model = build_client_deck_model(baseline)
    out_file = tmp_path / "slide12_empty.pptx"
    saved_path = write_client_deck(full_model, out_file)
    prs = pptx.Presentation(str(saved_path))
    slide12 = prs.slides[11]

    tbl = next(s.table for s in slide12.shapes if s.has_table)
    assert len(tbl.rows) == 1  # Only header row remains


# =========================================================================
# 5. Slide 15 Next Steps Tests
# =========================================================================

def test_slide15_next_steps_dynamic_selection_and_tbd_due(rich_client_deck_baseline, tmp_path):
    """OUT-14.5: Slide 15 draws open items dynamically and enforces literal 'TBD' in Due column."""
    model = build_slide15_model(rich_client_deck_baseline)

    assert len(model.next_steps) >= 2
    # Verify Due column is strictly "TBD" across all rows
    assert all(step.due == "TBD" for step in model.next_steps)

    # Customer obligation present
    assert any("Provide AWS IAM root access" in step.action for step in model.next_steps)

    # Write presentation and verify table
    out_file = tmp_path / "slide15_test.pptx"
    full_model = build_client_deck_model(rich_client_deck_baseline)
    saved_path = write_client_deck(full_model, out_file)
    prs = pptx.Presentation(str(saved_path))
    slide15 = prs.slides[14]

    tbl = next(s.table for s in slide15.shapes if s.has_table)
    for row_idx in range(1, len(tbl.rows)):
        assert tbl.rows[row_idx].cells[2].text.strip() == "TBD"


# =========================================================================
# 6. Traceability Manifest & Boilerplate Preservation Tests
# =========================================================================

def test_trace_manifest_generation_and_boilerplate_preservation(rich_client_deck_baseline, tmp_path):
    """OUT-14.7: Generates trace manifest and validates boilerplate slides (2,3,4,7,8,9,10,11,13,14,16) are untouched."""
    out_dir = tmp_path / "client_deck_trace_test"
    result = export_client_deck(rich_client_deck_baseline, out_dir)

    assert result.file_path.exists()
    assert result.manifest_path.exists()
    assert result.slides_count == 16
    assert result.trace_entries_count > 0

    # Traceability validator check
    findings = check_client_deck_traceability(rich_client_deck_baseline, result.file_path, result.manifest_path)
    assert len(findings) == 0

    # Explicit boilerplate preservation check
    prs = pptx.Presentation(str(result.file_path))
    is_boilerplate_ok, bp_errors = check_boilerplate_slides_unchanged(prs)
    assert is_boilerplate_ok is True
    assert len(bp_errors) == 0


# =========================================================================
# 7. Pipeline & Streamlit UI Integration Tests (HTL-45, HTL-46, HTL-47)
# =========================================================================

def test_validate_output_selection_with_client_deck():
    """HTL-47: Selecting client_deck satisfies minimum deliverable validation."""
    outputs = OutputSelection(kit=False, checklist=False, workbook=False, slides=False, client_deck=True)
    assert validate_output_selection(outputs=outputs) is None
    assert validate_output_selection(client_deck=True) is None

    # All False returns error
    all_false = OutputSelection(kit=False, checklist=False, workbook=False, slides=False, client_deck=False)
    assert validate_output_selection(outputs=all_false) is not None


def test_ui_checkboxes_default_to_false_and_pipeline_execution():
    """HTL-45 / HTL-46 / OUT-14: UI checkboxes default to False and checking client_deck executes generation."""
    at = AppTest.from_file(APP_FILE, default_timeout=15)
    at.session_state["generation_unlocked"] = True
    at.session_state["generation_unlocked_at"] = time.time()
    at.session_state["gen_admin_unlocked"] = True
    at.session_state["reingest_admin_unlocked"] = True
    at.run()

    assert not at.exception

    # Generate tab checkboxes
    kit_cb = next(cb for cb in at.checkbox if cb.key == "gen_out_kit")
    wb_cb = next(cb for cb in at.checkbox if cb.key == "gen_out_workbook")
    slides_cb = next(cb for cb in at.checkbox if cb.key == "gen_out_slides")
    client_deck_cb = next(cb for cb in at.checkbox if cb.key == "gen_out_client_deck")

    assert kit_cb.value is False
    assert wb_cb.value is False
    assert slides_cb.value is False
    assert client_deck_cb.value is False

    # Check client deck and submit
    at.file_uploader(key="gen_uploader").upload("sow.docx", b"sample-bytes").run()
    at.checkbox(key="gen_out_client_deck").check().run()

    mock_result = RunResult(
        readiness_score=88.5,
        paused=True,
        run_id="OUT14_Test_Run_20261025",
    )

    with patch("src.review_ui.generate._run_generate", return_value=mock_result) as mock_gen:
        at.button(key="gen_submit_button").click().run()
        assert not at.exception
        assert mock_gen.called
        assert mock_gen.call_args.kwargs["outputs"].client_deck is True


# =========================================================================
# 8. End-to-End Generated Deliverable Artifact Verification
# =========================================================================

def test_end_to_end_freshly_generated_client_kickoff_deck(rich_client_deck_baseline):
    """End-to-end generation of output/OUT14_Client_Kickoff_Deck_Verified.pptx and thorough inspection."""
    out_dir = Path("output")
    out_dir.mkdir(parents=True, exist_ok=True)
    target_deck_path = out_dir / "OUT14_Client_Kickoff_Deck_Verified.pptx"

    model = build_client_deck_model(rich_client_deck_baseline)
    saved_path = write_client_deck(model, target_deck_path)

    assert saved_path.exists()
    assert saved_path.stat().st_size > 100_000  # Non-empty real pptx file

    prs = pptx.Presentation(str(saved_path))
    assert len(prs.slides) == 16

    # 1. Slide 1 (Title)
    s1_text = "\n".join(s.text_frame.text for s in prs.slides[0].shapes if s.has_text_frame)
    assert "Apex Global Technologies" in s1_text
    assert "Apex Enterprise Cloud" in s1_text

    # 2. Slide 5 (Success Agreement)
    s5_text = "\n".join(s.text_frame.text for s in prs.slides[4].shapes if s.has_text_frame)
    assert "Modernize customer onboarding pipeline" in s5_text
    assert "Success is defined across key project milestones" in s5_text

    # 3. Slide 6 (What We Will Deliver)
    s6_text = "\n".join(s.text_frame.text for s in prs.slides[5].shapes if s.has_text_frame)
    assert "Architecture & Discovery" in s6_text
    assert "Out of Scope:" in s6_text

    # 4. Slide 12 (Risks)
    s12_tbl = next(s.table for s in prs.slides[11].shapes if s.has_table)
    assert len(s12_tbl.rows) == 4
    all_s12_text = " ".join(c.text for r in s12_tbl.rows for c in r.cells)
    assert "RSK-02" in all_s12_text
    assert "$350,000" not in all_s12_text

    # 5. Slide 15 (Next Steps)
    s15_tbl = next(s.table for s in prs.slides[14].shapes if s.has_table)
    assert len(s15_tbl.rows) >= 3
    for row_idx in range(1, len(s15_tbl.rows)):
        assert s15_tbl.rows[row_idx].cells[2].text.strip() == "TBD"
