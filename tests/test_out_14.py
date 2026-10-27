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


@pytest.fixture
def sample_real_failing_client_baseline():
    """Real known-failing baseline fixture (HTL-48) using authentic realistic-length SOW text."""
    return StartupKitBaseline(
        project_name="AI Infrastructure Intelligence Dashboard",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 10, 19),
        charter=ProjectStartupCharter(
            client_name="HealthTech AI Solutions",
            project_purpose="Move the client's AI Infrastructure Intelligence Dashboard from a static, hand-curated MVP covering 25 facilities to a pilot-ready product that can be onboarded to a pilot partner.",
            delivery_manager="David Miller",
            pmo_lead="Sarah Connor",
            talent_pm="Alex Rivera",
            delivery_objectives=[
                "Deploy scalable multi-facility data pipeline and ingestion microservices",
                "Integrate real-time anomaly detection and predictive infrastructure analytics",
            ],
            success_criteria=[
                "All four milestones accepted within five business days",
                "All 25 facility records in Postgres with no field-level discrepancies",
                "Persona-based access per the role-permission matrix",
                "WCAG 2.1 AA compliance",
                "Production live and handover complete",
            ],
            high_level_scope=[
                "Multi-facility telemetry ingestion, PostgreSQL data pipeline, and role-permission security matrix",
            ],
            exclusions=[
                "Hardware procurement and on-premise sensor installation",
                "Third-party proprietary clinical telemetry licensing fees",
            ],
        ),
        sow_interpretation=SOWInterpretationSummary(
            contracted_deliverables=[
                "Phase 1 - Data and Backend Foundation (18 core deliverables)",
                "Phase 2 - Analytics Engine and Anomaly Detection",
                "Phase 3 - Frontend Pilot Portal and WCAG Accessibility",
                "Phase 4 - Production Cutover and Partner Handover",
            ],
            out_of_scope_items=[
                "Hardware procurement and on-premise sensor deployment",
                "Third-party clinical telemetry licensing agreements",
            ],
            customer_obligations=[
                "Provide secure VPN credentials and PostgreSQL staging schema access within 3 business days of kickoff",
                "Designate authorized facility clinical telemetry reviewers for deliverable sign-offs",
            ],
            constraints=[
                "Fixed-fee engagement of $139,600 billed by milestone, with a $26,800 prepayment (about 50% of Milestone 1) due before the start date and applied to the final invoice(s); Estimated schedule runs from October 19, 2026 to January 22, 2027; if the start date shifts by mutual agreement, the completion date shifts equally without a Change Order.",
            ],
            dependencies=[
                "Pilot partner facility VPN endpoints configured with mutual TLS encryption",
            ],
        ),
        milestones=[
            Milestone(
                id="M1",
                description="Phase 1 - Data and Backend Foundation",
                phase_display="Phase 1",
                external_date=date(2026, 11, 20),
                owner="David Miller",
            ),
            Milestone(
                id="M2",
                description="Phase 2 - Analytics Engine and Dashboard",
                phase_display="Phase 2",
                external_date=date(2026, 12, 18),
                owner="David Miller",
            ),
            Milestone(
                id="M3",
                description="Phase 3 - User Access Matrix & Hardening",
                phase_display="Phase 3",
                external_date=date(2027, 1, 15),
                owner="David Miller",
            ),
            Milestone(
                id="M4",
                description="Phase 4 - Production Live & Handover",
                phase_display="Phase 4",
                external_date=date(2027, 1, 22),
                owner="David Miller",
            ),
        ],
        deliverables=[
            # 18 deliverables for Phase 1 to test overflow handling
            *[
                Deliverable(
                    id=f"DEL-1-{i:02d}",
                    name=f"Phase 1 Data Foundation Module {i:02d}: Schema & Pipeline Component",
                    owner="David Miller",
                )
                for i in range(1, 19)
            ],
            Deliverable(
                id="DEL-2-01",
                name="Phase 2: Analytics & Anomaly Detection Pipeline Service",
                owner="David Miller",
            ),
            Deliverable(
                id="DEL-3-01",
                name="Phase 3: WCAG 2.1 AA Compliant Dashboard UI & Security Matrix",
                owner="David Miller",
            ),
            Deliverable(
                id="DEL-4-01",
                name="Phase 4: Final Handover Documentation and Production Deployment",
                owner="David Miller",
            ),
        ],
        dependencies_assumptions=[
            DependencyAssumptionItem(
                id="DEP-01",
                type="Dependency",
                description="Pilot partner facility security authorization and network routing sign-off",
                category="Dependencies",
                status="Open",
                owner="Client",
            ),
        ],
        raid_items=[
            # Commercial risk: Must be scrubbed
            RiskAssumption(
                id="RSK-01",
                type="Risk",
                description="Fixed-fee milestone payment cap of $139,600 exceeded due to talent overtime",
                category="Commercial",
                probability="High",
                impact="High",
                mitigation_or_response="Weekly financial burn review to manage billable hours",
                due_date=date(2026, 12, 15),
            ),
            # Delivery risk 1 (Multi-sentence mitigation)
            RiskAssumption(
                id="RSK-02",
                type="Risk",
                description="Telemetry ingestion latency exceeding 2-second SLA under peak 25-facility load",
                category="Technical",
                probability="High",
                impact="High",
                mitigation_or_response="Implement asynchronous ingestion queue with Kafka partitioning and pre-aggregated Redis cache layers to ensure sub-second response times across all pilot facilities.",
                due_date=date(2026, 11, 30),
            ),
            # Delivery risk 2 (Multi-sentence mitigation)
            RiskAssumption(
                id="RSK-03",
                type="Risk",
                description="PostgreSQL schema field-level discrepancy across legacy disparate EHR database formats",
                category="Delivery Schedule",
                probability="High",
                impact="Medium",
                mitigation_or_response="Execute automated database migration dry runs and field-level validation checksum scripts prior to final cutover.",
                due_date=date(2026, 12, 10),
            ),
            # Delivery risk 3 (Multi-sentence mitigation)
            RiskAssumption(
                id="RSK-04",
                type="Risk",
                description="Delay in partner security sign-off for mutual TLS VPN endpoints",
                category="Dependencies",
                probability="Medium",
                impact="High",
                mitigation_or_response="Conduct weekly security sync meetings with pilot partner network engineering leads.",
                due_date=date(2026, 11, 15),
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
    """OUT-14.2 / HTL-52: Slide 5 maps project purpose, synthesizes problem statement from delivery objectives, and formats prose success criteria."""
    model = build_slide5_model(rich_client_deck_baseline)

    # Why are we doing this?
    assert model.why_are_we_doing_this == "Modernize customer onboarding pipeline with event-driven cloud microservices."

    # What problem are we solving? (deterministic synthesis from delivery objectives, without constraint splicing)
    assert "Addressing operational bottlenecks and technical limitations" in model.what_problem_are_we_solving
    assert "deploying microservices architecture on AWS" in model.what_problem_are_we_solving
    assert "integrating real-time identity verification" in model.what_problem_are_we_solving
    assert "specifically resolving" not in model.what_problem_are_we_solving

    # What does success look like? (narrative prose, not bullet list)
    assert model.what_does_success_look_like.startswith("Success is defined across key project milestones:")
    assert "reduce onboarding processing latency" in model.what_does_success_look_like
    assert "99.95% service uptime" in model.what_does_success_look_like
    assert "•" not in model.what_does_success_look_like
    assert "\n" not in model.what_does_success_look_like


def test_format_success_criteria_prose_variations():
    """OUT-14.2 / HTL-50: format_success_criteria_prose correctly formats 0, 1, 2, and 3+ criteria with zero-fabrication fallback."""
    # 0 criteria -> explicit system placeholder
    assert format_success_criteria_prose([]) == "[To be confirmed in Project Success Agreement]"

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
    """OUT-14.2 / HTL-52: synthesize_problem_statement hierarchically falls back through objectives, scope, purpose, and placeholder."""
    # 1. Primary: delivery_objectives
    b_objs = StartupKitBaseline(
        project_name="Objectives Project",
        charter=ProjectStartupCharter(
            delivery_objectives=["Deploy scalable microservices", "Integrate data pipelines"],
            project_purpose="Build platform",
        ),
    )
    s_objs = synthesize_problem_statement(b_objs)
    assert s_objs == "Addressing operational bottlenecks and technical limitations by deploying scalable microservices, and integrating data pipelines."

    # 2. Secondary: high_level_scope
    b_scope = StartupKitBaseline(
        project_name="Scope Project",
        charter=ProjectStartupCharter(
            high_level_scope=["Cloud migration and security matrix"],
            project_purpose="Build platform",
        ),
    )
    s_scope = synthesize_problem_statement(b_scope)
    assert s_scope == "Addressing operational bottlenecks and architectural limitations across key solution domains: Cloud migration and security matrix."

    # 3. Tertiary: project_purpose
    b_purp = StartupKitBaseline(
        project_name="Purpose Project",
        charter=ProjectStartupCharter(project_purpose="Migrate existing databases to cloud."),
    )
    s_purp = synthesize_problem_statement(b_purp)
    assert s_purp == "Resolving existing manual bottlenecks and operational constraints to enable: migrate existing databases to cloud."

    # 4. Fallback: Minimal / scrubbed project
    b_min = StartupKitBaseline(project_name="Minimal Project")
    s_min = synthesize_problem_statement(b_min)
    assert s_min == "[To be confirmed in Project Success Agreement]"


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

    # Verify deliverable boxes have native bullet formatting on every paragraph with text
    deliv_shapes = [s for s in slide6.shapes if s.shape_id in (205, 206, 208, 210)]
    for ds in deliv_shapes:
        if ds.has_text_frame and ds.text_frame.text.strip():
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

    # Verify first workstream has all deliverables in model
    ws1 = model.slide6.workstreams[0]
    assert len(ws1.deliverables) == 5

    saved_path = write_client_deck(model, out_file)
    prs = pptx.Presentation(str(saved_path))
    slide6 = prs.slides[5]

    all_text = "\n".join(s.text_frame.text for s in slide6.shapes if s.has_text_frame)
    assert "Phase 1: Discovery" in all_text
    assert "Phase 6: Multi-Region Deployment" in all_text
    assert "more:" in all_text
    assert "(see Project Delivery Workbook · Project Schedule)" in all_text

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
    """OUT-14.4 / HTL-50: When baseline has only commercial risks, Slide 12 uses zero-fabrication fallback and table shrinks to 1 row."""
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
    assert len(model.risks) == 1
    assert model.risks[0].description == "[No non-commercial risks identified at kickoff · See RAID Log]"

    full_model = build_client_deck_model(baseline)
    out_file = tmp_path / "slide12_empty.pptx"
    saved_path = write_client_deck(full_model, out_file)
    prs = pptx.Presentation(str(saved_path))
    slide12 = prs.slides[11]

    tbl = next(s.table for s in slide12.shapes if s.has_table)
    assert len(tbl.rows) == 2  # Header + 1 explicit placeholder row
    assert "[No non-commercial risks identified at kickoff · See RAID Log]" in tbl.rows[1].cells[0].text


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


# =========================================================================
# 9. HTL-48: Real Realistic Benchmark & Dynamic Text-Fitting Tests
# =========================================================================

def test_htl_48_real_failing_baseline_problem_statement_scoped(sample_real_failing_client_baseline):
    """HTL-48 / HTL-52: Problem statement derives from delivery objectives without constraint splicing."""
    problem_stmt = synthesize_problem_statement(sample_real_failing_client_baseline)

    # Must exclude raw commercial figures and payment terms
    assert "$139,600" not in problem_stmt
    assert "$26,800" not in problem_stmt
    assert "prepayment" not in problem_stmt.lower()
    assert "change order" not in problem_stmt.lower()
    assert "fixed-fee" not in problem_stmt.lower()

    # Must exclude scheduling/logistics constraints (specifically resolving: ...)
    assert "specifically resolving" not in problem_stmt
    assert "Estimated schedule runs" not in problem_stmt
    assert "Oct 19, 2026" not in problem_stmt

    # Must be grounded in delivery objectives
    assert "operational bottlenecks and technical limitations" in problem_stmt
    assert "deploying scalable multi-facility data pipeline and ingestion microservices" in problem_stmt
    assert "integrating real-time anomaly detection and predictive infrastructure analytics" in problem_stmt


def test_htl_48_real_failing_baseline_slide5_fit(sample_real_failing_client_baseline, tmp_path):
    """HTL-48 / HTL-52: Slide 5 cards dynamically scale font sizes uniformly and top-anchor to fit long real SOW text."""
    out_file = tmp_path / "htl48_slide5.pptx"
    model = build_client_deck_model(sample_real_failing_client_baseline)
    write_client_deck(model, out_file)

    prs = pptx.Presentation(str(out_file))
    slide5 = prs.slides[4]

    # Find the 3 cards
    shapes = [s for s in slide5.shapes if s.has_text_frame]

    # Card 1 (Why are we doing this?)
    card1 = next(s for s in shapes if "Move the client" in s.text_frame.text or s.shape_id == 176)
    assert card1.text_frame.margin_top == 0
    p1 = card1.text_frame.paragraphs[0]

    # Card 2 (Problem Statement)
    card2 = next(s for s in shapes if "operational bottlenecks" in s.text_frame.text or s.shape_id == 180)
    assert card2.text_frame.margin_top == 0
    p2 = card2.text_frame.paragraphs[0]

    # Card 3 (Success Criteria - 5 item prose)
    card3 = next(s for s in shapes if "Success is defined across key project milestones" in s.text_frame.text or s.shape_id == 184)
    assert card3.text_frame.margin_top == 0
    p3 = card3.text_frame.paragraphs[0]
    assert "all four milestones accepted within five business days" in card3.text_frame.text
    assert "production live and handover complete" in card3.text_frame.text

    # HTL-52: All three cards must share identical uniform font size
    sz1 = p1.runs[0].font.size.pt
    sz2 = p2.runs[0].font.size.pt
    sz3 = p3.runs[0].font.size.pt
    assert sz1 == sz2 == sz3
    assert sz1 <= 10.5


def test_htl_48_real_failing_baseline_slide6_fit(sample_real_failing_client_baseline, tmp_path):
    """HTL-48 / HTL-50 / HTL-52: Slide 6 dynamically scales deliverable font size, handles 18 deliverables overflow, and maintains Out of Scope bottom margin."""
    out_file = tmp_path / "htl48_slide6.pptx"
    model = build_client_deck_model(sample_real_failing_client_baseline)
    write_client_deck(model, out_file)

    prs = pptx.Presentation(str(out_file))
    slide6 = prs.slides[5]

    all_s6_text = "\n".join(s.text_frame.text for s in slide6.shapes if s.has_text_frame)

    # Phase 1 with 18 deliverables rendered with explicit-ID overflow
    assert "Phase 1 - Data and Backend Foundation" in all_s6_text
    assert "more:" in all_s6_text
    assert "(see Project Delivery Workbook · Project Schedule)" in all_s6_text
    assert "Phase 4 - Production Live & Handover" in all_s6_text

    # HTL-52: Out of Scope shape (shape 202) maintains visible bottom margin (top + height <= 4,700,000 EMUs)
    oos_shape = next(s for s in slide6.shapes if s.shape_id == 202 or (s.has_text_frame and "Out of Scope:" in s.text_frame.text))
    assert oos_shape.top + oos_shape.height <= 4700000


def test_htl_48_real_failing_baseline_slide12_fit(sample_real_failing_client_baseline, tmp_path):
    """HTL-48 / HTL-52: Slide 12 scales table cell font sizes uniformly per column and bounds multi-sentence risk mitigations."""
    out_file = tmp_path / "htl48_slide12.pptx"
    model = build_client_deck_model(sample_real_failing_client_baseline)
    write_client_deck(model, out_file)

    prs = pptx.Presentation(str(out_file))
    slide12 = prs.slides[11]
    tbl = next(s.table for s in slide12.shapes if s.has_table)

    # 4 rows: 1 header + 3 data rows
    assert len(tbl.rows) == 4

    # Commercial risk RSK-01 must be excluded
    all_text = " ".join(c.text for r in tbl.rows for c in r.cells)
    assert "$139,600" not in all_text
    assert "RSK-01" not in all_text

    # Delivery risks RSK-02, RSK-03, RSK-04 present
    assert "RSK-02" in all_text
    assert "RSK-03" in all_text
    assert "RSK-04" in all_text

    # HTL-52: Col 0 (Description) and Col 2 (Mitigation) must share uniform font size across all rows
    desc_sizes = [tbl.rows[r_idx].cells[0].text_frame.paragraphs[0].runs[0].font.size.pt for r_idx in range(1, 4)]
    mitigation_sizes = [tbl.rows[r_idx].cells[2].text_frame.paragraphs[0].runs[0].font.size.pt for r_idx in range(1, 4)]

    assert desc_sizes[0] == desc_sizes[1] == desc_sizes[2]
    assert mitigation_sizes[0] == mitigation_sizes[1] == mitigation_sizes[2]
    assert mitigation_sizes[0] <= 10.0


def test_htl_48_real_failing_baseline_slide15_fit(sample_real_failing_client_baseline, tmp_path):
    """HTL-48: Slide 15 scales table cells for realistic-length customer obligations and next steps."""
    out_file = tmp_path / "htl48_slide15.pptx"
    model = build_client_deck_model(sample_real_failing_client_baseline)
    write_client_deck(model, out_file)

    prs = pptx.Presentation(str(out_file))
    slide15 = prs.slides[14]
    tbl = next(s.table for s in slide15.shapes if s.has_table)

    assert len(tbl.rows) >= 3
    # Check Due column is strictly TBD
    for r_idx in range(1, len(tbl.rows)):
        assert tbl.rows[r_idx].cells[2].text.strip() == "TBD"
        cell_p = tbl.rows[r_idx].cells[1].text_frame.paragraphs[0]
        assert cell_p.runs[0].font.size.pt <= 10.0


def test_htl_48_end_to_end_real_failing_deck_generation(sample_real_failing_client_baseline, tmp_path):
    """HTL-48: Full end-to-end export of real failing baseline passes all validation audits."""
    out_dir = tmp_path / "htl48_export"
    res = export_client_deck(sample_real_failing_client_baseline, out_dir)

    assert res.file_path.exists()
    assert res.manifest_path.exists()
    assert res.slides_count == 16
    assert res.trace_entries_count > 0

    # Traceability and boilerplate preservation checks
    findings = check_client_deck_traceability(sample_real_failing_client_baseline, res.file_path, res.manifest_path)
    assert len(findings) == 0


# =========================================================================
# 9. HTL-49: Slide 1 Deterministic Text-Fitting & normAutofit Removal Tests
# =========================================================================

def test_htl_49_slide1_long_names_deterministic_fit(tmp_path):
    """HTL-49: Slide 1 strips native normAutofit, applies deterministic font scaling, and prevents subtitle overlap."""
    baseline = StartupKitBaseline(
        project_name="Pilot-Ready Product Implementation",
        charter=ProjectStartupCharter(
            client_name="AI Infrastructure Dashboard Client",
            project_purpose="Move the client's dashboard from MVP to pilot-ready product.",
        ),
    )
    out_file = tmp_path / "htl49_slide1_long.pptx"
    model = build_client_deck_model(baseline)
    write_client_deck(model, out_file)

    prs = pptx.Presentation(str(out_file))
    slide1 = prs.slides[0]

    title_shape = next(s for s in slide1.shapes if s.shape_id == 92 or (s.has_text_frame and "Kickoff" in s.text_frame.text))
    body_pr = title_shape._element.xpath(".//a:bodyPr")[0]

    # Native normAutofit must be stripped and replaced with noAutofit
    assert len(body_pr.xpath("./a:normAutofit")) == 0
    assert len(body_pr.xpath("./a:noAutofit")) == 1
    assert body_pr.get("anchor") == "t"

    # Runs must have explicit font sizing and styling
    for p in title_shape.text_frame.paragraphs:
        for r in p.runs:
            assert r.font.name == "Proxima Nova"
            assert r.font.size is not None
            # Font stepped down to fit available 1.42 in vertical clearance
            assert r.font.size.pt <= 22.0
            assert r.font.size.pt >= 14.0

    # Subtitle shape (Shape 1, ID 93) must remain intact and positioned below title area
    sub_shape = next(s for s in slide1.shapes if s.shape_id == 93 or (s.has_text_frame and "Aligning on outcomes" in s.text_frame.text))
    assert sub_shape.top >= title_shape.top + title_shape.height


def test_htl_49_slide1_short_names_fit(rich_client_deck_baseline, tmp_path):
    """HTL-49: Short client and project names scale appropriately without native normAutofit."""
    out_file = tmp_path / "htl49_slide1_short.pptx"
    model = build_client_deck_model(rich_client_deck_baseline)
    write_client_deck(model, out_file)

    prs = pptx.Presentation(str(out_file))
    slide1 = prs.slides[0]

    title_shape = next(s for s in slide1.shapes if s.shape_id == 92 or (s.has_text_frame and "Kickoff" in s.text_frame.text))
    body_pr = title_shape._element.xpath(".//a:bodyPr")[0]

    assert len(body_pr.xpath("./a:normAutofit")) == 0
    assert len(body_pr.xpath("./a:noAutofit")) == 1
    for p in title_shape.text_frame.paragraphs:
        for r in p.runs:
            assert r.font.size is not None
            assert r.font.size.pt >= 18.0


# =========================================================================
# 10. HTL-49: Architectural Unification & Cross-Artifact Consistency Tests
# =========================================================================

def test_htl_49_cross_artifact_consistency_arc_baseline(tmp_path):
    """HTL-49: Verifies exact deliverable and metadata consistency between Onboarding Deck and Client Kickoff Deck on ARC baseline."""
    from tests.deck_bundle import load_baseline
    from src.generators.kit_values import kit_header_values
    from src.generators.pmo_workbook.builder import build_workbook_model

    baseline = load_baseline()
    headers = kit_header_values(baseline)

    # 1. Slide 1 identity matches kit_header_values exactly
    client_deck = build_client_deck_model(baseline)
    assert client_deck.slide1.client_name == headers["client_sponsor"]
    assert client_deck.slide1.client_name == "Syngenta"
    assert client_deck.slide1.project_name == headers["project_name"]
    assert client_deck.slide1.project_name == "ARC Genomics Platform"

    # 2. Slide 6 deliverables match Onboarding Deck Slide 3 and Workbook schedule rows exactly
    wb = build_workbook_model(baseline)
    level2_milestones = [r for r in wb.schedule_rows if r.row_type == "Milestone"]
    assert len(client_deck.slide6.workstreams) == len(level2_milestones)

    for idx, r in enumerate(level2_milestones):
        ws = client_deck.slide6.workstreams[idx]
        assert ws.title == r.name
        linked_ids = [x.strip() for x in (r.linked_deliverables or "").split(",") if x.strip()]
        assert len(ws.deliverables) == len(linked_ids)
        for d_idx, did in enumerate(linked_ids):
            assert ws.deliverables[d_idx].startswith(did)

    out_file = tmp_path / "arc_kickoff_deck.pptx"
    write_client_deck(client_deck, out_file)
    prs = pptx.Presentation(str(out_file))
    slide6 = prs.slides[5]
    deliv_shapes = [s for s in slide6.shapes if s.shape_id in (205, 206, 208, 210)]
    deliv_shapes.sort(key=lambda s: s.top)
    # HTL-50: Rendered deliverables show fitted items + Slide 3 explicit-ID overflow lines
    assert len(deliv_shapes[0].text_frame.paragraphs) >= 2
    assert "more:" in deliv_shapes[0].text_frame.paragraphs[-1].text
    assert "(see Project Delivery Workbook · Project Schedule)" in deliv_shapes[0].text_frame.paragraphs[-1].text
    assert "DEL-03" in deliv_shapes[0].text_frame.paragraphs[-1].text

    assert len(deliv_shapes[1].text_frame.paragraphs) >= 2
    assert "more:" in deliv_shapes[1].text_frame.paragraphs[-1].text
    assert "DEL-08" in deliv_shapes[1].text_frame.paragraphs[-1].text

    # Row 3 (P2b Application Surface): All 4 deliverables fit with zero overflow
    assert len(deliv_shapes[2].text_frame.paragraphs) == 4
    assert not any("more:" in p.text for p in deliv_shapes[2].text_frame.paragraphs)
    assert "DEL-11" in deliv_shapes[2].text_frame.paragraphs[0].text
    assert "DEL-14" in deliv_shapes[2].text_frame.paragraphs[3].text

    assert len(deliv_shapes[3].text_frame.paragraphs) >= 2
    assert "more:" in deliv_shapes[3].text_frame.paragraphs[-1].text
    assert "DEL-18" in deliv_shapes[3].text_frame.paragraphs[-1].text


def test_htl_49_cross_artifact_consistency_failing_sow_baseline(sample_real_failing_client_baseline, tmp_path):
    """HTL-49: Verifies Slide 1 and Slide 6 consistency on realistic failing SOW baseline (no fabrication or cross-contamination)."""
    from src.generators.kit_values import kit_header_values
    from src.generators.pmo_workbook.builder import build_workbook_model

    baseline = sample_real_failing_client_baseline
    headers = kit_header_values(baseline)

    # 1. Slide 1 identity
    client_deck = build_client_deck_model(baseline)
    assert client_deck.slide1.client_name == headers["client_sponsor"]
    assert client_deck.slide1.client_name == "HealthTech AI Solutions"
    assert client_deck.slide1.project_name == headers["project_name"]
    assert client_deck.slide1.project_name == "AI Infrastructure Intelligence Dashboard"

    # 2. Slide 6 deliverables
    wb = build_workbook_model(baseline)
    level2_milestones = [r for r in wb.schedule_rows if r.row_type == "Milestone"]
    assert len(client_deck.slide6.workstreams) == len(level2_milestones)

    # Check Phase 1 (18 deliverables in model, rendered with overflow)
    ws1 = client_deck.slide6.workstreams[0]
    assert ws1.title == "Phase 1 - Data and Backend Foundation"
    assert len(ws1.deliverables) == 18
    assert ws1.deliverables[0].startswith("DEL-1-01")
    assert ws1.deliverables[1].startswith("DEL-1-02")

    # Check Phase 2 (contains only linked deliverables, no fabricated text)
    ws2 = client_deck.slide6.workstreams[1]
    assert ws2.title == "Phase 2 - Analytics Engine and Dashboard"
    assert len(ws2.deliverables) == 1
    assert ws2.deliverables[0].startswith("DEL-2-01")
    for d_text in ws2.deliverables:
        assert not d_text.startswith("Milestone completion:")

    # Check Phase 3 (contains only linked deliverables, no fabricated text)
    ws3 = client_deck.slide6.workstreams[2]
    assert ws3.title == "Phase 3 - User Access Matrix & Hardening"
    assert len(ws3.deliverables) == 1
    assert ws3.deliverables[0].startswith("DEL-3-01")
    for d_text in ws3.deliverables:
        assert not d_text.startswith("Milestone completion:")

    # Check Phase 4 (contains only linked deliverables, no fabricated text)
    ws4 = client_deck.slide6.workstreams[3]
    assert ws4.title == "Phase 4 - Production Live & Handover"
    assert len(ws4.deliverables) == 1
    assert ws4.deliverables[0].startswith("DEL-4-01")

    # Verify rendered presentation
    out_file = tmp_path / "failing_kickoff_deck.pptx"
    write_client_deck(client_deck, out_file)
    prs = pptx.Presentation(str(out_file))
    slide6 = prs.slides[5]
    deliv_shapes = [s for s in slide6.shapes if s.shape_id in (205, 206, 208, 210)]
    deliv_shapes.sort(key=lambda s: s.top)

    # Row 1 (18 items) renders fitted deliverables + explicit-ID overflow summary line
    assert len(deliv_shapes[0].text_frame.paragraphs) >= 1
    assert "more:" in deliv_shapes[0].text_frame.paragraphs[-1].text
    assert "(see Project Delivery Workbook · Project Schedule)" in deliv_shapes[0].text_frame.paragraphs[-1].text

    # Rows 2, 3, 4 render 1 deliverable each with NO overflow summary line
    for row_idx in (1, 2, 3):
        assert len(deliv_shapes[row_idx].text_frame.paragraphs) == 1
        assert not any("additional deliverables" in p.text for p in deliv_shapes[row_idx].text_frame.paragraphs)


def test_htl_49_slide6_column_font_uniformity(sample_real_failing_client_baseline, tmp_path):
    """HTL-49: Verifies that all deliverable boxes in the Outcomes/Deliverables column share the exact same font size."""
    from tests.deck_bundle import load_baseline

    for name, bl in [("ARC", load_baseline()), ("Failing", sample_real_failing_client_baseline)]:
        out_file = tmp_path / f"uniform_font_{name}.pptx"
        model = build_client_deck_model(bl)
        write_client_deck(model, out_file)

        prs = pptx.Presentation(str(out_file))
        slide6 = prs.slides[5]

        # Collect font sizes of all deliverable runs in column 2 (Outcomes / Deliverables)
        deliv_runs_font_sizes = []
        for shape in slide6.shapes:
            # Deliverable shapes have left coordinate around 2,726,700 EMUs (~2.98 in)
            if shape.has_text_frame and shape.left > 2500000 and shape.left < 5800000:
                tf = shape.text_frame
                # Exclude column header shape "Outcomes / Deliverables"
                if tf.text.strip() and "Outcomes / Deliverables" not in tf.text:
                    for p in tf.paragraphs:
                        for r in p.runs:
                            if r.font and r.font.size:
                                deliv_runs_font_sizes.append(r.font.size.pt)

        assert len(deliv_runs_font_sizes) > 0
        # All deliverable runs across all rows must have identical font size
        unique_sizes = set(deliv_runs_font_sizes)
        assert len(unique_sizes) == 1, f"Found inconsistent font sizes in Deliverables column: {unique_sizes}"


def test_slide6_right_column_left_alignment(tmp_path):
    """Slide 6: Shape 193 ('Solution Overview'), Shape 194 (body), and Shape 202 ('Out of Scope:') share exact same left coordinate."""
    from tests.deck_bundle import load_baseline
    baseline = load_baseline()
    out_file = tmp_path / "align_test.pptx"
    model = build_client_deck_model(baseline)
    write_client_deck(model, out_file)

    prs = pptx.Presentation(str(out_file))
    slide6 = prs.slides[5]

    s193 = next(s for s in slide6.shapes if s.shape_id == 193 or (s.has_text_frame and "Solution Overview" in s.text_frame.text))
    s194 = next(s for s in slide6.shapes if s.shape_id == 194 or (s.has_text_frame and "P1 Foundation" in s.text_frame.text or "Comprehensive" in s.text_frame.text))
    s202 = next(s for s in slide6.shapes if s.shape_id == 202 or (s.has_text_frame and "Out of Scope:" in s.text_frame.text))

    assert s193.left == 6347125
    assert s194.left == 6347125
    assert s202.left == 6347125
    assert s193.width == 2600000
    assert s194.width == 2600000
    assert s202.width == 2600000


def test_slide6_dynamic_deliverable_row_filling_algorithm():
    """Slide 6: fit_deliverables_for_block dynamically tests and displays maximum fitting deliverables."""
    from src.generators.client_deck.fit import fit_deliverables_for_block

    delivs = [f"DEL-{i:02d} System Component Architecture Deliverable Specification {i}" for i in range(1, 10)]

    # 1. When all deliverables fit within height, returns all items with 0 overflow
    items_all, ovf_all = fit_deliverables_for_block(delivs[:4], width_in=3.0, max_height_in=1.55, font_size_pt=10.0)
    assert ovf_all == 0
    assert len(items_all) == 4
    assert not any("more:" in it for it in items_all)

    # 2. When only subset fits, returns max k items + explicit-ID summary line
    items_sub, ovf_sub = fit_deliverables_for_block(delivs, width_in=3.0, max_height_in=0.78, font_size_pt=7.5)
    assert ovf_sub > 0
    assert len(items_sub) == len(delivs) - ovf_sub + 1
    assert "more:" in items_sub[-1]
    assert "(see Project Delivery Workbook · Project Schedule)" in items_sub[-1]
    assert "DEL-" in items_sub[-1]

    # 3. Single deliverable fits cleanly with 0 overflow
    items_one, ovf_one = fit_deliverables_for_block(delivs[:1], width_in=3.0, max_height_in=0.50, font_size_pt=9.5)
    assert ovf_one == 0
    assert items_one == [delivs[0]]


# =========================================================================
# 11. HTL-50: Explicit-ID Overflow & Deck-Wide Financial Scrubbing Tests
# =========================================================================

def test_htl_50_slide6_deliverables_overflow_explicit_ids(sample_real_failing_client_baseline, tmp_path):
    """HTL-50: Slide 6 Phase 1 (18 deliverables) shows full items plus Slide 3 explicit-ID overflow."""
    out_file = tmp_path / "htl50_slide6_overflow.pptx"
    model = build_client_deck_model(sample_real_failing_client_baseline)
    write_client_deck(model, out_file)

    prs = pptx.Presentation(str(out_file))
    slide6 = prs.slides[5]
    deliv_shapes = [s for s in slide6.shapes if s.shape_id in (205, 206, 208, 210)]
    deliv_shapes.sort(key=lambda s: s.top)

    p_texts = [p.text for p in deliv_shapes[0].text_frame.paragraphs]
    summary_p = p_texts[-1]

    # Must NOT contain the old generic "+N additional deliverables" text
    assert "+ 16 additional deliverables" not in summary_p
    assert "additional deliverables" not in summary_p

    # Must contain Slide 3's real explicit-ID format listing omitted IDs
    assert summary_p.startswith("+")
    assert "more:" in summary_p
    assert "DEL-1-" in summary_p
    assert "(see Project Delivery Workbook · Project Schedule)" in summary_p


def test_htl_50_financial_data_scrubbing_across_all_fields(tmp_path):
    """HTL-50: Verifies NO dollar figures, rates, or commercial terms appear anywhere in generated deck."""
    financial_baseline = StartupKitBaseline(
        project_name="Financial Scrubbing Validation Platform",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 11, 1),
        charter=ProjectStartupCharter(
            client_name="Global Financial Scrubbing Corp",
            project_purpose="Deploy cloud core platform under $250,000 fixed-bid agreement with monthly invoicing.",
            delivery_manager="Jane Doe",
            pmo_lead="Sarah Connor",
            talent_pm="Alex Rivera",
            delivery_objectives=[
                "Deploy microservices architecture on AWS",
                "Comply with budget cap of $500,000",
            ],
            success_criteria=[
                "Timely payment of $50,000 milestone invoice upon UAT signoff",
                "No budget overrun beyond agreed fee ceiling",
                "Reduce onboarding processing latency from 48 hours to under 15 minutes",
            ],
            high_level_scope=[
                "Phase 1 implementation capped at $100k contract value",
                "Core microservices development and API orchestration",
                "Database schema migration from legacy Oracle to PostgreSQL",
            ],
            exclusions=[
                "Work billed under change orders exceeding $150/hr",
                "Travel expenses over $1,000",
                "Legacy mainframe decommissioning and hardware salvage",
            ],
        ),
        sow_interpretation=SOWInterpretationSummary(
            contracted_deliverables=["Core API Gateway", "Authentication Service", "Initial Invoice & Payment Sign-off"],
            out_of_scope_items=["Hardware procurement exceeding $5,000", "On-premise network reconfiguration"],
            customer_obligations=[
                "Process milestone invoices within 30 days of receipt",
                "Provide AWS IAM root access and staging credentials within 3 business days",
            ],
            constraints=[
                "Billing rate must not exceed $185/hr for cloud architects",
                "Must comply with European GDPR data residency constraints",
            ],
            dependencies=["Single Sign-On federation with Okta directory"],
            ambiguity_notes=[
                "Clarify invoice payment timing for milestone fee releases",
                "Clarify staging environment provisioning timeline",
            ],
        ),
        milestones=[
            Milestone(id="M1", description="Phase 1 - $50k Deposit Gate", external_date=date(2026, 12, 1), owner="Jane Doe"),
            Milestone(id="M2", description="Phase 2 - Core Services Build", external_date=date(2027, 1, 15), owner="Jane Doe"),
        ],
        deliverables=[
            Deliverable(id="DEL-01", name="DEL-01 Initial Invoice & Deposit Milestone Signoff", owner="Jane Doe"),
            Deliverable(id="DEL-02", name="DEL-02 API Gateway & Auth Service Implementation", owner="Jane Doe"),
            Deliverable(id="DEL-03", name="DEL-03 Automated Integration & Regression Test Suite", owner="Jane Doe"),
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
                id="ASM-02",
                type="Dependency",
                description="Production AWS environment provisioned and configured by Client DevOps team",
                category="Technical",
                status="Active",
            ),
        ],
        raid_items=[
            RiskAssumption(
                id="RSK-01",
                type="Risk",
                category="Commercial",
                probability="High",
                impact="High",
                description="Potential engagement spend budget overrun exceeding $350,000 due to legacy scope changes",
                mitigation_or_response="Implement formal change order approval gate and enforce fixed-fee ceiling",
                due_date=date(2026, 11, 10),
            ),
            RiskAssumption(
                id="RSK-02",
                type="Risk",
                category="Technical",
                probability="High",
                impact="High",
                description="Legacy database schema lacks foreign key constraints causing data ingestion errors",
                mitigation_or_response="Implement automated schema validation pre-migration script with rollback plan",
                due_date=date(2026, 11, 10),
            ),
        ],
    )

    out_file = tmp_path / "financial_scrubbed_deck.pptx"
    model = build_client_deck_model(financial_baseline)
    write_client_deck(model, out_file)

    prs = pptx.Presentation(str(out_file))

    # Audit all text across Slides 1, 5, 6, 12, 15
    prohibited_terms = [
        "$", "250,000", "50,000", "100k", "150/hr", "185/hr", "175/hr", "350,000", "1,000", "5,000",
        "fixed-bid", "fixed-fee", "fixed fee", "fixed bid", "billing rate", "hourly rate", "blended rate",
        "profit margin", "margin erosion", "fee ceiling", "fee cap", "budget overrun", "budget cap",
        "contract value", "change order", "travel expenses", "invoice", "invoicing", "invoices",
        "Deposit Gate", "Payment Sign-off",
    ]

    for slide_idx in (0, 4, 5, 11, 14):
        slide = prs.slides[slide_idx]
        slide_text_blocks = []
        for s in slide.shapes:
            if s.has_text_frame:
                slide_text_blocks.append(s.text_frame.text)
            if s.has_table:
                for row in s.table.rows:
                    slide_text_blocks.extend(c.text for c in row.cells)

        combined_slide_text = " ".join(slide_text_blocks)
        for term in prohibited_terms:
            assert term.lower() not in combined_slide_text.lower(), (
                f"Prohibited financial/commercial term '{term}' found on Slide {slide_idx+1}:\n{combined_slide_text}"
            )


