"""Tests for MAP-16: 1:1 mapping from SOW Work Output bullets to Deliverables and SOW reference rollup."""

import pytest
from datetime import date
from io import BytesIO
from docx import Document

from src.core.models import (
    StartupKitBaseline,
    Deliverable,
    Milestone,
    SOWWorkItem,
    WorkPackageSeed,
    SourceReference,
    ValidationReport,
)
from src.llm.validation import validate_and_repair_baseline
from src.generators.docx_generator import DocxGenerator


# Real Undivide Project SOW Section 3 Work Output & Acceptance Criteria verbatim data (27 total bullets: M1=8, M2=6, M3=5, M4=8)
UNDIVIDE_M1_WORK_OUTPUTS = [
    (
        "Postgres schema and Drizzle migrations, with the twenty-five (25) Baseline MVP facility records migrated",
        "All twenty-five (25) facility records are present in Postgres on staging, and a reconciliation report provided by Toptal shows no field-level discrepancies against the Baseline MVP data",
    ),
    (
        "Normalization layer and ingestion framework deployed in Client's AWS account",
        "The AWS data tier can be provisioned in Client's AWS account from the infrastructure-as-code definition",
    ),
    (
        "Infrastructure-as-code definition for the AWS data tier",
        "The AWS data tier can be provisioned in Client's AWS account from the infrastructure-as-code definition",
    ),
    (
        "Ingestion connectors for the three (3) Launch Sources, with data-quality checks",
        "Each Launch Source connector completes a scheduled ingestion run on staging that lands raw data in Amazon S3, writes normalized data, and loads application-served records into Postgres, with data-quality check results logged for each run. A simulated failure of one Launch Source connector does not stop ingestion from the other Launch Sources and generates an alert",
    ),
    (
        "Scraper Interface Specification (documented interface, schema, and sample payload mapping between Client's news-site scraper output and Toptal's ingestion pipeline)",
        "The Scraper Interface Specification is delivered to Client with confirmed alignment by the end of Week 1",
    ),
    (
        "Ingestion connector for Client's news-site scraper output, built to the Scraper Interface Specification",
        "A representative sample payload provided by Client is ingested through the scraper connector on staging, normalized, and loaded into Postgres",
    ),
    (
        "Authenticated API with rate limiting, export endpoints, and API documentation",
        "API endpoints reject unauthenticated requests, enforce the configured rate limit, and return export data in the formats stated in the API documentation",
    ),
    (
        "Automated backend API route test suite",
        "The backend API route test suite executes against staging with all tests passing",
    ),
]

UNDIVIDE_M2_WORK_OUTPUTS = [
    (
        "Enrichment service integrating Client's AI component into the Platform codebase",
        "The enrichment service validates each output from Client's AI component against the Client-approved output schema; conforming outputs are written to the Platform, and non-conforming outputs are logged and not written",
    ),
    (
        "Prompt versioning and documentation mechanism for Client-provided prompts",
        "Client-provided prompts are stored under version control, and each enriched record references the prompt version used to produce it",
    ),
    (
        "Confidence-score capture and threshold-based review-queue routing",
        "Each enriched record stores the confidence score produced by Client's AI component, and records below the configured threshold are placed in the review queue and are not published until a reviewer actions them",
    ),
    (
        "Review-queue admin user interface (design files and built interface)",
        "A reviewer can approve, edit, or reject a queued record in the review-queue admin user interface, and each action is recorded with the user and a timestamp",
    ),
    (
        "Output caching and per-run cost-ceiling controls",
        "Re-submission of unchanged input is served from cache without a new LLM call, and an enrichment run stops issuing LLM calls and logs the event when the configured cost ceiling is reached",
    ),
    (
        "Automated ingestion normalizer test suite",
        "The ingestion normalizer test suite executes with all tests passing",
    ),
]

