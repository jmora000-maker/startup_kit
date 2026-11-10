"""Comprehensive test suite for Scope Baseline generator (HTL-108)."""

import tempfile
from pathlib import Path
import docx
import pytest

from src.core.models import (
    StartupKitBaseline,
    ProjectStartupCharter,
    SOWInterpretationSummary,
    Deliverable,
    Milestone,
    DependencyAssumptionItem,
    CommercialGuardrail,
)
from src.core.outputs import OutputSelection, RunResult
from src.generators.scope_baseline import (
    export_scope_baseline,
    build_scope_baseline_document,
    write_scope_baseline_docx,
    validate_scope_baseline_document,
    ScopeBaselineResult,
    ScopeBaselineDocument,
)
from src.generators.scope_baseline.templates import resolve_contract_variant
from src.generators.scope_baseline.models import (
    ScopeBaselineTable5Extraction,
    PracticalDecisionExample,
)
from src.review_ui.generate import (
    validate_output_selection,
    collect_download_targets,
)
from src.review_ui.facts import label_for_generated_file


def _create_sample_baseline(contract_type: str = "Time and Materials") -> StartupKitBaseline:
    charter = ProjectStartupCharter(
        project_name="Syngenta Pipeline Pilot",
        client_name="Syngenta",
        contract_type=contract_type,
        governance_tier="Partnered",
        delivery_model="Toptal Talent Team (Agile/Milestone Hybrid)",
        project_purpose="Accelerate pipeline pilot delivery and establish data engineering foundation.",
        problem_statement="Legacy data pipeline throughput is insufficient for real-time agronomic analytics.",
        delivery_objectives=["Deploy pilot pipeline", "Validate ingestion latency < 5 minutes"],
        high_level_scope=["Core ingestion pipeline", "Cloud data warehouse staging", "Data validation APIs"],
        exclusions=["Legacy on-premise database remediation", "Third-party ERP integration", "Production 24/7 on-call support"],
        key_deliverables_summary=["DEL-01: Architecture Design", "DEL-02: Pipeline Implementation"],
    )
    sow_int = SOWInterpretationSummary(
        contracted_deliverables=["Architecture Blueprint", "Data Pipeline MVP"],
        out_of_scope_items=["Legacy ERP Migration", "Custom Reporting Portal"],
        platform_environment_commitments=["AWS Glue", "Snowflake Staging Environment"],
        dependencies=["Client AWS environment access", "Sample agronomic dataset provision"],
        customer_obligations=["Provide cloud credentials within 3 business days of kickoff"],
    )
    delivs = [
        Deliverable(id="DEL-01", name="Architecture Blueprint", description="Technical architecture document and data flow diagrams"),
        Deliverable(id="DEL-02", name="Pipeline MVP", description="Production-ready ingestion pipeline with automated unit testing"),
    ]
    deps = [
        DependencyAssumptionItem(
            id="DEP-01",
            type="Dependency",
            description="Client cloud VPC access and IAM roles",
            impact_if_unmet="Deployment delayed; milestone gate blocked",
        )
    ]
    guardrails = CommercialGuardrail(
        contract_type_implication=f"Operates under {contract_type} governance.",
        approved_work_rule="Only authorized project scope is permitted.",
        change_control_trigger="Scope addition or budget variance > 10%",
    )
    return StartupKitBaseline(
        project_name="Syngenta Pipeline Pilot",
        contract_type=contract_type,
        governance_tier="Partnered",
        charter=charter,
        sow_interpretation=sow_int,
        deliverables=delivs,
        dependencies_assumptions=deps,
        commercial_guardrails=guardrails,
    )


def test_variant_resolution():
    assert resolve_contract_variant("Fixed Bid") == "Fixed Bid"
    assert resolve_contract_variant("Fixed-Price Milestone") == "Fixed Bid"
    assert resolve_contract_variant("Time and Materials") == "Time and Materials"
    assert resolve_contract_variant("T&M Hourly") == "Time and Materials"
    assert resolve_contract_variant(None) == "Time and Materials"
    assert resolve_contract_variant("Unrecognized Custom Type") == "Time and Materials"


