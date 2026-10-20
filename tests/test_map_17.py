"""Tests for MAP-17: Decimal-shaped synthetic SOW references (WO-1.1..WO-4.8) are preserved without truncation."""

import pytest
from datetime import date

from src.config import (
    extract_sow_references,
    extract_sow_references_with_kind,
    detect_sow_reference_kind,
    normalize_sow_reference,
)
from src.core.models import (
    StartupKitBaseline,
    Deliverable,
    Milestone,
    SOWWorkItem,
    SourceReference,
    ProjectStartupCharter,
)
from src.generators.pmo_workbook.builder import build_workbook_model
from src.llm.validation import validate_and_repair_baseline
from tests.test_map_16 import (
    UNDIVIDE_M1_WORK_OUTPUTS,
    UNDIVIDE_M2_WORK_OUTPUTS,
    UNDIVIDE_M3_WORK_OUTPUTS,
    UNDIVIDE_M4_WORK_OUTPUTS,
)


def test_map_17_extract_and_normalize_decimal_references():
    """MAP-17: extract_sow_references and normalize_sow_reference preserve decimal reference shapes."""
    # 1. Extraction of individual decimal references
    assert extract_sow_references("WO-1.1") == ["WO-1.1"]
    assert extract_sow_references("WO-4.8") == ["WO-4.8"]
    assert extract_sow_references("Work Output 1.1") == ["Work Output 1.1"]

    # 2. Multi-reference extraction preserving all distinct decimals
    sample_text = "Deliverables covering WO-1.1, WO-1.2, WO-2.1, WO-3.5, and WO-4.8 for staging deployment."
    extracted = extract_sow_references(sample_text)
    assert extracted == ["WO-1.1", "WO-1.2", "WO-2.1", "WO-3.5", "WO-4.8"]

    # 3. Kind detection
    assert detect_sow_reference_kind("WO-1.1") == "Deliverable number"
    assert detect_sow_reference_kind("WO-4.8") == "Deliverable number"
    assert extract_sow_references_with_kind("WO-1.1") == [("WO-1.1", "Deliverable number")]

    # 4. Canonical normalization
    assert normalize_sow_reference("WO-1.1") == "WO:1.1"
    assert normalize_sow_reference("WO-4.8") == "WO:4.8"
    assert normalize_sow_reference("Work Output 1.1") == "WO:1.1"
    assert normalize_sow_reference("WO-01.01") == "WO:1.1"

    # 5. Non-decimal (flat integer) references remain completely unaffected
    assert extract_sow_references("WO-1") == ["WO-1"]
    assert extract_sow_references("WO-01") == ["WO-01"]
    assert extract_sow_references("WO-12") == ["WO-12"]
    assert detect_sow_reference_kind("WO-1") == "Deliverable number"
    assert detect_sow_reference_kind("WO-01") == "Story ID"
    assert normalize_sow_reference("WO-1") == "WO:1"
    assert normalize_sow_reference("WO-01") == "WO:1"
    assert normalize_sow_reference("WO-12") == "WO:12"


