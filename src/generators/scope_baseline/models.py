"""Models for the Scope Baseline document generator (HTL-108)."""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class ScopeBaselineSummaryRow(BaseModel):
    """Row in Table 1: Scope Baseline Summary (6 rows total)."""
    dimension: str
    authorized_work: str
    excluded_scope: str


class ChangeDecisionMatrixRow(BaseModel):
    """Row in Table 2: Change Decision Matrix (4 classifications)."""
    classification: Literal["Clarification", "Reprioritization", "Expansion", "Dependency Impact"]
    trigger_condition: str
    governance_action: str
    commercial_impact: str


class DecisionRuleControlRow(BaseModel):
    """Row in Table 3: Decision Rules & Commercial Controls (5 dimensions)."""
    control_dimension: str
    governing_rule: str
    boundary_violation_trigger: str
    commercial_control_route: str


class ClassificationGuideRow(BaseModel):
    """Row in Table 4: Scope Classification Guide (4 classifications)."""
    classification: Literal["Clarification", "Reprioritization", "Expansion", "Dependency Impact"]
    operational_characteristics: str
    budget_milestone_impact: str
    approval_pathway: str


class PracticalDecisionExample(BaseModel):
    """Row in Table 5: Practical Example Decisions (4 grounded scenarios)."""
    classification: Literal["Clarification", "Reprioritization", "Expansion", "Dependency Impact"]
    scenario_description: str = Field(
        description="A realistic, hypothetical scenario specific to this project's real domain and deliverables."
    )
    analysis: str = Field(
        description="Evaluation of why this scenario fits this classification against the project's baseline boundaries."
    )
    resolution_and_governance: str = Field(
        description="Concrete operational, approval, and commercial resolution strictly framed for the contract type."
    )


class ScopeBaselineTable5Extraction(BaseModel):
    """Structured extraction container for Table 5's 4 practical examples."""
    examples: List[PracticalDecisionExample] = Field(
        description="Exactly 4 grounded examples: one for Clarification, one for Reprioritization, one for Expansion, and one for Dependency Impact."
    )


class ScopeBaselineDocument(BaseModel):
    """Complete Scope Baseline document model."""
    project_name: str
    client_name: Optional[str] = None
    contract_variant: str  # "Fixed Bid" or "Time and Materials"
    governance_tier: str = "Partnered"
    delivery_model: str = "Toptal Talent Team (Agile/Milestone Hybrid)"
    table1_summary: List[ScopeBaselineSummaryRow] = Field(default_factory=list)
    table2_change_matrix: List[ChangeDecisionMatrixRow] = Field(default_factory=list)
    table3_decision_rules: List[DecisionRuleControlRow] = Field(default_factory=list)
    table4_classification_guide: List[ClassificationGuideRow] = Field(default_factory=list)
    table5_examples: List[PracticalDecisionExample] = Field(default_factory=list)