def test_htl_50_zero_fabrication_placeholders_and_table_resizing(tmp_path):
    """HTL-50: Explicit system placeholders appear when categories are scrubbed and tables shrink."""
    all_commercial_baseline = StartupKitBaseline(
        project_name="All Commercial Baseline",
        charter=ProjectStartupCharter(
            client_name="Test Sponsor",
            project_purpose="Fixed-fee delivery under $100,000 contract value.",
            delivery_manager="Jane Doe",
            talent_pm="Alex Rivera",
            pmo_lead="Sarah Connor",
            success_criteria=[
                "Payment of $50,000 milestone invoice",
                "Billing under $150/hr rate cap",
            ],
            exclusions=[
                "Hourly rate billing over $200/hr",
                "Travel expenses over $500",
            ],
        ),
        sow_interpretation=SOWInterpretationSummary(
            customer_obligations=["Process $100,000 invoice within 10 days"],
            ambiguity_notes=["Clarify payment schedule for change orders"],
        ),
        raid_items=[
            RiskAssumption(
                id="RSK-C1",
                type="Risk",
                category="Commercial",
                description="Margin erosion exceeding $20,000",
                mitigation_or_response="Enforce change order hourly rates",
            )
        ],
    )

    model = build_client_deck_model(all_commercial_baseline)

    # 1. Slide 5 Success Criteria placeholder
    assert model.slide5.what_does_success_look_like == "[To be confirmed in Project Success Agreement]"

    # 2. Slide 6 Out of Scope placeholder
    assert model.slide6.out_of_scope == ["None explicitly identified in SOW exclusions."]

    # 3. Slide 12 Risks placeholder
    assert len(model.slide12.risks) == 1
    assert model.slide12.risks[0].description == "[No non-commercial risks identified at kickoff · See RAID Log]"

    # 4. Slide 15 Next Steps placeholder
    assert len(model.slide15.next_steps) == 1
    assert model.slide15.next_steps[0].action == "[None identified in SOW · Open items tracked in Project Delivery Workbook]"

    # Verify rendered presentation table row shrinking
    out_file = tmp_path / "placeholders_and_tables.pptx"
    write_client_deck(model, out_file)
    prs = pptx.Presentation(str(out_file))

    # Slide 12: Header + 1 placeholder row = exactly 2 rows
    slide12 = prs.slides[11]
    tbl12 = next(s.table for s in slide12.shapes if s.has_table)
    assert len(tbl12.rows) == 2
    assert "[No non-commercial risks identified at kickoff · See RAID Log]" in tbl12.rows[1].cells[0].text

    # Slide 15: Header + 1 placeholder row = exactly 2 rows
    slide15 = prs.slides[14]
    tbl15 = next(s.table for s in slide15.shapes if s.has_table)
    assert len(tbl15.rows) == 2
    assert "[None identified in SOW · Open items tracked in Project Delivery Workbook]" in tbl15.rows[1].cells[1].text


