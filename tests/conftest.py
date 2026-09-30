"""Shared pytest fixtures."""

import pytest
from datetime import date
import pymupdf as fitz
from pptx import Presentation
from src.core.models import (
    SourceReference,
    Deliverable,
    Milestone,
    RiskAssumption,
    DependencyAssumptionItem,
    ContractAmbiguityItem,
    WorkPackageSeed,
    CommunicationsPlanItem,
    ProjectStartupCharter,
    CommercialGuardrail,
    ReadinessChecklistItem,
    GateDecision,
    ActionRequiredItem,
    TalentOnboardingRecord,
    GovernanceContext,
    StartupKitBaseline,
)


@pytest.fixture
def minimal_baseline():
    """Minimal baseline with no milestones or deliverables."""
    return StartupKitBaseline(
        project_name="Minimal Test Project",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        charter=ProjectStartupCharter(
            project_name="Minimal Test Project",
            client_name="Acme Corp",
            contract_type="Time and Materials",
            delivery_manager="Jane Doe",
            talent_pm="John Smith",
            pmo_lead="Sarah Connor",
        ),
        milestones=[],
        deliverables=[],
        backlog_seed=[],
        raid_items=[],
    )


@pytest.fixture
def arc_baseline():
    """ARC Genomics Platform fixture built strictly from Appendix A."""
    ref = SourceReference(document_name="ARC_Genomics_SOW.pdf", clause_or_slide="Section 3", confidence_score=0.95)
    
    milestones = [
        Milestone(
            id="M1",
            description="P1 Foundation accepted: micro-frontend shell, Azure AD/MSAL authentication, E2E test harness, and Client-built pipeline, data model and governance validation completed (est. weeks 1–6).",
            external_date=None,
            internal_buffer_date=None,
            critical_path_assumptions=["Schedule is estimated from the Start Date, with P1 running weeks 1–6"],
            key_dependencies=[
                "Client design system access (code library, tokens, design files, guidelines, named contact) by the start date",
                "Client IdP team availability for Azure AD / MSAL authentication",
                "Client-owned stories and code dependencies completed before dependent Toptal work begins",
                "Coding and delivery documentation standards provided on or before the start date",
            ],
            source_reference=ref,
        ),
        Milestone(
            id="M2",
            description="P2a Services and Data accepted: FastAPI search and async services, OneGWAS integration, performance spike, and Client-built data ingestion validation completed (est. weeks 7–16).",
            external_date=None,
            internal_buffer_date=None,
            critical_path_assumptions=[
                "P2a begins upon completion of HS-4781",
                "P2a runs weeks 7–16 from the Start Date",
            ],
            key_dependencies=[
                "Client completion of HS-4781 (Snowflake schema) before P2a begins",
                "Client-built data ingestion and migration completed before related validation",
                "Domain users and domain experts for trait taxonomy available",
                "Cogen API available and stable at about 95%",
            ],
            source_reference=ref,
        ),
        Milestone(
            id="M3",
            description="P2b Application Surface accepted: ARC micro-frontend search and detail views, haplotype features, nomenclature service, and related test suites completed (est. weeks 17–21).",
            external_date=None,
            internal_buffer_date=None,
            critical_path_assumptions=[
                "P2b begins upon acceptance of P2a",
                "P2b runs weeks 17–21 from the Start Date",
            ],
            key_dependencies=[
                "Acceptance of P2a before P2b begins",
                "Client UI/UX designs for Milestone 3 screens provided by the start date",
                "Client design system access and advance notice of design-system changes",
            ],
            source_reference=ref,
        ),
        Milestone(
            id="M4",
            description="P3 Launch accepted: integration, performance, security and cross-browser testing, UAT, hardening, production smoke tests with 48-hour defect watch, and training materials completed (est. weeks 22–26).",
            external_date=None,
            internal_buffer_date=None,
            critical_path_assumptions=[
                "P3 begins upon acceptance of P2b",
                "P3 runs weeks 22–26 from the Start Date",
            ],
            key_dependencies=[
                "Acceptance of P2b before P3 begins",
                "Client scientist UAT groups available",
                "Client maintains development, staging and production environments",
                "Client remediation of defects in Client-built components",
            ],
            source_reference=ref,
        ),
    ]

    deliverables = [
        Deliverable(id="DEL-01", name="Micro-frontend shell", description="Micro-frontend shell", owner="Talent PM", source_reference=ref),
        Deliverable(id="DEL-02", name="Azure AD / MSAL authentication integration", description="Azure AD / MSAL authentication integration", owner="Talent PM", source_reference=ref),
        Deliverable(id="DEL-03", name="Shell and authentication E2E test harness", description="Shell and authentication E2E test harness", owner="Talent PM", source_reference=ref),
        Deliverable(id="DEL-04", name="Pipeline quality gates and deployment smoke checks", description="Pipeline quality gates and deployment smoke checks", owner="Talent PM", source_reference=ref),
        Deliverable(id="DEL-05", name="Authentication negative-test suite and security scan results", description="Authentication negative-test suite and security scan results", owner="Talent PM", source_reference=ref),
        Deliverable(id="DEL-06", name="FastAPI search, detail and async query services with backend tests", description="FastAPI search, detail and async query services with backend tests", owner="Talent PM", source_reference=ref),
        Deliverable(id="DEL-07", name="Performance engineering spike output", description="Performance engineering spike output", owner="Talent PM", source_reference=ref),
        Deliverable(id="DEL-08", name="OneGWAS direct-write integration and E2E/retry tests", description="OneGWAS direct-write integration and E2E/retry tests", owner="Talent PM", source_reference=ref),
        Deliverable(id="DEL-09", name="Client-built data tier validation scripts, results and defect reports", description="Client-built data tier validation scripts, results and defect reports", owner="Talent PM", source_reference=ref),
        Deliverable(id="DEL-10", name="ARC micro-frontend faceted search, results table and detail view", description="ARC micro-frontend faceted search, results table and detail view", owner="Talent PM", source_reference=ref),
        Deliverable(id="DEL-11", name="Haplotype filter, comparison, and API endpoints", description="Haplotype filter, comparison, and API endpoints", owner="Talent PM", source_reference=ref),
        Deliverable(id="DEL-12", name="Nomenclature service and test suite", description="Nomenclature service and test suite", owner="Talent PM", source_reference=ref),
        Deliverable(id="DEL-13", name="P2b frontend and haplotype test suites", description="P2b frontend and haplotype test suites", owner="Talent PM", source_reference=ref),
        Deliverable(id="DEL-14", name="Integration, performance, security and cross-browser test suites with test data", description="Integration, performance, security and cross-browser test suites with test data", owner="Talent PM", source_reference=ref),
        Deliverable(id="DEL-15", name="UAT execution records and defect log", description="UAT execution records and defect log", owner="Talent PM", source_reference=ref),
        Deliverable(id="DEL-16", name="Pre-launch hardening iteration results", description="Pre-launch hardening iteration results", owner="Talent PM", source_reference=ref),
        Deliverable(id="DEL-17", name="Production smoke test results and 48-hour defect watch report", description="Production smoke test results and 48-hour defect watch report", owner="Talent PM", source_reference=ref),
        Deliverable(id="DEL-18", name="MTA Store parity and usage-zero confirmation report", description="MTA Store parity and usage-zero confirmation report", owner="Talent PM", source_reference=ref),
        Deliverable(id="DEL-19", name="Training materials and user documentation", description="Training materials and user documentation", owner="Talent PM", source_reference=ref),
    ]

    # Work packages with Kit's incorrect parent
    backlog_seed = [
        WorkPackageSeed(id="WP-01", title="Micro-frontend shell and Azure AD/MSAL authentication", parent_deliverable_id="DEL-01", preliminary_sequence=1, owner="Talent PM"),
        WorkPackageSeed(id="WP-02", title="Shell E2E harness and authentication security testing", parent_deliverable_id="DEL-01", preliminary_sequence=2, owner="Talent PM"),
        WorkPackageSeed(id="WP-03", title="P1 certification testing of Client-built pipeline, data model and governance", parent_deliverable_id="DEL-01", preliminary_sequence=3, owner="Talent PM"),
        WorkPackageSeed(id="WP-04", title="FastAPI search/detail endpoints and async query processing", parent_deliverable_id="DEL-02", preliminary_sequence=4, owner="Talent PM"),
        WorkPackageSeed(id="WP-05", title="Performance spike and backend integration/load testing", parent_deliverable_id="DEL-02", preliminary_sequence=5, owner="Talent PM"),
        WorkPackageSeed(id="WP-06", title="OneGWAS direct-write integration and tests", parent_deliverable_id="DEL-02", preliminary_sequence=6, owner="Talent PM"),
        WorkPackageSeed(id="WP-07", title="P2a certification testing of Client-built data ingestion and migration", parent_deliverable_id="DEL-02", preliminary_sequence=7, owner="Talent PM"),
        WorkPackageSeed(id="WP-08", title="ARC faceted search, results table and result detail view", parent_deliverable_id="DEL-03", preliminary_sequence=8, owner="Talent PM"),
        WorkPackageSeed(id="WP-09", title="Haplotype filter, comparison, search endpoints and API", parent_deliverable_id="DEL-03", preliminary_sequence=9, owner="Talent PM"),
        WorkPackageSeed(id="WP-10", title="Nomenclature service", parent_deliverable_id="DEL-03", preliminary_sequence=10, owner="Talent PM"),
        WorkPackageSeed(id="WP-11", title="P2b frontend, haplotype and nomenclature test suites", parent_deliverable_id="DEL-03", preliminary_sequence=11, owner="Talent PM"),
        WorkPackageSeed(id="WP-12", title="Test data, fixtures and full integration/performance/security/cross-browser suites", parent_deliverable_id="DEL-04", preliminary_sequence=12, owner="Talent PM"),
        WorkPackageSeed(id="WP-13", title="UAT execution and pre-launch hardening", parent_deliverable_id="DEL-04", preliminary_sequence=13, owner="Talent PM"),
        WorkPackageSeed(id="WP-14", title="Production smoke tests, 48-hour defect watch and MTA Store parity check", parent_deliverable_id="DEL-04", preliminary_sequence=14, owner="Talent PM"),
        WorkPackageSeed(id="WP-15", title="Training materials and user documentation", parent_deliverable_id="DEL-04", preliminary_sequence=15, owner="Talent PM"),
    ]

    comms = [
        CommunicationsPlanItem(id="COM-01", name="Kickoff Call", audience="Client & Toptal Team", content_owner="Delivery Manager", cadence="One-time"),
        CommunicationsPlanItem(id="COM-02", name="Daily Standups", audience="Delivery Team", content_owner="Talent PM", cadence="Daily"),
        CommunicationsPlanItem(id="COM-03", name="Biweekly Sprint Demo", audience="Client Stakeholders", content_owner="Delivery Manager", cadence="Biweekly"),
        CommunicationsPlanItem(id="COM-04", name="Weekly Status Meeting", audience="Client Leadership", content_owner="Delivery Manager", cadence="Weekly"),
        CommunicationsPlanItem(id="COM-05", name="Weekly Status Report", audience="All Stakeholders", content_owner="Talent PM", cadence="Weekly"),
        CommunicationsPlanItem(id="COM-06", name="Milestone Acceptance Review", audience="Client Approvers", content_owner="Delivery Manager", cadence="End of each Milestone"),
        CommunicationsPlanItem(id="COM-07", name="Ad-Hoc Working Sessions", audience="Technical Leads", content_owner="Talent PM", cadence="As needed"),
    ]

    # RAID items & Dependency Log (with M1 default fill)
    raid_items = [
        RiskAssumption(id="RAID-01", type="Dependency", description="Cogen API availability and stability at 95%", category="Technical Dependency", owner="Delivery Manager", status="Open"),
        RiskAssumption(id="RAID-09", type="Dependency", description="Client completion of HS-4781 (Snowflake schema) before P2a begins", category="Technical Dependency", owner="Talent PM", status="Open"),
        RiskAssumption(id="RAID-10", type="Risk", description="Cross-phase delivery sequencing across P1, P2a, P2b, and P3", category="Delivery Risk", owner="Delivery Manager", status="Open"),
        RiskAssumption(id="RAID-16", type="Risk", description="Sequencing dependencies across all phases P1, P2a, P2b, and P3", category="Delivery Risk", owner="Delivery Manager", status="Open"),
    ]

    # 12 dependency log entries all with default fill M1
    deps = [
        DependencyAssumptionItem(id=f"DEP-{i:02d}", type="Dependency", description=f"Technical dependency {i}", category="Technical Dependency", owner="Talent PM", status="Open", linked_milestone="M1")
        for i in range(1, 13)
    ]

    # Ambiguities
    ambiguities = [
        ContractAmbiguityItem(anomaly_id="AMB-01", conflicting_clauses="Section 2 vs Section 4 SLA wording", risk_impact="Schedule delay risk", recommended_clarification="Clarify SLA turnaround window")
    ]

    return StartupKitBaseline(
        project_name="ARC Genomics Platform",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        sow_awarded_date=date(2026, 9, 29),
        charter=ProjectStartupCharter(
            project_name="ARC Genomics Platform",
            client_name="ARC Therapeutics",
            contract_type="Time and Materials",
            delivery_manager="Jane Doe",
            talent_pm="John Smith",
            pmo_lead="Sarah Connor",
        ),
        commercial_guardrails=CommercialGuardrail(
            change_control_trigger="Formal change order required when scope variance exceeds 10% or budget expands.",
            change_order_route="PMO Lead leads -> DM aligns client -> client approves -> Contracting issues change order"
        ),
        milestones=milestones,
        deliverables=deliverables,
        backlog_seed=backlog_seed,
        communications_plan=comms,
        raid_items=raid_items,
        dependencies_assumptions=deps,
        contract_ambiguities=ambiguities,
        # Readiness fields populated with marker text (should NOT appear in workbook)
        readiness_score=75.0,
        readiness_checklist=[
            ReadinessChecklistItem(
                item_id="G01-01",
                gate_criterion="Charter Authority",
                related_section4_artifact="Project Startup Charter",
                owner="PMO Lead",
                status="Complete",
                evidence="Readiness Gate Approval Marker Text"
            )
        ],
        gate_decision=GateDecision(
            gate_decision_status="Approved with Exception",
            decision_summary="Readiness Score and gate decision marker"
        ),
        action_required_items=[
            ActionRequiredItem(
                action_id="ACT-01",
                item_type="Open Exception",
                checklist_id="G01-01",
                related_artifact="Project Startup Charter",
                finding_description="Missing formal sign-off",
                required_action="Resolve readiness gate exception marker",
                owner="PMO Lead"
            )
        ],
        readiness_breakdown={"d1": 70.0, "d2": 80.0},
        workflow_state="Ready for G-01 Gate Review",
        sla_met=True,
        kit_drafted_date=date(2026, 9, 30),
        talent_onboarding=TalentOnboardingRecord(
            pmo_lead="Sarah Connor",
            delivery_manager="Jane Doe",
            talent_pm="John Smith",
            overall_status="Onboarding in progress"
        )
    )


