"""Tests for KIT-01 parser round-trip across all artifact registers and IDs."""

import pytest
from pathlib import Path
from src.core.models import (
    StartupKitBaseline,
    Milestone,
    Deliverable,
    WorkPackageSeed,
    RiskAssumption,
    DecisionItem,
    CommunicationsPlanItem,
)
from src.generators.docx_generator import DocxGenerator
from src.extractors.startup_kit_docx_parser import StartupKitDocxParser


def test_parser_roundtrip_all_registers(tmp_path: Path):
    """Verify that every register ID (M, CP, DEL, WP, RSK, ISS, DEP, ASM, DEC, COM) round-trips (KIT-01)."""
    m1 = Milestone(id="M1", description="P1 Foundation accepted: shell")
    cp = Milestone(id="CP-01", description="P1 Shell and auth checkpoint")
    deliv = Deliverable(id="DEL-01", name="Foundation Architecture", sow_reference="HS-01")
    wp = WorkPackageSeed(id="WP-01", parent_deliverable_id="DEL-01", title="Foundation Core Task", owner="Talent PM")
    rsk = RiskAssumption(id="RSK-01", type="Risk", description="Technical latency risk", probability="High", impact="Medium")
    dec = DecisionItem(id="DEC-01", decision_text="Architecture standard is AWS.")
    com = CommunicationsPlanItem(id="COM-01", name="Weekly PSR", cadence="Weekly", format="PDF", audience="Stakeholders", content_owner="Talent PM")

    baseline = StartupKitBaseline(
        project_name="Roundtrip Test",
        milestones=[m1],
        interim_checkpoints=[cp],
        deliverables=[deliv],
        backlog_seed=[wp],
        raid_items=[rsk],
        decisions=[dec],
        communications_plan=[com],
    )

    writer = DocxGenerator()
    kit_file, _ = writer.write_documents(baseline, tmp_path)

    parser = StartupKitDocxParser()
    reparsed = parser.parse_startup_kit_docx(kit_file)

    assert any(m.id == "M1" for m in reparsed.milestones)
    assert any(c.id == "CP-01" for c in reparsed.interim_checkpoints)
    assert any(d.id == "DEL-01" for d in reparsed.deliverables)
    assert any(w.id == "WP-01" for w in reparsed.backlog_seed)
    assert any(r.type == "Risk" for r in reparsed.raid_items)
    assert any(dec_item.id == "DEC-01" for dec_item in reparsed.decisions)
    assert any(c_item.id == "COM-01" for c_item in reparsed.communications_plan)
