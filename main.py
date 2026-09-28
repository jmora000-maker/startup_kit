"""Toptal PMO Startup Kit Generator CLI Entry Point."""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional, Union

from src.config import config, normalize_person_name
from src.extractors.service import IngestionService
from src.llm.client import LangChainLLMClient, MockLLMClient
from src.llm.aggregator import BaselineAggregator
from src.generators.docx_generator import DocxGenerator
from src.orchestrator import StartupKitController
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
from datetime import date


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )


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
            communications_plan=[
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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Toptal PMO Startup Kit Generator - Automated Document Ingestion and Word Report Generation."
    )
    parser.add_argument(
        "--inputs-dir",
        type=Path,
        default=None,
        help="Path to inputs directory containing SOWs and decks (default: inputs/)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Path to output directory for generated Word reports (default: output/)"
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=None,
        help="Explicit destination file path for regenerated Word report"
    )
    parser.add_argument(
        "--reingest-docx",
        "--docx-file",
        type=Path,
        dest="reingest_docx",
        default=None,
        help="Path to existing *_Startup_Kit.docx to re-ingest and recalculate readiness score"
    )
    parser.add_argument(
        "--provider",
        "--llm-provider",
        type=str,
        default=config.default_provider,
        choices=["anthropic", "openai", "claude", "gpt"],
        help="LLM provider to use: 'anthropic' (Claude, default) or 'openai' (GPT)"
    )
    parser.add_argument(
        "--openai",
        "--open-ai",
        action="store_true",
        help="Use OpenAI as the LLM provider"
    )
    parser.add_argument(
        "--anthropic",
        "--claude",
        action="store_true",
        help="Use Anthropic Claude as the LLM provider (default)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="LLM model name (defaults to 'claude-sonnet-5-5' for Anthropic or 'gpt-4o' for OpenAI)"
    )
    parser.add_argument(
        "--tier",
        type=str,
        choices=["Guided", "Partnered", "Elevated"],
        default=None,
        help="Override Governance Tier (Guided, Partnered, Elevated)"
    )
    parser.add_argument(
        "--contract-type",
        type=str,
        default=None,
        help="Override Contract Type (e.g., 'Time and Materials', 'Fixed Bid')"
    )
    parser.add_argument(
        "--pmo-lead",
        type=str,
        default=None,
        help="PMO Lead name (defaults to '[UNASSIGNED - TO BE CONFIRMED]' if not provided)"
    )
    parser.add_argument(
        "--delivery-lead",
        "--delivery-manager",
        type=str,
        dest="delivery_lead",
        default=None,
        help="Delivery Lead / Manager name (defaults to '[UNASSIGNED - TO BE CONFIRMED]' if not provided)"
    )
    parser.add_argument(
        "--talent-pm",
        type=str,
        default=None,
        help="Talent PM name (defaults to '[UNASSIGNED - TO BE CONFIRMED]' if not provided)"
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Disable interactive directory and role prompts (uses default paths and unassigned roles)"
    )
    parser.add_argument(
        "--api-key",
        "--anthropic-api-key",
        type=str,
        dest="api_key",
        default=None,
        help="Anthropic API Key (overrides ANTHROPIC_API_KEY environment variable and .env)"
    )
    parser.add_argument(
        "--openai-api-key",
        type=str,
        dest="openai_api_key",
        default=None,
        help="OpenAI API Key for fallback or direct execution (overrides OPENAI_API_KEY environment variable and .env)"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run using offline deterministic Mock LLM client (no API keys required)"
    )
    parser.add_argument(
        "--export-tools",
        action="store_true",
        help="Export downstream PMO Operating System workbook toolkits (CSV/JSON seeds) to output/"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose debug logging"
    )
    return parser.parse_args()


def prompt_directories(
    inputs_dir: Optional[Union[str, Path]] = None,
    output_dir: Optional[Union[str, Path]] = None,
    interactive: bool = True,
    default_inputs_dir: Path = config.inputs_dir,
    default_output_dir: Path = config.output_dir
) -> tuple[Path, Path]:
    """Request input and output directory paths via CLI arguments or interactive prompts, falling back to defaults."""
    def _resolve(prompt_label: str, val: Optional[Union[str, Path]], default_path: Path) -> Path:
        if val is not None:
            if isinstance(val, str):
                cleaned = val.strip()
                return Path(cleaned) if cleaned else default_path
            return val
        if interactive:
            try:
                entered = input(f"Enter {prompt_label} [default: {default_path}]: ").strip()
                return Path(entered) if entered else default_path
            except (EOFError, OSError):
                return default_path
        return default_path

    resolved_inputs = _resolve("inputs directory", inputs_dir, default_inputs_dir)
    resolved_output = _resolve("output directory", output_dir, default_output_dir)
    return resolved_inputs, resolved_output


