"""Deterministic talking-point templates for the Onboarding Deck speaker notes (DECK-09, Appendix K.3).

Every template is filled only with traced values; a template whose value is missing is skipped by the
builder, never filled with a guess. Templates contain no project, client, or SOW names (P-08) and no
evaluative filler. They are plain sentences built from facts.
"""

from typing import List, Optional

MAX_TALKING_POINT_WORDS = 30

# Fixed guidance sentences (no traced value): allowed only on the cover and Your Project Kit slides (DECK-09)
COVER_GUIDANCE = (
    "This deck is for the Talent PM and the Talent Project Team; use these notes as a script and for later reference.",
)
KIT_SLIDE_GUIDANCE = (
    "Both files sit in the same folder as this deck.",
    "The Startup Kit is the approved baseline; changes to it go through the escalation path on slide 2.",
    "The Project Delivery Workbook is the plan to keep current as work progresses.",
    "Each slide's SOURCES note says which section or sheet to open for detail.",
)


def sentence(text: str) -> str:
    """End `text` with a full stop unless it already ends a sentence (no doubled punctuation)."""
    text = text.strip()
    return text if text.endswith((".", "?", "!")) else f"{text}."


def spoken(value: str, is_placeholder: bool) -> str:
    """A value as it reads inside a sentence: a placeholder reads `to be confirmed`."""
    return "to be confirmed" if is_placeholder else value


# --- Slide 1 (Cover): fixed guidance is allowed here ----------------------------------------------
def cover_project_and_client(project: str, client: str) -> str:
    return sentence(f"This deck covers {project} for {client}")


def cover_start_date(start_date: str, basis: str) -> str:
    return f"The start date is {start_date}, and it was {basis.lower()}."


# --- Slide 2: Project Charter -----------------------------------------------------------------------
def charter_purpose(purpose_sentence: str) -> str:
    return sentence(f"Purpose: {purpose_sentence}")


def charter_contract_and_tier(contract_type: str, tier: str) -> str:
    return sentence(f"The contract type is {contract_type}, and the governance tier is {tier}")


def charter_leads(delivery_manager: str, talent_pm: str, pmo_lead: str) -> str:
    return sentence(f"Delivery Manager: {delivery_manager}; Talent PM: {talent_pm}; PMO Lead: {pmo_lead}")


def charter_escalation(path: str) -> str:
    return sentence(f"Issues escalate along this path: {path}")


def charter_start_date(start_date: str, basis: str) -> str:
    return f"The start date is {start_date}, and it was {basis.lower()}."


def phases_and_span(phase_count: int, first_start: str, last_finish: str) -> str:
    return sentence(f"The project runs in {phase_count} phases, from {first_start} to {last_finish}")


# --- Slide 3: Workstreams, Milestones, Deliverables and Dates -----------------------------------------
def gate_due(gate_id: str, phase: str, planned_finish: str, predecessor: Optional[str]) -> str:
    base = f"{gate_id} ({phase}) is due {planned_finish}"
    return f"{base}; it starts after {predecessor} is accepted." if predecessor else f"{base}."


def date_basis(gate_id: str, basis: str) -> str:
    return sentence(f"The dates for {gate_id} are based on: {basis}")


def checkpoints(count: int, ids: List[str]) -> str:
    return sentence(f"{count} checkpoints sit inside phases: {', '.join(ids)}")


# --- Slide 4: Acceptance Criteria ----------------------------------------------------------------------
def acceptance_mode(mode: str, gate_id: str, step_count: int, first_step: str) -> str:
    return f"Acceptance is {mode}; the {gate_id} acceptance package has {step_count} steps, starting with: {first_step}."


def acceptance_review(review_window: str, approver: str) -> str:
    return sentence(f"Review window: {review_window}; client approver: {approver}")


def acceptance_evidence(deliverable_id: str, evidence: str) -> str:
    return sentence(f"Evidence expected for {deliverable_id}: {evidence}")


def criteria_to_confirm(count: int, ids: List[str]) -> str:
    return sentence(f"{count} deliverables have acceptance criteria still to be confirmed: {', '.join(ids)}")


# --- Slide 5: High-Risk Items ---------------------------------------------------------------------------
def high_risks(high_count: int, raid_id: str, first_clause: Optional[str]) -> str:
    base = f"{high_count} risks and issues are rated High; the first to watch is {raid_id}"
    return sentence(f"{base}: {first_clause}") if first_clause else f"{base}."


def early_warning(raid_id: str, trigger: str) -> str:
    return sentence(f"Early warning for {raid_id}: {trigger}")


def item_owner(raid_id: str, owner: str) -> str:
    return sentence(f"Owner of {raid_id}: {owner}")


def raise_new_risks(path: str) -> str:
    return sentence(f"Raise new risks and issues along this path: {path}")


# --- Slide 6: Client Collaboration ----------------------------------------------------------------------
def sign_off(stakeholder: str) -> str:
    return sentence(f"Milestone sign-off sits with {stakeholder}")


def meeting_cadence(name: str, cadence: str) -> str:
    return sentence(f"{name}: {cadence}")


def first_prerequisite(phase: str, planned_start: str, prerequisite: str) -> str:
    return sentence(f"Before {phase} starts on {planned_start}, the client prerequisite is: {prerequisite}")


def first_prerequisite_short(phase: str, planned_start: str) -> str:
    return f"Before {phase} starts on {planned_start}, the client has prerequisites to provide (see the Project Schedule)."


def open_questions(count: int, first_raid_id: str) -> str:
    return sentence(f"{count} open questions are waiting on the client; the first is {first_raid_id}")


# --- Notes assembly --------------------------------------------------------------------------------------
def build_notes(points: List[str], sources_line: str) -> str:
    """Speaker notes: a TALKING POINTS section and a SOURCES line (DECK-09)."""
    body = "\n".join(f"• {p}" for p in points)
    return f"TALKING POINTS:\n{body}\n\nSOURCES: {sources_line}"
