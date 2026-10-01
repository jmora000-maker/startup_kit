"""Comprehensive verification tests for Revision 4 carried requirements against multi-milestone and arc_run5 scenarios."""

import pytest
from datetime import date
from tests.conftest import arc_run4, arc_overextracted
from src.core.models import (
    StartupKitBaseline,
    Milestone,
    Deliverable,
    RiskAssumption,
    SourceReference,
)
from src.generators.pmo_workbook.builder import build_workbook_model
from src.generators.docx_generator import DocxGenerator
from src.extractors.startup_kit_docx_parser import StartupKitDocxParser
from src.llm.validation import validate_and_repair_baseline


def test_carried_ms02_ms05_and_fmt03_on_10_milestones(arc_overextracted):
    """MS-02 to MS-05, FMT-03: arc_overextracted baseline builds into 4 phase workstreams and backward-only predecessors."""
    baseline = arc_overextracted

    # 1. Validation & Reconciliation
    report = validate_and_repair_baseline(baseline)
    assert len(baseline.milestones) == 4  # 4 primary gates

    # 2. Build Workbook Model
    model = build_workbook_model(baseline, start_date=date(2026, 10, 5))

    # MS-02: Exactly 4 phase workstreams
    workstream_rows = [s for s in model.schedule_rows if s.row_type == "Workstream"]
    assert len(workstream_rows) == 4
    ws_names = [w.workstream for w in workstream_rows]
    assert any("P1" in w for w in ws_names)
    assert any("P2a" in w or "P2A" in w for w in ws_names)
    assert any("P2b" in w or "P2B" in w for w in ws_names)
    assert any("P3" in w for w in ws_names)

    # Predecessors are backward-only (DT-06)
    wbs_codes = [s.wbs_code for s in model.schedule_rows]
    wbs_to_idx = {code: i for i, code in enumerate(wbs_codes)}
    for s in model.schedule_rows:
        if s.predecessor and s.predecessor != "-":
            preds = [p.strip() for p in s.predecessor.split(",") if p.strip()]
            curr_idx = wbs_to_idx[s.wbs_code]
            for p in preds:
                p_ms = next((m for m in model.schedule_rows if m.milestone_id == p or m.milestone_id.startswith(f"{p} (") or m.milestone_id.startswith(f"{p} (+") or m.wbs_code == p), None)
                p_idx = wbs_to_idx[p_ms.wbs_code] if p_ms else wbs_to_idx.get(p)
                assert p_idx is not None
                assert p_idx < curr_idx, f"Forward predecessor link: {s.wbs_code} -> {p}"

    # TR-01: Traceability self-check
    assert "Milestones" in model.traceability
    assert "Deliverables" in model.traceability
    assert "Work packages" in model.traceability
    assert "RAID items" in model.traceability


def test_carried_kit_roundtrip_with_checkpoints(tmp_path):
    """KIT-01, KIT-02, KIT-09: Checkpoint table is rendered in Startup Kit and successfully round-tripped."""
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="Sec 1", confidence_score=1.0)
    baseline = StartupKitBaseline(
        project_name="Test Checkpoints",
        client_name="Test Client",
        contract_type="Fixed Bid",
        governance_tier="Partnered",
        pmo_lead="Sarah Connor",
        milestones=[Milestone(id="M1", description="P1 Gate", source_reference=ref)],
        interim_checkpoints=[
            Milestone(id="CP-01", description="Integration Test Sign-off", source_reference=ref),
            Milestone(id="CP-02", description="UAT Readiness Checkpoint", source_reference=ref),
        ],
        deliverables=[Deliverable(id="DEL-01", name="D1", description="Desc", acceptance_criteria="OK", owner="DM", source_reference=ref)],
    )

    gen = DocxGenerator()
    doc_path = gen.write_kit_docx(baseline, tmp_path)

    parser = StartupKitDocxParser()
    parsed_baseline = parser.parse_startup_kit_docx(doc_path)

    assert len(parsed_baseline.interim_checkpoints) == 2
    assert parsed_baseline.interim_checkpoints[0].id == "CP-01"
    assert "Integration Test" in parsed_baseline.interim_checkpoints[0].description
    assert parsed_baseline.interim_checkpoints[1].id == "CP-02"
    assert "UAT Readiness" in parsed_baseline.interim_checkpoints[1].description
