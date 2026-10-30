"""Data specification for PS Governance Kickoff Deck generator (HTL-72)."""

from dataclasses import dataclass, field
from typing import List, Optional
from src.generators.governance_deck.trace import GovernanceDeckTraceManifest


@dataclass
class Slide1Model:
    """Model for Slide 1 (Title slide)."""
    client_name: str
    project_name: str


@dataclass
class Slide13WhyModel:
    """Model for Slide 13 (Project Success Agreement - Why We're Here - Lifted Client Slide 5)."""
    why_are_we_doing_this: str
    what_problem_are_we_solving: str
    what_does_success_look_like: str


@dataclass
class WorkstreamBlock:
    """One workstream block on Slide 14."""
    title: str
    deliverables: List[str] = field(default_factory=list)
    overflow_count: int = 0


@dataclass
class Slide14DeliverModel:
    """Model for Slide 14 (Project Success Agreement - What We Will Deliver - Lifted Client Slide 6)."""
    workstreams: List[WorkstreamBlock] = field(default_factory=list)
    solution_overview: str = ""
    out_of_scope: List[str] = field(default_factory=list)


@dataclass
class AcceptanceCriterionRow:
    """One deliverable row in Slide 15 Deliverable Acceptance Criteria table (HTL-72)."""
    deliverable_id: str
    deliverable_name: str
    acceptance_criteria: List[str] = field(default_factory=list)
    milestone_gate: str = ""
    wbs_code: str = ""


@dataclass
class Slide15AcceptanceCriteriaModel:
    """Model for Slide 15 (Acceptance Criteria - Phase 2)."""
    rows: List[AcceptanceCriterionRow] = field(default_factory=list)


@dataclass
class Slide16AcceptanceNarrativeModel:
    """Model for Slide 16 (How Milestone Acceptance Works - Phase 2)."""
    narrative: str = ""


@dataclass
class Slide17ApproachModel:
    """Model for Slide 17 (Approach - Phase 2)."""
    pass


@dataclass
class RiskItem:
    """One risk row on Slide 18."""
    id: str
    description: str
    prob_impact: str
    mitigation: str
    target_date: str = "TBD"
    severity_score: int = 0


@dataclass
class Slide18RisksModel:
    """Model for Slide 18 (Initial Risk Register - Lifted Client Slide 12)."""
    risks: List[RiskItem] = field(default_factory=list)


@dataclass
class NextStepItem:
    """One next step row on Slide 19."""
    owner: str
    action: str
    due: str = "TBD"


@dataclass
class Slide19NextStepsModel:
    """Model for Slide 19 (Next Steps - Lifted Client Slide 15)."""
    next_steps: List[NextStepItem] = field(default_factory=list)


@dataclass
class GovernanceDeckModel:
    """Complete data model representing the populated PS Governance Kickoff Deck."""
    project_name: str
    slide1: Slide1Model
    slide13: Slide13WhyModel
    slide14: Slide14DeliverModel
    slide18: Slide18RisksModel
    slide19: Slide19NextStepsModel
    slide15: Slide15AcceptanceCriteriaModel = field(default_factory=Slide15AcceptanceCriteriaModel)
    slide16: Slide16AcceptanceNarrativeModel = field(default_factory=Slide16AcceptanceNarrativeModel)
    slide17: Slide17ApproachModel = field(default_factory=Slide17ApproachModel)
    manifest: GovernanceDeckTraceManifest = field(default_factory=lambda: GovernanceDeckTraceManifest(project_name=""))
