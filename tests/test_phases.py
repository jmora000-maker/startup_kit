"""Test phase label parsing, week-range date calculation, delivery ordering, and predecessor links."""

from datetime import date
from src.core.models import Milestone
from src.generators.pmo_workbook.workstreams import parse_milestone_phase
from src.generators.pmo_workbook.builder import (
    build_workbook_model,
    parse_week_range,
    calculate_start_date,
)


def test_phase_label_parsing():
    desc1 = "P1 Foundation accepted: micro-frontend shell, Azure AD/MSAL authentication, E2E test harness (est. weeks 1–6)."
    p1 = parse_milestone_phase(desc1)
    assert p1.phase_code == "P1"
    assert p1.workstream_name == "P1 Foundation"
    assert p1.milestone_name == "P1 Foundation accepted"
    assert p1.has_phase_label is True
    assert "(est. weeks 1–6)" not in p1.milestone_scope_clean

    desc2 = "P2a Services and Data accepted: FastAPI search and async services (est. weeks 7–16)."
    p2 = parse_milestone_phase(desc2)
    assert p2.phase_code == "P2a"
    assert p2.workstream_name == "P2a Services and Data"
    assert p2.milestone_name == "P2a Services and Data accepted"

    desc3 = "P2b Application Surface accepted: ARC micro-frontend search and detail views (est. weeks 17–21)."
    p3 = parse_milestone_phase(desc3)
    assert p3.phase_code == "P2b"
    assert p3.workstream_name == "P2b Application Surface"

    desc4 = "P3 Launch accepted: integration, performance, security and cross-browser testing (est. weeks 22–26)."
    p4 = parse_milestone_phase(desc4)
    assert p4.phase_code == "P3"
    assert p4.workstream_name == "P3 Launch"


def test_wrapped_phase_label_parsing():
    desc1 = "Milestone 1 (P1 Foundation) accepted: micro-frontend shell, Azure AD/MSAL authentication, E2E test harness (est. weeks 1–6)."
    p1 = parse_milestone_phase(desc1)
    assert p1.phase_code == "P1"
    assert p1.workstream_name == "P1 Foundation"
    assert p1.milestone_name == "Milestone 1 (P1 Foundation) accepted"
    assert p1.has_phase_label is True
    assert "(est. weeks 1–6)" not in p1.milestone_scope_clean

    desc2 = "Milestone 4 (P3 Launch) accepted and project completed: integration, performance, security and cross-browser testing (est. weeks 22–26)."
    p2 = parse_milestone_phase(desc2)
    assert p2.phase_code == "P3"
    assert p2.workstream_name == "P3 Launch"
    assert p2.milestone_name == "Milestone 4 (P3 Launch) accepted and project completed"
    assert p2.has_phase_label is True

    # Ensure phase mentioned later in scope is not mistaken for milestone's own phase
    desc3 = "Testing and Validation: E2E test harness verification for P1 Foundation."
    p3 = parse_milestone_phase(desc3)
    assert p3.phase_code is None
    assert p3.has_phase_label is False


def test_week_range_parsing():
    assert parse_week_range("Running weeks 1–6 from Start Date") == (1, 6)
    assert parse_week_range("est. weeks 7—16") == (7, 16)
    assert parse_week_range("weeks 17-21") == (17, 21)
    assert parse_week_range("weeks 22 to 26") == (22, 26)
    assert parse_week_range("week 5 delivery") == (5, 5)
    assert parse_week_range("No dates mentioned") is None


