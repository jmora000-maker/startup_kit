import os
from pathlib import Path
from datetime import date
from src.core.models import (
    StartupKitBaseline,
    ProjectStartupCharter,
    SOWInterpretationSummary,
    Milestone,
    Deliverable,
    RiskAssumption,
    DependencyAssumptionItem,
)
from src.generators.client_deck.builder import build_client_deck_model
from src.generators.client_deck.writer import write_client_deck


def main():
    out_dir = Path("output/review_htl_52")
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Real sample_real_failing_client_baseline (Phase 1 18 deliverables)
    from tests.test_out_14 import sample_real_failing_client_baseline
    baseline_18 = sample_real_failing_client_baseline.__wrapped__()

    deck1_path = out_dir / "Phase1_18_Deliverables_Kickoff_Deck.pptx"
    model1 = build_client_deck_model(baseline_18)
    write_client_deck(model1, deck1_path)
    print(f"Generated {deck1_path}")

    # 2. Financial scrubbing baseline
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

    deck2_path = out_dir / "Financial_Scrubbing_Validation_Kickoff_Deck.pptx"
    model2 = build_client_deck_model(financial_baseline)
    write_client_deck(model2, deck2_path)
    print(f"Generated {deck2_path}")


if __name__ == "__main__":
    main()
