"""Pydantic data models and schemas for the Startup Kit Generator."""

import re
from datetime import date, datetime
from typing import List, Optional, Literal, Dict, Any, Union, Annotated
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, model_validator, BeforeValidator
from src.core.pdf_models import PDFDocumentMetadata, PDFPageMetadata


def parse_flexible_date(v: Any) -> Optional[date]:
    """Parse flexible date strings, timestamps, or date objects gracefully."""
    if v is None or v == "":
        return None
    if isinstance(v, date):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        v_clean = v.strip()
        if not v_clean or v_clean.lower() in (
            "none", "null", "n/a", "na", "tbd", "to be determined",
            "undefined", "[confirmation required]", "unassigned"
        ):
            return None
        # Match standard ISO YYYY-MM-DD or YYYY/MM/DD
        iso_match = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", v_clean)
        if iso_match:
            try:
                year, month, day = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
                return date(year, month, day)
            except ValueError:
                pass
        # Match DD/MM/YYYY or MM/DD/YYYY
        alt_match = re.search(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", v_clean)
        if alt_match:
            try:
                p1, p2, year = int(alt_match.group(1)), int(alt_match.group(2)), int(alt_match.group(3))
                if p1 > 12 >= p2:
                    return date(year, p2, p1)
                elif p2 > 12 >= p1:
                    return date(year, p1, p2)
                else:
                    return date(year, p1, p2)
            except ValueError:
                pass
        return None
    return None


FlexibleDate = Annotated[Optional[date], BeforeValidator(parse_flexible_date)]


def normalize_governance_tier(v: Any) -> Any:
    if not isinstance(v, str):
        return v
    v_clean = v.strip()
    v_lower = v_clean.lower()
    if "guided" in v_lower:
        return "Guided"
    if "elevated" in v_lower:
        return "Elevated"
    if "partnered" in v_lower:
        return "Partnered"
    return v_clean


GovernanceTier = Annotated[Literal["Guided", "Partnered", "Elevated"], BeforeValidator(normalize_governance_tier)]


def normalize_raid_type(v: Any) -> Any:
    if not isinstance(v, str):
        return v
    v_clean = v.strip()
    v_lower = v_clean.lower()
    if "risk" in v_lower:
        return "Risk"
    if "assump" in v_lower:
        return "Assumption"
    if "issue" in v_lower:
        return "Issue"
    if "depend" in v_lower:
        return "Dependency"
    return v_clean


RAIDType = Annotated[Literal["Risk", "Assumption", "Issue", "Dependency"], BeforeValidator(normalize_raid_type)]


def normalize_dep_assump_type(v: Any) -> Any:
    if not isinstance(v, str):
        return v
    v_clean = v.strip()
    v_lower = v_clean.lower()
    if "depend" in v_lower:
        return "Dependency"
    if "assump" in v_lower:
        return "Assumption"
    return v_clean


DependencyAssumptionType = Annotated[Literal["Dependency", "Assumption"], BeforeValidator(normalize_dep_assump_type)]


def normalize_checklist_status(v: Any) -> Any:
    if not isinstance(v, str):
        return v
    valid = {
        "not started": "Not Started",
        "in progress": "In Progress",
        "review required": "Review Required",
        "confirmation required": "Confirmation Required",
        "complete": "Complete",
        "exception required": "Exception Required",
        "approved": "Approved",
        "approved with exception": "Approved with Exception",
        "rework required": "Rework Required",
    }
    v_clean = v.strip().lower()
    return valid.get(v_clean, v)


ChecklistStatus = Annotated[
    Literal[
        "Not Started",
        "In Progress",
        "Review Required",
        "Confirmation Required",
        "Complete",
        "Exception Required",
        "Approved",
        "Approved with Exception",
        "Rework Required"
    ],
    BeforeValidator(normalize_checklist_status)
]


class DocumentSection(BaseModel):
    """Represents an extracted structural section or slide of a document."""
    model_config = ConfigDict(extra="forbid")

    title: str = ""
    content: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExtractedDocument(BaseModel):
    """Represents normalized extracted content from a single input file."""
    model_config = ConfigDict(extra="forbid")

    file_name: str
    file_type: str
    file_path: Path
    text_content: str = ""
    sections: List[DocumentSection] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_pdf_invariants(self) -> "ExtractedDocument":
        if self.file_type.lower() != "pdf":
            return self

        # 1. Validate document-level metadata
        try:
            doc_meta = PDFDocumentMetadata.model_validate(self.metadata)
        except Exception as exc:
            raise ValueError(f"Invalid PDF document metadata in '{self.file_name}': {exc}") from exc

        # 2. Total pages invariant
        if doc_meta.total_pages != len(self.sections):
            raise ValueError(
                f"PDF metadata total_pages ({doc_meta.total_pages}) does not match "
                f"section count ({len(self.sections)}) in '{self.file_name}'"
            )

        # 3. Section page metadata & sequential order invariant
        normalized_sections: List[DocumentSection] = []
        for idx, sec in enumerate(self.sections):
            try:
                page_meta = PDFPageMetadata.model_validate(sec.metadata)
            except Exception as exc:
                raise ValueError(
                    f"Invalid PDF page metadata in '{self.file_name}' at section index {idx}: {exc}"
                ) from exc

            expected_page_num = idx + 1
            if page_meta.page_number != expected_page_num:
                raise ValueError(
                    f"PDF page sequence error in '{self.file_name}': section index {idx} "
                    f"has page_number {page_meta.page_number}, expected {expected_page_num}"
                )

            # Build normalized section copy without mutating caller-owned objects
            normalized_sec = sec.model_copy(update={"metadata": page_meta.model_dump()})
            normalized_sections.append(normalized_sec)

        # 4. Commit validated metadata and sections
        self.metadata = doc_meta.model_dump()
        self.sections = normalized_sections
        return self


class SourceReference(BaseModel):
    """Traceability reference linking extracted data to source files and clauses."""
    document_name: str = "Project Baseline"
    clause_or_slide: Optional[str] = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)


