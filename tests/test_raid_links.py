"""Test RAID default-fill detection, multi-milestone linking, and phase workstream assignment (v3 spec)."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model
from src.generators.pmo_workbook.mapping import detect_default_filled_milestone, detect_default_filled_deliverable


def test_default_fill_detection(arc_baseline):
    all_raw = list(arc_baseline.raid_items) + list(arc_baseline.dependencies_assumptions)
    val_ms = detect_default_filled_milestone(all_raw)
    assert val_ms == "M1"
    val_deliv = detect_default_filled_deliverable(all_raw)
    assert val_deliv == "DEL-01"


def test_arc_raid_linking(arc_baseline):
    model = build_workbook_model(arc_baseline, start_date=date(2026, 10, 5))

    # Total 52 RAID rows in v3 Appendix B
    assert len(model.raid_rows) == 52

    raid_by_id = {r.raid_id: r for r in model.raid_rows}

    # RAID-01 (Design system in P1) -> P1 Foundation (M1)
    r1 = raid_by_id["RAID-01"]
    assert r1.workstream == "P1 Foundation"
    assert r1.linked_milestone == "M1"

    # DEP-02 (HS-4781 before P2a) -> RAID-10 -> P2a Services and Data (M2)
    r10 = raid_by_id["RAID-10"]
    assert r10.source_id == "DEP-02"
    assert r10.workstream == "P2a Services and Data"
    assert r10.linked_milestone == "M2"

    # DEP-03 (Sequential gates P1, P2a, P2b, P3) -> RAID-11 -> Multiple phases
    r11 = raid_by_id["RAID-11"]
    assert r11.source_id == "DEP-03"
    assert r11.workstream == "Multiple phases"
    assert "M1" in r11.linked_milestone and "M2" in r11.linked_milestone and "M3" in r11.linked_milestone and "M4" in r11.linked_milestone

    # ASM-01 (week ranges for all phases) -> RAID-17 -> Multiple phases
    r17 = raid_by_id["RAID-17"]
    assert r17.source_id == "ASM-01"
    assert r17.workstream == "Multiple phases"
    assert "M1" in r17.linked_milestone and "M2" in r17.linked_milestone and "M3" in r17.linked_milestone and "M4" in r17.linked_milestone

    # AMB-02 (P1 delivery timeline) -> RAID-21 -> P1 Foundation (M1)
    r21 = raid_by_id["RAID-21"]
    assert r21.source_id == "AMB-02"
    assert r21.workstream == "P1 Foundation"
    assert r21.linked_milestone == "M1"
    assert r21.contract_reference != ""

    # AMB-08 (P3 launch window) -> RAID-27 -> P3 Launch (M4)
    r27 = raid_by_id["RAID-27"]
    assert r27.source_id == "AMB-08"
    assert r27.workstream == "P3 Launch"
    assert r27.linked_milestone == "M4"

    # Q-01 (Start Date for P1) -> RAID-35 -> P1 Foundation (M1)
    r35 = raid_by_id["RAID-35"]
    assert r35.source_id == "Q-01"
    assert r35.workstream == "P1 Foundation"
    assert r35.linked_milestone == "M1"

    # Check evidence consistency flags count in model: exactly 12 (v3 A9)
    assert model.evidence_flags_count == 12


def test_raid_linking_shared_section_and_multi_deliverable_reference():
    """Verify that section-kind references and references shared by multiple deliverables
    are not used to link RAID items to deliverables or milestones."""
    from src.core.models import (
        SourceReference,
        Deliverable,
        Milestone,
        RiskAssumption,
        ContractAmbiguityItem,
        ProjectStartupCharter,
        StartupKitBaseline,
    )

    ref = SourceReference(document_name="Test_SOW.pdf", clause_or_slide="Section 3.1", confidence_score=0.95)
    milestones = [
        Milestone(id="M1", description="P1 Foundation accepted: auth and foundation delivered", source_reference=ref),
        Milestone(id="M2", description="P2 Services accepted: api and services delivered", source_reference=ref),
    ]
    deliverables = [
        Deliverable(id="DEL-01", milestone_id="M1", name="P1 Delivery Auth", sow_reference="Section 3.1, HS-4770"),
        Deliverable(id="DEL-02", milestone_id="M1", name="P1 Delivery Ingestion", sow_reference="Section 3.1, HS-4809"),
        Deliverable(id="DEL-03", milestone_id="M2", name="P2 Delivery API", sow_reference="Section 3.1, HS-4809"),
    ]
    r_item1 = ContractAmbiguityItem(
        id="CONF-01",
        anomaly_id="CONF-01",
        category="Date Conflict",
        conflicting_clauses="Proposal schedule commits Milestone 2 delivery per Section 3.1 by 2026-11-15, but SOW Table 3 lists 2026-11-30.",
        status="Open",
        contract_reference="Section 3.1",
        source_reference=ref,
    )
    r_item2 = RiskAssumption(
        id="RSK-01",
        description="Risk around shared work items HS-4809 across deliverables.",
        type="Risk",
        category="Delivery Risk",
        status="Open",
        source_reference=ref,
    )
    r_item3 = RiskAssumption(
        id="RSK-02",
        description="Risk on specific component HS-4770.",
        type="Risk",
        category="Delivery Risk",
        status="Open",
        source_reference=ref,
    )

    baseline = StartupKitBaseline(
        project_name="Test Project",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        charter=ProjectStartupCharter(
            project_name="Test Project",
            client_name="Client Corp",
            contract_type="Time and Materials",
            delivery_manager="Jane Doe",
            talent_pm="John Smith",
            pmo_lead="Sarah Connor",
        ),
        milestones=milestones,
        deliverables=deliverables,
        backlog_seed=[],
        raid_items=[r_item2, r_item3],
        contract_ambiguities=[r_item1],
    )

    model = build_workbook_model(baseline, start_date=date(2026, 10, 5))
    raid_by_src = {r.source_id: r for r in model.raid_rows}

    # CONF-01 should link to M2 (from text) and NOT link to DEL-01, DEL-02, DEL-03 via Section 3.1
    conf1_row = raid_by_src["CONF-01"]
    assert conf1_row.linked_milestone == "M2"
    assert conf1_row.linked_deliverables == ""

    # RSK-01 cites SOW-SHARED which is shared by DEL-02 and DEL-03, so it must not link to any deliverable
    rsk1_row = raid_by_src["RSK-01"]
    assert rsk1_row.linked_deliverables == ""

    # RSK-02 cites SOW-01 which uniquely belongs to DEL-01 (in M1)
    rsk2_row = raid_by_src["RSK-02"]
    assert rsk2_row.linked_deliverables == "DEL-01"
    assert rsk2_row.linked_milestone == "M1"