def test_start_date_calculation(arc_baseline):
    # With no award date and today=2026-10-02 -> first Monday on or after is 2026-10-05
    baseline_no_award = arc_baseline.model_copy(update={"sow_awarded_date": None})
    calc_start, basis = calculate_start_date(baseline_no_award, user_start_date=None, today=date(2026, 10, 2))
    assert calc_start == date(2026, 10, 5)
    assert "Assumed" in basis

    # With stated award date (VAL-11 provenance)
    baseline_stated = arc_baseline.model_copy(update={"award_date_source": "stated"})
    calc_start_award, basis_award = calculate_start_date(baseline_stated, user_start_date=None)
    assert calc_start_award == date(2026, 9, 29)
    assert basis_award == "Provided"

    # Award date without VAL-11 provenance is treated as no date
    calc_start_unprov, basis_unprov = calculate_start_date(arc_baseline, user_start_date=None, today=date(2026, 10, 2))
    assert calc_start_unprov == date(2026, 10, 5)
    assert basis_unprov == "Assumed - first Monday after generation date; confirm"

    # With user start date override
    user_start = date(2026, 11, 2)
    calc_start2, basis2 = calculate_start_date(arc_baseline, user_start_date=user_start)
    assert calc_start2 == user_start
    assert basis2 == "Provided"


def test_arc_baseline_phases_and_predecessors(arc_baseline):
    model = build_workbook_model(arc_baseline, start_date=date(2026, 10, 5))

    # Milestones in delivery order
    ms_rows = [s for s in model.schedule_rows if s.row_type == "Milestone"]
    assert len(ms_rows) == 4
    assert [m.milestone_id for m in ms_rows] == ["M1", "M2", "M3", "M4"]

    # Dates and Predecessors
    m1 = ms_rows[0]
    assert m1.workstream == "P1 Foundation"
    assert m1.planned_start == date(2026, 10, 5)
    assert m1.planned_finish == date(2026, 11, 13)
    assert m1.date_basis == "SOW estimate, weeks 1–6"
    assert m1.predecessor == ""

    m2 = ms_rows[1]
    assert m2.workstream == "P2a Services and Data"
    assert m2.planned_start == date(2026, 11, 16)
    assert m2.planned_finish == date(2027, 1, 22)
    assert m2.date_basis == "SOW estimate, weeks 7–16"
    assert m2.predecessor == "M1"

    m3 = ms_rows[2]
    assert m3.workstream == "P2b Application Surface"
    assert m3.planned_start == date(2027, 1, 25)
    assert m3.planned_finish == date(2027, 2, 26)
    assert m3.date_basis == "SOW estimate, weeks 17–21"
    assert m3.predecessor == "M2"

    m4 = ms_rows[3]
    assert m4.workstream == "P3 Launch"
    assert m4.planned_start == date(2027, 3, 1)
    assert m4.planned_finish == date(2027, 4, 2)
    assert m4.date_basis == "SOW estimate, weeks 22–26"
    assert m4.predecessor == "M3"


def test_phase_display_preferred_over_internal_bookkeeping_field():
    """Verify phase_display is preferred with original casing, and absence falls through cleanly."""
    # (a) Milestone with phase_display="P2a" correctly produces "P2a Services and Data" workstream name, not "P2A"
    ms_stated = Milestone(
        id="M2",
        description="P2a Services and Data accepted: FastAPI search and async services (est. weeks 7–16).",
        phase="P2A",
        phase_display="P2a",
    )
    p_stated = parse_milestone_phase(ms_stated)
    assert p_stated.phase_code == "P2a"
    assert p_stated.workstream_name == "P2a Services and Data"
    assert p_stated.milestone_name == "P2a Services and Data accepted"
    assert p_stated.has_phase_label is True

    # (b) Milestone with phase=None, phase_display=None (synthetic-placeholder case) falls through to existing behavior, never showing "G_1"
    ms_synthetic = Milestone(
        id="M1",
        description="Initial Kickoff, Architecture Discovery and Workshop",
        phase=None,
        phase_display=None,
    )
    p_synthetic = parse_milestone_phase(ms_synthetic)
    assert p_synthetic.phase_code is None
    assert "G_1" not in p_synthetic.workstream_name
    assert p_synthetic.workstream_name == "Discovery & Requirements"
    assert p_synthetic.has_phase_label is False

    # Also verify when internal bookkeeping phase is "G_1" but phase_display is None
    ms_synth_g1 = Milestone(
        id="M1",
        description="Initial Kickoff, Architecture Discovery and Workshop",
        phase="G_1",
        phase_display=None,
    )
    p_synth_g1 = parse_milestone_phase(ms_synth_g1)
    assert p_synth_g1.phase_code is None
    assert "G_1" not in p_synth_g1.workstream_name
    assert p_synth_g1.workstream_name == "Discovery & Requirements"
    assert p_synth_g1.has_phase_label is False


