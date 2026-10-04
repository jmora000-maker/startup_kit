"""Shared offline mock LLM response factory (HTL-19).

Moved out of ``main.py`` so both the CLI and the future Streamlit app can build the
same deterministic, offline fake-data generator without duplicating ~380 lines of
hard-coded extraction responses. This module contains no CLI-specific logic: it
takes no arguments from argparse or os.environ, and simply returns a ready-to-use
``MockLLMClient``.
"""

from datetime import date

from src.core.models import (
    SourceReference,
    Deliverable,
    Milestone,
    RiskAssumption,
    CharterExtraction,
    DeliverablesExtraction,
    MilestonesExtraction,
    RAIDExtraction,
    QuestionsExtraction,
    SOWInterpretationExtraction,
    ScopeDecompositionExtraction,
    AcceptanceProcessExtraction,
    StakeholdersExtraction,
    CommunicationsExtraction,
    CommercialGuardrailsExtraction,
    TalentOnboardingExtraction,
    DecisionsExtraction,
    ContractConflictsExtraction,
    ContractAmbiguityItem,
    WorkPackageSeed,
    DecisionItem,
    CommunicationsPlanItem,
    Stakeholder,
    CommercialGuardrail,
    TalentOnboardingRecord,
    TalentMember,
)
from src.llm.client import MockLLMClient