UNDIVIDE_M3_WORK_OUTPUTS = [
    (
        "Role-based access control for the Investor, Regulator, Community, and Analyst personas, with a role-permission matrix and automated access-control test suite",
        "The automated access-control test suite verifies that each of the four (4) personas can access only the views and data permitted by the role-permission matrix approved by Client, and passes on staging",
    ),
    (
        "Role-based views and admin panel (design files and built interface) supporting user invitations and role management, review-queue management, and data flagging",
        "An administrator can invite a user, assign or change a user's role, deactivate a user, and flag a data record; flagged records are visible in the admin panel. Automated accessibility testing of the role-based views and admin panel reports no critical or serious WCAG 2.1 Level AA violations",
    ),
    (
        "Observability stack: Sentry error monitoring, PostHog product analytics, and structured logging",
        "Application errors on staging are captured in Sentry, PostHog records the analytics events listed in the observability documentation, and application and ingestion services emit structured logs",
    ),
    (
        "CI/CD pipeline for staging and production",
        "A merge to the main branch triggers the CI/CD pipeline, which runs the automated test suites and deploys to staging; a failing test blocks deployment",
    ),
    (
        "All Phase 3 Work Output deployed to staging",
        "Phase 3 Work Output is operational on staging alongside the previously accepted Milestone 1 and Milestone 2 Work Output and is demonstrated to Client.",
    ),
]

UNDIVIDE_M4_WORK_OUTPUTS = [
    (
        "Platform deployed to the production environment",
        "The Platform is live in the production environment and accessible to the Pilot Partner user accounts provisioned by Client",
    ),
    (
        "Pilot Partner onboarding support",
        "The Platform is live in the production environment and accessible to the Pilot Partner user accounts provisioned by Client",
    ),
    (
        "Architecture documentation and architecture decision records",
        "All documentation, runbooks, and the mentoring runbook are committed to Client's GitHub repository",
    ),
    (
        "Runbooks covering the application and the AWS data tier, including deploy and rollback",
        "A deploy and rollback on staging is demonstrated to Client's internal team by following the runbook during a knowledge-transfer session",
    ),
    (
        "Platform data structure documentation based on the Launch Sources",
        "All documentation, runbooks, and the mentoring runbook are committed to Client's GitHub repository",
    ),
    (
        "Written mentoring runbook, including session structure, a task backlog graded by difficulty, and review checklists",
        "All documentation, runbooks, and the mentoring runbook are committed to Client's GitHub repository",
    ),
    (
        "Design files and design documentation",
        "All documentation, runbooks, and the mentoring runbook are committed to Client's GitHub repository",
    ),
    (
        "Completed handover checklist",
        "Each item on the handover checklist is marked complete",
    ),
]

ALL_UNDIVIDE_WORK_OUTPUTS = (
    [("M1", wo, ac, f"M1-WO-{idx+1:02d}") for idx, (wo, ac) in enumerate(UNDIVIDE_M1_WORK_OUTPUTS)] +
    [("M2", wo, ac, f"M2-WO-{idx+1:02d}") for idx, (wo, ac) in enumerate(UNDIVIDE_M2_WORK_OUTPUTS)] +
    [("M3", wo, ac, f"M3-WO-{idx+1:02d}") for idx, (wo, ac) in enumerate(UNDIVIDE_M3_WORK_OUTPUTS)] +
    [("M4", wo, ac, f"M4-WO-{idx+1:02d}") for idx, (wo, ac) in enumerate(UNDIVIDE_M4_WORK_OUTPUTS)]
)