def test_map_17_appendix_xx_decimal_reference_pipeline_and_traceability():
    """MAP-17: Appendix XX scenario with WO-1.1..WO-4.8 references across 4 milestones (27 items).

    Verifies:
    (a) sow_stories_catalogue has exactly 27 items, not 31;
    (b) no phantom WO-1/WO-2/WO-3/WO-4 entries exist;
    (c) each deliverable's sow_reference is its own distinct WO-N.M value;
    (d) zero INV-20 findings about phantom items;
    (e) zero INV-39 mismatch warnings;
    (f) the Workbook's traceability check shows 0 missing/unmatched references.
    """
    # 27 real Undivide SOW Work Output items formatted with WO-N.M decimal references
    milestones_data = [
        ("M1", "P1", UNDIVIDE_M1_WORK_OUTPUTS),
        ("M2", "P2", UNDIVIDE_M2_WORK_OUTPUTS),
        ("M3", "P3", UNDIVIDE_M3_WORK_OUTPUTS),
        ("M4", "P4", UNDIVIDE_M4_WORK_OUTPUTS),
    ]

    deliverables = []
    catalogue = []
    global_idx = 1

    for ms_num, (ms_id, phase_id, wo_list) in enumerate(milestones_data, start=1):
        for seq_num, (wo_title, ac_text) in enumerate(wo_list, start=1):
            ref = f"WO-{ms_num}.{seq_num}"
            deliv_id = f"DEL-{global_idx:02d}"

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
                    ),
                )
            )

            catalogue.append(
                SOWWorkItem(
                    reference=ref,
                    reference_kind="Deliverable number",
                    title=wo_title,
                    phase=phase_id,
                    owner="Toptal",
                    type="Build",
                    deliverable_id=deliv_id,
                )
            )

            global_idx += 1

    assert len(deliverables) == 27
    assert len(catalogue) == 27

    milestones = [
        Milestone(id="M1", description="Phase 1 - Data and Backend Foundation: Infrastructure and pipeline deployment."),
        Milestone(id="M2", description="Phase 2 - LLM Enrichment Layer: Enrichment service and prompt pipelines."),
        Milestone(id="M3", description="Phase 3 - Query and Retrieval Interface: Search API and caching layer."),
        Milestone(id="M4", description="Phase 4 - Access Control, Observability, and Pilot Readiness: RBAC and production cutover."),
    ]

    baseline = StartupKitBaseline(
        project_name="The Undivide Project",
        charter=ProjectStartupCharter(project_name="The Undivide Project"),
        deliverables=deliverables,
        milestones=milestones,
        sow_stories_catalogue=catalogue,
        backlog_seed=[],
    )

    # Validate and repair baseline
    validate_and_repair_baseline(baseline)

    # (a) sow_stories_catalogue has exactly 27 items, not 31
    assert len(baseline.sow_stories_catalogue) == 27

    # (b) no phantom WO-1/WO-2/WO-3/WO-4 entries exist
    phantom_refs = {"WO-1", "WO-2", "WO-3", "WO-4"}
    actual_refs = {item.reference for item in baseline.sow_stories_catalogue}
    assert phantom_refs.isdisjoint(actual_refs)

    # (c) each deliverable's sow_reference is its own distinct WO-N.M value, not a truncated milestone value
    for d in baseline.deliverables:
        assert d.sow_reference not in phantom_refs
        assert "." in d.sow_reference, f"Deliverable {d.id} sow_reference '{d.sow_reference}' lost decimal component"

    # Verify exact mapping
    expected_m1_refs = [f"WO-1.{i}" for i in range(1, 9)]
    actual_m1_refs = [d.sow_reference for d in baseline.deliverables[:8]]
    assert actual_m1_refs == expected_m1_refs

    # (d) zero INV-20 findings about phantom items
    inv20_findings = [f for f in baseline.validation_report.findings if f.invariant_id == "INV-20"]
    assert inv20_findings == []

    # (e) zero INV-39 mismatch warnings
    inv39_findings = [f for f in baseline.validation_report.findings if f.invariant_id == "INV-39"]
    assert inv39_findings == []

    # (f) Workbook traceability check shows 0 missing/unmatched references
    wb = build_workbook_model(baseline, today=date(2026, 10, 19))
    sow_trace = wb.traceability.get("SOW References", {})
    assert sow_trace.get("missing_ids") == []
    assert sow_trace.get("in_baseline") == 27
    assert sow_trace.get("in_workbook") == 27

    # Check that TR-01 findings are clean
    tr_findings = [f for f in baseline.validation_report.findings if f.invariant_id == "TR-01"]
    assert tr_findings == []

    # Verify WBS work packages retain full decimal reference in titles and sow_reference
    assert len(baseline.backlog_seed) == 27
    for wp in baseline.backlog_seed:
        assert wp.sow_reference not in phantom_refs
        assert "." in wp.sow_reference