def test_build_scope_baseline_fixed_bid():
    baseline = _create_sample_baseline("Fixed Bid")
    doc_model = build_scope_baseline_document(baseline)

    assert doc_model.project_name == "Syngenta Pipeline Pilot"
    assert doc_model.contract_variant == "Fixed Bid"
    assert len(doc_model.table1_summary) == 6
    assert len(doc_model.table2_change_matrix) == 4
    assert len(doc_model.table3_decision_rules) == 5
    assert len(doc_model.table4_classification_guide) == 4
    assert len(doc_model.table5_examples) == 4

    # Neutral label verification
    t1_dims = [r.dimension for r in doc_model.table1_summary]
    assert "Delivery Model & Service Boundaries" in t1_dims
    assert "Depth of Advisory Services" not in t1_dims

    t3_dims = [r.control_dimension for r in doc_model.table3_decision_rules]
    assert "Service Depth & Delivery Boundaries" in t3_dims
    assert "Advisory vs. Execution" not in t3_dims

    # Validation
    findings = validate_scope_baseline_document(doc_model)
    assert findings == []


def test_build_scope_baseline_time_and_materials():
    baseline = _create_sample_baseline("Time and Materials")
    doc_model = build_scope_baseline_document(baseline)

    assert doc_model.project_name == "Syngenta Pipeline Pilot"
    assert doc_model.contract_variant == "Time and Materials"
    assert len(doc_model.table1_summary) == 6
    assert len(doc_model.table2_change_matrix) == 4
    assert len(doc_model.table3_decision_rules) == 5
    assert len(doc_model.table4_classification_guide) == 4
    assert len(doc_model.table5_examples) == 4

    # Classification check
    t5_classes = {e.classification for e in doc_model.table5_examples}
    assert t5_classes == {"Clarification", "Reprioritization", "Expansion", "Dependency Impact"}

    # Validation
    findings = validate_scope_baseline_document(doc_model)
    assert findings == []


def test_export_scope_baseline_docx_fixed_bid():
    baseline = _create_sample_baseline("Fixed Bid")
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = Path(tmp_dir)
        result: ScopeBaselineResult = export_scope_baseline(baseline, out_path)

        assert result.file_path.exists()
        assert result.file_path.name == "Syngenta_Pipeline_Pilot_Scope_Baseline_Fixed_Bid.docx"
        assert result.variant == "Fixed Bid"
        assert result.tables_count == 5
        assert result.examples_count == 4

        # Read back document with python-docx
        doc = docx.Document(str(result.file_path))
        assert len(doc.tables) >= 6  # 1 callout box table + 5 content tables

        # Table 1: Scope Baseline Summary
        t1 = doc.tables[1]
        assert len(t1.rows) == 7  # header + 6 data rows
        assert "Engagement Objective & Purpose" in t1.rows[1].cells[0].text
        assert "Delivery Model & Service Boundaries" in t1.rows[4].cells[0].text


def test_export_scope_baseline_docx_tm():
    baseline = _create_sample_baseline("Time and Materials")
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = Path(tmp_dir)
        result: ScopeBaselineResult = export_scope_baseline(baseline, out_path)

        assert result.file_path.exists()
        assert result.file_path.name == "Syngenta_Pipeline_Pilot_Scope_Baseline_Time_and_Materials.docx"
        assert result.variant == "Time and Materials"
        assert result.tables_count == 5
        assert result.examples_count == 4

        # Read back document with python-docx
        doc = docx.Document(str(result.file_path))
        assert len(doc.tables) >= 6


