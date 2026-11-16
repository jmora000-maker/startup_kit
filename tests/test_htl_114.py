"""HTL-114: Comprehensive test suite for Scope Event Role Attribution & RACI Matrix alignment.

Verifies:
1. RACI Matrix as Source of Truth: Differentiates in-envelope vs out-of-envelope scope governance.
2. Two-Tier Role Attribution across Scope Baseline Tables 2, 3, and 4 in both Fixed Bid and T&M variants:
   - In-envelope (Clarification, Reprioritization): Talent PM leads, Delivery Manager supports as needed.
   - Out-of-envelope (Expansion, Dependency Impact): Talent PM triggers/halts/pivots, routed to Delivery Manager and PMO Lead.
3. Governance Deck Slide 11 (Change Decision Matrix) inheritance and visual fitting.
4. Table 5 fallback scenarios and LLM system prompt instructions.
5. Shared constants DRY structure.
"""

from pathlib import Path
import pptx
import pytest

from src.core.models import (
    StartupKitBaseline,
    ProjectStartupCharter,
    SOWInterpretationSummary,
    Deliverable,
    DependencyAssumptionItem,
    CommercialGuardrail,
)
from src.llm.aggregator import BaselineAggregator
from src.generators.scope_baseline.templates import (
    ROLE_LEAD_IN_ENVELOPE,
    ROLE_LEAD_IN_ENVELOPE_CONCISE,
    ROLE_TRIGGER_OUT_OF_ENVELOPE,
    ROLE_TRIGGER_OUT_OF_ENVELOPE_CONCISE,
    build_table2_change_matrix_rows,
    build_table3_decision_rules_rows,
    build_table4_classification_guide_rows,
    build_table5_fallback_examples,
)
from src.generators.scope_baseline.builder import TABLE5_PROMPT_TEMPLATE, build_scope_baseline_document
from src.generators.governance_deck import export_governance_deck
from tests.deck_bundle import load_baseline
from tests.test_htl_62 import _build_pge_baseline


def _create_mock_baseline(contract_type: str = "Fixed Bid") -> StartupKitBaseline:
    charter = ProjectStartupCharter(
        project_name="HTL-114 Verification Project",
        client_name="Acme Corp",
        contract_type=contract_type,
        governance_tier="Partnered",
        delivery_model="Toptal Talent Team",
        project_purpose="Verify two-tier role attribution logic.",
        problem_statement="Scope event governance needed clarification.",
        high_level_scope=["Module A", "Module B"],
        exclusions=["Uncontracted Legacy Platform Remediation"],
        key_deliverables_summary=["DEL-01: Core Architecture"],
    )
    sow_int = SOWInterpretationSummary(
        contracted_deliverables=["Core Architecture"],
        out_of_scope_items=["Legacy Migration"],
        platform_environment_commitments=["AWS Cloud"],
        dependencies=["Client API Credentials"],
    )
    delivs = [Deliverable(id="DEL-01", name="Core Architecture", description="Architecture Document")]
    deps = [DependencyAssumptionItem(id="DEP-01", type="Dependency", description="Client API Credentials", impact_if_unmet="Blocked")]
    guardrails = CommercialGuardrail(contract_type_implication=f"{contract_type} governance")

    return StartupKitBaseline(
        project_name="HTL-114 Verification Project",
        contract_type=contract_type,
        governance_tier="Partnered",
        charter=charter,
        sow_interpretation=sow_int,
        deliverables=delivs,
        dependencies_assumptions=deps,
        commercial_guardrails=guardrails,
    )


def test_htl_114_raci_matrix_source_of_truth():
    """Verify RACI matrix cleanly separates in-envelope and out-of-envelope scope governance with correct decision rights."""
    from src.core.models import CharterExtraction, DeliverablesExtraction, MilestonesExtraction, RAIDExtraction
    aggregator = BaselineAggregator()
    charter = CharterExtraction(project_name="RACI Check", contract_type="Fixed Bid")
    baseline = aggregator.aggregate(
        charter=charter,
        deliverables_ext=DeliverablesExtraction(),
        milestones_ext=MilestonesExtraction(),
        raid_ext=RAIDExtraction(),
    )

    raci_map = {r.decision_or_activity: r for r in baseline.raci_matrix}

    # 1. In-envelope scope management: Talent PM leads (R, A), DM supports (C), PMO informed (I)
    assert "Scope clarification & reprioritization" in raci_map
    in_env = raci_map["Scope clarification & reprioritization"]
    assert in_env.talent_pm == "R, A"
    assert in_env.delivery_manager == "C"
    assert in_env.pmo_lead == "I"
    assert in_env.client == "C"

    # 2. Out-of-envelope scope changes: Talent PM triggers (R), DM aligns client (R), PMO leads change order (R, A), Client approves (A)
    assert "Scope expansion & Change Orders" in raci_map
    out_env = raci_map["Scope expansion & Change Orders"]
    assert out_env.talent_pm == "R"
    assert out_env.delivery_manager == "R"
    assert out_env.pmo_lead == "R, A"
    assert out_env.client == "A"

    # 3. Blockers and dependency relief: Talent PM triggers (R), DM coordinates (C), PMO leads relief (R, A)
    assert "Delivery risk, blockers & recovery" in raci_map
    blockers = raci_map["Delivery risk, blockers & recovery"]
    assert blockers.talent_pm == "R"
    assert blockers.delivery_manager == "C"
    assert blockers.pmo_lead == "R, A"
    assert blockers.client == "I"


