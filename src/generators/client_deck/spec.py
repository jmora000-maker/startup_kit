"""Data specification for Client Kickoff Deck generator (OUT-14)."""

from dataclasses import dataclass, field
from typing import List, Optional
from src.generators.client_deck.trace import ClientDeckTraceManifest


@dataclass
class Slide1Model:
    """Model for Slide 1 (Title slide)."""
    client_name: str
    project_name: str


@dataclass
class Slide5Model:
    """Model for Slide 5 (Project Success Agreement - Why We're Here)."""
    why_are_we_doing_this: str
    what_problem_are_we_solving: str
    what_does_success_look_like: str


@dataclass
class WorkstreamBlock:
    """One workstream block on Slide 6."""
    title: str
    deliverables: List[str] = field(default_factory=list)
    overflow_count: int = 0


@dataclass
class Slide6Model:
    """Model for Slide 6 (Project Success Agreement - What We Will Deliver)."""
    workstreams: List[WorkstreamBlock] = field(default_factory=list)
    solution_overview: str = ""
    out_of_scope: List[str] = field(default_factory=list)


@dataclass
class RiskItem:
    """One risk row on Slide 12."""
    id: str
    description: str
    prob_impact: str
    mitigation: str
    target_date: str = "TBD"
    severity_score: int = 0


@dataclass
class Slide12Model:
    """Model for Slide 12 (Initial Risk Register)."""
    risks: List[RiskItem] = field(default_factory=list)


@dataclass
class NextStepItem:
    """One next step row on Slide 15."""
    owner: str
    action: str
    due: str = "TBD"


@dataclass
class Slide15Model:
    """Model for Slide 15 (Next Steps)."""
    next_steps: List[NextStepItem] = field(default_factory=list)


@dataclass
class ClientDeckModel:
    """Complete data model representing the populated Client Kickoff Deck."""
    project_name: str
    slide1: Slide1Model
    slide5: Slide5Model
    slide6: Slide6Model
    slide12: Slide12Model
    slide15: Slide15Model
    manifest: ClientDeckTraceManifest = field(default_factory=lambda: ClientDeckTraceManifest(project_name=""))