class Deliverable(BaseModel):
    """Project deliverable with explicit acceptance criteria, ownership, and acceptance route."""
    id: str = "DEL-01"
    name: str = ""
    description: str = ""
    source_reference: SourceReference = Field(
        default_factory=lambda: SourceReference(document_name="Project Baseline")
    )
    owner: str = "Unassigned"
    acceptance_criteria: Optional[str] = None
    sow_reference: Optional[str] = None
    evidence_required: str = "[CONFIRMATION REQUIRED]"
    client_approver: str = "[UNASSIGNED - TO BE CONFIRMED]"
    submission_target_date: FlexibleDate = None
    review_window: str = "5 business days"
    rejection_rework_path: str = "Talent PM / Team rework within 3 business days of notice"
    unresolved_acceptance_clarifications: List[str] = Field(default_factory=list)
    linked_action_id: Optional[str] = Field(
        default=None,
        description="Associated Action ID if unassigned or unconfirmed (e.g. 'ACT-03')"
    )

    def model_post_init(self, __context: Any) -> None:
        if not self.name and self.description:
            self.name = self.description
        elif not self.description and self.name:
            self.description = self.name
        if not self.sow_reference and self.source_reference:
            loc = f" ({self.source_reference.clause_or_slide})" if self.source_reference.clause_or_slide else ""
            self.sow_reference = f"{self.source_reference.document_name}{loc}"


class Milestone(BaseModel):
    """Project milestone tracking external commitment dates, internal buffer dates, and dependencies."""
    id: str = "MS-01"
    description: str = ""
    external_date: FlexibleDate = None
    internal_buffer_date: FlexibleDate = None
    owner: str = "Delivery Manager"
    key_dependencies: List[str] = Field(default_factory=list)
    critical_path_assumptions: List[str] = Field(default_factory=list)
    source_reference: SourceReference = Field(
        default_factory=lambda: SourceReference(document_name="Project Baseline")
    )
    linked_action_id: Optional[str] = Field(
        default=None,
        description="Associated Action ID if date unconfirmed (e.g. 'ACT-04')"
    )


class RiskAssumption(BaseModel):
    """Risk, Assumption, Issue, or Dependency (RAID) item."""
    type: RAIDType = "Risk"
    description: str = ""
    owner: str = "Unassigned"
    status: str = "Open"
    source_reference: SourceReference = Field(
        default_factory=lambda: SourceReference(document_name="Project Baseline")
    )
    category: str = "Technical"
    probability: Optional[str] = "Medium"
    impact: str = "Medium"
    severity: str = "Medium"
    trigger_or_early_warning: str = "Initial startup assessment"
    mitigation_or_response: str = "Active monitoring by PMO and Delivery Manager"
    due_date: FlexibleDate = None
    linked_decision: Optional[str] = None
    linked_dependency_or_assumption: Optional[str] = None
    linked_action_id: Optional[str] = Field(
        default=None,
        description="Associated Action ID if unassigned or unmitigated (e.g. 'ACT-05')"
    )