def create_mock_llm_client() -> MockLLMClient:
    """Create a mock LLM client with realistic baseline extraction responses."""
    client = MockLLMClient()
    ref = SourceReference(
        document_name="SOW_Document.pdf",
        clause_or_slide="Section 3.1",
        confidence_score=0.92
    )
    client.set_response(
        CharterExtraction,
        CharterExtraction(
            project_name="Pfizer Analytics & Cloud Modernization",
            client_name="Pfizer Inc.",
            governance_tier="Partnered",
            contract_type="Time and Materials",
            delivery_manager="Jane Doe",
            talent_pm="John Smith",
            pmo_lead="Sarah Connor",
            executive_summary="Modernization of clinical analytics data pipelines into AWS cloud infrastructure.",
            project_purpose="Migrate on-premise clinical trial analytics pipelines to AWS with automated CI/CD and SOC2 compliance.",
            delivery_objectives=[
                "Deploy production-grade AWS infrastructure via Terraform",
                "Migrate and automate ETL pipelines for clinical analytics",
                "Establish automated testing and compliance reporting"
            ],
            success_criteria=[
                "Zero data loss during pipeline cutover",
                "ETL throughput improvement by 40%",
                "Full sign-off by Pfizer Architecture and Compliance leads"
            ],
            high_level_scope=[
                "Cloud infrastructure architecture and provisioning",
                "Automated CI/CD data ingestion pipeline",
                "Validation and regulatory compliance documentation"
            ],
            exclusions=[
                "Legacy data cleansing prior to migration",
                "On-premise hardware decommissioning"
            ],
            source_reference=ref
        )
    )
    client.set_response(
        DeliverablesExtraction,
        DeliverablesExtraction(
            deliverables=[
                Deliverable(
                    id="DEL-01",
                    name="Cloud Architecture & Security Design",
                    description="Cloud Architecture & Security Design",
                    source_reference=ref,
                    owner="Talent PM",
                    acceptance_criteria="Approved by Pfizer Enterprise Architecture Board",
                    evidence_required="Architecture Blueprint & Threat Model Document",
                    client_approver="Pfizer Chief Architect"
                ),
                Deliverable(
                    id="DEL-02",
                    name="Automated CI/CD Data Ingestion Pipeline",
                    description="Automated CI/CD Data Ingestion Pipeline",
                    source_reference=ref,
                    owner="Talent PM",
                    acceptance_criteria="Passing automated test suite report & pipeline run logs approved by Pfizer Data Engineering Lead",
                    evidence_required="Passing automated test suite report & pipeline run logs",
                    client_approver="Pfizer Data Engineering Lead"
                ),
                Deliverable(
                    id="DEL-03",
                    name="Validation and Compliance Documentation",
                    description="Validation and Compliance Documentation",
                    source_reference=ref,
                    owner="Talent PM",
                    acceptance_criteria="Signed off by Compliance Lead",
                    evidence_required="21 CFR Part 11 Validation Matrix & Traceability Report",
                    client_approver="Pfizer Regulatory Compliance Officer"
                )
            ]
        )
    )
    client.set_response(
        MilestonesExtraction,
        MilestonesExtraction(
            milestones=[
                Milestone(
                    id="M1",
                    description="Project Kickoff & Architecture Baseline",
                    external_date=date(2026, 10, 15),
                    internal_buffer_date=date(2026, 10, 8),
                    owner="Delivery Manager",
                    key_dependencies=["AWS IAM provisioning"],
                    source_reference=ref
                ),
                Milestone(
                    id="M2",
                    description="Data Pipeline Production Go-Live",
                    external_date=date(2026, 11, 30),
                    internal_buffer_date=None,  # Will be calculated by aggregator
                    owner="Delivery Manager",
                    key_dependencies=["Sample clinical dataset delivery"],
                    source_reference=ref
                )
            ]
        )
    )
    client.set_response(
        RAIDExtraction,
        RAIDExtraction(
            items=[
                RiskAssumption(
                    type="Risk",
                    description="Client IAM and AWS account provisioning delays",
                    category="Technical / Cloud",
                    owner="Delivery Manager",
                    probability="High",
                    impact="High",
                    severity="High",
                    trigger_or_early_warning="No IAM access provided 5 days prior to sprint 1",
                    mitigation_or_response="Escalate to Pfizer VP Sponsor and utilize local sandbox",
                    status="Open",
                    source_reference=ref
                ),
                RiskAssumption(
                    type="Assumption",
                    description="Pfizer provides sample dataset 2 weeks prior to sprint 1",
                    category="Data / Customer",
                    owner="PMO Lead",
                    status="Open",
                    source_reference=ref
                ),
                RiskAssumption(
                    type="Dependency",
                    description="Third-party vendor API access tokens and test endpoints",
                    category="External API",
                    owner="Client Lead",
                    status="Open",
                    source_reference=ref
                )
            ]
        )
    )
    client.set_response(
        QuestionsExtraction,
        QuestionsExtraction(
            open_questions=[
                "Confirm Pfizer UAT sign-off criteria for automated data pipeline.",
                "Validate whether internal QA environment is provided by client."
            ]
        )
    )
    client.set_response(
        SOWInterpretationExtraction,
        SOWInterpretationExtraction(
            contracted_deliverables=[
                "Cloud Architecture & Security Design",
                "Automated CI/CD Data Ingestion Pipeline",
                "Validation and Compliance Documentation"
            ],
            out_of_scope_items=[
                "Legacy on-premise hardware decommissioning",
                "Pre-migration data cleansing and enrichment"
            ],
            customer_obligations=[
                "Provide AWS account access and role credentials",
                "Deliver anonymized clinical test datasets",
                "Review deliverable submissions within 5 business days"
            ],
            assumptions=[
                "Core team operates remotely across Eastern time zone",
                "Pfizer security review board approves standard Terraform modules"
            ],
            constraints=[
                "HIPAA and 21 CFR Part 11 regulatory compliance",
                "Dedicated AWS VPC isolation requirements"
            ],
            platform_environment_commitments=[
                "AWS Cloud Infrastructure (EKS, S3, RDS PostgreSQL, IAM)"
            ],
            dependencies=[
                "Third-party clinical EDC system API access tokens"
            ],
            approval_expectations="Formal written approval from Pfizer Engineering Lead within 5 business days.",
            ambiguity_notes=[
                "Automated pipeline UAT threshold not defined in Section 4.2 of SOW."
            ],
            source_reference=ref
        )
    )
    client.set_response(
        DecisionsExtraction,
        DecisionsExtraction(
            decisions=[
                DecisionItem(
                    id="DEC-01",
                    decision_text="Adopt Terraform for all AWS cloud infrastructure provisioning.",
                    decision_owner="Sarah Connor (PMO Lead)",
                    status="Approved",
                    rationale="Enables standardized CI/CD deployment and automated audit trails.",
                    source_reference=ref
                ),
                DecisionItem(
                    id="DEC-02",
                    decision_text="Set project governance tier to Partnered with weekly PSR reporting.",
                    decision_owner="Jane Doe (Delivery Manager)",
                    status="Approved",
                    rationale="Matches engagement size, complexity, and client risk profile.",
                    source_reference=ref
                )
            ]
        )
    )
    client.set_response(
        ContractConflictsExtraction,
        ContractConflictsExtraction(
            ambiguities=[
                ContractAmbiguityItem(
                    anomaly_id="AMB-01",
                    category="Ambiguous Acceptance",
                    conflicting_clauses="Section 4.2 states acceptance requires 'complete client satisfaction' whereas Section 2.1 defines automated pytest validation suite.",
                    risk_impact="Subjective sign-off criteria could lead to prolonged review cycles and milestone delays.",
                    recommended_clarification="Align contractual acceptance criteria to objective automated test passing metrics.",
                    status="Open",
                    source_reference=ref
                ),
                ContractAmbiguityItem(
                    anomaly_id="CONF-01",
                    category="Date Conflict",
                    conflicting_clauses="Proposal schedule commits Milestone 2 delivery by 2026-11-15, but SOW Table 3 lists 2026-11-30.",
                    risk_impact="2-week schedule discrepancy between commercial proposal and signed SOW baseline.",
                    recommended_clarification="Confirm 2026-11-30 as the binding contractual date for M2 Production Go-Live.",
                    status="Open",
                    source_reference=ref
                )
            ]
        )
    )
    client.set_response(
        StakeholdersExtraction,
        StakeholdersExtraction(
            stakeholders=[
                Stakeholder(
                    name="Sarah Connor",
                    role="PMO Lead",
                    organization="Toptal PMO",
                    decision_rights="G-01 Gate Sign-off, Talent Staffing/Replacement, Work-at-Risk Approvals, Delivery Risk & Recovery",
                    approver_responsibilities="G-01 Gate, Baseline Exceptions, PMO Health Ratings, Talent Baseline Sign-off",
                    escalation_responsibility="Director, PMO",
                    reporting_accountability="Independent Weekly Health Rating, Leadership Rollup"
                ),
                Stakeholder(
                    name="Director, PMO",
                    role="Director, PMO",
                    organization="Toptal PMO Leadership",
                    decision_rights="Elevated Tier Approvals, Major Commercial Exception Sign-offs, Executive Escalations",
                    approver_responsibilities="Elevated Tier G-01 Concurrence, Governance Policy Exceptions",
                    escalation_responsibility="VP, Delivery / Executive Leadership",
                    reporting_accountability="Executive PMO Portfolio Review"
                ),
                Stakeholder(
                    name="Jane Doe",
                    role="Delivery Manager",
                    organization="Toptal",
                    decision_rights="Voice of the customer, scope accountability, client alignment",
                    approver_responsibilities="Scope change alignment, handoff readiness",
                    escalation_responsibility="PMO Lead",
                    reporting_accountability="Weekly PSR Review"
                ),
                Stakeholder(
                    name="John Smith",
                    role="Talent PM",
                    organization="Toptal",
                    decision_rights="Project delivery, sprint coordination, day-to-day execution",
                    approver_responsibilities="Work package progress, deliverable submission drafts",
                    escalation_responsibility="Delivery Manager",
                    reporting_accountability="Weekly PSR Author"
                ),
                Stakeholder(
                    name="Pfizer VP Sponsor",
                    role="Client Sponsor / Approver",
                    organization="Pfizer Inc.",
                    decision_rights="Contractual approvals, deliverable sign-offs, change orders",
                    approver_responsibilities="Deliverables acceptance, SOW amendments",
                    escalation_responsibility="Pfizer Executive Leadership",
                    reporting_accountability="Recipient of Weekly PSR & MBR"
                )
            ]
        )
    )
    client.set_response(
        CommercialGuardrailsExtraction,
        CommercialGuardrailsExtraction(
            commercial_guardrails=CommercialGuardrail(
                contract_type_implication="Time and Materials contract: Weekly burn oversight and milestone alignment.",
                billing_consumption_assumption="Weekly timesheet approval against contracted SOW rate card.",
                staffing_assumption="Dedicated core delivery team staffing as defined in Section 3.",
                commercial_exposure_note="Client dependency delays must be logged in RAID to prevent unfunded burn.",
                approved_work_rule="Only explicitly contracted SOW scope and approved Change Orders are authorized for execution.",
                non_approved_work_rule="Tasks exceeding agreed monthly burn ceiling require written client authorization.",
                work_at_risk_rule="Work-at-risk requires written PMO Lead approval and executive exception sign-off.",
                change_control_trigger="Budget burndown exceeding forecast by >10% or scope modification.",
                change_order_route="PMO Lead leads -> DM aligns client -> Client approves -> Contracting issues change order.",
                budget_baseline="$250,000 USD T&M Budget Cap",
                variance_indicator="Green (<5% variance)",
                margin_risk_indicator="Low",
                escalation_threshold="Budget burn rate exceeding weekly cap by >10%",
                source_reference=ref
            )
        )
    )
    client.set_response(
        TalentOnboardingExtraction,
        TalentOnboardingExtraction(
            talent_onboarding=TalentOnboardingRecord(
                talent_pm="John Smith",
                delivery_manager="Jane Doe",
                pmo_lead="Sarah Connor",
                onboarding_completion_date=date(2026, 10, 1),
                onboarding_attendees=["Sarah Connor", "Jane Doe", "John Smith"],
                artifacts_walked_through=["Startup Readiness Checklist", "Charter", "Deliverables Matrix", "RAID Log", "Commercial Guardrails"],
                delivery_talent_roster=[
                    TalentMember(role="Delivery Manager", name="Jane Doe", required_skills="Delivery Governance, Client Management", status="Confirmed"),
                    TalentMember(role="Talent PM", name="John Smith", required_skills="Agile Coordination, PMO Delivery", status="Confirmed"),
                    TalentMember(role="Cloud Architect", name="Alex Vance", required_skills="AWS Architecture, Terraform, Security", status="Confirmed"),
                    TalentMember(role="Data Engineer", name="Gordon Freeman", required_skills="Python, ETL Pipelines, CI/CD", status="Confirmed")
                ],
                required_roles=["Delivery Manager", "Talent PM", "Cloud Architect", "Data Engineer"],
                required_skills=["AWS Architecture", "Python ETL", "Agile Execution", "CI/CD Pipelines"],
                staffing_gaps=[],
                replacement_plan="PMO Lead coordinates talent matching within 5 business days if replacement needed.",
                team_baseline_review_confirmation=True,
                source_reference=ref
            )
        )
    )
    client.set_response(
        ScopeDecompositionExtraction,
        ScopeDecompositionExtraction(
            work_packages=[
                WorkPackageSeed(id="WP-01", parent_deliverable_id="DEL-01", title="AWS IAM & VPC Architecture", description="Provision core network and security baseline.", preliminary_sequence=1, owner="Cloud Architect", status="Draft"),
                WorkPackageSeed(id="WP-02", parent_deliverable_id="DEL-02", title="Automated Ingestion Pipeline", description="Develop CI/CD automated pipeline.", preliminary_sequence=2, owner="Data Engineer", status="Draft"),
                WorkPackageSeed(id="WP-03", parent_deliverable_id="DEL-03", title="Compliance & Traceability", description="Generate 21 CFR Part 11 validation evidence.", preliminary_sequence=3, owner="Talent PM", status="Draft")
            ]
        )
    )
    client.set_response(
        AcceptanceProcessExtraction,
        AcceptanceProcessExtraction(
            acceptance_matrix_items=[
                Deliverable(id="DEL-01", name="Cloud Architecture & Security Design", description="Cloud Architecture & Security Design", source_reference=ref, owner="Talent PM", acceptance_criteria="Approved by Pfizer Enterprise Architecture Board", evidence_required="Architecture Blueprint & Threat Model Document", client_approver="Pfizer Chief Architect"),
                Deliverable(id="DEL-02", name="Automated CI/CD Data Ingestion Pipeline", description="Automated CI/CD Data Ingestion Pipeline", source_reference=ref, owner="Talent PM", acceptance_criteria="Passing automated test suite report & pipeline run logs approved by Pfizer Data Engineering Lead", evidence_required="Passing automated test suite report & pipeline run logs", client_approver="Pfizer Data Engineering Lead"),
                Deliverable(id="DEL-03", name="Validation and Compliance Documentation", description="Validation and Compliance Documentation", source_reference=ref, owner="Talent PM", acceptance_criteria="Signed off by Compliance Lead", evidence_required="21 CFR Part 11 Validation Matrix & Traceability Report", client_approver="Pfizer Regulatory Compliance Officer")
            ]
        )
    )
    client.set_response(
        CommunicationsExtraction,
        CommunicationsExtraction(
            communications=[
                CommunicationsPlanItem(
                    id="COM-01",
                    name="Weekly Project Status Report (PSR)",
                    audience="Pfizer & Toptal Leadership",
                    content_owner="Talent PM",
                    cadence="Weekly (Fridays)",
                    format="Email & PDF attachment",
                    delivery_day="Friday"
                ),
                CommunicationsPlanItem(
                    id="COM-02",
                    name="Monthly Business Review (MBR)",
                    audience="Pfizer Executive Sponsor & Toptal DM",
                    content_owner="Delivery Manager",
                    cadence="Monthly",
                    format="Virtual Presentation",
                    delivery_day="Last Thursday"
                )
            ]
        )
    )
    return client
