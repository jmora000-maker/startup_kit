"""Validation rules for Scope Baseline document (HTL-108)."""

import re
from typing import List
from src.generators.scope_baseline.models import ScopeBaselineDocument, PracticalDecisionExample

REQUIRED_TABLE1_DIMENSIONS = [
    "Engagement Objective & Purpose",
    "Application Scope & Boundary",
    "Authorized Deliverables & Work Streams",
    "Delivery Model & Service Boundaries",
    "Operating Assumptions & Dependencies",
    "Commercial Controls & Governance",
]

REQUIRED_CLASSIFICATIONS = {"Clarification", "Reprioritization", "Expansion", "Dependency Impact"}

REQUIRED_TABLE3_DIMENSIONS = [
    "Deliverable Boundary",
    "Domain & Application Scope",
    "Service Depth & Delivery Boundaries",
    "Effort Burn & NTE Ceilings",
    "Core Dependency Health",
]

# Commercial term safeguards
BANNED_FIXED_BID_TERMS = [
    r"\bNTE\b",
    r"\bnot-to-exceed\b",
    r"\bhourly burn\b",
    r"\btimesheet(?:s)? billing\b",
    r"\bweekly burn rate\b",
]

BANNED_TM_TERMS = [
    r"\bfixed[- ]price milestone\b",
    r"\bfixed fee milestone\b",
    r"\bfixed contract fee\b",
]


def validate_table5_examples(examples: List[PracticalDecisionExample], variant: str) -> List[str]:
    """Validate Table 5 examples for structural completeness and commercial framing."""
    findings = []
    if len(examples) != 4:
        findings.append(f"Table 5 must have exactly 4 examples, found {len(examples)}.")
    
    seen_classes = set(e.classification for e in examples)
    if seen_classes != REQUIRED_CLASSIFICATIONS:
        missing = REQUIRED_CLASSIFICATIONS - seen_classes
        extra = seen_classes - REQUIRED_CLASSIFICATIONS
        findings.append(f"Table 5 classifications mismatch. Missing: {missing}, Extra: {extra}")

    # Check commercial framing in examples
    is_fixed = variant == "Fixed Bid"
    for ex in examples:
        text_to_check = f"{ex.scenario_description} {ex.analysis} {ex.resolution_and_governance}"
        if is_fixed:
            for pat in BANNED_FIXED_BID_TERMS:
                if re.search(pat, text_to_check, re.IGNORECASE):
                    findings.append(f"Fixed Bid example for '{ex.classification}' mentions forbidden T&M term matching '{pat}'.")
        else:
            for pat in BANNED_TM_TERMS:
                if re.search(pat, text_to_check, re.IGNORECASE):
                    findings.append(f"Time and Materials example for '{ex.classification}' mentions forbidden Fixed Bid term matching '{pat}'.")

    return findings


def validate_scope_baseline_document(doc: ScopeBaselineDocument) -> List[str]:
    """Validate full Scope Baseline document model."""
    findings = []

    # 1. Table 1 validation
    if len(doc.table1_summary) != 6:
        findings.append(f"Table 1 must have 6 rows, found {len(doc.table1_summary)}.")
    t1_dims = [r.dimension for r in doc.table1_summary]
    for req_dim in REQUIRED_TABLE1_DIMENSIONS:
        if req_dim not in t1_dims:
            findings.append(f"Table 1 missing required dimension '{req_dim}'.")

    # 2. Table 2 validation
    if len(doc.table2_change_matrix) != 4:
        findings.append(f"Table 2 must have 4 rows, found {len(doc.table2_change_matrix)}.")
    t2_classes = set(r.classification for r in doc.table2_change_matrix)
    if t2_classes != REQUIRED_CLASSIFICATIONS:
        findings.append(f"Table 2 classifications mismatch: {t2_classes} vs {REQUIRED_CLASSIFICATIONS}.")

    # 3. Table 3 validation
    if len(doc.table3_decision_rules) != 5:
        findings.append(f"Table 3 must have 5 rows, found {len(doc.table3_decision_rules)}.")
    t3_dims = [r.control_dimension for r in doc.table3_decision_rules]
    for req_dim in REQUIRED_TABLE3_DIMENSIONS:
        if req_dim not in t3_dims:
            findings.append(f"Table 3 missing required dimension '{req_dim}'.")

    # 4. Table 4 validation
    if len(doc.table4_classification_guide) != 4:
        findings.append(f"Table 4 must have 4 rows, found {len(doc.table4_classification_guide)}.")
    t4_classes = set(r.classification for r in doc.table4_classification_guide)
    if t4_classes != REQUIRED_CLASSIFICATIONS:
        findings.append(f"Table 4 classifications mismatch: {t4_classes} vs {REQUIRED_CLASSIFICATIONS}.")

    # 5. Table 5 validation
    t5_findings = validate_table5_examples(doc.table5_examples, doc.contract_variant)
    findings.extend(t5_findings)

    return findings