class DependencyAssumptionItem(BaseModel):
    """Dedicated Dependency and Assumption log item."""
    id: str = "DEP-01"
    type: DependencyAssumptionType = "Dependency"
    description: str = ""
    category: str = "Technical"
    source_reference: SourceReference = Field(
        default_factory=lambda: SourceReference(document_name="Project Baseline")
    )
    owner: str = "[UNASSIGNED - TO BE CONFIRMED]"
    required_validation_date: FlexibleDate = None
    impact_if_unmet: str = "Delivery delay / milestone impediment"
    status: str = "Open"
    escalation_trigger: str = "Milestone delay or unconfirmed prerequisite"
    linked_milestone: Optional[str] = None
    linked_deliverable: Optional[str] = None
    linked_open_question: Optional[str] = None
    linked_action_id: Optional[str] = Field(
        default=None,
        description="Associated Action ID if unassigned or open (e.g. 'ACT-05')"
    )


class DecisionItem(BaseModel):
    """Decision log record seeded during Readiness."""
    id: str = "DEC-01"
    decision_text: str = ""
    decision_owner: str = "PMO Lead"
    decision_date: FlexibleDate = None
    rationale: str = ""
    linked_raid_item: Optional[str] = None
    linked_artifact: Optional[str] = None
    source_reference: Optional[SourceReference] = None
    status: str = "Approved"
    linked_action_id: Optional[str] = Field(
        default=None,
        description="Associated Action ID"
    )


class WorkPackageSeed(BaseModel):
    """Scope decomposition / backlog seed item."""
    id: str = "WP-01"
    parent_deliverable_id: str = "DEL-01"
    title: str = ""
    description: str = ""
    preliminary_sequence: int = 1
    owner: str = "[UNASSIGNED - TO BE CONFIRMED]"
    dependency_references: List[str] = Field(default_factory=list)
    linked_milestones: List[str] = Field(default_factory=list)
    linked_acceptance_items: List[str] = Field(default_factory=list)
    uncertain_scope: bool = False
    status: str = "Draft"
    linked_action_id: Optional[str] = Field(
        default=None,
        description="Associated Action ID"
    )


class ProjectStartupCharter(BaseModel):
    """Project Startup Charter model (Layer 1)."""
    project_name: str = "Project Baseline"
    client_name: Optional[str] = None
    project_purpose: str = "[CONFIRMATION REQUIRED]"
    delivery_objectives: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    high_level_scope: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)
    key_deliverables_summary: List[str] = Field(default_factory=list)
    key_milestones_summary: List[str] = Field(default_factory=list)
    contract_type: str = "Time and Materials"
    governance_tier: GovernanceTier = "Partnered"
    delivery_model: str = "Toptal Talent Team (Agile/Milestone Hybrid)"
    governance_model: str = "PMO Standard Governance Model"
    major_startup_risks: List[str] = Field(default_factory=list)
    delivery_manager: str = "[UNASSIGNED - TO BE CONFIRMED]"
    talent_pm: str = "[UNASSIGNED - TO BE CONFIRMED]"
    pmo_lead: str = "[UNASSIGNED - TO BE CONFIRMED]"
    escalation_path: str = "Talent PM / Delivery Manager -> PMO Lead -> Director, PMO"
    unresolved_assumptions_status: str = "[CONFIRMATION REQUIRED]"
    source_reference: Optional[SourceReference] = None


class SOWInterpretationSummary(BaseModel):
    """SOW Interpretation Summary model (Layer 1)."""
    contracted_deliverables: List[str] = Field(default_factory=list)
    out_of_scope_items: List[str] = Field(default_factory=list)
    customer_obligations: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    platform_environment_commitments: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    approval_expectations: str = "[CONFIRMATION REQUIRED]"
    ambiguity_notes: List[str] = Field(default_factory=list)
    confirmation_required_items: List[str] = Field(default_factory=list)
    contract_ambiguities: List["ContractAmbiguityItem"] = Field(default_factory=list)
    source_reference: Optional[SourceReference] = None