def test_table5_mock_llm_synthesis():
    baseline = _create_sample_baseline("Fixed Bid")

    class FakeLLMClient:
        def generate_structured(self, prompt, schema, system_prompt=None):
            return ScopeBaselineTable5Extraction(
                examples=[
                    PracticalDecisionExample(
                        classification="Clarification",
                        scenario_description="Refining data schema validation format for DEL-01.",
                        analysis="Minor formatting update within deliverable boundary.",
                        resolution_and_governance="Logged in Decision Log with zero cost impact.",
                    ),
                    PracticalDecisionExample(
                        classification="Reprioritization",
                        scenario_description="Swapping module sequence in DEL-02.",
                        analysis="Equal effort trade-off.",
                        resolution_and_governance="Approved by Delivery Manager with no milestone date change.",
                    ),
                    PracticalDecisionExample(
                        classification="Expansion",
                        scenario_description="Adding third-party ERP integration.",
                        analysis="Exceeds stated fixed bid scope.",
                        resolution_and_governance="Requires formal Change Order and fee adjustment.",
                    ),
                    PracticalDecisionExample(
                        classification="Dependency Impact",
                        scenario_description="Client AWS access delayed by 10 days.",
                        analysis="Blocks milestone testing.",
                        resolution_and_governance="Schedule relief enacted day-for-day.",
                    ),
                ]
            )

    doc_model = build_scope_baseline_document(baseline, llm_client=FakeLLMClient())
    assert len(doc_model.table5_examples) == 4
    assert doc_model.table5_examples[0].scenario_description.startswith("Refining data schema")
    assert validate_scope_baseline_document(doc_model) == []


def test_ui_and_outputs_integration():
    # 1. OutputSelection
    out_sel = OutputSelection(scope_baseline=True)
    assert out_sel.scope_baseline is True

    # 2. validate_output_selection
    assert validate_output_selection(OutputSelection(scope_baseline=True)) is None
    assert validate_output_selection(scope_baseline=True) is None
    assert validate_output_selection(OutputSelection(kit=False, workbook=False, slides=False, client_deck=False, scope_baseline=False)) is not None

    # 3. collect_download_targets
    fake_path = Path("Syngenta_Scope_Baseline_Fixed_Bid.docx")
    run_result = RunResult(
        scope_baseline=ScopeBaselineResult(
            file_path=fake_path,
            variant="Fixed Bid",
            project_name="Syngenta",
        )
    )
    targets = collect_download_targets(run_result)
    assert any(t.label == "Scope Baseline (.docx)" for t in targets)

    # 4. label_for_generated_file
    assert label_for_generated_file("Syngenta_Scope_Baseline_Fixed_Bid.docx") == "Scope Baseline (.docx)"
    assert label_for_generated_file("Syngenta_Scope_Baseline_Time_and_Materials.docx") == "Scope Baseline (.docx)"


def test_methodology_neutrality_no_agile_jargon_in_scope_baseline():
    """Verify that neither Fixed Bid nor T&M Scope Baseline text contains hardcoded Agile/Scrum jargon."""
    import re

    banned_agile_patterns = [
        r"\bsprint(?:s)?\b",
        r"\bbacklog(?:s)?\b",
        r"\bproduct owner\b",
        r"\buser stor(?:y|ies)\b",
        r"\bstandup(?:s)?\b",
        r"\bceremon(?:y|ies)\b",
        r"\bstory points\b",
        r"\bepics?\b",
    ]

    for variant in ("Fixed Bid", "Time and Materials"):
        baseline = _create_sample_baseline(variant)
        doc_model = build_scope_baseline_document(baseline)

        # Collect all generated text across all 5 tables
        all_text_fragments = []
        for r in doc_model.table1_summary:
            all_text_fragments.extend([r.dimension, r.authorized_work, r.excluded_scope])
        for r in doc_model.table2_change_matrix:
            all_text_fragments.extend([r.classification, r.trigger_condition, r.governance_action, r.commercial_impact])
        for r in doc_model.table3_decision_rules:
            all_text_fragments.extend([r.control_dimension, r.governing_rule, r.boundary_violation_trigger, r.commercial_control_route])
        for r in doc_model.table4_classification_guide:
            all_text_fragments.extend([r.classification, r.operational_characteristics, r.budget_milestone_impact, r.approval_pathway])
        for e in doc_model.table5_examples:
            all_text_fragments.extend([e.classification, e.scenario_description, e.analysis, e.resolution_and_governance])

        full_doc_text = " ".join(all_text_fragments)

        for pat in banned_agile_patterns:
            matches = re.findall(pat, full_doc_text, flags=re.IGNORECASE)
            assert not matches, f"Found forbidden Agile/Scrum term matching '{pat}' in {variant} Scope Baseline: {matches}"
