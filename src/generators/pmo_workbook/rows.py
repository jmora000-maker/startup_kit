"""Dataclasses representing workbook rows and the complete workbook data model."""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Tuple, Dict, Any, Set


@dataclass(frozen=True)
class ScheduleRow:
    wbs_code: str
    row_type: str  # "Workstream", "Milestone", "Recurring"
    workstream: str
    milestone_id: str
    name: str  # Milestone name (text before colon)
    scope: str  # Milestone scope (text after colon without week range parenthetical)
    owner: str
    planned_start: Optional[date]
    planned_finish: Optional[date]
    internal_buffer_date: Optional[date]
    external_date: Optional[date]
    date_basis: str  # "Contract date", "SOW estimate, weeks a–b", or "To be confirmed"
    status: str
    predecessor: str
    client_prerequisites: str
    critical_path_assumptions: str
    linked_deliverables: str
    linked_raid_ids: str
    source: str
    notes: str
    outline_level: int = 0
    child_row_range: Optional[Tuple[int, int]] = None  # 1-based row indices (start_row, end_row) in Excel


@dataclass(frozen=True)
class WBSRow:
    wbs_code: str
    level: int  # 1 to 4
    element_type: str  # "Workstream", "Milestone", "Recurring", "Work Package", "Deliverable", "Task"
    name: str
    workstream: str
    milestone_id: str
    deliverable_id: str
    source_id: str
    owner: str
    planned_start: Optional[date]
    planned_finish: Optional[date]
    milestone_date: Optional[date]
    status: str
    cadence: str
    predecessors: str
    acceptance_criteria: str
    linked_raid_ids: str
    source: str
    mapping_basis: str
    notes: str
    outline_level: int = 0
    child_row_range: Optional[Tuple[int, int]] = None  # 1-based row indices (start_row, end_row) in Excel


@dataclass(frozen=True)
class RAIDRow:
    raid_id: str
    type: str  # "Risk", "Assumption", "Issue", "Dependency"
    description: str
    contract_reference: str
    category: str
    workstream: str
    linked_milestone: str
    linked_wbs_code: str
    linked_deliverables: str
    owner: str
    probability: str  # "Low", "Medium", "High", or ""
    impact: str  # "Low", "Medium", "High", or ""
    severity: str  # Column header is "Rating"
    trigger_or_early_warning: str
    mitigation_or_response: str
    due_date: Optional[date]
    status: str
    date_raised: Optional[date]
    last_updated: Optional[date]
    linked_decision: str
    linked_dependency_or_assumption: str
    source: str
    source_id: str
    notes: str


@dataclass(frozen=True)
class WorkbookModel:
    project_name: str
    client_name: str
    contract_type: str
    talent_pm: str
    delivery_manager: str
    start_date: date
    start_date_basis: str
    generation_date: date
    schedule_rows: List[ScheduleRow] = field(default_factory=list)
    wbs_rows: List[WBSRow] = field(default_factory=list)
    raid_rows: List[RAIDRow] = field(default_factory=list)
    unmapped_deliverables_count: int = 0
    timeline_weeks: List[date] = field(default_factory=list)
    timeline_truncated: bool = False
    excluded_items_count: int = 0
    evidence_flags_count: int = 0
    evidence_flags: List[str] = field(default_factory=list)
    flagged_evidence_deliverables: Set[str] = field(default_factory=set)
    traceability: Dict[str, Dict[str, Any]] = field(default_factory=dict)
