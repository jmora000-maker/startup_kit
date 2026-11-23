"""Tests for HTL-124: Primary-source routing of granular roadmap scope for Programmatic SOWs."""

import pytest
import re
from pathlib import Path
import pptx

from src.core.models import (
    StartupKitBaseline,
    Deliverable,
    Milestone,
    ProjectStartupCharter,
    SOWInterpretationSummary,
    SourceReference,
)
from src.generators.client_deck.builder import (
    build_slide6_model,
    build_client_deck_model,
    _is_duplicate_scope_item,
)
from src.generators.client_deck.writer import (
    write_client_deck,
    chunk_workstreams_for_deliverables_table,
)


def test_htl_124_granular_scope_primary_source_programmatic():
    """Verify that granular 11-item high_level_scope is prioritized as the primary source for Programmatic contracts."""
    scope_items = [
        "2.1.1 Feature development: Multi-user home access, roles, and permissions",
        "2.1.1 Feature development: Accessory maintenance and reminder flows",
        "2.1.1 Feature development: Account-level notification preferences and related consent or redirect surfaces",
        "2.1.1 Feature development: Alert, activity, and service-experience surfaces",
        "2.1.1 Feature development: Vacation, lockout, and other device-configuration flows",
        "2.1.2 Security and reliability: Identity, login, and security hardening, including security and audit remediation",
        "2.1.2 Security and reliability: Defect triage, production-defect remediation, and reliability fixes for core device control, connectivity, and time/sync behavior",
        "2.1.2 Security and reliability: Connectivity, stale-state, and device-sync recovery",
        "2.1.3 Quality engineering and release support: Automated and targeted test coverage, including accessibility and localization checks on changed screens",
        "2.1.3 Quality engineering and release support: Regression and release-candidate support on iOS and Android in alignment with the client's release train",
        "2.1.3 Quality engineering and release support: Development of a device simulator for the T-Stat tool to perform Doppelio-facilitated automation testing",
    ]

    # Deliverables represent sprint-level agreements
    deliverables = [
        Deliverable(
            id="DEL-01",
            name="Sprint-Committed Mobile App Work Items",
            description="Work items committed in each two-week Sprint Plan for the Smart Home iOS and Android apps.",
            source_reference=SourceReference(document_name="sow.pdf", clause_or_slide="Section 2.2.5"),
        ),
        Deliverable(
            id="DEL-02",
            name="T-Stat Device Simulator for Automation Testing",
            description="A device simulator for the T-Stat tool that enables Doppelio-facilitated automation testing.",
            source_reference=SourceReference(document_name="sow.pdf", clause_or_slide="Section 2.1.3"),
        ),
        Deliverable(
            id="DEL-03",
            name="Sprint Demo and Sprint Sign-Off",
            description="Sprint demo and sign-off document for client acceptance.",
            source_reference=SourceReference(document_name="sow.pdf", clause_or_slide="Section 2.2.4"),
        ),
        Deliverable(
            id="DEL-04",
            name="Weekly Status Report",
            description="Weekly status report covering progress against Sprint Plan.",
            source_reference=SourceReference(document_name="sow.pdf", clause_or_slide="Section 5.1"),
        ),
        Deliverable(
            id="DEL-05",
            name="Documentation of All Work Performed",
            description="Documentation covering all work performed during the engagement term.",
            source_reference=SourceReference(document_name="sow.pdf", clause_or_slide="Section 5.1"),
        ),
        Deliverable(
            id="DEL-06",
            name="Final Engagement Completion Sign-Off",
            description="Sign-off document confirming completion of the engagement.",
            source_reference=SourceReference(document_name="sow.pdf", clause_or_slide="Section 3"),
        ),
    ]

    baseline = StartupKitBaseline(
        project_name="Smart Home Mobile App",
        client_name="Carrier",
        contract_type="Programmatic",
        contract_type_variant="Programmatic",
        charter=ProjectStartupCharter(
            project_name="Smart Home Mobile App",
            client_name="Carrier",
            contract_type="Programmatic",
            governance_tier="Partnered",
            high_level_scope=scope_items,
            solution_overview="Two-week sprints deliver prioritized features, security and reliability fixes, and test automation.",
        ),
        sow_interpretation=SOWInterpretationSummary(
            out_of_scope_items=["UX/UI design", "Backend services"],
        ),
        deliverables=deliverables,
        milestones=[
            Milestone(id="M1", description="Sprint Backlog Execution"),
        ],
    )

    s6 = build_slide6_model(baseline)

    # 1. Exactly 3 canonical workstream blocks
    assert len(s6.workstreams) == 3
    titles = [ws.title for ws in s6.workstreams]
    assert titles == [
        "Feature development",
        "Security and reliability",
        "Quality engineering and release support",
    ]

    # 2. Granular counts: 5 items in Feature dev, 3 in Security, 3 in Quality
    feat_ws = s6.workstreams[0]
    sec_ws = s6.workstreams[1]
    qa_ws = s6.workstreams[2]

    assert len(feat_ws.deliverables) == 5
    assert len(sec_ws.deliverables) == 3
    assert len(qa_ws.deliverables) == 3

    # 3. Check that redundant section prefixes were cleanly stripped
    for ws in s6.workstreams:
        for item in ws.deliverables:
            assert not re.match(r"^2\.1\.[123]", item)
            assert not item.startswith("Feature development:")
            assert not item.startswith("Security and reliability:")
            assert not item.startswith("Quality engineering and release support:")

    # 4. Check specific item presence
    assert any("Multi-user home access" in d for d in feat_ws.deliverables)
    assert any("Vacation, lockout" in d for d in feat_ws.deliverables)
    assert any("Identity, login, and security hardening" in d for d in sec_ws.deliverables)
    assert any("Connectivity, stale-state" in d for d in sec_ws.deliverables)
    assert any("Automated and targeted test coverage" in d for d in qa_ws.deliverables)
    assert any("device simulator for the T-Stat tool" in d for d in qa_ws.deliverables)


