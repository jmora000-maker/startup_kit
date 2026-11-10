"""Builder for the Scope Baseline document model (HTL-108)."""

import logging
from typing import Optional
from src.core.interfaces import ILLMClient
from src.core.models import StartupKitBaseline
from src.generators.scope_baseline.models import (
    ScopeBaselineDocument,
    ScopeBaselineTable5Extraction,
)
from src.generators.scope_baseline.templates import (
    resolve_contract_variant,
    build_table1_summary_rows,
    build_table2_change_matrix_rows,
    build_table3_decision_rules_rows,
    build_table4_classification_guide_rows,
    build_table5_fallback_examples,
)
from src.generators.scope_baseline.validator import validate_table5_examples

logger = logging.getLogger(__name__)

TABLE5_SYSTEM_PROMPT = """You are an expert PMO Delivery Consultant drafting Section 5 ("Practical Example Decisions") of a project Scope Baseline document.
Your job is to generate exactly 4 realistic, hypothetical decision scenarios grounded strictly in the project's real scope boundary, deliverables, exclusions, and commercial structure."""

TABLE5_PROMPT_TEMPLATE = """Generate exactly 4 realistic, hypothetical decision scenarios that illustrate how the established scope baseline rules apply during delivery.

GROUNDING FACTS (DO NOT CONTRADICT OR INVENT NEW CONTRACTUAL SCOPE):
- Project Name: {project_name}
- Client Name: {client_name}
- Commercial Structure: {contract_variant}
- Delivery Model: {delivery_model}
- Authorized Scope: {high_level_scope}
- Target Platforms / Environments: {platform_commitments}
- Key Deliverables: {deliverables_summary}
- Stated Exclusions & Out-of-Scope: {exclusions_summary}
- Key Dependencies & Client Obligations: {dependencies_summary}

RULES:
1. Generate EXACTLY ONE example for each of the following 4 classifications:
   - Clarification: Minor ambiguity, format adjustment, or design refinement within an authorized deliverable that requires no schedule or budget variance.
   - Reprioritization: Request to swap, reorder, or defer work items of equivalent complexity within the authorized scope envelope without altering overall price or milestone delivery dates.
   - Expansion: Request for new functionality, unsupported platforms, or features outside the authorized scope, requiring a formal Change Order (Fixed Bid) or Work Authorization / NTE ceiling increase (Time & Materials).
   - Dependency Impact: Client delay or external blocker to a stated dependency, triggering contractual Schedule Relief protocols or standby procedures.
2. GROUNDING REQUIREMENT: Scenarios must directly reference the real components, tools, systems, dependencies, and deliverables listed above. Do NOT use generic placeholder text (e.g., 'System X', 'Feature Y').
3. COMMERCIAL FRAMING CONSISTENCY:
   - If Fixed Bid: Frame resolutions around fixed deliverable acceptance, milestone sign-offs, zero unauthorized budget variance, and formal Change Orders. Never mention hourly caps, timesheet tracking, or NTE burn.
   - If Time and Materials: Frame resolutions around work package prioritization, authorized weekly capacity, effort burn rates, and NTE ceiling governance. Never claim deliverables are fixed-price milestones.
4. Each scenario must include:
   - classification: "Clarification" | "Reprioritization" | "Expansion" | "Dependency Impact"
   - scenario_description: Concrete, realistic narrative vignette.
   - analysis: Detailed evaluation of why this scenario fits this classification against the project's baseline boundaries.
   - resolution_and_governance: Specific operational, approval, and commercial resolution strictly framed for {contract_variant}.
"""


def _format_context_summary(items: list, default: str = "None specified") -> str:
    clean = [str(x).strip() for x in items if str(x).strip() and not str(x).startswith("[CONFIRMATION")]
    return "; ".join(clean) if clean else default


def build_scope_baseline_document(
    baseline: StartupKitBaseline,
    llm_client: Optional[ILLMClient] = None,
) -> ScopeBaselineDocument:
    """Build complete Scope Baseline document model from StartupKitBaseline."""
    variant = resolve_contract_variant(baseline.contract_type)
    charter = baseline.charter
    sow_int = baseline.sow_interpretation

    project_name = baseline.project_name or "Project"
    client_name = charter.client_name if charter else None
    governance_tier = baseline.governance_tier or "Partnered"
    delivery_model = charter.delivery_model if (charter and charter.delivery_model) else "Toptal Talent Team (Agile/Milestone Hybrid)"

    # Deterministic generation for Tables 1 to 4
    table1 = build_table1_summary_rows(baseline, variant)
    table2 = build_table2_change_matrix_rows(baseline, variant)
    table3 = build_table3_decision_rules_rows(baseline, variant)
    table4 = build_table4_classification_guide_rows(baseline, variant)

    # Table 5: Single-pass LLM synthesis with deterministic fallback
    table5_examples = None
    if llm_client is not None and hasattr(llm_client, "generate_structured"):
        try:
            high_level_scope = _format_context_summary(charter.high_level_scope if charter else [])
            platform_commitments = _format_context_summary(sow_int.platform_environment_commitments if sow_int else [])
            deliv_list = [f"{d.id}: {d.name}" for d in baseline.deliverables] if baseline.deliverables else (charter.key_deliverables_summary if charter else [])
            deliverables_summary = _format_context_summary(deliv_list)
            excl_list = (charter.exclusions if charter else []) + (sow_int.out_of_scope_items if sow_int else [])
            exclusions_summary = _format_context_summary(excl_list)
            dep_list = [f"{d.id}: {d.description}" for d in baseline.dependencies_assumptions] if baseline.dependencies_assumptions else (sow_int.dependencies if sow_int else [])
            dependencies_summary = _format_context_summary(dep_list)

            prompt = TABLE5_PROMPT_TEMPLATE.format(
                project_name=project_name,
                client_name=client_name or "Client",
                contract_variant=variant,
                delivery_model=delivery_model,
                high_level_scope=high_level_scope,
                platform_commitments=platform_commitments,
                deliverables_summary=deliverables_summary,
                exclusions_summary=exclusions_summary,
                dependencies_summary=dependencies_summary,
            )

            logger.info("Executing single-pass LLM synthesis for Scope Baseline Table 5 (%s)...", variant)
            result = llm_client.generate_structured(
                prompt=prompt,
                schema=ScopeBaselineTable5Extraction,
                system_prompt=TABLE5_SYSTEM_PROMPT,
            )

            if isinstance(result, ScopeBaselineTable5Extraction) and result.examples:
                findings = validate_table5_examples(result.examples, variant)
                if not findings:
                    table5_examples = result.examples
                    logger.info("Table 5 single-pass LLM synthesis succeeded and passed all validation checks.")
                else:
                    logger.warning("Table 5 LLM output failed validation checks (%s); using deterministic fallback.", findings)
            else:
                logger.warning("Table 5 LLM output was empty or invalid schema; using deterministic fallback.")
        except Exception as exc:
            logger.warning("Error during Scope Baseline Table 5 LLM generation: %s. Using deterministic fallback.", exc)

    if not table5_examples:
        table5_examples = build_table5_fallback_examples(baseline, variant)

    return ScopeBaselineDocument(
        project_name=project_name,
        client_name=client_name,
        contract_variant=variant,
        governance_tier=governance_tier,
        delivery_model=delivery_model,
        table1_summary=table1,
        table2_change_matrix=table2,
        table3_decision_rules=table3,
        table4_classification_guide=table4,
        table5_examples=table5_examples,
    )