def test_phase_display_with_terse_colonless_gpt4o_shape():
    """Verify behavior of parse_milestone_phase for real GPT-4o shape with terse description and no colon."""
    ms_gpt4o = Milestone(
        id="M1",
        description="P1 Foundation completion.",
        phase="P1",
        phase_display="P1",
        key_dependencies=["Completion of micro-frontend shell and authentication integration."],
        critical_path_assumptions=["Shell load and authentication success metrics met."],
    )
    p = parse_milestone_phase(ms_gpt4o)
    assert p.phase_code == "P1"
    assert p.workstream_name == "P1"
    assert p.milestone_name == "P1 Foundation completion."
    assert p.milestone_scope == "P1 Foundation completion."
    assert p.milestone_scope_clean == "P1 Foundation completion."
    assert p.has_phase_label is True


def test_ms_13_spelled_out_phase_label_parsing():
    """MS-13: Test spelled-out 'Phase N - Name' milestone descriptions are recognized by MS-01 pattern."""
    desc1 = "Phase 1 - Data and Backend Foundation: Postgres schema and Drizzle migrations with 25 MVP facility records."
    p1 = parse_milestone_phase(desc1)
    assert p1.phase_code == "P1"
    assert p1.workstream_name == "Phase 1 - Data and Backend Foundation"
    assert p1.milestone_name == "Phase 1 - Data and Backend Foundation"
    assert p1.has_phase_label is True
    assert p1.milestone_scope == "Postgres schema and Drizzle migrations with 25 MVP facility records."

    desc2 = "Phase 2 - LLM Enrichment Layer: enrichment service with schema validation, confidence-score capture and review queue."
    p2 = parse_milestone_phase(desc2)
    assert p2.phase_code == "P2"
    assert p2.workstream_name == "Phase 2 - LLM Enrichment Layer"
    assert p2.milestone_name == "Phase 2 - LLM Enrichment Layer"
    assert p2.has_phase_label is True

    desc3 = "Phase 3 - Access Control, Observability, and Pilot Readiness: RBAC for four personas, observability stack and CI/CD."
    p3 = parse_milestone_phase(desc3)
    assert p3.phase_code == "P3"
    assert p3.workstream_name == "Phase 3 - Access Control, Observability, and Pilot Readiness"
    assert p3.has_phase_label is True

    desc4 = "Phase 4 - Launch and Handoff: platform production deployment, pilot partner onboarding support, and runbooks."
    p4 = parse_milestone_phase(desc4)
    assert p4.phase_code == "P4"
    assert p4.workstream_name == "Phase 4 - Launch and Handoff"
    assert p4.has_phase_label is True

    # Wrapped spelled-out format
    desc_wrapped = "Milestone 2 (Phase 2 - LLM Enrichment Layer) accepted: enrichment service and prompt versioning."
    p_wrapped = parse_milestone_phase(desc_wrapped)
    assert p_wrapped.phase_code == "P2"
    assert p_wrapped.workstream_name == "Phase 2 - LLM Enrichment Layer"
    assert p_wrapped.has_phase_label is True


