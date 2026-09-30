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
    SOWInterpretationSummary,
    DecisionItem,
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
    """ARC Genomics Platform fixture built strictly from Appendix A of PMO_Workbook_Quality_and_Traceability_Spec_v3.md."""
    ref = SourceReference(document_name="ARC_Genomics_SOW.pdf", clause_or_slide="Section 3", confidence_score=0.95)
    
    milestones = [
        Milestone(
            id="M1",
            description="P1 Foundation accepted: micro-frontend shell, Azure AD/MSAL authentication, E2E test harness, pipeline quality gates, and security/data validation delivered (estimated weeks 1-6).",
            external_date=None,
            internal_buffer_date=None,
            critical_path_assumptions=["Schedule is estimated from the Start Date, with P1 running weeks 1–6"],
            key_dependencies=[
                "Client provides design system access (code library, tokens, design files, guidelines, named contact) by the start date",
                "Client IdP team available for Azure AD / MSAL authentication",
                "Client-built pipelines, Snowflake data model, and governance controls completed before related testing begins",
            ],
            source_reference=ref,
        ),
        Milestone(
            id="M2",
            description="P2a Services and Data accepted: FastAPI search/detail endpoints, async processing, OneGWAS direct-write integration, performance spike, and data ingestion validations delivered (estimated weeks 7-16).",
            external_date=None,
            internal_buffer_date=None,
            critical_path_assumptions=[
                "P2a begins upon completion of HS-4781",
                "P2a runs weeks 7–16 from the Start Date",
            ],
            key_dependencies=[
                "Client completes HS-4781 (Snowflake schema) before P2a begins",
                "P1 Foundation accepted",
                "Client-built ingestion and migration pipelines completed before validation work",
                "Domain users and trait taxonomy domain experts available",
                "Cogen API stable at approximately 95%",
            ],
            source_reference=ref,
        ),
        Milestone(
            id="M3",
            description="P2b Application Surface accepted: ARC faceted search, result detail and haplotype visualization, haplotype endpoints, nomenclature service, and related test suites delivered (estimated weeks 17-21).",
            external_date=None,
            internal_buffer_date=None,
            critical_path_assumptions=[
                "P2b begins upon acceptance of P2a",
                "P2b runs weeks 17–21 from the Start Date",
            ],
            key_dependencies=[
                "P2a Services and Data accepted",
                "Client provides UI/UX designs for the Milestone 3 screens by the start date",
                "Client design system available and any design-system changes communicated in advance",
            ],
            source_reference=ref,
        ),
        Milestone(
            id="M4",
            description="P3 Launch accepted: integration, performance, security, and cross-browser testing, UAT, hardening, production smoke tests with 48-hour defect watch, MTA Store parity confirmation, and training materials delivered (estimated weeks 22-26).",
            external_date=None,
            internal_buffer_date=None,
            critical_path_assumptions=[
                "P3 begins upon acceptance of P2b",
                "P3 runs weeks 22–26 from the Start Date",
            ],
            key_dependencies=[
                "P2b Application Surface accepted",
                "Client maintains development, staging, and production environments",
                "Client scientist UAT groups available",
                "Client remediates defects in Client-built components before cutover",
            ],
            source_reference=ref,
        ),
    ]

    deliverables = [
        Deliverable(
            id="DEL-01",
            name="Micro-frontend shell",
            description="Micro-frontend shell architecture and deployment",
            acceptance_criteria="Shell loads and hosts micro-frontends",
            evidence_required="Micro-frontend shell architecture and deployment verification",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-02",
            name="Azure AD / MSAL authentication integration",
            description="Azure AD / MSAL authentication integration",
            acceptance_criteria="Authentication token exchange and RBAC enforced",
            evidence_required="Pipeline quality gates and deployment smoke check execution logs",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-03",
            name="Shell and authentication E2E test harness",
            description="Shell and authentication E2E test harness",
            acceptance_criteria="Automated E2E test harness passing in pipeline",
            evidence_required="FastAPI search, detail and async query services backend test logs",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-04",
            name="P1 pipeline quality gates and deployment smoke checks",
            description="Pipeline quality gates and deployment smoke checks",
            acceptance_criteria="Automated pipeline gates stop failing builds",
            evidence_required="FastAPI search, detail and async query services backend test logs",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-05",
            name="FastAPI search, detail and async query services",
            description="FastAPI search, detail and async query services with backend tests",
            acceptance_criteria="FastAPI endpoints return within 200ms and async jobs complete",
            evidence_required="Performance engineering spike output and bottleneck mitigation architecture",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-06",
            name="Backend integration and load tests",
            description="FastAPI backend integration and load tests",
            acceptance_criteria="Backend integration and load tests pass latency targets",
            evidence_required="Backend integration and load tests execution logs and benchmarks",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-07",
            name="Performance engineering spike output",
            description="Performance engineering spike output",
            acceptance_criteria="Performance bottlenecks documented with mitigation architecture",
            evidence_required="OneGWAS direct-write integration and retry test results",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-08",
            name="OneGWAS direct-write integration and tests",
            description="OneGWAS direct-write integration and E2E/retry tests",
            acceptance_criteria="Direct-write to Snowflake succeeds with retry on failure",
            evidence_required="P2a data tier validation scripts and defect reports",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-09",
            name="P2a data tier validation scripts and defect reports",
            description="Client-built data tier validation scripts, results and defect reports",
            acceptance_criteria="Data tier validation scripts executed and defects logged",
            evidence_required="P2a data tier validation scripts, results and defect reports",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-10",
            name="ARC micro-frontend faceted search, results table and detail view",
            description="ARC micro-frontend faceted search, results table and detail view",
            acceptance_criteria="Faceted search filters and renders results table within SLA",
            evidence_required="Haplotype visualization and endpoints test output",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-11",
            name="Haplotype visualization and endpoints",
            description="Haplotype filter, comparison, and API endpoints",
            acceptance_criteria="Haplotype comparison algorithm returns accurate genomic data",
            evidence_required="Nomenclature service and taxonomy mapping verification report",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-12",
            name="Nomenclature service and test suite",
            description="Nomenclature service and test suite",
            acceptance_criteria="Nomenclature resolution conforms to standard taxonomy",
            evidence_required="ARC micro-frontend faceted search results table demo sign-off",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-13",
            name="Frontend and haplotype test suites",
            description="P2b frontend and haplotype test suites",
            acceptance_criteria="100% test coverage for P2b frontend and haplotype features",
            evidence_required="Production smoke test results and 48-hour defect watch report",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-14",
            name="P2b nomenclature integration and test results",
            description="P2b nomenclature integration and test results",
            acceptance_criteria="Nomenclature integration verified across search and detail views",
            evidence_required="MTA Store parity confirmation report",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-15",
            name="Integration, performance, security and cross-browser test suites with test data",
            description="Integration, performance, security and cross-browser test suites with test data",
            acceptance_criteria="Full test matrix passing across Chrome, Firefox, Safari",
            evidence_required="Training materials and user documentation walkthrough sign-off",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-16",
            name="UAT execution records and defect log",
            description="UAT execution records and defect log",
            acceptance_criteria="UAT test cases executed by client scientists with zero blocker defects",
            evidence_required="[CONFIRMATION REQUIRED]",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-17",
            name="Pre-launch hardening iteration results",
            description="Pre-launch hardening iteration results",
            acceptance_criteria="Hardening fixes verified and performance baselines met",
            evidence_required="[TBD]",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-18",
            name="Production smoke test results and 48-hour defect watch report",
            description="Production smoke test results and 48-hour defect watch report",
            acceptance_criteria="Production smoke tests pass with 48 hours zero defect severity 1/2",
            evidence_required="[UNASSIGNED - TO BE CONFIRMED]",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-19",
            name="MTA Store parity confirmation report",
            description="MTA Store parity and usage-zero confirmation report",
            acceptance_criteria="Parity with legacy MTA Store confirmed and usage zero verified",
            evidence_required="[CONFIRMATION REQUIRED]",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-20",
            name="Training materials and user documentation",
            description="Training materials and user documentation",
            acceptance_criteria="Comprehensive user guides, admin guides and training decks delivered",
            evidence_required="[TBD]",
            owner="Talent PM",
            source_reference=ref,
        ),
    ]

    backlog_seed = [
        WorkPackageSeed(id="WP-01", title="Micro-frontend shell and architecture setup", parent_deliverable_id="DEL-01", preliminary_sequence=1, owner="Talent PM"),
        WorkPackageSeed(id="WP-02", title="Azure AD / MSAL authentication integration", parent_deliverable_id="DEL-01", preliminary_sequence=2, owner="Talent PM"),
        WorkPackageSeed(id="WP-03", title="Shell and authentication E2E test harness", parent_deliverable_id="DEL-01", preliminary_sequence=3, owner="Talent PM"),
        WorkPackageSeed(id="WP-04", title="P1 pipeline quality gates and deployment smoke checks", parent_deliverable_id="DEL-01", preliminary_sequence=4, owner="Talent PM"),
        WorkPackageSeed(id="WP-05", title="FastAPI search, detail and async query services", parent_deliverable_id="DEL-02", preliminary_sequence=5, owner="Talent PM"),
        WorkPackageSeed(id="WP-06", title="Backend integration and load tests", parent_deliverable_id="DEL-02", preliminary_sequence=6, owner="Talent PM"),
        WorkPackageSeed(id="WP-07", title="OneGWAS direct-write integration and retry tests", parent_deliverable_id="DEL-02", preliminary_sequence=7, owner="Talent PM"),
        WorkPackageSeed(id="WP-08", title="P2a data tier validation scripts and defect reports", parent_deliverable_id="DEL-02", preliminary_sequence=8, owner="Talent PM"),
        WorkPackageSeed(id="WP-09", title="ARC micro-frontend faceted search and results view", parent_deliverable_id="DEL-03", preliminary_sequence=9, owner="Talent PM"),
        WorkPackageSeed(id="WP-10", title="Nomenclature service and taxonomy mapping", parent_deliverable_id="DEL-03", preliminary_sequence=10, owner="Talent PM"),
        WorkPackageSeed(id="WP-11", title="P2b frontend and haplotype test suites", parent_deliverable_id="DEL-03", preliminary_sequence=11, owner="Talent PM"),
        WorkPackageSeed(id="WP-12", title="P2b nomenclature integration and test results", parent_deliverable_id="DEL-03", preliminary_sequence=12, owner="Talent PM"),
        WorkPackageSeed(id="WP-13", title="Integration, performance, security and cross-browser test suites", parent_deliverable_id="DEL-04", preliminary_sequence=13, owner="Talent PM"),
        WorkPackageSeed(id="WP-14", title="UAT execution records and defect log", parent_deliverable_id="DEL-04", preliminary_sequence=14, owner="Talent PM"),
        WorkPackageSeed(id="WP-15", title="MTA Store parity confirmation report", parent_deliverable_id="DEL-04", preliminary_sequence=15, owner="Talent PM"),
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

    raid_items = [
        RiskAssumption(id="RAID-01", type="Risk", description="Design system token changes during P1 execution", category="Delivery Risk", owner="Talent PM", probability="Medium", impact="High", status="Open"),
        RiskAssumption(id="RAID-02", type="Risk", description="Azure AD tenant permissions delay for test environments", category="Technical Dependency", owner="Talent PM", probability="High", impact="High", status="Open"),
        RiskAssumption(id="RAID-03", type="Risk", description="Snowflake query latency under high concurrent load", category="Delivery Risk", owner="Talent PM", probability="Medium", impact="Medium", status="Open"),
        RiskAssumption(id="RAID-04", type="Risk", description="OneGWAS write throughput bottleneck", category="Delivery Risk", owner="Talent PM", probability="Low", impact="High", status="Open"),
        RiskAssumption(id="RAID-05", type="Risk", description="Genomic trait taxonomy mapping ambiguity across systems", category="Delivery Risk", owner="Talent PM", probability="Medium", impact="Medium", status="Open"),
        RiskAssumption(id="RAID-06", type="Risk", description="Scientist UAT participant availability during peak research cycle", category="Delivery Risk", owner="Delivery Manager", probability="High", impact="Medium", status="Open"),
        RiskAssumption(id="RAID-07", type="Risk", description="Legacy MTA Store data extraction access constraints", category="Technical Dependency", owner="Talent PM", probability="Medium", impact="High", status="Open"),
        RiskAssumption(id="RAID-08", type="Risk", description="Cross-browser rendering differences on Safari for haplotype graphs", category="Delivery Risk", owner="Talent PM", probability="Low", impact="Medium", status="Open"),
    ]

    deps = [
        DependencyAssumptionItem(id="DEP-01", type="Dependency", description="Client provides design system access (code library, tokens, design files, guidelines, named contact) by the start date", category="Client Prerequisite", owner="Talent PM", status="Open", linked_milestone="M1", linked_deliverable="DEL-01"),
        DependencyAssumptionItem(id="DEP-02", type="Dependency", description="Client completes HS-4781 (Snowflake schema) before P2a begins", category="Technical Dependency", owner="Talent PM", status="Open", linked_milestone="M1", linked_deliverable="DEL-01"),
        DependencyAssumptionItem(id="DEP-03", type="Dependency", description="Sequential gate approvals across P1, P2a, P2b, P3", category="Governance", owner="Delivery Manager", status="Open", linked_milestone="M1", linked_deliverable="DEL-01"),
        DependencyAssumptionItem(id="DEP-04", type="Dependency", description="Client IdP team available for Azure AD / MSAL authentication", category="Technical Dependency", owner="Talent PM", status="Open", linked_milestone="M1", linked_deliverable="DEL-01"),
        DependencyAssumptionItem(id="DEP-05", type="Dependency", description="Client provides UI/UX designs for the Milestone 3 screens by the start date", category="Client Prerequisite", owner="Talent PM", status="Open", linked_milestone="M1", linked_deliverable="DEL-01"),
        DependencyAssumptionItem(id="DEP-06", type="Dependency", description="Client-built ingestion and migration pipelines completed before validation work", category="Technical Dependency", owner="Talent PM", status="Open", linked_milestone="M1", linked_deliverable="DEL-01"),
        DependencyAssumptionItem(id="DEP-07", type="Dependency", description="Client maintains development, staging, and production environments", category="Technical Dependency", owner="Talent PM", status="Open", linked_milestone="M1", linked_deliverable="DEL-01"),
        DependencyAssumptionItem(id="DEP-08", type="Dependency", description="Client remediates defects in Client-built components before cutover", category="Technical Dependency", owner="Delivery Manager", status="Open", linked_milestone="M1", linked_deliverable="DEL-01"),
        DependencyAssumptionItem(id="ASM-01", type="Assumption", description="SOW schedule estimated from start date with week ranges for all phases", category="Commercial Assumption", owner="Delivery Manager", status="Open", linked_milestone="M1", linked_deliverable="DEL-01"),
        DependencyAssumptionItem(id="ASM-02", type="Assumption", description="Fixed Bid commercial model billed on milestone acceptance sign-off", category="Commercial Assumption", owner="Delivery Manager", status="Open", linked_milestone="M1", linked_deliverable="DEL-01"),
        DependencyAssumptionItem(id="ASM-03", type="Assumption", description="Toptal delivery team staffed according to talent onboarding plan", category="Commercial Assumption", owner="Talent PM", status="Open", linked_milestone="M1", linked_deliverable="DEL-01"),
    ]

    ambiguities = [
        ContractAmbiguityItem(
            anomaly_id="AMB-01",
            category="Ambiguous Acceptance",
            conflicting_clauses="[V1] Exhibit A - Arc Genomics Platform.pdf, Section 4 (Latency Acceptance Criteria): test-suite acceptance criteria latency must be under 200ms",
            risk_impact="Schedule and rework risk if latency cannot be met with Snowflake data volumes",
            recommended_clarification="Clarify target SLA for complex queries"
        ),
        ContractAmbiguityItem(
            anomaly_id="AMB-02",
            category="Date Conflict",
            conflicting_clauses="[V1] Exhibit A - Arc Genomics Platform.pdf, Section 2 (Milestone Timeline): P1 delivery timeline estimated as 6 weeks vs Exhibit B stating 5 weeks",
            risk_impact="Timeline ambiguity impacting resource scheduling",
            recommended_clarification="Confirm contractual week duration for P1"
        ),
        ContractAmbiguityItem(
            anomaly_id="AMB-03",
            category="Scope Contradiction",
            conflicting_clauses="[V1] Exhibit A - Arc Genomics Platform.pdf, Section 3 (Search Features): search filters specify 12 facet types vs Section 5 mentioning 8 core facets",
            risk_impact="Scope creep and extra frontend development effort",
            recommended_clarification="Confirm final facet list for P2b search"
        ),
        ContractAmbiguityItem(
            anomaly_id="AMB-04",
            category="Unclear SLA",
            conflicting_clauses="[V1] Exhibit A - Arc Genomics Platform.pdf, Section 6 (Client Review Period): client sign-off window stated as 5 business days vs 10 days in MSA",
            risk_impact="Review turnaround delay impacting milestone gating",
            recommended_clarification="Confirm binding acceptance turnaround window"
        ),
        ContractAmbiguityItem(
            anomaly_id="AMB-05",
            category="Ownership Gap",
            conflicting_clauses="[V1] Exhibit A - Arc Genomics Platform.pdf, Section 1 (Snowflake Governance): data security policy ownership split between Client and Toptal",
            risk_impact="Compliance and accountability ambiguity",
            recommended_clarification="Confirm data governance authority matrix"
        ),
        ContractAmbiguityItem(
            anomaly_id="AMB-06",
            category="Ambiguous Acceptance",
            conflicting_clauses="[V1] Exhibit A - Arc Genomics Platform.pdf, Section 7 (UAT Criteria): UAT passed upon scientist satisfaction without numeric criteria",
            risk_impact="Subjective acceptance criteria causing sign-off delays",
            recommended_clarification="Define quantitative pass/fail thresholds for UAT"
        ),
        ContractAmbiguityItem(
            anomaly_id="AMB-07",
            category="Scope Contradiction",
            conflicting_clauses="[V1] Exhibit A - Arc Genomics Platform.pdf, Section 4 (OneGWAS Integration): async retry logic maximum retries set to 3 vs 5 in architecture deck",
            risk_impact="Error handling behavior mismatch",
            recommended_clarification="Align retry thresholds across technical specs"
        ),
        ContractAmbiguityItem(
            anomaly_id="AMB-08",
            category="Date Conflict",
            conflicting_clauses="[V1] Exhibit A - Arc Genomics Platform.pdf, Section 5 (Launch Window): P3 launch scheduled for Q1 vs Q2 cutover in deployment deck",
            risk_impact="Target go-live alignment",
            recommended_clarification="Confirm binding launch calendar target"
        ),
        ContractAmbiguityItem(
            anomaly_id="AMB-09",
            category="Unclear SLA",
            conflicting_clauses="[V1] Exhibit A - Arc Genomics Platform.pdf, Section 8 (Hypercare Support): 48-hour defect watch resolution SLA not defined for Sev-3/4",
            risk_impact="Post-launch support expectation mismatch",
            recommended_clarification="Establish response and fix SLAs by defect severity"
        ),
        ContractAmbiguityItem(
            anomaly_id="AMB-10",
            category="Ambiguous Acceptance",
            conflicting_clauses="[V1] Exhibit A - Arc Genomics Platform.pdf, Section 3 (MTA Parity): 100% parity with legacy system without feature comparison matrix",
            risk_impact="Disputes over legacy edge-case feature parity",
            recommended_clarification="Baseline exact legacy feature inventory to match"
        ),
        ContractAmbiguityItem(
            anomaly_id="AMB-11",
            category="Ownership Gap",
            conflicting_clauses="[V1] Exhibit A - Arc Genomics Platform.pdf, Section 2 (Deployment Infrastructure): Kubernetes cluster provisioning owner unspecified",
            risk_impact="Deployment environment readiness block",
            recommended_clarification="Confirm responsible party for cluster provisioning"
        ),
        ContractAmbiguityItem(
            anomaly_id="AMB-12",
            category="Scope Contradiction",
            conflicting_clauses="[V1] Exhibit A - Arc Genomics Platform.pdf, Section 4 (Authentication): SSO integration includes external collaborators vs internal Azure AD only",
            risk_impact="IdP integration complexity expansion",
            recommended_clarification="Confirm user identity boundary for initial launch"
        ),
        ContractAmbiguityItem(
            anomaly_id="AMB-13",
            category="Ambiguous Acceptance",
            conflicting_clauses="[V1] Exhibit A - Arc Genomics Platform.pdf, Section 5 (Test Automation): automated test coverage target stated as comprehensive without % figure",
            risk_impact="Disagreement on gate exit criteria",
            recommended_clarification="Agree contractual test code coverage percentage"
        ),
        ContractAmbiguityItem(
            anomaly_id="AMB-14",
            category="Unclear SLA",
            conflicting_clauses="[V1] Exhibit A - Arc Genomics Platform.pdf, Section 6 (Defect Remediation): Client component fix turnaround SLA during P3 undefined",
            risk_impact="Cutover delay caused by unblocked client defects",
            recommended_clarification="Establish defect turnaround commitment for client components"
        ),
        ContractAmbiguityItem(
            anomaly_id="AMB-15",
            category="Ownership Gap",
            conflicting_clauses="[V1] Exhibit A - Arc Genomics Platform.pdf, Section 7 (Training Delivery): responsibility for end-user scientist training delivery vs materials authoring",
            risk_impact="Talent staffing allocation gap",
            recommended_clarification="Confirm delivery scope: material authoring only vs live facilitation"
        ),
    ]

    open_questions = [
        "What is the confirmed project Start Date for P1?",
        "Who is the primary client approver for Milestone 1?",
        "When will design system code tokens and repositories be shared?",
        "Who is the technical contact for Azure AD IdP integration?",
        "What is the completion timeline for Snowflake schema HS-4781?",
        "What are the target SLA latency benchmarks for P2a search endpoints?",
        "Who are the designated trait taxonomy domain experts for P2a?",
        "What is the availability schedule for the Cogen API environment?",
        "When will the UI/UX design deliverables for P2b be ready for review?",
        "Which client scientist research groups will participate in P3 UAT?",
        "What is the target deployment date for staging and production cutover?",
        "What are the acceptance criteria for MTA Store legacy parity confirmation?",
        "Who will approve final gate acceptance for P3 Launch?",
        "What is the required format and platform for training materials?",
        "Are external research collaborators included in P1 SSO scope?",
        "What automated test coverage threshold is required for pipeline gates?",
        "Who manages the production release rollback approval decision?",
        "What are the environment maintenance windows for P3?",
        "PMO Lead role is unassigned in the charter - confirm assignee",
        "Delivery Manager role is unassigned in the charter - confirm assignee",
        "Talent PM role is unassigned in the charter - confirm assignee",
    ]

    sow_interp = SOWInterpretationSummary(
        contracted_deliverables=[
            "P1 Foundation (weeks 1–6): Micro-frontend shell, Azure AD/MSAL authentication, E2E test harness, and Client pipeline validation.",
            "P1 quality: Pipeline quality gates and security scan results.",
            "P2a Services and Data (weeks 7–16): FastAPI search and async services, OneGWAS integration, performance spike, and Client data validation.",
            "P2a testing: Backend integration and load tests, performance spike results, and data ingestion defect reports.",
            "P2b Application Surface (weeks 17–21): ARC micro-frontend search and detail views, haplotype visualization and endpoints, nomenclature service, and frontend test suites.",
            "P3 Launch (weeks 22–26): Integration, performance, security, and cross-browser testing, UAT execution, hardening, and production smoke tests with 48-hour defect watch.",
            "P3 parity: MTA Store parity confirmation report.",
            "Training materials and user documentation.",
        ],
        out_of_scope_items=["Legacy infrastructure decommission"],
        customer_obligations=["Snowflake schema HS-4781", "Azure AD access"],
        assumptions=["Client environments available 24/7"],
        constraints=["Zero critical security defects at launch"],
    )

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
        open_questions=open_questions,
        sow_interpretation=sow_interp,
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
def arc_run1(arc_baseline):
    """ARC Genomics Platform fixture for run 1 (v3 Appendix A)."""
    return arc_baseline


@pytest.fixture
def arc_run2():
    """ARC Genomics Platform fixture for run 2 built strictly from Appendix A of PMO_Workbook_Quality_and_Traceability_Spec_v4.md."""
    ref = SourceReference(document_name="ARC_Genomics_SOW.pdf", clause_or_slide="Section 3", confidence_score=0.95)

    milestones = [
        Milestone(
            id="M1",
            description="P1 Foundation accepted: micro-frontend shell, Azure AD/MSAL authentication, E2E test harness, pipeline quality gates, and security/data validation delivered (estimated weeks 1-6).",
            external_date=None,
            internal_buffer_date=None,
            critical_path_assumptions=["Schedule is estimated from the Start Date, with P1 running weeks 1–6"],
            key_dependencies=[
                "Client provides design system access (code library, tokens, design files, guidelines, named contact) by the start date",
                "Client IdP team available for Azure AD / MSAL authentication",
                "Client-built pipelines, Snowflake data model, and governance controls completed before related testing begins",
            ],
            source_reference=ref,
        ),
        Milestone(
            id="M2",
            description="P2a Services and Data accepted: FastAPI search/detail endpoints, async processing, OneGWAS direct-write integration, performance spike, and data ingestion validations delivered (estimated weeks 7-16).",
            external_date=None,
            internal_buffer_date=None,
            critical_path_assumptions=[
                "P2a begins upon completion of HS-4781",
                "P2a runs weeks 7–16 from the Start Date",
            ],
            key_dependencies=[
                "Client completes HS-4781 (Snowflake schema) before P2a begins",
                "Client-built ingestion and migration pipelines completed before validation work",
                "Domain users and trait taxonomy domain experts available",
            ],
            source_reference=ref,
        ),
        Milestone(
            id="M3",
            description="P2b Application Surface accepted: ARC faceted search, result detail and haplotype visualization, haplotype endpoints, nomenclature service, and related test suites delivered (estimated weeks 17-21).",
            external_date=None,
            internal_buffer_date=None,
            critical_path_assumptions=[
                "P2b begins upon acceptance of P2a",
                "P2b runs weeks 17–21 from the Start Date",
            ],
            key_dependencies=[
                "P2a Services and Data accepted",
                "Client provides UI/UX screen designs and design system assets for Milestone 3 before start date",
            ],
            source_reference=ref,
        ),
        Milestone(
            id="M4",
            description="P3 Launch accepted: integration, performance, security, and cross-browser testing, UAT, hardening, production smoke tests with 48-hour defect watch, MTA Store parity confirmation, and training materials delivered (estimated weeks 22-26).",
            external_date=None,
            internal_buffer_date=None,
            critical_path_assumptions=[
                "P3 begins upon acceptance of P2b",
                "P3 runs weeks 22–26 from the Start Date",
            ],
            key_dependencies=[
                "P2b Application Surface accepted",
                "Client maintains development, staging, and production environments",
                "Client scientist UAT groups available",
            ],
            source_reference=ref,
        ),
    ]

    deliverables = [
        Deliverable(
            id="DEL-01",
            name="Micro-frontend shell",
            description="Micro-frontend shell architecture and deployment",
            acceptance_criteria="Shell loads and hosts micro-frontends",
            evidence_required="Micro-frontend shell architecture and deployment verification",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-02",
            name="Azure AD / MSAL authentication integration",
            description="Azure AD / MSAL authentication integration",
            acceptance_criteria="Authentication token exchange and RBAC enforced",
            evidence_required="Pipeline quality gates and deployment smoke check execution logs",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-03",
            name="Shell and authentication E2E test harness",
            description="Shell and authentication E2E test harness",
            acceptance_criteria="Automated E2E test harness passing in pipeline",
            evidence_required="FastAPI search, detail and async query services backend test logs",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-04",
            name="Authentication negative-test suite",
            description="Authentication negative-test suite",
            acceptance_criteria="Negative tests verify security rejection on invalid token",
            evidence_required="FastAPI search, detail and async query services backend test logs",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-05",
            name="P1 pipeline quality gates and deployment smoke checks",
            description="Pipeline quality gates and deployment smoke checks",
            acceptance_criteria="Automated pipeline gates stop failing builds",
            evidence_required="P1 pipeline quality gates and deployment smoke check execution logs",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-06",
            name="FastAPI search, detail and async query services",
            description="FastAPI search, detail and async query services",
            acceptance_criteria="FastAPI endpoints return within 200ms and async jobs complete",
            evidence_required="Performance engineering spike output and bottleneck mitigation architecture",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-07",
            name="Backend integration and load test suites",
            description="Backend integration and load test suites",
            acceptance_criteria="Integration and load tests pass latency targets",
            evidence_required="Backend integration and load tests execution logs and benchmarks",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-08",
            name="Performance engineering spike output",
            description="Performance engineering spike output",
            acceptance_criteria="Performance bottlenecks documented with mitigation architecture",
            evidence_required="OneGWAS direct-write integration and retry test results",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-09",
            name="OneGWAS direct-write integration and tests",
            description="OneGWAS direct-write integration and tests",
            acceptance_criteria="Direct-write to Snowflake succeeds with retry on failure",
            evidence_required="P2a data tier validation scripts and defect reports",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-10",
            name="P2a data tier validation scripts and defect reports",
            description="Data tier validation scripts and defect reports",
            acceptance_criteria="Data tier validation scripts executed and defects logged",
            evidence_required="P2a data tier validation scripts, results and defect reports",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-11",
            name="ARC micro-frontend faceted search, results table and detail view",
            description="ARC micro-frontend faceted search, results table and detail view",
            acceptance_criteria="Faceted search filters and renders results table within SLA",
            evidence_required="Haplotype visualization and endpoints test output",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-12",
            name="Haplotype visualization and endpoints",
            description="Haplotype visualization and endpoints",
            acceptance_criteria="Haplotype comparison algorithm returns accurate genomic data",
            evidence_required="Nomenclature service and taxonomy mapping verification report",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-13",
            name="Nomenclature service and test suite",
            description="Nomenclature service and test suite",
            acceptance_criteria="Nomenclature resolution conforms to standard taxonomy",
            evidence_required="Production smoke test results and 48-hour defect watch report",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-14",
            name="P2b frontend and haplotype test suites",
            description="P2b frontend and haplotype test suites",
            acceptance_criteria="100% test coverage for P2b frontend and haplotype features",
            evidence_required="MTA Store parity confirmation report",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-15",
            name="Integration, performance, security and cross-browser test suites with test data",
            description="Integration, performance, security and cross-browser test suites with test data",
            acceptance_criteria="Full test matrix passing across Chrome, Firefox, Safari",
            evidence_required="Training materials and user documentation walkthrough sign-off",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-16",
            name="UAT execution records and defect log",
            description="UAT execution records and defect log",
            acceptance_criteria="UAT test cases executed by client scientists with zero blocker defects",
            evidence_required="[CONFIRMATION REQUIRED]",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-17",
            name="Pre-launch hardening iteration results",
            description="Pre-launch hardening iteration results",
            acceptance_criteria="Hardening fixes verified and performance baselines met",
            evidence_required="[TBD]",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-18",
            name="Production smoke test results and 48-hour defect watch report",
            description="Production smoke test results and 48-hour defect watch report",
            acceptance_criteria="Production smoke tests pass with 48 hours zero defect severity 1/2",
            evidence_required="[UNASSIGNED - TO BE CONFIRMED]",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-19",
            name="MTA Store parity confirmation report",
            description="MTA Store parity confirmation report",
            acceptance_criteria="Parity with legacy MTA Store confirmed and usage zero verified",
            evidence_required="[CONFIRMATION REQUIRED]",
            owner="Talent PM",
            source_reference=ref,
        ),
        Deliverable(
            id="DEL-20",
            name="Training materials and user documentation",
            description="Training materials and user documentation",
            acceptance_criteria="Comprehensive user guides, admin guides and training decks delivered",
            evidence_required="[TBD]",
            owner="Talent PM",
            source_reference=ref,
        ),
    ]

    backlog_seed = [
        WorkPackageSeed(id="WP-01", title="Micro-frontend shell and architecture setup", parent_deliverable_id="DEL-01", preliminary_sequence=1, owner="Talent PM"),
        WorkPackageSeed(id="WP-02", title="Azure AD / MSAL authentication integration", parent_deliverable_id="DEL-01", preliminary_sequence=2, owner="Talent PM"),
        WorkPackageSeed(id="WP-03", title="Shell and authentication E2E test harness", parent_deliverable_id="DEL-01", preliminary_sequence=3, owner="Talent PM"),
        WorkPackageSeed(id="WP-04", title="Authentication negative-test suite", parent_deliverable_id="DEL-01", preliminary_sequence=4, owner="Talent PM"),
        WorkPackageSeed(id="WP-05", title="FastAPI search, detail and async query services", parent_deliverable_id="DEL-02", preliminary_sequence=5, owner="Talent PM"),
        WorkPackageSeed(id="WP-06", title="Backend integration and load tests", parent_deliverable_id="DEL-02", preliminary_sequence=6, owner="Talent PM"),
        WorkPackageSeed(id="WP-07", title="OneGWAS direct-write integration and retry tests", parent_deliverable_id="DEL-02", preliminary_sequence=7, owner="Talent PM"),
        WorkPackageSeed(id="WP-08", title="P2a data tier validation scripts and defect reports", parent_deliverable_id="DEL-02", preliminary_sequence=8, owner="Talent PM"),
        WorkPackageSeed(id="WP-09", title="ARC micro-frontend faceted search and results view", parent_deliverable_id="DEL-03", preliminary_sequence=9, owner="Talent PM"),
        WorkPackageSeed(id="WP-10", title="Haplotype visualization and endpoints", parent_deliverable_id="DEL-03", preliminary_sequence=10, owner="Talent PM"),
        WorkPackageSeed(id="WP-11", title="Nomenclature service and taxonomy mapping", parent_deliverable_id="DEL-03", preliminary_sequence=11, owner="Talent PM"),
        WorkPackageSeed(id="WP-12", title="P2b frontend and haplotype test suites", parent_deliverable_id="DEL-03", preliminary_sequence=12, owner="Talent PM"),
        WorkPackageSeed(id="WP-13", title="Integration, performance, security and cross-browser test suites", parent_deliverable_id="DEL-04", preliminary_sequence=13, owner="Talent PM"),
        WorkPackageSeed(id="WP-14", title="Pre-launch hardening iteration results", parent_deliverable_id="DEL-04", preliminary_sequence=14, owner="Talent PM"),
        WorkPackageSeed(id="WP-15", title="MTA Store parity confirmation report", parent_deliverable_id="DEL-04", preliminary_sequence=15, owner="Talent PM"),
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

    raid_items = [
        RiskAssumption(id="RSK-01", type="Risk", category="Delivery Risk", description="Delay in HS-4781 Snowflake data model schema delivery will block P2a start.", owner="Unassigned", status="Open", probability="High", impact="High", severity="High", trigger="HS-4781 not complete by week 6", mitigation="Escalate to Client Lead"),
        RiskAssumption(id="RSK-02", type="Risk", category="Technical Dependency", description="Cogen API instability exceeding 5% may cause rework in FastAPI integration.", owner="TBD", status="Open", probability="Medium", impact="High", severity="High", trigger="Cogen downtime > 5%", mitigation="Implement mock Cogen server"),
        RiskAssumption(id="RSK-03", type="Risk", category="Technical Dependency", description="Client IdP token claim mismatch may extend authentication integration schedule.", owner="Talent PM", status="Open", probability="Low", impact="Medium", severity="Medium", trigger="IdP token schema changes", mitigation="Early claim mapping workshop in week 2"),
        RiskAssumption(id="ISS-01", type="Issue", category="Technical Dependency", description="Snowflake staging environment rate limits currently throttle async queries.", owner="Talent PM", status="Open", probability="High", impact="Medium", severity="High", trigger="Rate limit exceeded", mitigation="Request quota increase from Snowflake admin"),
        RiskAssumption(id="ISS-02", type="Issue", category="Technical Dependency", description="MTA Store legacy data export contains undocumented trait schema formats.", owner="Talent PM", status="Open", probability="Medium", impact="Medium", severity="Medium", trigger="Schema validation failures", mitigation="Schedule data format review with legacy domain expert"),
        RiskAssumption(id="RSK-04", type="Risk", category="Delivery Risk", description="UAT scientist availability may be constrained during peak research quarters.", owner="[UNASSIGNED]", status="Open", probability="Medium", impact="High", severity="High", trigger="UAT attendance < 80%", mitigation="Pre-book scientist testing windows 4 weeks in advance"),
    ]

    deps = [
        DependencyAssumptionItem(id="ASM-01", type="Assumption", category="Commercial Assumption", description="Milestones run in sequence. Each milestone is an acceptance gate; subsequent phases commence after the prior milestone is accepted.", owner="PMO Lead", status="Approved"),
        DependencyAssumptionItem(id="ASM-02", type="Assumption", category="Technical Dependency", description="Client provides design system access (tokens, components, styles) by the project start date.", owner="Talent PM", status="Approved"),
        DependencyAssumptionItem(id="ASM-03", type="Assumption", category="Technical Dependency", description="Cogen API interface stability is at approximately 95%.", owner="Delivery Manager", status="Approved"),
        DependencyAssumptionItem(id="ASM-04", type="Assumption", category="Technical Dependency", description="Trait taxonomy domain experts are available during P2a and P2b for consultation.", owner="Talent PM", status="Approved"),
        DependencyAssumptionItem(id="ASM-05", type="Assumption", category="Technical Dependency", description="Production deployment assumes client maintains dev, test, and prod AWS accounts with Snowflake connectivity.", owner="Delivery Manager", status="Approved"),
        DependencyAssumptionItem(id="ASM-06", type="Assumption", category="Delivery Risk", description="UAT window is 10 business days with named client testers.", owner="Delivery Manager", status="Approved"),
        DependencyAssumptionItem(id="DEP-01", type="Dependency", category="Technical Dependency", description="HS-4781 (Snowflake data model) completed by Client before P2a begins.", owner="Talent PM", status="Open"),
        DependencyAssumptionItem(id="DEP-02", type="Dependency", category="Technical Dependency", description="Client provides Azure AD tenant access and client secret for MSAL integration.", owner="Talent PM", status="Open"),
        DependencyAssumptionItem(id="DEP-03", type="Dependency", category="Technical Dependency", description="Client IdP team available during P1 for token claim mappings.", owner="Talent PM", status="Open"),
        DependencyAssumptionItem(id="DEP-04", type="Dependency", category="Technical Dependency", description="Client provides Snowflake warehouse credentials with write permissions for OneGWAS integration.", owner="Talent PM", status="Open"),
        DependencyAssumptionItem(id="DEP-05", type="Dependency", category="Technical Dependency", description="Client delivers UI/UX screen designs for Milestone 3 before P2b begins.", owner="Talent PM", status="Open"),
        DependencyAssumptionItem(id="DEP-06", type="Dependency", category="Technical Dependency", description="Client completes ingestion and migration pipelines before data validation scripts execute.", owner="Talent PM", status="Open"),
        DependencyAssumptionItem(id="DEP-07", type="Dependency", category="Technical Dependency", description="Client signs off on MTA Store parity before production cutover.", owner="Delivery Manager", status="Open"),
    ]

    decisions = [
        DecisionItem(id="DEC-01", decision_text="Use MSAL.js for Azure AD authentication integration.", rationale="Aligns with client enterprise identity standard.", decision_owner="Tech Lead", status="Approved"),
        DecisionItem(id="DEC-02", decision_text="FastAPI selected as the backend asynchronous query service framework.", rationale="High-performance async I/O required for genomic searches.", decision_owner="Tech Lead", status="Approved"),
        DecisionItem(id="DEC-03", decision_text="OneGWAS direct-write integration via Snowflake Python connector.", rationale="Minimizes data transit latency.", decision_owner="Tech Lead", status="Approved"),
        DecisionItem(id="DEC-04", decision_text="Tailwind CSS adopted for micro-frontend design system implementation.", rationale="Supports rapid theme token composition.", decision_owner="Tech Lead", status="Approved"),
        DecisionItem(id="DEC-05", decision_text="Snowflake schema defined in HS-4781 is accepted as prerequisite for P2a.", rationale="Prevents data model churn during backend build.", decision_owner="Delivery Manager", status="Approved"),
        DecisionItem(id="DEC-06", decision_text="Cogen API v2 selected as trait resolution baseline.", rationale="Stable version matching current production endpoints.", decision_owner="Tech Lead", status="Approved"),
        DecisionItem(id="DEC-07", decision_text="UAT defect threshold set to zero severity 1 and severity 2 defects.", rationale="Contractual acceptance gateway requirement.", decision_owner="Delivery Manager", status="Approved"),
        DecisionItem(id="DEC-08", decision_text="Cross-browser support matrix includes Chrome, Firefox, Safari (latest 2 versions).", rationale="Standard browser matrix across client research workstations.", decision_owner="Delivery Manager", status="Approved"),
        DecisionItem(id="DEC-09", decision_text="48-hour production defect watch period before final MTA Store decommissioning.", rationale="Ensures production operational stability.", decision_owner="Delivery Manager", status="Approved"),
        DecisionItem(id="DEC-10", decision_text="P2a performance testing target: 200ms latency for search endpoints.", rationale="Required for interactive genomic data explorer.", decision_owner="Tech Lead", status="Approved"),
        DecisionItem(id="DEC-11", decision_text="Nomenclature resolution conforms to HGVS and ClinVar standard taxonomies.", rationale="Industry standard bioinformatics nomenclatures.", decision_owner="Tech Lead", status="Approved"),
        DecisionItem(id="DEC-12", decision_text="Single sign-on enforced with Azure AD RBAC groups.", rationale="Client security compliance.", decision_owner="Tech Lead", status="Approved"),
        DecisionItem(id="DEC-13", decision_text="End-to-end automated test harness implemented with Playwright.", rationale="Cross-browser E2E automation support.", decision_owner="Tech Lead", status="Approved"),
        DecisionItem(id="DEC-14", decision_text="Weekly status report and PSR delivered on Fridays.", rationale="Governance communication cadence.", decision_owner="Talent PM", status="Approved"),
        DecisionItem(id="DEC-15", decision_text="Milestone Acceptance Reviews conducted at completion of each SOW phase.", rationale="Formal gate governance.", decision_owner="Delivery Manager", status="Approved"),
    ]

    ambiguities = [
        ContractAmbiguityItem(anomaly_id="AMB-01", category="Date Conflict", conflicting_clauses="HS-4781 completion required before P2a begins vs P2a fixed start at week 7", recommended_clarification="Clarify whether P2a start floats with HS-4781 completion."),
        ContractAmbiguityItem(anomaly_id="AMB-02", category="Ambiguous Acceptance", conflicting_clauses="Section 5 requires Snowflake schema completion in HS-4781 while Section 6 lists schema validation in P2a", recommended_clarification="Clarify division of responsibility between Client and Toptal."),
        ContractAmbiguityItem(anomaly_id="AMB-03", category="Scope Contradiction", conflicting_clauses="OneGWAS direct-write integration mentions Snowflake staging tables and production tables in Section 4", recommended_clarification="Confirm direct-write destination environment."),
        ContractAmbiguityItem(anomaly_id="AMB-04", category="Unclear SLA", conflicting_clauses="Cogen API availability target listed as 95% in dependencies and 99% in Section 7", recommended_clarification="Confirm applicable SLA for Cogen API."),
        ContractAmbiguityItem(anomaly_id="AMB-05", category="Ownership Gap", conflicting_clauses="Client data ingestion pipeline defect remediation ownership is unassigned", recommended_clarification="Confirm party responsible for ingestion pipeline defects."),
        ContractAmbiguityItem(anomaly_id="AMB-06", category="Ambiguous Acceptance", conflicting_clauses="MTA Store parity criteria do not specify acceptable discrepancy percentage in Section 8", recommended_clarification="Define numeric parity threshold."),
        ContractAmbiguityItem(anomaly_id="AMB-07", category="Date Conflict", conflicting_clauses="UAT duration stated as 10 business days in Section 9 and 2 calendar weeks in Section 3", recommended_clarification="Confirm UAT calendar window."),
        ContractAmbiguityItem(anomaly_id="AMB-08", category="Scope Contradiction", conflicting_clauses="HS-4828 and HS-4943 UAT test scenarios mention legacy MTA store and new ARC platform", recommended_clarification="Confirm scope of UAT test execution across platforms."),
        ContractAmbiguityItem(anomaly_id="AMB-09", category="Unclear SLA", conflicting_clauses="FastAPI 200ms latency requirement in Section 4 does not state concurrency load", recommended_clarification="Specify concurrent user load for 200ms latency benchmark."),
        ContractAmbiguityItem(anomaly_id="AMB-10", category="Ambiguous Acceptance", conflicting_clauses="Hardening iteration exit criteria lack quantitative threshold definitions", recommended_clarification="Confirm exit criteria for pre-launch hardening."),
        ContractAmbiguityItem(anomaly_id="AMB-11", category="Date Conflict", conflicting_clauses="Project kickoff date mismatch between contract header and delivery schedule", recommended_clarification="Confirm engagement kickoff date."),
        ContractAmbiguityItem(anomaly_id="AMB-12", category="Ownership Gap", conflicting_clauses="Client-built deployment pipeline maintenance responsibility post-launch is unstated", recommended_clarification="Confirm post-launch pipeline support ownership."),
        ContractAmbiguityItem(anomaly_id="AMB-13", category="Scope Contradiction", conflicting_clauses="Haplotype visualization screen designs reference desktop and mobile layouts", recommended_clarification="Confirm whether mobile view is in scope."),
        ContractAmbiguityItem(anomaly_id="AMB-14", category="Ambiguous Acceptance", conflicting_clauses="Training material delivery format unspecified in delivery notes", recommended_clarification="Confirm training deck and video requirements."),
        ContractAmbiguityItem(anomaly_id="AMB-15", category="Unclear SLA", conflicting_clauses="48-hour defect watch criteria in Section 9 do not define severity classifications", recommended_clarification="Confirm severity 1/2 definition for defect watch."),
    ]

    open_questions = [
        "What is the target completion date for client Snowflake schema delivery?",
        "Who is the primary client approver for Azure AD authentication integration?",
        "When will client test data for HS-4781 integration be provisioned in staging?",
        "What are the target concurrent user loads for FastAPI search endpoints?",
        "Who will provide sign-off on the trait taxonomy nomenclature mapping?",
        "What is the SLA response window for Cogen API service interruptions?",
        "When will client UAT scientist testing groups be finalized?",
        "Who is the designated client approver for MTA Store parity sign-off?",
        "What are the specific video and deck formats required for user training materials?",
        "Will client provide dedicated staging environments for cross-browser testing?",
        "What is the escalation contact if Cogen API availability drops below 95%?",
        "Who is responsible for verifying HS-4788 trait taxonomy resolution rules?",
        "What is the rework window for rejected milestone acceptance deliverables?",
        "Are mobile device browser views in scope for ARC micro-frontend search views?",
        "Who manages the production Snowflake warehouse deployment permissions?",
        "What is the schedule contingency buffer between UAT sign-off and production cutover?",
        "When will client security teams perform the MSAL SSO authentication audit?",
        "What are the G-01 readiness gate sign-off requirements?",
        "Who is the PMO Lead as the role is unassigned?",
        "What is the Startup Readiness score threshold?",
    ]

    sow_interp = SOWInterpretationSummary(
        contracted_deliverables=[
            "P1 Foundation (weeks 1–6): Micro-frontend shell, Azure AD/MSAL authentication, E2E test harness, and Client pipeline validation.",
            "P1 Foundation QA: Pipeline quality gates and authentication negative tests.",
            "P2a Services and Data (weeks 7–16): FastAPI search and async services, OneGWAS integration, performance spike, and Client data validation.",
            "P2a OneGWAS integration: FastAPI search, detail and async query services, OneGWAS direct-write, and backend test suites.",
            "P2a validation of Client-built data work: Data tier validation scripts and defect reports.",
            "P2b Application Surface (weeks 17–21): ARC micro-frontend search and detail views, haplotype visualization and endpoints, nomenclature service, and frontend test suites.",
            "P2b test suites: Frontend and haplotype test suites and nomenclature integration test results.",
            "P3 Launch (weeks 22–26): Integration, performance, security, and cross-browser testing, UAT execution, hardening, production smoke tests with 48-hour defect watch, MTA Store parity confirmation report, and training materials.",
        ],
        out_of_scope_items=["Legacy infrastructure decommission"],
        customer_obligations=["Snowflake schema HS-4781", "Azure AD access"],
        assumptions=["Milestones run in sequence. Each milestone is an acceptance gate."],
        constraints=["Zero critical security defects at launch"],
    )

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
        decisions=decisions,
        contract_ambiguities=ambiguities,
        open_questions=open_questions,
        sow_interpretation=sow_interp,
        readiness_score=75.0,
        readiness_checklist=[
            ReadinessChecklistItem(item_id=f"G01-{i:02d}", gate_criterion=f"Gate {i}", related_section4_artifact="Artifact", owner="PMO Lead", status="Complete", evidence="Evidence")
            for i in range(1, 16)
        ],
        gate_decision=GateDecision(
            gate_decision_status="Approved with Exception",
            decision_summary="Readiness Score and gate decision marker"
        ),
        action_required_items=[],
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