def test_htl_50_slide6_all_commercial_deliverables_zero_fabrication_placeholder(tmp_path):
    """HTL-50: When all linked deliverables in a workstream are commercial, render explicit system placeholder without invented labels."""
    commercial_deliv_baseline = StartupKitBaseline(
        project_name="Commercial Deliverables Baseline",
        charter=ProjectStartupCharter(
            client_name="Test Client",
            project_purpose="Deliver core platform components",
            delivery_manager="Jane Doe",
            talent_pm="Alex Rivera",
            pmo_lead="Sarah Connor",
        ),
        milestones=[
            Milestone(id="M1", description="Phase 1 - Initial Invoicing & Deposit Gate", external_date=date(2026, 12, 1), owner="Jane Doe"),
            Milestone(id="M2", description="Phase 2 - Core Platform Build", external_date=date(2027, 1, 15), owner="Jane Doe"),
        ],
        deliverables=[
            Deliverable(id="D-01", name="D-01 Initial Invoice & $50,000 Deposit Signoff", owner="Jane Doe"),
            Deliverable(id="D-02", name="D-02 Hourly Rate & Profit Margin Billing Approval", owner="Jane Doe"),
            Deliverable(id="D-03", name="D-03 Data Pipeline & Ingestion Microservices", owner="Jane Doe"),
        ],
    )

    model = build_client_deck_model(commercial_deliv_baseline)

    # Workstream 1 (M1) had D-01 and D-02 (both commercial) -> must show explicit placeholder
    ws1 = model.slide6.workstreams[0]
    assert len(ws1.deliverables) == 1
    assert ws1.deliverables[0] == "[No non-commercial deliverables identified for this phase · See Project Delivery Workbook]"
    assert "Delivery Item" not in ws1.deliverables[0]

    # Workstream 2 (M2) has D-03 (non-commercial) -> shows actual deliverable
    ws2 = model.slide6.workstreams[1]
    assert len(ws2.deliverables) == 1
    assert "D-03 Data Pipeline & Ingestion Microservices" in ws2.deliverables[0]

    # Verify rendered presentation Slide 6 shapes
    out_file = tmp_path / "commercial_delivs_slide6.pptx"
    write_client_deck(model, out_file)
    prs = pptx.Presentation(str(out_file))
    slide6 = prs.slides[5]

    deliv_shapes = [s for s in slide6.shapes if s.shape_id in (205, 206, 208, 210)]
    deliv_shapes.sort(key=lambda s: s.top)

    ws1_text = deliv_shapes[0].text_frame.text
    assert "[No non-commercial deliverables identified for this phase · See Project Delivery Workbook]" in ws1_text
    assert "Delivery Item" not in ws1_text
    assert "$50,000" not in ws1_text
    assert "Invoice" not in ws1_text


