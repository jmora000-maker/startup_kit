"""Fixed labels written by the tool (DECK-04, DECK-09, Appendix K). Everything else on a slide is traced.

This module holds only generic labels: no project, client, or SOW names (P-08).
"""

import re
from typing import List

PLACEHOLDER_TEXT = "To be confirmed"

SLIDE_TITLES = {
    2: "Project Charter",
    3: "Workstreams, Milestones, Deliverables and Dates",
    4: "Acceptance Criteria",
    5: "High-Risk Items",
    6: "Client Collaboration",
    7: "Your Project Kit",
}

KICKER_SUFFIX = "TALENT TEAM ONBOARDING"
COVER_SUBTITLE_PREFIX = "Talent Team Onboarding"

# Card headings (K.1) and subheadings (K.2)
CARD_HEADINGS = (
    "Key facts",
    "Purpose & delivery",
    "Phases & scope",
    "How acceptance works",
    "Client roles",
    "Working rhythm",
    "Client prerequisites",
    "Startup Kit",
    "Project Delivery Workbook",
)
SUBHEADINGS = (
    "Purpose",
    "Delivery model",
    "Escalation path",
    "Phases",
    "Out of scope",
    "Sections used in this deck",
    "Sheets",
)

# Table column headers
TABLE_HEADERS = {
    3: ("Workstream", "Milestone", "Dates", "Deliverables"),
    4: ("ID", "Acceptance Criteria", "Gate"),
    5: ("ID", "Item", "Rating", "Owner", "Response", "Phase"),
}

# Slide 2 Key facts labels (the field labels shown in the Kit header table)
KEY_FACT_LABELS = (
    "Client Sponsor",
    "Contract Type",
    "Governance Tier",
    "Start Date",
    "Talent PM",
    "Delivery Manager",
    "PMO Lead",
)

# Kit section headings in Kit order, and Workbook sheets in Workbook order (slide 7 lists them in these orders)
KIT_SECTION_ORDER = (
    "Project Startup Charter",
    "SOW Interpretation Summary",
    "Milestone Delivery Plan",
    "Scope Decomposition / Backlog Seed",
    "Deliverables and Acceptance Matrix",
    "Dependency and Assumption Log",
    "RAID Log",
    "Communications and Reporting Plan",
    "Stakeholder and Responsibility Model",
)
SHEET_ORDER = ("Project Schedule", "WBS", "RAID Log")
HEADER_TABLE = "Header table"

# Labels placed in front of a traced value inside a card paragraph
INLINE_LABELS = ("Review window:", "Client approver:")

# Empty-section lines (DECK-15)
NONE_IN_KIT = "None recorded in the Startup Kit"
NONE_IN_WORKBOOK = "None recorded in the Project Delivery Workbook"

# Slide 7 fixed lines (K.2)
KIT_DESCRIPTION = "The approved project baseline: scope, deliverables and acceptance, governance, and RAID."
WORKBOOK_DESCRIPTION = "The working delivery plan: schedule by phase, tasks, and the RAID Log."
SHEET_PURPOSES = {
    "Project Schedule": "gates, dates, and client prerequisites",
    "WBS": "deliverables and tasks, with acceptance steps",
    "RAID Log": "risks, issues, dependencies, and open questions",
}
TRACE_STATEMENT = "Every fact in this deck traces to these two documents. Each slide's notes list its sources."

KIT_LABEL = "Startup Kit"
WORKBOOK_LABEL = "Project Delivery Workbook"

# Residue patterns allowed in text that is otherwise fully covered by traced values
OVERFLOW_PATTERN = re.compile(
    r"\+\d+ more(?::)?|\(see (?:Startup Kit|Project Delivery Workbook)(?: · [A-Za-z /&]+)?\)"
)


def fixed_phrases() -> List[str]:
    """Every fixed phrase that may appear on slides 2 to 7 without a TraceRef, longest first."""
    phrases = set(CARD_HEADINGS) | set(SUBHEADINGS) | set(INLINE_LABELS) | set(KEY_FACT_LABELS)
    phrases |= {NONE_IN_KIT, NONE_IN_WORKBOOK, KIT_DESCRIPTION, WORKBOOK_DESCRIPTION, TRACE_STATEMENT, PLACEHOLDER_TEXT}
    phrases |= set(SLIDE_TITLES.values())
    for hdrs in TABLE_HEADERS.values():
        phrases |= set(hdrs)
    phrases |= {f"{n}: {p}" for n, p in SHEET_PURPOSES.items()}
    phrases |= set(SHEET_PURPOSES.values())
    phrases |= {COVER_SUBTITLE_PREFIX, "Start", KIT_LABEL, WORKBOOK_LABEL}
    return sorted(phrases, key=len, reverse=True)
