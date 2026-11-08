"""Tests for defensive baseline-object-drop filtering and warning logging in PMO workbook (HTL-94)."""

import logging
import re
from datetime import date
from pathlib import Path
import openpyxl
import pytest

from src.core.models import (
    StartupKitBaseline,
    ProjectStartupCharter,
    Milestone,
    Deliverable,
    WorkPackageSeed,
    RiskAssumption,
    DependencyAssumptionItem,
    ContractAmbiguityItem,
)
from src.generators.pmo_workbook import export_pmo_workbook
from src.generators.pmo_workbook.builder import build_workbook_model


def _create_clean_base_baseline() -> StartupKitBaseline:
    """Helper to create a standard clean baseline structure."""
    return StartupKitBaseline(
        project_name="Defensive Drop Test Project",
        governance_tier="Partnered",
        contract_type="Time and Materials",
        charter=ProjectStartupCharter(
            project_name="Defensive Drop Test Project",
            client_name="Acme Corp",
            contract_type="Time and Materials",
            delivery_manager="Jane Doe",
            talent_pm="John Smith",
            pmo_lead="Sarah Connor",
        ),
        milestones=[
            Milestone(id="M1", description="Phase 1: Architecture and Discovery accepted"),
            Milestone(id="M2", description="Phase 2: Core Platform Deployment accepted"),
        ],
        deliverables=[
            Deliverable(id="DEL-01", name="Architecture Blueprint", description="System architecture specification"),
        ],
        backlog_seed=[
            WorkPackageSeed(id="WP-01", title="Setup Infrastructure", parent_deliverable_id="DEL-01"),
        ],
        raid_items=[
            RiskAssumption(id="RSK-01", description="Third-party API rate limits might impact ingest", category="Risk"),
        ],
        dependencies_assumptions=[
            DependencyAssumptionItem(id="DEP-01", description="Client provides SSO credentials", category="Dependency"),
        ],
        contract_ambiguities=[
            ContractAmbiguityItem(anomaly_id="AMB-01", conflicting_clauses="Section 2 vs Section 4 SLA targets", risk_impact="Schedule delay"),
        ],
    )


# ==============================================================================
# 1. Milestone Defensive Drop & Warning Logging
# ==============================================================================

def test_defensive_filter_drops_milestone_and_logs_warning(caplog):
    """Contaminated milestone with readiness gate content is dropped and logged at WARNING level."""
    baseline = _create_clean_base_baseline()
    baseline.milestones.append(
        Milestone(id="M0", description="Executive Readiness Gate Sign-off and Mobilization Approval")
    )

    with caplog.at_level(logging.WARNING, logger="src.generators.pmo_workbook.builder"):
        model = build_workbook_model(baseline, start_date=date(2026, 10, 5))

    # Excluded from schedule rows
    schedule_ms_ids = [row.milestone_id for row in model.schedule_rows if row.row_type == "Milestone"]
    assert "M0" not in schedule_ms_ids
    assert "M1" in schedule_ms_ids
    assert "M2" in schedule_ms_ids

    # Excluded items accounted for
    assert model.excluded_items_count == 1

    # Warning log emitted with exact format
    assert "Defensive filter dropped milestone: M0 (Executive Readiness Gate Sign-off and Mobilization Approval)" in caplog.text
    records = [r for r in caplog.records if r.levelname == "WARNING" and "Defensive filter dropped milestone: M0" in r.message]
    assert len(records) == 1


# ==============================================================================
# 2. Checkpoint Defensive Drop & Warning Logging
# ==============================================================================

def test_defensive_filter_drops_checkpoint_and_logs_warning(caplog):
    """Contaminated checkpoint containing readiness terms is dropped and logged at WARNING level."""
    baseline = _create_clean_base_baseline()
    baseline.interim_checkpoints = [
        Milestone(id="CP-01", description="Phase 1 Smoke Testing Checkpoint"),
        Milestone(id="CP-02", description="Team mobilization readiness audit"),
    ]

    with caplog.at_level(logging.WARNING, logger="src.generators.pmo_workbook.builder"):
        model = build_workbook_model(baseline, start_date=date(2026, 10, 5))

    # Clean checkpoint preserved, contaminated checkpoint dropped
    cp_descriptions = [row.name for row in model.schedule_rows if row.row_type == "Checkpoint"]
    assert any("Phase 1 Smoke Testing Checkpoint" in d or "Smoke Testing" in d for d in cp_descriptions)
    assert not any("mobilization readiness audit" in d for d in cp_descriptions)

    assert model.excluded_items_count == 1
    assert "Defensive filter dropped checkpoint: CP-02 (Team mobilization readiness audit)" in caplog.text
    records = [r for r in caplog.records if r.levelname == "WARNING" and "Defensive filter dropped checkpoint: CP-02" in r.message]
    assert len(records) == 1


# ==============================================================================
# 3. Deliverable Defensive Drop & Warning Logging
# ==============================================================================