def test_map_16_undivide_sow_section_3_27_deliverables_and_acceptance_criteria():
    """MAP-16: 27 real Work Output bullets produce 27 deliverables (1:1), each with correct criteria and references."""
    assert len(ALL_UNDIVIDE_WORK_OUTPUTS) == 27
    assert len(UNDIVIDE_M1_WORK_OUTPUTS) == 8
    assert len(UNDIVIDE_M2_WORK_OUTPUTS) == 6
    assert len(UNDIVIDE_M3_WORK_OUTPUTS) == 5
    assert len(UNDIVIDE_M4_WORK_OUTPUTS) == 8

    deliverables = []
    catalogue = []
    for idx, (ms_id, wo_title, ac_text, ref) in enumerate(ALL_UNDIVIDE_WORK_OUTPUTS, start=1):
        deliv_id = f"DEL-{idx:02d}"
        deliverables.append(
            Deliverable(
                id=deliv_id,
                name=wo_title,
                description=f"Delivery and operationalization of {wo_title}.",
                acceptance_criteria=ac_text,
                sow_reference=ref,
                owner="Toptal Delivery Team",
                client_approver="Client Approver",
                source_reference=SourceReference(
                    document_name="The Undivide Project SOW",
                    clause_or_slide=f"Section 3 - {ms_id}",
                    confidence_score=0.95,
                )
            )
        )
        catalogue.append(
            SOWWorkItem(
                reference=ref,
                reference_kind="Synthetic",
                title=wo_title,
                phase=ms_id,
                owner="Toptal",
                type="Build",
                deliverable_id=deliv_id,
            )
        )

    milestones = [
        Milestone(id="M1", description="Phase 1 - Data and Backend Foundation: Infrastructure and pipeline deployment."),
        Milestone(id="M2", description="Phase 2 - LLM Enrichment Layer: Enrichment service and prompt pipelines."),
        Milestone(id="M3", description="Phase 3 - Query and Retrieval Interface: Search API and caching layer."),
        Milestone(id="M4", description="Phase 4 - Access Control, Observability, and Pilot Readiness: RBAC and production cutover."),
    ]

    baseline = StartupKitBaseline(
        project_name="The Undivide Project",
        deliverables=deliverables,
        milestones=milestones,
        sow_stories_catalogue=catalogue,
        backlog_seed=[],
    )

    validate_and_repair_baseline(baseline)

    # 1. Strict 1:1 count verification: 27 real Work Output bullets produce 27 real deliverables
    assert len(baseline.deliverables) == 27

    # 2. Complete, correctly-attached Acceptance Criteria text for every deliverable
    for idx, (ms_id, wo_title, ac_text, ref) in enumerate(ALL_UNDIVIDE_WORK_OUTPUTS, start=1):
        d = baseline.deliverables[idx - 1]
        assert d.id == f"DEL-{idx:02d}"
        assert d.name == wo_title
        assert "; ".join(d.acceptance_criteria) == ac_text or d.acceptance_criteria == [ac_text]
        assert d.sow_reference == ref

    # 3. Check specific DEL-02 and DEL-04 items (connector ingestion criteria attached to its own deliverable)
    del_04 = baseline.deliverables[3]  # Ingestion connectors for the three (3) Launch Sources
    assert del_04.id == "DEL-04"
    assert any("Each Launch Source connector completes a scheduled ingestion run on staging" in c for c in del_04.acceptance_criteria)
    assert del_04.sow_reference == "M1-WO-04"

    del_02 = baseline.deliverables[1]  # Normalization layer and ingestion framework deployed in Client's AWS account
    assert del_02.id == "DEL-02"
    assert any("The AWS data tier can be provisioned in Client's AWS account" in c for c in del_02.acceptance_criteria)
    assert del_02.sow_reference == "M1-WO-02"

    del_03 = baseline.deliverables[2]  # Infrastructure-as-code definition for the AWS data tier
    assert del_03.id == "DEL-03"
    assert any("The AWS data tier can be provisioned in Client's AWS account" in c for c in del_03.acceptance_criteria)
    assert del_03.sow_reference == "M1-WO-03"

    # 4. Check that no INV-39 mismatch warning is recorded when counts match
    inv39_findings = [f for f in baseline.validation_report.findings if f.invariant_id == "INV-39"]
    assert len(inv39_findings) == 0