def prompt_reingest_file(
    docx_file: Optional[Union[str, Path]] = None,
    interactive: bool = True
) -> Optional[Path]:
    """Prompt for the path to the updated Startup Kit .docx file to re-ingest.

    A path/filename is required; there is no default. Typing 'exit' cancels and exits.
    """
    if docx_file is not None:
        if isinstance(docx_file, str):
            cleaned = docx_file.strip().strip("\"'")
            if cleaned:
                if cleaned.lower() in ("exit", "quit"):
                    return None
                return Path(cleaned)
            return None
        return docx_file

    if not interactive:
        return None

    while True:
        try:
            entered = input("Enter path to updated *_Startup_Kit.docx file (or type 'exit'): ").strip().strip("\"'")
            if not entered:
                print("Path/filename is required. Please enter a valid file path or type 'exit' to quit.")
                continue
            if entered.lower() in ("exit", "quit"):
                return None
            return Path(entered)
        except (EOFError, KeyboardInterrupt):
            return None


def prompt_execution_mode(interactive: bool = True) -> str:
    """Prompt user to select between Initial Generation (1) and DOCX Re-ingestion (2)."""
    if not interactive:
        return "1"
    try:
        print("Select Startup Kit execution mode:")
        print("  [1] Initial Generation (Ingest raw SOWs/decks from inputs directory)")
        print("  [2] Re-evaluate & Ingest updated *_Startup_Kit.docx")
        choice = input("Enter choice [1/2, default: 1]: ").strip()
        if choice in ("2", "re-evaluate", "reingest", "docx"):
            return "2"
        return "1"
    except (EOFError, OSError):
        return "1"


def prompt_role_names(
    pmo_lead: Optional[str] = None,
    delivery_lead: Optional[str] = None,
    talent_pm: Optional[str] = None,
    interactive: bool = True,
    default: str = "[UNASSIGNED - TO BE CONFIRMED]"
) -> tuple[str, str, str]:
    """Request leadership role names via CLI arguments or interactive prompts, defaulting to '[UNASSIGNED - TO BE CONFIRMED]'."""
    def _resolve(role_name: str, val: Optional[str]) -> str:
        if val is not None:
            cleaned = val.strip()
            return normalize_person_name(cleaned, default=default) if cleaned else default
        if interactive:
            try:
                entered = input(f"Enter {role_name} name [default: {default}]: ").strip()
                return normalize_person_name(entered, default=default) if entered else default
            except (EOFError, OSError):
                return default
        return default

    resolved_pmo_lead = _resolve("PMO Lead", pmo_lead)
    resolved_delivery_lead = _resolve("Delivery Lead", delivery_lead)
    resolved_talent_pm = _resolve("Talent PM", talent_pm)
    return resolved_pmo_lead, resolved_delivery_lead, resolved_talent_pm


def prompt_api_keys(
    api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    interactive: bool = False,
    default_anthropic_key: str = "",
    default_openai_key: str = "",
) -> tuple[str, str]:
    """Resolve Anthropic and OpenAI API keys via CLI arguments, environment variables, or configuration."""
    resolved_anthropic = api_key if api_key is not None else (default_anthropic_key or config.anthropic_api_key)
    resolved_openai = openai_api_key if openai_api_key is not None else (default_openai_key or config.openai_api_key)
    return resolved_anthropic, resolved_openai