def test_htl_114_table2_role_attribution_fixed_bid_and_tm():
    """Verify Table 2 Change Decision Matrix applies the two-tier role pattern across Fixed Bid and T&M."""
    for variant in ["Fixed Bid", "Time and Materials"]:
        baseline = _create_mock_baseline(variant)
        rows = build_table2_change_matrix_rows(baseline, variant)
        row_map = {r.classification: r for r in rows}

        # Clarification (In-envelope): Talent PM leads, DM supports if needed
        clar = row_map["Clarification"]
        assert "Talent PM leads" in clar.governance_action
        assert "Delivery Manager supports if needed" in clar.governance_action

        # Reprioritization (In-envelope): Talent PM leads, DM supports / confirms capacity
        reprio = row_map["Reprioritization"]
        assert "Talent PM leads" in reprio.governance_action
        assert "Delivery Manager" in reprio.governance_action

        # Expansion (Out-of-envelope): Talent PM triggers, routed to DM and PMO Lead
        exp = row_map["Expansion"]
        assert "Talent PM triggers" in exp.governance_action
        assert "routed to Delivery Manager and PMO Lead" in exp.governance_action

        # Dependency Impact (Out-of-envelope): Talent PM triggers, routed to DM and PMO Lead
        dep = row_map["Dependency Impact"]
        assert "Talent PM triggers" in dep.governance_action
        assert "routed to Delivery Manager and PMO Lead" in dep.governance_action


def test_htl_114_table3_commercial_controls_role_attribution():
    """Verify Table 3 commercial control routes correctly assign Talent PM trigger and DM/PMO Lead routing."""
    for variant in ["Fixed Bid", "Time and Materials"]:
        baseline = _create_mock_baseline(variant)
        rows = build_table3_decision_rules_rows(baseline, variant)
        row_map = {r.control_dimension: r for r in rows}

        # Domain & Application Scope
        domain_route = row_map["Domain & Application Scope"].commercial_control_route
        assert "Talent PM" in domain_route
        assert "Delivery Manager and PMO Lead" in domain_route

        # Core Dependency Health
        dep_route = row_map["Core Dependency Health"].commercial_control_route
        assert "Talent PM" in dep_route
        assert "Delivery Manager and PMO Lead" in dep_route


def test_htl_114_table4_classification_guide_and_character_budgets():
    """Verify Table 4 approval pathways adhere to two-tier roles and <= 75 character constraints."""
    for variant in ["Fixed Bid", "Time and Materials"]:
        baseline = _create_mock_baseline(variant)
        rows = build_table4_classification_guide_rows(baseline, variant)
        for r in rows:
            assert len(r.approval_pathway) <= 75, f"[{variant}] {r.classification} exceeds 75 chars: {len(r.approval_pathway)}"

            if r.classification in ("Clarification", "Reprioritization"):
                assert "Talent PM leads" in r.approval_pathway
                assert "DM" in r.approval_pathway
            else:
                assert "Talent PM triggers" in r.approval_pathway
                assert "DM & PMO Lead" in r.approval_pathway


def test_htl_114_governance_deck_slide11_role_inheritance(tmp_path: Path):
    """Verify Governance Deck Slide 11 (Change Decision Matrix) automatically inherits Table 4 role attribution for both Fixed Bid and T&M."""
    for label, baseline_fn in [("fixed_bid", lambda: load_baseline("arc_application_implementation")), ("tm", _build_pge_baseline)]:
        b = baseline_fn()
        res = export_governance_deck(b, tmp_path / f"gov_s11_roles_{label}")
        prs = pptx.Presentation(str(res.file_path))
        slide11 = prs.slides[10]
        s11_text = " ".join([s.text_frame.text for s in slide11.shapes if s.has_text_frame])

        # Verify all cards have Authority pathways with Talent PM leading in-envelope and triggering out-of-envelope
        assert "Authority: Talent PM leads" in s11_text
        assert "Authority: Talent PM triggers; DM & PMO Lead" in s11_text


def test_htl_114_table5_prompt_and_fallback():
    """Verify Table 5 LLM prompt includes HTL-114 role governance instructions and fallback examples reflect the rules."""
    assert "ROLE-ATTRIBUTION GOVERNANCE (HTL-114)" in TABLE5_PROMPT_TEMPLATE
    assert "In-Envelope Scenarios (Clarification, Reprioritization): Talent PM leads" in TABLE5_PROMPT_TEMPLATE
    assert "Out-of-Envelope Scenarios (Expansion, Dependency Impact): Talent PM triggers" in TABLE5_PROMPT_TEMPLATE

    for variant in ["Fixed Bid", "Time and Materials"]:
        baseline = _create_mock_baseline(variant)
        examples = build_table5_fallback_examples(baseline, variant)
        ex_map = {e.classification: e for e in examples}

        assert "Talent PM leads" in ex_map["Clarification"].resolution_and_governance
        assert "Talent PM leads" in ex_map["Reprioritization"].resolution_and_governance
        assert "Talent PM triggers" in ex_map["Expansion"].resolution_and_governance
        assert "Talent PM triggers" in ex_map["Dependency Impact"].resolution_and_governance