class ContractAmbiguityItem(BaseModel):
    """Detected contractual ambiguity, conflict, or non-testable clause (NFR-02)."""
    anomaly_id: str = "AMB-01"
    category: str = "Scope Contradiction"  # Date Conflict, Scope Contradiction, Ambiguous Acceptance, Unclear SLA, Ownership Gap
    conflicting_clauses: str = ""
    risk_impact: str = "Potential schedule or cost variance"
    recommended_clarification: str = ""
    status: str = "Open"  # Open, Escalated, Resolved
    source_reference: Optional[SourceReference] = None
    linked_action_id: Optional[str] = Field(
        default=None,
        description="Associated Action ID (e.g. 'ACT-14')"
    )


ReadinessWorkflowState = Literal[
    "Awarded",
    "Drafting in Progress",
    "Review in Progress",
    "Clarification Pending",
    "Talent Onboarding in Progress",
    "Ready for G-01 Gate Review",
    "Approved for Mobilize",
    "Approved with Exception",
    "Rework Required"
]


class CommunicationsPlanItem(BaseModel):
    """Communications and Reporting Plan item (Layer 2)."""
    id: str = "COM-01"
    name: str = "Status Report"
    audience: str = "Stakeholders"
    content_owner: str = "Delivery Manager"
    cadence: str = "Weekly"
    governance_tier_applicability: str = "All Tiers"
    format: str = "Meeting / Written Report"
    delivery_day: str = "Weekly"
    escalation_route: str = "PMO Lead -> Director, PMO"
    pmo_health_rating_notes: str = "PMO Lead issues independent health rating after evidence exchange"
    linked_action_id: Optional[str] = Field(
        default=None,
        description="Associated Action ID (e.g. 'ACT-11')"
    )


class Stakeholder(BaseModel):
    """Stakeholder record (Layer 3)."""
    name: str = "Client Sponsor"
    role: str = "Sponsor"
    organization: str = "Toptal"
    decision_rights: str = "Standard"
    approver_responsibilities: str = "N/A"
    escalation_responsibility: str = "PMO Lead"
    reporting_accountability: str = "Weekly PSR"
    linked_action_id: Optional[str] = Field(
        default=None,
        description="Associated Action ID (e.g. 'ACT-09')"
    )


class RACIItem(BaseModel):
    """RACI decision rights matrix entry (Layer 3)."""
    decision_or_activity: str = ""
    pmo_lead: str = "A"
    delivery_manager: str = "C"
    talent_pm: str = "R"
    sales_accounts: str = "I"
    client: str = "I"


class CommercialGuardrail(BaseModel):
    """Commercial and Margin Guardrails model (Layer 3)."""
    contract_type_implication: str = ""
    billing_consumption_assumption: str = ""
    staffing_assumption: str = ""
    commercial_exposure_note: str = ""
    approved_work_rule: str = "Only authorized project scope and approved Change Orders are authorized for execution."
    non_approved_work_rule: str = "No out-of-scope tasks shall be performed without written Change Order."
    work_at_risk_rule: str = "Work-at-risk requires written PMO Lead approval and executive exception sign-off."
    change_control_trigger: str = "Material scope shift, timeline variance > 5 days, or budget variance > 10%"
    change_order_route: str = "PMO Lead leads -> DM aligns client -> Client approves -> Contracting issues change order"
    budget_baseline: str = "[CONFIRMATION REQUIRED]"
    variance_indicator: str = "Green (<5% variance)"
    margin_risk_indicator: str = "Low"
    escalation_threshold: str = "Budget burn rate exceeding weekly cap by >10%"


class TalentMember(BaseModel):
    """Member in talent onboarding roster."""
    role: str = "Engineer"
    name: str = "[UNASSIGNED - TO BE CONFIRMED]"
    required_skills: str = "TBD"
    status: str = "Staffed"
    linked_action_id: Optional[str] = Field(
        default=None,
        description="Associated Action ID if unstaffed or unassigned (e.g. 'ACT-08')"
    )


class TalentOnboardingRecord(BaseModel):
    """Talent Onboarding Record model (Layer 3)."""
    talent_pm: str = "[UNASSIGNED - TO BE CONFIRMED]"
    delivery_manager: str = "[UNASSIGNED - TO BE CONFIRMED]"
    pmo_lead: str = "[UNASSIGNED - TO BE CONFIRMED]"
    onboarding_completion_date: FlexibleDate = None
    onboarding_attendees: List[str] = Field(default_factory=list)
    artifacts_walked_through: List[str] = Field(default_factory=list)
    delivery_talent_roster: List[TalentMember] = Field(default_factory=list)
    required_roles: List[str] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)
    staffing_gaps: List[str] = Field(default_factory=list)
    replacement_plan: str = "PMO Lead coordinates talent matching within 5 business days if replacement needed"
    team_baseline_review_confirmation: bool = True