# =========================================================================
# HTL-52: Four Confirmed Client Kickoff Deck Findings Tests
# =========================================================================

def test_htl_52_four_findings_verification(sample_real_failing_client_baseline, tmp_path):
    """HTL-52: Comprehensive test validating all four findings:
    1. Problem statement derived from delivery_objectives without constraint splicing and distinct from Card 1.
    2. Slide 5 uniform font sizing across all three cards.
    3. Slide 6 Out of Scope bottom margin >= 0.20 in clearance.
    4. Slide 12 Risk table uniform column font sizing across all rows.
    """
    out_file = tmp_path / "htl52_verified_deck.pptx"
    model = build_client_deck_model(sample_real_failing_client_baseline)
    write_client_deck(model, out_file)
    prs = pptx.Presentation(str(out_file))

    # 1. Slide 5 Problem Statement Narrative & Non-Duplication
    card1_why = model.slide5.why_are_we_doing_this
    card2_prob = model.slide5.what_problem_are_we_solving
    assert card1_why != card2_prob
    assert "AI Infrastructure Intelligence Dashboard" in card1_why
    assert "deploying scalable multi-facility data pipeline and ingestion microservices" in card2_prob
    assert "integrating real-time anomaly detection and predictive infrastructure analytics" in card2_prob
    assert "specifically resolving" not in card2_prob
    assert "Estimated schedule runs" not in card2_prob
    assert "Oct 19, 2026" not in card2_prob

    # 2. Slide 5 Card Font Size Uniformity
    slide5 = prs.slides[4]
    s5_shapes = [s for s in slide5.shapes if s.has_text_frame]
    c1_shape = next(s for s in s5_shapes if s.shape_id == 176 or "Move the client" in s.text_frame.text)
    c2_shape = next(s for s in s5_shapes if s.shape_id == 180 or "operational bottlenecks" in s.text_frame.text)
    c3_shape = next(s for s in s5_shapes if s.shape_id == 184 or "Success is defined" in s.text_frame.text)

    sz1 = c1_shape.text_frame.paragraphs[0].runs[0].font.size.pt
    sz2 = c2_shape.text_frame.paragraphs[0].runs[0].font.size.pt
    sz3 = c3_shape.text_frame.paragraphs[0].runs[0].font.size.pt
    assert sz1 == sz2 == sz3
    assert sz1 <= 10.5

    # 3. Slide 6 Out of Scope Bottom Margin
    slide6 = prs.slides[5]
    oos_shape = next(s for s in slide6.shapes if s.shape_id == 202 or (s.has_text_frame and "Out of Scope:" in s.text_frame.text))
    assert oos_shape.top + oos_shape.height <= 4700000

    # 4. Slide 12 Risk Table Column Uniformity
    slide12 = prs.slides[11]
    tbl12 = next(s.table for s in slide12.shapes if s.has_table)
    desc_sizes = [tbl12.rows[r_idx].cells[0].text_frame.paragraphs[0].runs[0].font.size.pt for r_idx in range(1, len(tbl12.rows))]
    mit_sizes = [tbl12.rows[r_idx].cells[2].text_frame.paragraphs[0].runs[0].font.size.pt for r_idx in range(1, len(tbl12.rows))]

    assert len(set(desc_sizes)) == 1, f"Expected uniform description font sizes, got {desc_sizes}"
    assert len(set(mit_sizes)) == 1, f"Expected uniform mitigation font sizes, got {mit_sizes}"
