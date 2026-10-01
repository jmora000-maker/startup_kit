"""Task template library providing deterministic PM best-practice workstream and deliverable tasks."""

import re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

@dataclass(frozen=True)
class DeliverableTaskTemplate:
    name: str
    owner_role: str
    is_core: bool = False


WORK_TYPES: List[Tuple[str, List[str], List[DeliverableTaskTemplate]]] = [
    (
        "Integration",
        ["integrat", "api", "endpoint", "direct-write", "interface", "authentication"],
        [
            DeliverableTaskTemplate("Confirm interface contract, credentials, and environment access", "Talent PM", is_core=False),
            DeliverableTaskTemplate("Build the integration", "Talent PM", is_core=True),
            DeliverableTaskTemplate("Test error handling, retries, and performance targets", "Talent PM", is_core=False),
            DeliverableTaskTemplate("Demo the working integration to the client", "Delivery Manager", is_core=False),
        ]
    ),
    (
        "Build",
        ["shell", "service", "frontend", "micro-frontend", "view", "feature", "component", "search"],
        [
            DeliverableTaskTemplate("Refine stories and acceptance criteria", "Talent PM", is_core=False),
            DeliverableTaskTemplate("Develop and configure", "Talent PM", is_core=True),
            DeliverableTaskTemplate("Peer review and unit test", "Talent PM", is_core=False),
            DeliverableTaskTemplate("Demo completed work to the client", "Delivery Manager", is_core=False),
        ]
    ),
    (
        "Test",
        ["test", "suite", "harness", "uat", "scan", "validation", "smoke", "certification", "defect", "hardening", "quality"],
        [
            DeliverableTaskTemplate("Agree test scope, targets, and environment", "Talent PM", is_core=False),
            DeliverableTaskTemplate("Prepare test scripts, data, and fixtures", "Talent PM", is_core=True),
            DeliverableTaskTemplate("Execute tests in the target environment", "Talent PM", is_core=False),
            DeliverableTaskTemplate("Log defects and produce the results report", "Talent PM", is_core=False),
        ]
    ),
    (
        "Analysis",
        ["spike", "parity", "assessment", "benchmark", "report"],
        [
            DeliverableTaskTemplate("Agree method, targets, and data sources", "Talent PM", is_core=False),
            DeliverableTaskTemplate("Perform the analysis", "Talent PM", is_core=True),
            DeliverableTaskTemplate("Document findings and recommendations", "Talent PM", is_core=False),
            DeliverableTaskTemplate("Review findings with the client", "Delivery Manager", is_core=False),
        ]
    ),
    (
        "Documentation",
        ["training", "documentation", "material", "guide", "runbook"],
        [
            DeliverableTaskTemplate("Agree outline and audience", "Talent PM", is_core=False),
            DeliverableTaskTemplate("Draft the content", "Talent PM", is_core=True),
            DeliverableTaskTemplate("Walk through the draft with the client", "Delivery Manager", is_core=False),
            DeliverableTaskTemplate("Finalize and publish", "Talent PM", is_core=False),
        ]
    ),
]


def _build_work_type_regex(kw: str) -> re.Pattern:
    """Build word-start regex for deliverable work type matching."""
    kw_lower = kw.lower()
    pattern = r"\b" + re.escape(kw_lower) + r"\w*"
    return re.compile(pattern, re.IGNORECASE)


WORK_TYPE_PATTERNS = [
    (
        name,
        [(_build_work_type_regex(kw)) for kw in kws],
        templates
    )
    for name, kws, templates in WORK_TYPES
]


WORK_TYPE_VERBS: Dict[str, str] = {
    "Build": "Build",
    "Integration": "Build",
    "Test": "Automate and execute",
    "Analysis": "Complete",
    "Documentation": "Produce",
}


def get_work_type_verb(work_type: str) -> str:
    """Get the standard story task verb for a work type (v5 A21)."""
    return WORK_TYPE_VERBS.get(work_type, "Build")


def classify_deliverable_work_type(deliverable_name: str) -> Tuple[str, List[DeliverableTaskTemplate]]:
    """Classify deliverable name into work type by counting keyword hits (word-start, case-insensitive).
    
    Highest count wins; ties follow table order. With no hits, default to Build.
    """
    clean_name = deliverable_name or ""
    best_type = "Build"
    best_count = 0
    best_templates = [t for name, _, t in WORK_TYPES if name == "Build"][0]

    for name, patterns, templates in WORK_TYPE_PATTERNS:
        hits = 0
        for pat in patterns:
            # Count distinct matches or occurrences
            matches = pat.findall(clean_name)
            hits += len(matches)
        if hits > best_count:
            best_count = hits
            best_type = name
            best_templates = templates

    return best_type, best_templates