class ActionRequiredItem(BaseModel):
    """Represents a specific unresolved validation point, open exception, or clarification."""
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(..., description="Unique ID, e.g. 'ACT-01', 'ACT-02'")
    item_type: Literal["Open Exception", "Open Clarification"] = Field(
        ..., description="Classification: formal exception vs contractual ambiguity"
    )
    checklist_id: str = Field(..., description="Mapped G-01 Checklist ID (e.g., 'G01-03')")
    related_artifact: str = Field(..., description="Section 4 artifact title")
    target_table_title: str = Field(
        default="",
        description="Section 4 artifact table title where action is embedded"
    )
    target_column_header: str = Field(
        default="",
        description="Target table column header where remediation is located"
    )
    target_entity_id: Optional[str] = Field(
        default=None,
        description="Unique entity identifier if applicable, e.g. 'DEL-01', 'MS-02'"
    )
    finding_description: str = Field(..., description="Specific validation gap or ambiguity identified")
    required_action: str = Field(..., description="Explicit corrective step required to close the item")
    owner: str = Field(..., description="Accountable role responsible for resolution")
    resolution_deadline: str = Field(
        default="Prior to Mobilize Kickoff",
        description="Target resolution milestone"
    )
    score_recovery_delta: float = Field(
        default=0.0,
        description="Estimated points added to composite Readiness Score upon closure"
    )
    target_gate_impact: str = Field(
        default="Clears G-01 checklist item to Approved",
        description="Impact on gate health upon resolution"
    )


class ReadinessChecklistItem(BaseModel):
    """Structured readiness checklist record for G-01 Gate."""
    item_id: str
    gate_criterion: str
    related_section4_artifact: str
    owner: str
    reviewer: str = "PMO Lead"
    approver: str = "PMO Lead / Director, PMO"
    due_date: FlexibleDate = None
    status: ChecklistStatus = "In Progress"
    evidence: str = ""
    exception_required: bool = False
    exception_details: Optional[str] = None
    approval_status: str = "Pending Review"


class GateDecision(BaseModel):
    """G-01 Gate Decision record."""
    gate_decision_status: str = "Pending Gate Review"
    approver_name: str = "PMO Lead"
    approval_date: FlexibleDate = None
    decision_comments: str = "Readiness baseline reviewed; awaiting mobilization sign-off."
    approved_with_exception: bool = False
    rework_required: bool = False
    bypass_reason: Optional[str] = None
    bypass_approving_authority: Optional[str] = None
    exception_expiry_date: FlexibleDate = None
    readiness_score: float = 0.0
    readiness_breakdown: Dict[str, float] = Field(default_factory=dict)
    workflow_state: ReadinessWorkflowState = "Ready for G-01 Gate Review"
    sla_met: bool = True
    segregation_of_duties_verified: bool = True
    author_name: str = "PMO Lead"
    reviewer_names: List[str] = Field(default_factory=lambda: ["Delivery Manager", "Technical Lead"])
    concurring_approver_name: Optional[str] = None
    open_exceptions_count: int = 0

    @model_validator(mode="before")
    @classmethod
    def handle_status_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "decision_status" in data and "gate_decision_status" not in data:
                data["gate_decision_status"] = data["decision_status"]
        return data

    @property
    def decision_status(self) -> str:
        return self.gate_decision_status


class GovernanceContext(BaseModel):
    """Overall project governance context, roles, and commercial summary."""
    project_name: str
    governance_tier: GovernanceTier = "Partnered"
    contract_type: str = "Time and Materials"
    client_name: Optional[str] = None
    delivery_manager: Optional[str] = None
    talent_pm: Optional[str] = None
    pmo_lead: Optional[str] = None
    executive_summary: Optional[str] = None
    workflow_state: ReadinessWorkflowState = "Ready for G-01 Gate Review"
    sla_met: bool = True