def main():
    args = parse_args()
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger("main")

    logger.info("=========================================================")
    logger.info("    TOPTAL PMO STARTUP KIT GENERATOR (Readiness Phase)   ")
    logger.info("=========================================================")

    try:
        is_interactive = not args.non_interactive

        # Determine execution mode: Flag takes priority, then interactive prompt
        if args.reingest_docx is not None:
            mode = "2"
        elif is_interactive:
            mode = prompt_execution_mode(interactive=True)
        else:
            mode = "1"

        if mode == "2":
            target_docx = prompt_reingest_file(
                docx_file=args.reingest_docx,
                interactive=is_interactive,
            )
            if target_docx is None:
                if is_interactive:
                    logger.info("Exiting Startup Kit re-ingestion.")
                    return 0
                else:
                    logger.error("No DOCX file provided for re-ingestion mode. Specify --reingest-docx <path>.")
                    return 1

            logger.info("Mode: DOCX Re-ingestion & Readiness Recalculation")
            logger.info("Target Document: %s", target_docx)

            pmo_lead, delivery_lead, talent_pm = prompt_role_names(
                pmo_lead=args.pmo_lead,
                delivery_lead=args.delivery_lead,
                talent_pm=args.talent_pm,
                interactive=is_interactive
            )

            controller = StartupKitController(
                doc_writer=DocxGenerator(),
                aggregator=BaselineAggregator()
            )

            output_file = controller.run_reingest(
                docx_path=target_docx,
                output_dir=args.output_dir,
                output_file=args.output_file,
                pmo_lead=pmo_lead if (args.pmo_lead is not None or (is_interactive and pmo_lead != "[UNASSIGNED - TO BE CONFIRMED]")) else None,
                delivery_lead=delivery_lead if (args.delivery_lead is not None or (is_interactive and delivery_lead != "[UNASSIGNED - TO BE CONFIRMED]")) else None,
                talent_pm=talent_pm if (args.talent_pm is not None or (is_interactive and talent_pm != "[UNASSIGNED - TO BE CONFIRMED]")) else None,
                tier_override=args.tier,
                contract_type_override=args.contract_type,
                export_tools=args.export_tools,
            )

            logger.info("SUCCESS: Project Startup Kit re-evaluated and updated successfully!")
            logger.info("Updated Report File: %s", output_file.resolve())
            return 0

        # Mode 1: Initial Generation
        logger.info("Mode: Initial Generation (From SOWs and input artifacts)")
        inputs_dir, output_dir = prompt_directories(
            inputs_dir=args.inputs_dir,
            output_dir=args.output_dir,
            interactive=is_interactive,
            default_inputs_dir=config.inputs_dir,
            default_output_dir=config.output_dir
        )
        logger.info("Directories -> Inputs: %s | Output: %s", inputs_dir, output_dir)

        pmo_lead, delivery_lead, talent_pm = prompt_role_names(
            pmo_lead=args.pmo_lead,
            delivery_lead=args.delivery_lead,
            talent_pm=args.talent_pm,
            interactive=is_interactive
        )
        logger.info("Leadership Roles -> PMO Lead: %s | Delivery Lead: %s | Talent PM: %s", pmo_lead, delivery_lead, talent_pm)

        # Determine selected LLM provider
        if args.openai or (args.provider and args.provider.lower() in ("openai", "open-ai", "gpt", "chatgpt")):
            selected_provider = "openai"
        else:
            selected_provider = "anthropic"

        active_api_key, active_openai_key = prompt_api_keys(
            api_key=args.api_key,
            openai_api_key=getattr(args, "openai_api_key", None),
            interactive=False,
            default_anthropic_key=config.anthropic_api_key,
            default_openai_key=config.openai_api_key,
        )

        if args.mock:
            logger.info("Using offline Mock LLM client for deterministic generation.")
            llm_client = create_mock_llm_client()
        elif selected_provider == "openai":
            if not active_openai_key:
                logger.warning("OPENAI_API_KEY is not set. Falling back to offline Mock LLM client.")
                llm_client = create_mock_llm_client()
            else:
                openai_model = args.model if (args.model and args.model != config.anthropic_model) else config.openai_model
                logger.info("Using OpenAI LangChain client with model: %s", openai_model)
                llm_client = LangChainLLMClient(
                    api_key="",
                    openai_api_key=active_openai_key,
                    openai_model_name=openai_model,
                    temperature=config.temperature,
                )
        else:  # anthropic (default)
            if not active_api_key and not active_openai_key:
                logger.warning("Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY is set. Falling back to offline Mock LLM client.")
                llm_client = create_mock_llm_client()
            elif not active_api_key and active_openai_key:
                logger.info("ANTHROPIC_API_KEY is not set; using OpenAI LangChain client with model: %s", config.openai_model)
                llm_client = LangChainLLMClient(
                    api_key="",
                    openai_api_key=active_openai_key,
                    openai_model_name=config.openai_model,
                    temperature=config.temperature,
                )
            else:
                anthropic_model = args.model or config.anthropic_model
                if active_openai_key:
                    logger.info("Using Anthropic Claude client (%s) with OpenAI fallback (%s)", anthropic_model, config.openai_model)
                else:
                    logger.info("Using Anthropic Claude LangChain client with model: %s", anthropic_model)

                llm_client = LangChainLLMClient(
                    api_key=active_api_key,
                    model_name=anthropic_model,
                    temperature=config.temperature,
                    openai_api_key=active_openai_key,
                    openai_model_name=config.openai_model,
                )

        controller = StartupKitController(
            ingestion_service=IngestionService(),
            llm_client=llm_client,
            aggregator=BaselineAggregator(),
            doc_writer=DocxGenerator()
        )

        output_file = controller.run(
            inputs_dir=inputs_dir,
            output_dir=output_dir,
            tier_override=args.tier,
            contract_type_override=args.contract_type,
            pmo_lead=pmo_lead,
            delivery_lead=delivery_lead,
            talent_pm=talent_pm,
            export_tools=args.export_tools,
        )

        if hasattr(llm_client, "fallback_domains") and llm_client.fallback_domains:
            logger.info("Notice: The following extraction domain(s) used secondary OpenAI fallback: %s", ", ".join(llm_client.fallback_domains))

        logger.info("SUCCESS: Project Startup Kit generated successfully!")
        logger.info("Report File: %s", output_file.resolve())
        return 0

    except Exception as exc:
        logger.error("Startup Kit generation failed: %s", exc, exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())