def test_defensive_filter_drops_deliverable_and_logs_warning(caplog):
    """Contaminated deliverable referencing PMO startup kit / G-01 checklist is dropped and logged."""
    baseline = _create_clean_base_baseline()
    baseline.deliverables.append(
        Deliverable(id="DEL-00", name="PMO Startup Kit & G-01 Checklist", description="Initial mobilization deck")
    )

    with caplog.at_level(logging.WARNING, logger="src.generators.pmo_workbook.builder"):
        model = build_workbook_model(baseline, start_date=date(2026, 10, 5))

    # Excluded from WBS rows
    wbs_names = [row.name for row in model.wbs_rows if row.level == 3]
    assert not any("Startup Kit" in n for n in wbs_names)
    assert any("Architecture Blueprint" in n for n in wbs_names)

    assert model.excluded_items_count == 1
    assert "Defensive filter dropped deliverable: DEL-00 (PMO Startup Kit & G-01 Checklist)" in caplog.text
    records = [r for r in caplog.records if r.levelname == "WARNING" and "Defensive filter dropped deliverable: DEL-00" in r.message]
    assert len(records) == 1


# ==============================================================================
# 4. Work Package Defensive Drop & Warning Logging
# ==============================================================================

def test_defensive_filter_drops_work_package_and_logs_warning(caplog):
    """Contaminated work package referencing readiness tasks is dropped and logged."""
    baseline = _create_clean_base_baseline()
    baseline.backlog_seed.append(
        WorkPackageSeed(id="WP-02", title="ACT-01 Complete Readiness Score Review", parent_deliverable_id="DEL-01")
    )

    with caplog.at_level(logging.WARNING, logger="src.generators.pmo_workbook.builder"):
        model = build_workbook_model(baseline, start_date=date(2026, 10, 5))

    wbs_tasks = [row.name for row in model.wbs_rows if row.level == 4]
    assert not any("Readiness Score" in t for t in wbs_tasks)
    assert any("Setup Infrastructure" in t for t in wbs_tasks)

    assert model.excluded_items_count == 1
    assert "Defensive filter dropped work package: WP-02 (ACT-01 Complete Readiness Score Review)" in caplog.text
    records = [r for r in caplog.records if r.levelname == "WARNING" and "Defensive filter dropped work package: WP-02" in r.message]
    assert len(records) == 1


# ==============================================================================
# 5. RAID Item Defensive Drop & Warning Logging
# ==============================================================================

def test_defensive_filter_drops_raid_item_and_logs_warning(caplog):
    """Contaminated RAID risk referencing readiness gate approval is dropped and logged."""
    baseline = _create_clean_base_baseline()
    baseline.raid_items.append(
        RiskAssumption(id="RSK-02", description="Delay in readiness gate approval halts project start", category="Risk")
    )

    with caplog.at_level(logging.WARNING, logger="src.generators.pmo_workbook.builder"):
        model = build_workbook_model(baseline, start_date=date(2026, 10, 5))

    raid_descriptions = [row.description for row in model.raid_rows]
    assert not any("readiness gate approval" in d for d in raid_descriptions)
    assert any("API rate limits" in d for d in raid_descriptions)

    assert model.excluded_items_count == 1
    assert "Defensive filter dropped RAID item: RSK-02 (Delay in readiness gate approval halts project start)" in caplog.text
    records = [r for r in caplog.records if r.levelname == "WARNING" and "Defensive filter dropped RAID item: RSK-02" in r.message]
    assert len(records) == 1


# ==============================================================================
# 6. Dependency Item Defensive Drop & Warning Logging
# ==============================================================================

def test_defensive_filter_drops_dependency_item_and_logs_warning(caplog):
    """Contaminated dependency referencing G01 checklist completion is dropped and logged."""
    baseline = _create_clean_base_baseline()
    baseline.dependencies_assumptions.append(
        DependencyAssumptionItem(id="DEP-02", description="G01 checklist completion before kickoff", category="Dependency")
    )

    with caplog.at_level(logging.WARNING, logger="src.generators.pmo_workbook.builder"):
        model = build_workbook_model(baseline, start_date=date(2026, 10, 5))

    raid_descriptions = [row.description for row in model.raid_rows]
    assert not any("G01 checklist" in d for d in raid_descriptions)
    assert any("SSO credentials" in d for d in raid_descriptions)

    assert model.excluded_items_count == 1
    assert "Defensive filter dropped dependency item: DEP-02 (G01 checklist completion before kickoff)" in caplog.text
    records = [r for r in caplog.records if r.levelname == "WARNING" and "Defensive filter dropped dependency item: DEP-02" in r.message]
    assert len(records) == 1


# ==============================================================================
# 7. Contract Ambiguity Defensive Drop & Warning Logging
# ==============================================================================