def test_htl_124_scope_deduplication_preserves_distinct_numeric_items():
    """Verify that _is_duplicate_scope_item correctly flags semantic overlaps while preserving distinct numbered items."""
    existing = [
        "A device simulator for the T-Stat tool that enables Doppelio-facilitated automation testing.",
        "Phase 1 Foundation Setup",
    ]

    # True duplicate (near-identical wording)
    assert _is_duplicate_scope_item("T-Stat device simulator for Doppelio-facilitated automation testing", existing)

    # Distinct numeric identifiers must not collide
    assert not _is_duplicate_scope_item("Phase 2 Foundation Setup", existing)
    assert not _is_duplicate_scope_item("Deliverable 1: Ingestion Pipeline", ["Deliverable 2: Ingestion Pipeline"])


def test_htl_124_programmatic_slide6_render_pagination(tmp_path: Path):
    """Verify that the Client Kickoff Deck renders all 11 scope items across paginated Slide 6 / Slide 7."""
    scope_items = [
        "2.1.1 Feature development: Multi-user home access, roles, and permissions",
        "2.1.1 Feature development: Accessory maintenance and reminder flows",
        "2.1.1 Feature development: Account-level notification preferences and related consent or redirect surfaces",
        "2.1.1 Feature development: Alert, activity, and service-experience surfaces",
        "2.1.1 Feature development: Vacation, lockout, and other device-configuration flows",
        "2.1.2 Security and reliability: Identity, login, and security hardening, including security and audit remediation",
        "2.1.2 Security and reliability: Defect triage, production-defect remediation, and reliability fixes for core device control, connectivity, and time/sync behavior",
        "2.1.2 Security and reliability: Connectivity, stale-state, and device-sync recovery",
        "2.1.3 Quality engineering and release support: Automated and targeted test coverage, including accessibility and localization checks on changed screens",
        "2.1.3 Quality engineering and release support: Regression and release-candidate support on iOS and Android in alignment with the client's release train",
        "2.1.3 Quality engineering and release support: Development of a device simulator for the T-Stat tool to perform Doppelio-facilitated automation testing",
    ]

    baseline = StartupKitBaseline(
        project_name="Smart Home Mobile App",
        client_name="Carrier",
        contract_type="Programmatic",
        contract_type_variant="Programmatic",
        charter=ProjectStartupCharter(
            project_name="Smart Home Mobile App",
            client_name="Carrier",
            contract_type="Programmatic",
            governance_tier="Partnered",
            high_level_scope=scope_items,
            solution_overview="Two-week sprints deliver prioritized features, security and reliability fixes, and test automation.",
        ),
        sow_interpretation=SOWInterpretationSummary(
            out_of_scope_items=["UX/UI design", "Backend services"],
        ),
        deliverables=[],
        milestones=[
            Milestone(id="M1", description="Sprint Backlog Execution"),
        ],
    )

    client_model = build_client_deck_model(baseline)
    out_deck_path = tmp_path / "deck.pptx"
    write_client_deck(client_model, out_deck_path)

    prs = pptx.Presentation(str(out_deck_path))
    chunks = chunk_workstreams_for_deliverables_table(client_model.slide6.workstreams)
    assert len(chunks) == 2  # 11 items chunk into 2 pages

    # Slide 6 (index 5) and Slide 7 (index 6)
    slide6 = prs.slides[5]
    slide7 = prs.slides[6]

    # Verify Slide 6 has Feature development table row
    s6_table_text = " ".join([c.text for row in slide6.shapes[len(slide6.shapes)-1].table.rows for c in row.cells])
    assert "Feature development" in s6_table_text
    assert "Multi-user home access" in s6_table_text
    assert "Vacation, lockout" in s6_table_text

    # Verify Slide 7 has Security and Quality table rows
    s7_table_text = " ".join([c.text for row in slide7.shapes[len(slide7.shapes)-1].table.rows for c in row.cells])
    assert "Security and reliability" in s7_table_text
    assert "Quality engineering and release support" in s7_table_text
    assert "Identity, login, and security hardening" in s7_table_text
    assert "device simulator for the T-Stat tool" in s7_table_text
