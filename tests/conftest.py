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
    GovernanceContext,
    StartupKitBaseline,
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