@pytest.fixture
def populated_inputs_dir(tmp_path):
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()

    # 1. Create SOW PDF
    pdf_path = inputs_dir / "sow.pdf"
    doc_fitz = fitz.open()
    page = doc_fitz.new_page()
    page.insert_text((50, 50), "Statement of Work: Pfizer Modernization. Deliverables: DEL-01, DEL-02.")
    doc_fitz.save(str(pdf_path))
    doc_fitz.close()

    # 2. Create Deck PPTX
    pptx_path = inputs_dir / "deck.pptx"
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "PMO Governance Deck"
    prs.save(str(pptx_path))

    # 3. Create context.txt
    (inputs_dir / "context.txt").write_text("Sponsor: Pfizer VP. Governance Tier: Elevated.", encoding="utf-8")

    return inputs_dir


@pytest.fixture
def sample_source_ref():
    return SourceReference(
        document_name="sample_sow.pdf",
        clause_or_slide="Section 4.1",
        confidence_score=0.95
    )


@pytest.fixture
def sample_deliverables(sample_source_ref):
    return [
        Deliverable(
            id="DEL-01",
            description="Cloud Migration Architecture Design",
            source_reference=sample_source_ref,
            owner="Talent PM",
            acceptance_criteria="Approved by Enterprise Architect"
        ),
        Deliverable(
            id="DEL-02",
            description="Terraform Infrastructure Pipeline",
            source_reference=sample_source_ref,
            owner="Unassigned",
            acceptance_criteria=None  # Triggers confirmation required
        )
    ]