def test_map_16_non_bulleted_prose_sow_no_artificial_inflation():
    """MAP-16: Prose-style narrative SOW deliverable extraction preserves natural scope without artificial inflation."""
    # A prose SOW stating 3 distinct contracted commitments in narrative paragraphs
    prose_deliverables = [
        Deliverable(
            id="DEL-01",
            name="Cloud Migration Assessment Report",
            description="Comprehensive analysis of existing infrastructure and cloud target architecture recommendations.",
            acceptance_criteria="Delivery of final assessment report reviewed and accepted by Client Technical Sponsor.",
            owner="Toptal Delivery Team",
            sow_reference="Section 2.1",
        ),
        Deliverable(
            id="DEL-02",
            name="Target Architecture Blueprint",
            description="Detailed design documents for containerized microservices deployment on GCP.",
            acceptance_criteria="Architecture blueprint approved by Enterprise Architecture Board.",
            owner="Toptal Delivery Team",
            sow_reference="Section 2.2",
        ),
        Deliverable(
            id="DEL-03",
            name="Migration Execution Roadmap",
            description="Phase-by-phase migration plan with estimated timelines, resource allocations, and risk mitigations.",
            acceptance_criteria="Roadmap signed off by Client Delivery Lead.",
            owner="Toptal Delivery Team",
            sow_reference="Section 2.3",
        ),
    ]

    milestones = [
        Milestone(id="M1", description="Phase 1 - Assessment and Architecture Planning"),
    ]

    catalogue = [
        SOWWorkItem(reference="Section 2.1", reference_kind="Section", title="Cloud Migration Assessment", phase="P1", owner="Toptal", type="Analysis", deliverable_id="DEL-01"),
        SOWWorkItem(reference="Section 2.2", reference_kind="Section", title="Target Architecture Blueprint", phase="P1", owner="Toptal", type="Design", deliverable_id="DEL-02"),
        SOWWorkItem(reference="Section 2.3", reference_kind="Section", title="Migration Roadmap", phase="P1", owner="Toptal", type="Documentation", deliverable_id="DEL-03"),
    ]

    baseline = StartupKitBaseline(
        project_name="GCP Cloud Migration Planning",
        deliverables=prose_deliverables,
        milestones=milestones,
        sow_stories_catalogue=catalogue,
        backlog_seed=[],
    )

    validate_and_repair_baseline(baseline)

    # Deliverables are exactly the 3 distinct commitments stated in the prose SOW (no inflation)
    assert len(baseline.deliverables) == 3
    assert [d.id for d in baseline.deliverables] == ["DEL-01", "DEL-02", "DEL-03"]
    assert all(d.acceptance_criteria is not None for d in baseline.deliverables)


def test_map_16_inv_39_mismatch_validation_finding():
    """MAP-16 / INV-39: Mismatch between Work Output bullets count (27) and Deliverables count (19) produces warning."""
    # Simulate old bug state: 19 deliverables produced from 27 Work Output catalogue items
    deliverables_19 = [
        Deliverable(
            id=f"DEL-{i+1:02d}",
            name=f"Consolidated Deliverable {i+1}",
            description=f"Scope for deliverable {i+1}",
            acceptance_criteria=f"Acceptance criteria {i+1}",
            owner="Toptal Delivery Team",
        )
        for i in range(19)
    ]

    catalogue_27 = [
        SOWWorkItem(
            reference=ref,
            reference_kind="Synthetic",
            title=title,
            phase=ms,
            owner="Toptal",
            type="Build",
        )
        for ms, title, _, ref in ALL_UNDIVIDE_WORK_OUTPUTS
    ]

    milestones = [
        Milestone(id="M1", description="Phase 1 - Foundation"),
        Milestone(id="M2", description="Phase 2 - Enrichment"),
        Milestone(id="M3", description="Phase 3 - Query"),
        Milestone(id="M4", description="Phase 4 - Launch"),
    ]

    baseline = StartupKitBaseline(
        project_name="The Undivide Project (Consolidated Bug State)",
        deliverables=deliverables_19,
        milestones=milestones,
        sow_stories_catalogue=catalogue_27,
        backlog_seed=[],
    )

    validate_and_repair_baseline(baseline)

    # Invariant INV-39 must be present as a warning
    inv39_findings = [f for f in baseline.validation_report.findings if f.invariant_id == "INV-39"]
    assert len(inv39_findings) == 1
    finding = inv39_findings[0]
    assert finding.severity == "warning"
    assert "Deliverable count (19) does not match SOW Work Output item count (27)" in finding.message
    assert "check for consolidated or missing deliverables" in finding.message


