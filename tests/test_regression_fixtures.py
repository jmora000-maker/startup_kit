"""Tests for regression fixtures arc_run1 and arc_run2 against Appendix B expected results (spec v4 A20)."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model


def test_arc_run1_matches_v3_appendix_b(arc_run1):
    """Assert arc_run1 matches v3 Appendix B exact expected structure."""
    model = build_workbook_model(arc_run1, start_date=date(2026, 10, 5))

    # Schedule workstreams & milestones
    ms_rows = [s for s in model.schedule_rows if s.row_type == "Milestone"]
    assert len(ms_rows) == 4
    ws_rows = [s for s in model.schedule_rows if s.row_type == "Workstream"]
    assert len(ws_rows) == 4

    # Predecessors
    sched_map = {s.milestone_id: s for s in ms_rows}
    assert sched_map["M1"].predecessor == ""
    assert sched_map["M2"].predecessor == "M1"
    assert sched_map["M3"].predecessor == "M2"
    assert sched_map["M4"].predecessor == "M3"

    # Tasks count: 156 tasks
    tasks = [w for w in model.wbs_rows if w.level == 4]
    assert len(tasks) == 156

    # Deliverables: 20 deliverables (0 unmapped)
    assert model.unmapped_deliverables_count == 0
    deliv_rows = [w for w in model.wbs_rows if w.element_type == "Deliverable"]
    assert len(deliv_rows) == 20

    # RAID: 52 rows
    assert len(model.raid_rows) == 52

    # Evidence flags: 12
    assert model.evidence_flags_count == 12

    # Traceability
    for cat, data in model.traceability.items():
        assert len(data["missing_ids"]) == 0


def test_arc_run2_matches_v4_appendix_b(arc_run2):
    """Assert arc_run2 matches v4 Appendix B exact expected structure."""
    model = build_workbook_model(arc_run2, start_date=date(2026, 10, 5))

    # Schedule workstreams & milestones
    ms_rows = [s for s in model.schedule_rows if s.row_type == "Milestone"]
    assert len(ms_rows) == 4
    ws_rows = [s for s in model.schedule_rows if s.row_type == "Workstream"]
    assert len(ws_rows) == 4

    # Predecessors
    sched_map = {s.milestone_id: s for s in ms_rows}
    assert sched_map["M1"].predecessor == ""
    assert sched_map["M2"].predecessor == "M1"
    assert "Predecessor from sequential-gate assumption (ASM-01)" in sched_map["M2"].notes
    assert sched_map["M3"].predecessor == "M2"
    assert sched_map["M4"].predecessor == "M3"

    # Deliverables mapping
    deliv_map = {w.deliverable_id: w for w in model.wbs_rows if w.element_type == "Deliverable"}
    assert len(deliv_map) == 20
    assert model.unmapped_deliverables_count == 0

    # M1 deliverables
    assert deliv_map["DEL-01"].milestone_id == "M1"
    assert deliv_map["DEL-02"].milestone_id == "M1"
    assert deliv_map["DEL-03"].milestone_id == "M1"
    assert deliv_map["DEL-04"].milestone_id == "M1"
    assert deliv_map["DEL-05"].milestone_id == "M1"
    assert deliv_map["DEL-05"].mapping_basis == "Phase code"

    # M2 deliverables
    assert deliv_map["DEL-06"].milestone_id == "M2"
    assert deliv_map["DEL-07"].milestone_id == "M2"
    assert deliv_map["DEL-07"].mapping_basis == "Backlog match (WP-06)"
    assert deliv_map["DEL-08"].milestone_id == "M2"
    assert deliv_map["DEL-09"].milestone_id == "M2"
    assert deliv_map["DEL-10"].milestone_id == "M2"
    assert deliv_map["DEL-10"].mapping_basis == "Phase code"

    # M3 deliverables
    assert deliv_map["DEL-11"].milestone_id == "M3"
    assert deliv_map["DEL-12"].milestone_id == "M3"
    assert deliv_map["DEL-13"].milestone_id == "M3"
    assert deliv_map["DEL-14"].milestone_id == "M3"
    assert deliv_map["DEL-14"].mapping_basis == "Phase code"

    # M4 deliverables
    for d_num in range(15, 21):
        assert deliv_map[f"DEL-{d_num}"].milestone_id == "M4"

    # Work package placement
    wp_tasks = {w.source_id: w for w in model.wbs_rows if w.level == 4 and w.source == "Baseline - Backlog"}
    assert wp_tasks["WP-01"].deliverable_id == "DEL-01"
    assert wp_tasks["WP-02"].deliverable_id == "DEL-02"
    assert wp_tasks["WP-03"].deliverable_id == "DEL-03"
    assert wp_tasks["WP-04"].deliverable_id == "DEL-04"
    assert wp_tasks["WP-05"].deliverable_id == "DEL-06"
    assert wp_tasks["WP-06"].deliverable_id == "DEL-07"
    assert wp_tasks["WP-07"].deliverable_id == "DEL-09"
    assert wp_tasks["WP-08"].deliverable_id == "DEL-10"
    assert wp_tasks["WP-09"].deliverable_id == "DEL-11"
    assert wp_tasks["WP-10"].deliverable_id == "DEL-12"
    assert wp_tasks["WP-11"].deliverable_id == "DEL-13"
    assert wp_tasks["WP-12"].deliverable_id == "DEL-14"
    assert wp_tasks["WP-13"].deliverable_id == "DEL-15"
    assert wp_tasks["WP-14"].deliverable_id == "DEL-17"
    assert wp_tasks["WP-15"].deliverable_id == "DEL-19"

    # Tasks count: 153 tasks
    tasks = [w for w in model.wbs_rows if w.level == 4]
    assert len(tasks) == 153

    # RAID: 51 rows
    assert len(model.raid_rows) == 51

    # Evidence flags: 11
    assert model.evidence_flags_count == 11

    # Traceability: 0 missing IDs
    for cat, data in model.traceability.items():
        assert len(data["missing_ids"]) == 0


def test_arc_run3_matches_v5_appendix(arc_run3):
    """Assert arc_run3 matches v5 Appendix exact expected structure."""
    model = build_workbook_model(arc_run3, start_date=date(2026, 10, 5))

    # Schedule workstreams & milestones
    ms_rows = [s for s in model.schedule_rows if s.row_type == "Milestone"]
    assert len(ms_rows) == 4
    ws_rows = [s for s in model.schedule_rows if s.row_type == "Workstream"]
    assert len(ws_rows) == 4

    # Predecessors
    sched_map = {s.milestone_id: s for s in ms_rows}
    assert sched_map["M1"].predecessor == ""
    assert sched_map["M2"].predecessor == "M1"
    assert sched_map["M3"].predecessor == "M2"
    assert sched_map["M4"].predecessor == "M3"

    # Schedule SOW Stories column counts
    m1_stories = [s.strip() for s in sched_map["M1"].sow_stories.split(",") if s.strip()]
    m2_stories = [s.strip() for s in sched_map["M2"].sow_stories.split(",") if s.strip()]
    m3_stories = [s.strip() for s in sched_map["M3"].sow_stories.split(",") if s.strip()]
    m4_stories = [s.strip() for s in sched_map["M4"].sow_stories.split(",") if s.strip()]
    assert len(m1_stories) == 7
    assert len(m2_stories) == 11
    assert len(m3_stories) == 10
    assert len(m4_stories) == 7

    # Deliverables: 19 deliverables (0 unmapped)
    assert model.unmapped_deliverables_count == 0
    deliv_map = {w.deliverable_id: w for w in model.wbs_rows if w.element_type == "Deliverable"}
    assert len(deliv_map) == 19

    # Deliverables per phase
    assert deliv_map["DEL-01"].milestone_id == "M1"
    assert deliv_map["DEL-02"].milestone_id == "M1"
    assert deliv_map["DEL-03"].milestone_id == "M1"

    for d_num in range(4, 9):
        assert deliv_map[f"DEL-{d_num:02d}"].milestone_id == "M2"

    for d_num in range(9, 14):
        assert deliv_map[f"DEL-{d_num:02d}"].milestone_id == "M3"

    for d_num in range(14, 20):
        assert deliv_map[f"DEL-{d_num:02d}"].milestone_id == "M4"

    # No deliverable's basis is 'Backlog match'
    for d in deliv_map.values():
        assert "backlog match" not in d.mapping_basis.lower()

    # Tasks count: 165 or 166 tasks
    tasks = [w for w in model.wbs_rows if w.level == 4]
    assert len(tasks) in (165, 166)

    prereq_tasks = [w for w in tasks if "Confirm:" in w.name]
    assert len(prereq_tasks) == 11

    story_tasks = [w for w in tasks if w.source in ("Baseline - SOW Stories", "Baseline - SOW Work Items")]
    assert len(story_tasks) == 35

    deliv_tasks = [w for w in tasks if w.deliverable_id != ""]
    assert len(deliv_tasks) == 130

    accept_tasks = [w for w in tasks if w.deliverable_id == "" and "Confirm:" not in w.name]
    assert len(accept_tasks) == 24

    # RAID: 52 rows
    assert len(model.raid_rows) == 52

    # RAID-21 (AMB-02) links M2, M3, M4 with 'Multiple phases'
    raid_map = {r.source_id: r for r in model.raid_rows}
    assert "AMB-02" in raid_map
    r21 = raid_map["AMB-02"]
    assert r21.workstream == "Multiple phases"
    assert "M2" in r21.linked_milestone and "M3" in r21.linked_milestone and "M4" in r21.linked_milestone

    # Every Contract Clarification and Open Question has Contract Reference
    for r in model.raid_rows:
        if r.category in ("Contract Clarification", "Open Question"):
            assert r.contract_reference != ""

    # Evidence notes: 10 or 11
    assert model.evidence_flags_count == 0  # 0 evidence consistency flags in run 3
    missing_ev_count = sum(1 for w in deliv_map.values() if "Evidence not defined in baseline" in w.notes)
    assert missing_ev_count in (10, 11)

    # Traceability: 0 missing IDs across all categories including SOW Stories
    for cat, data in model.traceability.items():
        assert len(data["missing_ids"]) == 0


def test_arc_run4_matches_v6_appendix(arc_run4):
    """Assert arc_run4 matches v6 Appendix exact expected structure."""
    model = build_workbook_model(arc_run4, start_date=date(2026, 10, 5))

    # Schedule workstreams & milestones
    ms_rows = [s for s in model.schedule_rows if s.row_type == "Milestone"]
    assert len(ms_rows) == 4
    ws_rows = [s for s in model.schedule_rows if s.row_type == "Workstream"]
    assert len(ws_rows) == 4

    # Predecessors
    sched_map = {s.milestone_id: s for s in ms_rows}
    assert sched_map["M1"].predecessor == ""
    assert sched_map["M2"].predecessor == "M1"
    assert sched_map["M3"].predecessor == "M2"
    assert sched_map["M4"].predecessor == "M3"

    # Schedule SOW References column counts
    m1_stories = [s.strip() for s in sched_map["M1"].sow_stories.split(",") if s.strip()]
    m2_stories = [s.strip() for s in sched_map["M2"].sow_stories.split(",") if s.strip()]
    m3_stories = [s.strip() for s in sched_map["M3"].sow_stories.split(",") if s.strip()]
    m4_stories = [s.strip() for s in sched_map["M4"].sow_stories.split(",") if s.strip()]
    assert len(m1_stories) == 7
    assert len(m2_stories) == 11
    assert len(m3_stories) == 10
    assert len(m4_stories) == 7

    # Deliverables: 19 deliverables (0 unmapped)
    assert model.unmapped_deliverables_count == 0
    deliv_map = {w.deliverable_id: w for w in model.wbs_rows if w.element_type == "Deliverable"}
    assert len(deliv_map) == 19

    # WP-10 under DEL-12
    deliv_12_tasks = [w for w in model.wbs_rows if w.deliverable_id == "DEL-12" and w.level == 4]
    wp10_task = next((t for t in deliv_12_tasks if t.source_id == "WP-10"), None)
    assert wp10_task is not None

    # No Other-work package in WBS
    other_work_tasks = [w for w in model.wbs_rows if "Other" in w.workstream and "work" in w.name.lower()]
    assert len(other_work_tasks) == 0

    # Tasks count: 149 or 150 tasks
    tasks = [w for w in model.wbs_rows if w.level == 4]
    assert len(tasks) in (149, 150)

    # RAID: 51 rows
    assert len(model.raid_rows) == 51

    # All 15 contract clarifications have a citation-based Contract Reference (no 'Not cited')
    amb_rows = [r for r in model.raid_rows if r.category == "Contract Clarification"]
    assert len(amb_rows) == 15
    for r in amb_rows:
        assert r.contract_reference != "Not cited"
        assert "Exhibit A" in r.contract_reference

    # Evidence notes: 6 missing-evidence notes
    missing_ev_count = sum(1 for w in deliv_map.values() if "Evidence not defined in baseline" in w.notes)
    assert missing_ev_count == 6

    # Traceability: 0 missing IDs across all categories
    for cat, data in model.traceability.items():
        assert len(data["missing_ids"]) == 0