class StartupKitBaseline(BaseModel):
    """Consolidated project startup baseline model carrying all Section 4 artifacts."""
    project_name: str
    governance_tier: GovernanceTier = "Partnered"
    contract_type: str = "Time and Materials"
    governance_context: Optional[GovernanceContext] = None
    charter: Optional[ProjectStartupCharter] = None
    sow_interpretation: Optional[SOWInterpretationSummary] = None
    deliverables: List[Deliverable] = Field(default_factory=list)
    milestones: List[Milestone] = Field(default_factory=list)
    backlog_seed: List[WorkPackageSeed] = Field(default_factory=list)
    dependencies_assumptions: List[DependencyAssumptionItem] = Field(default_factory=list)
    raid_items: List[RiskAssumption] = Field(default_factory=list)
    decisions: List[DecisionItem] = Field(default_factory=list)
    communications_plan: List[CommunicationsPlanItem] = Field(default_factory=list)
    stakeholders: List[Stakeholder] = Field(default_factory=list)
    raci_matrix: List[RACIItem] = Field(default_factory=list)
    commercial_guardrails: Optional[CommercialGuardrail] = None
    talent_onboarding: Optional[TalentOnboardingRecord] = None
    readiness_checklist: List[ReadinessChecklistItem] = Field(default_factory=list)
    gate_decision: Optional[GateDecision] = None
    action_required_items: List[ActionRequiredItem] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    contract_ambiguities: List[ContractAmbiguityItem] = Field(default_factory=list)
    readiness_score: float = 0.0
    readiness_breakdown: Dict[str, float] = Field(default_factory=dict)
    workflow_state: ReadinessWorkflowState = "Ready for G-01 Gate Review"
    sow_awarded_date: FlexibleDate = None
    kit_drafted_date: FlexibleDate = None
    sla_met: bool = True
    author_name: str = "PMO Lead"
    reviewer_names: List[str] = Field(default_factory=lambda: ["Delivery Manager", "Technical Lead"])
    approver_name: str = "PMO Lead"
    concurring_approver_name: Optional[str] = None
    segregation_of_duties_verified: bool = True


# Intermediate domain extraction schemas for multi-pass LLM prompts
class CharterExtraction(BaseModel):
    project_name: str = "Project Baseline"
    client_name: Optional[str] = None
    governance_tier: GovernanceTier = "Partnered"
    contract_type: str = "Time and Materials"
    delivery_manager: Optional[str] = None
    talent_pm: Optional[str] = None
    pmo_lead: Optional[str] = None
    executive_summary: Optional[str] = None
    project_purpose: Optional[str] = None
    delivery_objectives: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    high_level_scope: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)
    source_reference: SourceReference = Field(
        default_factory=lambda: SourceReference(document_name="Project Baseline")
    )


class DeliverablesExtraction(BaseModel):
    deliverables: List[Deliverable] = Field(default_factory=list)


class MilestonesExtraction(BaseModel):
    milestones: List[Milestone] = Field(default_factory=list)


class RAIDExtraction(BaseModel):
    items: List[RiskAssumption] = Field(default_factory=list)


class QuestionsExtraction(BaseModel):
    open_questions: List[str] = Field(default_factory=list)


class SOWInterpretationExtraction(BaseModel):
    contracted_deliverables: List[str] = Field(default_factory=list)
    out_of_scope_items: List[str] = Field(default_factory=list)
    customer_obligations: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    platform_environment_commitments: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    approval_expectations: Optional[str] = None
    ambiguity_notes: List[str] = Field(default_factory=list)
    source_reference: Optional[SourceReference] = None


class ScopeDecompositionExtraction(BaseModel):
    work_packages: List[WorkPackageSeed] = Field(default_factory=list)


class AcceptanceProcessExtraction(BaseModel):
    acceptance_matrix_items: List[Deliverable] = Field(default_factory=list)


class StakeholdersExtraction(BaseModel):
    stakeholders: List[Stakeholder] = Field(default_factory=list)


class CommunicationsExtraction(BaseModel):
    communications: List[CommunicationsPlanItem] = Field(default_factory=list)


class CommercialGuardrailsExtraction(BaseModel):
    commercial_guardrails: Optional[CommercialGuardrail] = None


class TalentOnboardingExtraction(BaseModel):
    talent_onboarding: Optional[TalentOnboardingRecord] = None


class DecisionsExtraction(BaseModel):
    decisions: List[DecisionItem] = Field(default_factory=list)


class ContractConflictsExtraction(BaseModel):
    ambiguities: List[ContractAmbiguityItem] = Field(default_factory=list)