def test_ms_13_undivide_project_sow_milestone_reconciliation_produces_real_phase_display():
    """MS-13: Full real Undivide Project SOW milestone shape produces real phase_display values, not synthetic G_N codes."""
    from src.core.models import StartupKitBaseline
    from src.llm.validation import reconcile_gates_and_checkpoints

    milestones = [
        Milestone(id="M1", description="Phase 1 - Data and Backend Foundation: Postgres schema, normalization layer, and scraper connector."),
        Milestone(id="M2", description="Phase 2 - LLM Enrichment Layer: enrichment service with schema validation and confidence scoring."),
        Milestone(id="M3", description="Phase 3 - Access Control, Observability, and Pilot Readiness: RBAC and staging deployment."),
        Milestone(id="M4", description="Phase 4 - Launch and Handoff: production deployment and handover checklist."),
    ]

    baseline = StartupKitBaseline(
        project_name="The Undivide Project",
        deliverables=[],
        milestones=milestones,
        sow_stories_catalogue=[],
        backlog_seed=[]
    )

    findings = []
    reconcile_gates_and_checkpoints(baseline, findings)

    # Verify that milestones receive real canonical phase codes and stated phase_display values
    assert [m.phase for m in baseline.milestones] == ["P1", "P2", "P3", "P4"]
    assert [m.phase_display for m in baseline.milestones] == ["Phase 1", "Phase 2", "Phase 3", "Phase 4"]

    # Verify Workbook Schedule Level 1 Workstream rows reflect the stated phase names
    wb = build_workbook_model(baseline, start_date=date(2026, 10, 16))
    ws_rows = [r for r in wb.schedule_rows if r.row_type == "Workstream"]
    assert len(ws_rows) == 4
    assert ws_rows[0].name == "Phase 1 - Data and Backend Foundation"
    assert ws_rows[1].name == "Phase 2 - LLM Enrichment Layer"
    assert ws_rows[2].name == "Phase 3 - Access Control, Observability, and Pilot Readiness"
    assert ws_rows[3].name == "Phase 4 - Launch and Handoff"

    # Verify no Unclassified workstreams or G_N placeholders exist
    for r in wb.schedule_rows:
        assert "Unclassified" not in r.workstream
        assert not r.workstream.startswith("G_")


def test_ms_13_genuinely_phase_less_sow_still_exercises_map_09_keyword_fallback():
    """MS-13: A genuinely phase-less SOW still correctly falls through to MAP-09 keyword classifier."""
    from src.core.models import StartupKitBaseline
    from src.llm.validation import reconcile_gates_and_checkpoints

    ms1 = Milestone(id="M1", description="Initial Kickoff, Architecture Discovery and Workshop: discovery and scoping")
    ms2 = Milestone(id="M2", description="Data Integration and ETL Pipeline Implementation: data pipelines")
    ms3 = Milestone(id="M3", description="Arbitrary Generic Activity with No Known Keywords: foobar baz qux")

    p1 = parse_milestone_phase(ms1)
    assert p1.phase_code is None
    assert p1.workstream_name == "Discovery & Requirements"
    assert p1.has_phase_label is False

    p2 = parse_milestone_phase(ms2)
    assert p2.phase_code is None
    assert p2.workstream_name == "Data & Integration"
    assert p2.has_phase_label is False

    p3 = parse_milestone_phase(ms3)
    assert p3.phase_code is None
    assert p3.workstream_name == "Unclassified"
    assert p3.has_phase_label is False

    baseline = StartupKitBaseline(
        project_name="Phase-less Project",
        deliverables=[],
        milestones=[ms1, ms2, ms3],
        sow_stories_catalogue=[],
        backlog_seed=[]
    )

    findings = []
    reconcile_gates_and_checkpoints(baseline, findings)

    # In a phase-less SOW, internal phase codes remain G_1, G_2, G_3 and phase_display is None
    assert [m.phase for m in baseline.milestones] == ["G_1", "G_2", "G_3"]
    assert [m.phase_display for m in baseline.milestones] == [None, None, None]
