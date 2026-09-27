"""Unit tests for Word document generation and G-01 checklist rendering."""

import pytest
from pathlib import Path
import docx
from src.core.models import StartupKitBaseline
from src.generators.docx_generator import DocxGenerator, sanitize_filename
from src.generators.checklist import G01ChecklistRenderer


def test_sanitize_filename():
    assert sanitize_filename("Pfizer Cloud Migration") == "Pfizer_Cloud_Migration"
    assert sanitize_filename("Project: Alpha / Beta (v1)") == "Project_Alpha__Beta_v1"
    assert sanitize_filename("") == "Project"


def test_docx_generator_output(sample_baseline, tmp_path):
    output_dir = tmp_path / "output"
    generator = DocxGenerator()
    generated_file = generator.write_docx(sample_baseline, output_dir)

    assert generated_file.exists()
    assert generated_file.name == "Pfizer_Cloud_Migration_Startup_Kit.docx"
    assert generated_file.suffix == ".docx"

    # Open and inspect the generated Word document
    doc = docx.Document(str(generated_file))

    # Verify headings and text
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "TOPTAL PMO STARTUP KIT" in full_text
    assert "Pfizer Cloud Migration" in full_text

    # Verify G-01 Executive Readiness Gateway comes BEFORE Layer 1
    g01_idx = full_text.find("Executive Readiness Gateway: Startup Readiness Checklist (G-01)")
    layer1_idx = full_text.find("Layer 1: Executive Startup Pack")
    layer2_idx = full_text.find("Layer 2: Delivery Control Pack")
    layer3_idx = full_text.find("Layer 3: Assurance Pack")

    assert g01_idx != -1, "G-01 Executive Readiness Gateway must be present"
    assert layer1_idx != -1, "Layer 1 must be present"
    assert layer2_idx != -1, "Layer 2 must be present"
    assert layer3_idx != -1, "Layer 3 must be present"
    assert g01_idx < layer1_idx < layer2_idx < layer3_idx, "Document sections must follow: G-01 Gateway -> Layer 1 -> Layer 2 -> Layer 3"

    # Verify all Section 4 layer headings
    assert "Layer 1: Executive Startup Pack" in full_text
    assert "Project Startup Charter" in full_text
    assert "SOW Interpretation Summary" in full_text
    assert "Milestone Delivery Plan" in full_text
    assert "Layer 2: Delivery Control Pack" in full_text
    assert "Scope Decomposition / Backlog Seed" in full_text
    assert "Deliverables and Acceptance Matrix" in full_text
    assert "Dependency and Assumption Log" in full_text
    assert "RAID Log" in full_text
    assert "Communications and Reporting Plan" in full_text
    assert "Layer 3: Assurance Pack" in full_text
    assert "Stakeholder and Responsibility Model" in full_text
    assert "RACI / Decision Rights Matrix" in full_text
    assert "Commercial and Margin Guardrails" in full_text
    assert "Talent Onboarding Record" in full_text

    # Verify tables
    assert len(doc.tables) >= 5

    table_texts = []
    for tbl in doc.tables:
        for row in tbl.rows:
            row_str = " | ".join(c.text.strip() for c in row.cells)
            table_texts.append(row_str)

    all_table_content = "\n".join(table_texts)
    assert "DEL-01" in all_table_content
    assert "Cloud Migration Architecture Design" in all_table_content
    assert "[CONFIRMATION REQUIRED]" in all_table_content  # DEL-02 acceptance criteria placeholder
    assert "M1" in all_table_content
    assert "2026-10-15" in all_table_content
    assert "G01-01" in all_table_content  # Checklist item
    assert "G01-07" in all_table_content  # Checklist item


def test_checklist_renderer(sample_baseline, tmp_path):
    doc = docx.Document()
    renderer = G01ChecklistRenderer()
    renderer.render(doc, sample_baseline)

    assert len(doc.tables) >= 1
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Startup Readiness Checklist" in full_text


def test_checklist_artifact_coverage_and_exceptions(sample_source_ref):
    from src.llm.aggregator import BaselineAggregator
    from src.core.models import (
        CharterExtraction,
        DeliverablesExtraction,
        MilestonesExtraction,
        RAIDExtraction,
        Deliverable,
        Milestone,
        RiskAssumption,
    )

    aggregator = BaselineAggregator()
    charter = CharterExtraction(
        project_name="Compliance Audit System",
        governance_tier="Partnered",
        contract_type="Fixed Bid",
        source_reference=sample_source_ref
    )

    # Deliverable with missing criteria to trigger Review Required
    deliverables = DeliverablesExtraction(deliverables=[
        Deliverable(
            id="DEL-01",
            description="Audit Reporting Engine",
            source_reference=sample_source_ref,
            acceptance_criteria=None  # Triggers unconfirmed criteria
        )
    ])

    # Milestone with missing date to trigger Confirmation Required
    milestones = MilestonesExtraction(milestones=[
        Milestone(
            id="M1",
            description="Production Readiness",
            external_date=None,  # Triggers unconfirmed date
            source_reference=sample_source_ref
        )
    ])

    raid = RAIDExtraction(items=[
        RiskAssumption(
            type="Risk",
            description="Regulatory review timeline slip",
            source_reference=sample_source_ref
        )
    ])

    baseline = aggregator.aggregate(
        charter=charter,
        deliverables_ext=deliverables,
        milestones_ext=milestones,
        raid_ext=raid
    )

    # Verify checklist covers all Section 4 artifacts
    assert len(baseline.readiness_checklist) >= 13

    # Check that each item has owner, status, evidence, reviewer, approver
    for item in baseline.readiness_checklist:
        assert item.item_id.startswith("G01-")
        assert item.gate_criterion != ""
        assert item.related_section4_artifact != ""
        assert item.owner != ""
        assert item.reviewer != ""
        assert item.approver != ""
        assert item.status in [
            "Not Started",
            "In Progress",
            "Review Required",
            "Confirmation Required",
            "Complete",
            "Exception Required",
            "Approved",
            "Approved with Exception",
            "Rework Required"
        ]

    # Verify incomplete items have Review/Confirmation/Exception flags
    deliv_check = next(c for c in baseline.readiness_checklist if "Deliverables" in c.related_section4_artifact)
    assert deliv_check.status == "Review Required"
    assert deliv_check.exception_required is True

    ms_check = next(c for c in baseline.readiness_checklist if "Milestone" in c.related_section4_artifact)
    assert ms_check.status == "Confirmation Required"
    assert ms_check.exception_required is True