def test_map_16_deliverables_and_acceptance_matrix_sow_reference_column():
    """MAP-16: Generated Startup Kit docx renders Deliverables and Acceptance Matrix with non-blank SOW References."""
    deliverables = []
    catalogue = []
    for idx, (ms_id, wo_title, ac_text, ref) in enumerate(ALL_UNDIVIDE_WORK_OUTPUTS, start=1):
        deliv_id = f"DEL-{idx:02d}"
        deliverables.append(
            Deliverable(
                id=deliv_id,
                name=wo_title,
                description=f"Delivery of {wo_title}.",
                acceptance_criteria=ac_text,
                sow_reference="",  # Initially empty at extraction
                owner="Toptal Delivery Team",
                client_approver="Client Approver",
            )
        )
        catalogue.append(
            SOWWorkItem(
                reference=ref,
                reference_kind="Synthetic",
                title=wo_title,
                phase=ms_id,
                owner="Toptal",
                type="Build",
                deliverable_id=deliv_id,
            )
        )

    milestones = [
        Milestone(id="M1", description="Phase 1 - Data and Backend Foundation"),
        Milestone(id="M2", description="Phase 2 - LLM Enrichment Layer"),
        Milestone(id="M3", description="Phase 3 - Query and Retrieval Interface"),
        Milestone(id="M4", description="Phase 4 - Access Control and Launch"),
    ]

    baseline = StartupKitBaseline(
        project_name="The Undivide Project",
        deliverables=deliverables,
        milestones=milestones,
        sow_stories_catalogue=catalogue,
        backlog_seed=[],
    )

    validate_and_repair_baseline(baseline)

    # Deliverables should have their SOW references rolled up from linked catalogue items
    for idx, d in enumerate(baseline.deliverables, start=1):
        expected_ref = ALL_UNDIVIDE_WORK_OUTPUTS[idx - 1][3]
        assert d.sow_reference == expected_ref

    # Generate document and inspect Deliverables and Acceptance Matrix table
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmp_dir:
        kit_path = Path(tmp_dir) / "test_Startup_Kit.docx"
        DocxGenerator().write_kit_docx(baseline, kit_path)
        doc = Document(str(kit_path))

    # Find the Deliverables table
    deliv_table = None
    for table in doc.tables:
        header_cells = [cell.text.strip() for cell in table.rows[0].cells]
        if "Deliverable Name" in header_cells and "SOW References" in header_cells:
            deliv_table = table
            break

    assert deliv_table is not None, "Deliverables and Acceptance Matrix table not found in document"

    # Verify all 27 rows exist and column 6 (SOW References) is non-blank
    rows = deliv_table.rows[1:]  # skip header
    assert len(rows) == 27

    for idx, row in enumerate(rows, start=1):
        deliv_id_cell = row.cells[0].text.strip()
        sow_ref_cell = row.cells[6].text.strip()
        expected_ref = ALL_UNDIVIDE_WORK_OUTPUTS[idx - 1][3]

        assert deliv_id_cell == f"DEL-{idx:02d}"
        assert sow_ref_cell == expected_ref
        assert sow_ref_cell != ""


def test_map_16_clean_sow_reference_rollup_no_section_citation():
    """MAP-16 Regression: Deliverable sow_reference contains ONLY clean work item reference, no section citation."""
    # Deliverable with initially set "Section 3" as sow_reference or in source_reference
    d1 = Deliverable(
        id="DEL-01",
        name="Postgres schema and Drizzle migrations, with the twenty-five (25) Baseline MVP facility records migrated",
        description="Delivery of Postgres schema and Drizzle migrations.",
        acceptance_criteria="All twenty-five (25) facility records are present in Postgres on staging.",
        sow_reference="Section 3",  # Contaminated with section citation
        owner="Toptal Delivery Team",
        source_reference=SourceReference(
            document_name="The Undivide Project SOW",
            clause_or_slide="Section 3 - M1",
            confidence_score=0.95,
        ),
    )

    catalogue = [
        SOWWorkItem(
            reference="M1-WO-01",
            reference_kind="Synthetic",
            title="Postgres schema and Drizzle migrations",
            phase="M1",
            owner="Toptal",
            type="Build",
            deliverable_id="DEL-01",
        )
    ]

    milestones = [
        Milestone(id="M1", description="Phase 1 - Foundation"),
    ]

    baseline = StartupKitBaseline(
        project_name="The Undivide Project",
        deliverables=[d1],
        milestones=milestones,
        sow_stories_catalogue=catalogue,
        backlog_seed=[],
    )

    validate_and_repair_baseline(baseline)

    # Deliverable sow_reference must be ONLY the clean catalogue reference, not "Section 3, M1-WO-01"
    assert baseline.deliverables[0].sow_reference == "M1-WO-01"
    assert "Section" not in baseline.deliverables[0].sow_reference