@pytest.fixture
def sample_milestones(sample_source_ref):
    return [
        Milestone(
            id="M1",
            description="Architecture Sign-off",
            external_date=date(2026, 10, 15),
            internal_buffer_date=date(2026, 10, 10),
            source_reference=sample_source_ref
        ),
        Milestone(
            id="M2",
            description="Go-Live Readiness",
            external_date=date(2026, 11, 30),
            internal_buffer_date=date(2026, 11, 20),
            source_reference=sample_source_ref
        )
    ]


@pytest.fixture
def sample_raid_items(sample_source_ref):
    return [
        RiskAssumption(
            type="Risk",
            description="Delay in client IAM access provisioning",
            owner="Delivery Manager",
            status="Open",
            source_reference=sample_source_ref
        ),
        RiskAssumption(
            type="Assumption",
            description="Client provides test environment 2 weeks prior to UAT",
            owner="PMO Lead",
            status="Open",
            source_reference=sample_source_ref
        ),
        RiskAssumption(
            type="Dependency",
            description="Third-party API credentials delivered by week 2",
            owner="Client Lead",
            status="Open",
            source_reference=sample_source_ref
        )
    ]


@pytest.fixture
def sample_governance_context():
    return GovernanceContext(
        project_name="Pfizer Cloud Migration",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        client_name="Pfizer Inc.",
        delivery_manager="Jane Doe",
        talent_pm="John Smith",
        pmo_lead="Sarah Connor",
        executive_summary="Modernization of clinical trial data pipeline into AWS."
    )


@pytest.fixture
def sample_baseline(
    sample_governance_context,
    sample_deliverables,
    sample_milestones,
    sample_raid_items
):
    return StartupKitBaseline(
        project_name="Pfizer Cloud Migration",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        governance_context=sample_governance_context,
        deliverables=sample_deliverables,
        milestones=sample_milestones,
        raid_items=sample_raid_items,
        open_questions=[
            "Confirm client UAT sign-off timeline.",
            "Verify acceptance criteria for Terraform Infrastructure Pipeline."
        ]
    )