def test_defensive_filter_drops_contract_ambiguity_and_logs_warning(caplog):
    """Contaminated contract ambiguity referencing Startup Kit delivery is dropped and logged."""
    baseline = _create_clean_base_baseline()
    baseline.contract_ambiguities.append(
        ContractAmbiguityItem(anomaly_id="AMB-02", conflicting_clauses="Startup Kit delivery cadence discrepancy", risk_impact="Delivery misalignment")
    )

    with caplog.at_level(logging.WARNING, logger="src.generators.pmo_workbook.builder"):
        model = build_workbook_model(baseline, start_date=date(2026, 10, 5))

    raid_descriptions = [row.description for row in model.raid_rows]
    assert not any("Startup Kit delivery" in d for d in raid_descriptions)
    assert any("SLA targets" in d for d in raid_descriptions)

    assert model.excluded_items_count == 1
    assert "Defensive filter dropped contract ambiguity item: AMB-02" in caplog.text
    records = [r for r in caplog.records if r.levelname == "WARNING" and "Defensive filter dropped contract ambiguity item: AMB-02" in r.message]
    assert len(records) == 1


# ==============================================================================
# 8. Multi-Drop Comprehensive Export & Workbook Cleanliness Integration
# ==============================================================================

def test_defensive_filter_comprehensive_workbook_export(caplog, tmp_path):
    """End-to-end export drops contaminated items across all 7 categories simultaneously and emits a clean workbook."""
    baseline = _create_clean_base_baseline()
    baseline.milestones.append(
        Milestone(id="M0", description="Executive Readiness Gate Sign-off")
    )
    baseline.interim_checkpoints = [
        Milestone(id="CP-01", description="Phase 1 Verification Checkpoint"),
        Milestone(id="CP-02", description="Team mobilization readiness audit"),
    ]
    baseline.deliverables.append(
        Deliverable(id="DEL-00", name="PMO Startup Kit & G-01 Checklist")
    )
    baseline.backlog_seed.append(
        WorkPackageSeed(id="WP-02", title="ACT-01 Complete Readiness Score Review", parent_deliverable_id="DEL-01")
    )
    baseline.raid_items.append(
        RiskAssumption(id="RSK-02", description="Delay in readiness gate approval halts project start", category="Risk")
    )
    baseline.dependencies_assumptions.append(
        DependencyAssumptionItem(id="DEP-02", description="G01 checklist completion before kickoff", category="Dependency")
    )
    baseline.contract_ambiguities.append(
        ContractAmbiguityItem(anomaly_id="AMB-02", conflicting_clauses="Startup Kit delivery cadence discrepancy", risk_impact="Delivery misalignment")
    )

    with caplog.at_level(logging.WARNING, logger="src.generators.pmo_workbook.builder"):
        result = export_pmo_workbook(baseline, tmp_path, start_date=date(2026, 10, 5))

    # 7 items dropped total
    assert result.excluded_items == 7

    # All 7 warning logs present in output
    assert "Defensive filter dropped milestone: M0 (Executive Readiness Gate Sign-off)" in caplog.text
    assert "Defensive filter dropped checkpoint: CP-02 (Team mobilization readiness audit)" in caplog.text
    assert "Defensive filter dropped deliverable: DEL-00 (PMO Startup Kit & G-01 Checklist)" in caplog.text
    assert "Defensive filter dropped work package: WP-02 (ACT-01 Complete Readiness Score Review)" in caplog.text
    assert "Defensive filter dropped RAID item: RSK-02 (Delay in readiness gate approval halts project start)" in caplog.text
    assert "Defensive filter dropped dependency item: DEP-02 (G01 checklist completion before kickoff)" in caplog.text
    assert "Defensive filter dropped contract ambiguity item: AMB-02" in caplog.text

    # Verify generated workbook has zero readiness terms across all sheets, properties, and cells
    wb = openpyxl.load_workbook(str(result.file_path))

    title = wb.properties.title or ""
    creator = wb.properties.creator or ""
    for prop in [title, creator]:
        assert "readiness" not in prop.lower()
        assert "g-01" not in prop.lower()
        assert "g01" not in prop.lower()
        assert "startup kit" not in prop.lower()

    for name in wb.sheetnames:
        assert "readiness" not in name.lower()
        assert "g-01" not in name.lower()
        assert "g01" not in name.lower()
        assert "startup" not in name.lower()

    for dn in wb.defined_names:
        dn_name = dn.name if hasattr(dn, "name") else str(dn)
        assert "readiness" not in dn_name.lower()
        assert "g-01" not in dn_name.lower()
        assert "g01" not in dn_name.lower()

    forbidden_pattern = re.compile(
        r"\b(readiness|G-?01|gate\s+approval|Startup\s+Kit|mobiliz|ACT-\d+)\b",
        re.IGNORECASE
    )
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        for row in ws.iter_rows(values_only=False):
            for cell in row:
                if cell.value is not None:
                    val_str = str(cell.value)
                    match = forbidden_pattern.search(val_str)
                    assert match is None, f"Found forbidden readiness content '{match.group(0)}' in {sheet_name}!{cell.coordinate}: '{val_str}'"