def test_map_16_no_phantom_catalogue_entry_from_section_citation():
    """MAP-16 Regression: Rebuilding catalogue/backlog never creates a phantom 'Section 3' catalogue entry."""
    # 27 deliverables and 27 catalogue items as in real Undivide SOW run,
    # where deliverables initially had "Section 3" or clause citations
    deliverables = []
    catalogue = []
    for idx, (ms_id, wo_title, ac_text, ref) in enumerate(ALL_UNDIVIDE_WORK_OUTPUTS, start=1):
        deliv_id = f"DEL-{idx:02d}"
        deliverables.append(
            Deliverable(
                id=deliv_id,
                name=wo_title,
                description=f"Delivery of {wo_title}.",
                acceptance_criteria=ac_text,
                sow_reference="Section 3",  # Initial section citation
                owner="Toptal Delivery Team",
                source_reference=SourceReference(
                    document_name="The Undivide Project SOW",
                    clause_or_slide=f"Section 3 - {ms_id}",
                    confidence_score=0.95,
                ),
            )
        )
        catalogue.append(
            SOWWorkItem(
                reference=ref,
                reference_kind="Synthetic",
                title=wo_title,
                phase=ms_id,
                owner="Toptal",
                type="Build",
                deliverable_id=deliv_id,
            )
        )

    # Also simulate accidental bare "Section 3" in catalogue before validation
    catalogue.append(
        SOWWorkItem(
            reference="Section 3",
            reference_kind="Section",
            title="",
            phase="",
            owner="Toptal",
            type="Build",
            deliverable_id="DEL-01",
        )
    )

    milestones = [
        Milestone(id="M1", description="Phase 1 - Foundation"),
        Milestone(id="M2", description="Phase 2 - Enrichment"),
        Milestone(id="M3", description="Phase 3 - Query"),
        Milestone(id="M4", description="Phase 4 - Launch"),
    ]

    baseline = StartupKitBaseline(
        project_name="The Undivide Project",
        deliverables=deliverables,
        milestones=milestones,
        sow_stories_catalogue=catalogue,
        backlog_seed=[],
    )

    validate_and_repair_baseline(baseline)

    # 1. Phantom "Section 3" catalogue entry must be filtered out
    assert len(baseline.sow_stories_catalogue) == 27
    assert not any(item.reference == "Section 3" for item in baseline.sow_stories_catalogue)

    # 2. No spurious INV-20 findings for "Section 3"
    inv20_findings = [f for f in baseline.validation_report.findings if f.invariant_id == "INV-20" and "Section 3" in f.message]
    assert len(inv20_findings) == 0

    # 3. Exactly 27 work packages rebuilt (not 28)
    assert len(baseline.backlog_seed) == 27
    inv07_findings = [f for f in baseline.validation_report.findings if f.invariant_id == "INV-07"]
    assert len(inv07_findings) == 1
    assert "Rebuilt 27 work packages" in inv07_findings[0].message
    assert "28" not in inv07_findings[0].message

    # 4. Each deliverable has only clean reference
    for idx, d in enumerate(baseline.deliverables, start=1):
        expected_ref = ALL_UNDIVIDE_WORK_OUTPUTS[idx - 1][3]
        assert d.sow_reference == expected_ref
        assert "Section" not in (d.sow_reference or "")
