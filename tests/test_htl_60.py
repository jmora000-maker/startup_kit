from datetime import date
import pytest
from src.core.models import (
    StartupKitBaseline,
    ProjectStartupCharter,
    GovernanceTier,
    Deliverable,
    Milestone,
    CharterExtraction,
    DeliverablesExtraction,
    MilestonesExtraction,
    RAIDExtraction,
)
from src.generators.client_deck.builder import (
    build_slide5_model,
    build_slide6_model,
    format_success_criteria_prose,
)
from src.llm.aggregator import BaselineAggregator


def test_htl_60_tier1_llm_synthesis_fields_used_directly():
    """HTL-60: When solution_overview and success_criteria_summary are present, deck models use them directly."""
    sol_overview = "The engagement delivers a comprehensive assessment and cloud migration roadmap for PGE's Operational Compliance Program (OCP) systems. Workstreams inventory in-scope workloads and map dependencies to establish target architectures and a multi-year TCO model. Delivery culminates in a 7 Rs disposition register and sequenced migration wave plan aligned with compliance standards."
    succ_summary = "Project success is defined by formal client acceptance of the Cloud Migration Assessment Report within the 5-business-day review window. In-scope workloads must achieve at least 95% inventory coverage with hosting requirements recorded, mapped dependencies, and right-sized cost estimates. Every workload receives an approved 7 Rs disposition and is sequenced into a validated migration wave roadmap."

    baseline = StartupKitBaseline(
        project_name="Cloud Migration Assessment",
        charter=ProjectStartupCharter(
            client_name="Portland General Electric Company",
            project_purpose="Assessment and cloud migration roadmap.",
            problem_statement="Legacy OCP system outages and manual overrides.",
            solution_overview=sol_overview,
            success_criteria_summary=succ_summary,
            success_criteria=["Sign-off on M1", "100% workloads assigned disposition"],
            high_level_scope=["Portfolio inventory", "Dependency mapping", "Wave roadmap"],
        ),
        milestones=[
            Milestone(id="MS-01", description="Milestone 1: Assessment Report", external_date=date(2026, 11, 18), linked_deliverables="DEL-01, DEL-02")
        ],
        deliverables=[
            Deliverable(id="DEL-01", name="Portfolio Inventory"),
            Deliverable(id="DEL-02", name="Dependency Map"),
        ]
    )

    s5 = build_slide5_model(baseline)
    assert s5.what_does_success_look_like == succ_summary

    s6 = build_slide6_model(baseline)
    assert s6.solution_overview == sol_overview


def test_htl_60_tier1_commercial_scrubbing_applied():
    """HTL-60: Commercial / fee terms in synthesis fields are scrubbed before rendering."""
    sol_overview_comm = "The team will build the data pipelines under a $19,650 fixed-fee milestone contract. Architecture review takes place in Week 3."
    succ_summary_comm = "Success is defined by delivering all components within the $19,650 budget ceiling. All UAT test cases pass 100%."

    baseline = StartupKitBaseline(
        project_name="Commercial Synthesis Project",
        charter=ProjectStartupCharter(
            solution_overview=sol_overview_comm,
            success_criteria_summary=succ_summary_comm,
            success_criteria=["UAT pass 100%"],
            high_level_scope=["Data pipelines"],
        ),
    )

    s5 = build_slide5_model(baseline)
    assert "$19,650" not in s5.what_does_success_look_like
    assert "All UAT test cases pass 100%." in s5.what_does_success_look_like

    s6 = build_slide6_model(baseline)
    assert "$19,650" not in s6.solution_overview
    assert "Architecture review takes place in Week 3." in s6.solution_overview


def test_htl_60_tier2_deterministic_fallback_when_llm_fields_absent():
    """HTL-60: When synthesis fields are absent, Tier 2 produces clean, capitalized, period-delimited sentences."""
    # 1. PGE-like structure
    b_pge = StartupKitBaseline(
        project_name="PGE Assessment",
        charter=ProjectStartupCharter(
            project_purpose="Assessment and cloud migration roadmap for PGE.",
            problem_statement="Aging legacy system with manual data overrides.",
            success_criteria=[
                "Formal client sign-off on Milestone 1 Assessment Report",
                "100% of in-scope workloads assigned target architecture and migration wave sequencing",
            ],
            high_level_scope=[
                "Portfolio inventory across in-scope workloads",
                "Dependency mapping and integration catalog",
                "Disposition register, target architecture, and wave migration roadmap",
            ],
        ),
    )

    s5_pge = build_slide5_model(b_pge)
    assert s5_pge.what_does_success_look_like == "Formal client sign-off on Milestone 1 Assessment Report. 100% of in-scope workloads assigned target architecture and migration wave sequencing."

    s6_pge = build_slide6_model(b_pge)
    assert s6_pge.solution_overview == "Portfolio inventory across in-scope workloads. Dependency mapping and integration catalog. Disposition register, target architecture, and wave migration roadmap."

    # 2. ARC Genomics-like structure
    b_arc = StartupKitBaseline(
        project_name="ARC Platform",
        charter=ProjectStartupCharter(
            project_purpose="Build ARC micro-frontend application.",
            success_criteria=[
                "Each milestone passes its acceptance gate with sign-off.",
                "Latency targets are met for Toptal-built components (search P95 under 1s).",
                "No open critical defects at UAT exit.",
            ],
            high_level_scope=[
                "P1 Foundation (est. weeks 1-6): micro-frontend shell and auth",
                "P2a Services and Data (est. weeks 7-16): FastAPI search endpoints",
            ],
        ),
    )

    s5_arc = build_slide5_model(b_arc)
    assert "Each milestone passes its acceptance gate with sign-off." in s5_arc.what_does_success_look_like
    assert "Latency targets are met for Toptal-built components" in s5_arc.what_does_success_look_like
    assert "No open critical defects at UAT exit." in s5_arc.what_does_success_look_like

    s6_arc = build_slide6_model(b_arc)
    assert "P1 Foundation (est. weeks 1-6): micro-frontend shell and auth." in s6_arc.solution_overview
    assert "P2a Services and Data (est. weeks 7-16): FastAPI search endpoints." in s6_arc.solution_overview


def test_htl_60_aggregator_maps_charter_extraction_synthesis_fields():
    """HTL-60: BaselineAggregator properly transfers solution_overview and success_criteria_summary into charter_obj."""
    charter_ext = CharterExtraction(
        project_name="Aggregator Test Project",
        client_name="Test Client",
        project_purpose="Test Purpose",
        problem_statement="Test Problem Statement",
        solution_overview="Test Solution Overview Narrative.",
        success_criteria_summary="Test Success Criteria Summary Narrative.",
        delivery_objectives=["Obj 1"],
        success_criteria=["Crit 1"],
        high_level_scope=["Scope 1"],
    )

    aggregator = BaselineAggregator()
    baseline = aggregator.aggregate(
        charter=charter_ext,
        deliverables_ext=DeliverablesExtraction(),
        milestones_ext=MilestonesExtraction(),
        raid_ext=RAIDExtraction(),
        questions_ext=None,
        sow_interpretation_ext=None,
    )

    assert baseline.charter is not None
    assert baseline.charter.solution_overview == "Test Solution Overview Narrative."
    assert baseline.charter.success_criteria_summary == "Test Success Criteria Summary Narrative."
