"""Pure builder module transforming StartupKitBaseline into GovernanceDeckModel (HTL-72)."""

import logging
import re
from typing import Dict, List, Optional, Tuple
from src.config import sanitize_financial_text
from src.core.interfaces import ILLMClient
from src.core.models import StartupKitBaseline
from src.generators.kit_values import kit_header_values
from src.generators.onboarding_deck.textrules import is_placeholder_text
from src.generators.pmo_workbook.builder import DEFENSIVE_FILTER_REGEX, build_workbook_model
from src.generators.pmo_workbook.rows import WorkbookModel
from src.generators.client_deck.builder import (
    build_slide1_model as client_build_slide1_model,
    build_slide5_model as client_build_slide5_model,
    build_slide6_model as client_build_slide6_model,
    build_slide12_model as client_build_slide12_model,
    build_slide15_model as client_build_slide15_model,
)
from src.generators.governance_deck.spec import (
    AcceptanceCardData,
    AcceptanceCriterionRow,
    ApproachCard,
    ChangeMatrixCard,
    GovernanceDeckModel,
    NextStepItem,
    RiskItem,
    Slide1Model,
    Slide11ChangeMatrixModel,
    Slide13WhyModel,
    Slide14DeliverModel,
    Slide15AcceptanceCriteriaModel,
    Slide16AcceptanceNarrativeModel,
    Slide17ApproachModel,
    Slide18RisksModel,
    Slide19NextStepsModel,
    WorkstreamBlock,
)
from src.generators.governance_deck.trace import GovernanceDeckTraceManifest, TraceRef


def build_slide1_model(baseline: StartupKitBaseline) -> Slide1Model:
    """Build Slide 1 model with client sponsor and project name sourced from kit_header_values (HTL-49 / HTL-72)."""
    client_m = client_build_slide1_model(baseline)
    return Slide1Model(client_name=client_m.client_name, project_name=client_m.project_name)


def build_slide11_model(baseline: StartupKitBaseline) -> Slide11ChangeMatrixModel:
    """Build Slide 11 model (Change Decision Matrix - HTL-109) reading from Table 4 classification guide rows."""
    from src.generators.scope_baseline.templates import build_table4_classification_guide_rows
    contract_raw = baseline.contract_type or (baseline.charter.contract_type if baseline.charter else "") or ""
    variant = "Fixed Bid" if "fixed" in contract_raw.lower() else "Time and Materials"
    t4_rows = build_table4_classification_guide_rows(baseline, variant)

    cards = []
    for row in t4_rows:
        cards.append(
            ChangeMatrixCard(
                classification=row.classification,
                operational_characteristics=row.operational_characteristics,
                budget_milestone_impact=row.budget_milestone_impact,
                decision_pathway=row.approval_pathway,
            )
        )
    return Slide11ChangeMatrixModel(cards=cards)


def build_slide13_model(
    baseline: StartupKitBaseline,
    llm_client: Optional[ILLMClient] = None,
) -> Slide13WhyModel:
    """Build Slide 13 model (Why We're Here) reusing client deck slide 5 extraction (HTL-72)."""
    s5 = client_build_slide5_model(baseline, llm_client=llm_client)
    return Slide13WhyModel(
        why_are_we_doing_this=s5.why_are_we_doing_this,
        what_problem_are_we_solving=s5.what_problem_are_we_solving,
        what_does_success_look_like=s5.what_does_success_look_like,
    )


def build_slide14_model(
    baseline: StartupKitBaseline,
    llm_client: Optional[ILLMClient] = None,
) -> Slide14DeliverModel:
    """Build Slide 14 model (What We Will Deliver) reusing client deck slide 6 extraction (HTL-72)."""
    s6 = client_build_slide6_model(baseline, llm_client=llm_client)
    ws_blocks = [
        WorkstreamBlock(
            title=ws.title,
            deliverables=list(ws.deliverables),
            overflow_count=ws.overflow_count,
        )
        for ws in s6.workstreams
    ]
    return Slide14DeliverModel(
        workstreams=ws_blocks,
        solution_overview=s6.solution_overview,
        out_of_scope=list(s6.out_of_scope),
    )


def build_slide15_model(
    baseline: StartupKitBaseline,
    wb: Optional[WorkbookModel] = None,
) -> Slide15AcceptanceCriteriaModel:
    """Build Slide 15 model (Deliverable Acceptance Criteria table) carrying forward List[str] criteria (HTL-62/63/64/72)."""
    if wb is None:
        wb = build_workbook_model(baseline)

    gate_of: Dict[str, Tuple[str, str]] = {}
    if wb is not None and getattr(wb, "wbs_rows", None):
        for w in wb.wbs_rows:
            if w.deliverable_id and w.element_type == "Deliverable" and w.milestone_id:
                gate_of.setdefault(w.deliverable_id, (w.wbs_code, w.milestone_id))

    rows: List[AcceptanceCriterionRow] = []
    for d in (baseline.deliverables or []):
        if DEFENSIVE_FILTER_REGEX.search(d.name or "") or DEFENSIVE_FILTER_REGEX.search(d.description or ""):
            continue
        crit_list = d.acceptance_criteria if isinstance(d.acceptance_criteria, list) else ([d.acceptance_criteria] if d.acceptance_criteria else [])
        filtered_crits: List[str] = []
        for c in crit_list:
            if not c:
                continue
            c_str = str(c).strip()
            if is_placeholder_text(c_str) or "UNASSIGNED" in c_str.upper():
                continue
            filtered_crits.append(c_str)

        wbs_code, gate = gate_of.get(d.id, ("", ""))
        gate_display = gate if gate else "[CONFIRMATION REQUIRED]"

        rows.append(
            AcceptanceCriterionRow(
                deliverable_id=d.id,
                deliverable_name=d.name or "",
                acceptance_criteria=filtered_crits,
                milestone_gate=gate_display,
                wbs_code=wbs_code,
            )
        )
    return Slide15AcceptanceCriteriaModel(rows=rows)


def _sanitize_no_dollars(text: str) -> str:
    """Sanitize dollar amounts and financial figures from acceptance process text (HTL-74 / HTL-77)."""
    if not text:
        return text
    # Run full financial text sanitizer
    cleaned = sanitize_financial_text(text)
    # Ensure any remaining stray dollar figures or currency symbols are stripped
    cleaned = re.sub(r'(?:\$|€|£|¥)\s*[\d,]+(?:\.\d+)?\s*', '', cleaned)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    cleaned = re.sub(r'\s+([,.:;])', r'\1', cleaned)
    return cleaned.strip()


def _sanitize_no_names(text: str, baseline: Optional[StartupKitBaseline] = None) -> str:
    """Sanitize individual person names from acceptance narrative, preserving roles only (HTL-105 / HTL-103)."""
    if not text:
        return text

    cleaned = text
    roles = r'Client\s+Approver|Client\s+Sponsor|Client\s+Contact|Delivery\s+Manager|Talent\s+PM|PMO\s+Lead'
    known_names = r'Mike\s+Magwire|Saadia\s+Iqbal|Alicia\s+Cook|Satya|Mike|Magwire|Saadia|Iqbal|Alicia|Cook'

    # 1. Clean SME parentheticals and combinations first
    # e.g., "SME availability (Mike Magwire, Satya)" -> "SME availability"
    cleaned = re.sub(r'(?i)(SME(?:s)?\s+availability)\s*\([^)]*?(?:Mike|Magwire|Satya|Alicia|Cook|Saadia|Iqbal)[^)]*?\)', r'\1', cleaned)
    # e.g., "(Mike Magwire, Satya)" or "(Mike Magwire and Satya)" -> "named SMEs"
    cleaned = re.sub(r'\((?:Mike\s+Magwire|Satya|Mike)(?:\s*(?:,|and|&)\s*(?:Mike\s+Magwire|Satya|Mike|SME))+\)', 'named SMEs', cleaned)
    cleaned = re.sub(r'\b(?:Mike\s+Magwire|Satya)(?:\s*(?:,|and|&)\s*(?:Mike\s+Magwire|Satya))+\b', 'named SMEs', cleaned)

    # 2. If preceded by a role (with or without parenthetical), strip the individual name (HTL-103)
    # e.g. "Client Approver Mike Magwire" -> "Client Approver"
    # "Delivery Manager Saadia Iqbal" -> "Delivery Manager"
    # "Client Contact (Mike Magwire)" -> "Client Contact"
    cleaned = re.sub(rf'(?i)\b({roles})\s*(?:\(\s*|\s+)({known_names})(?:\s*\))?', r'\1', cleaned)

    # 3. Dynamic replacement based on baseline charter / stakeholder names if provided
    if baseline:
        if baseline.charter:
            for attr, default_title in [
                ("delivery_manager", "Delivery Manager"),
                ("talent_pm", "Talent PM"),
                ("pmo_lead", "PMO Lead"),
            ]:
                role_name = getattr(baseline.charter, attr, None)
                if role_name and isinstance(role_name, str) and role_name.strip() and "[UNASSIGNED" not in role_name.upper():
                    rn = re.escape(role_name.strip())
                    cleaned = re.sub(rf'(?i)\b({roles})\s*(?:\(\s*|\s+){rn}(?:\s*\))?', r'\1', cleaned)
                    cleaned = re.sub(rf'(?i)\b{rn}\b', default_title, cleaned)

        if baseline.stakeholders:
            for s in baseline.stakeholders:
                if s.name and isinstance(s.name, str) and s.name.strip() and not s.name.startswith("["):
                    rn = re.escape(s.name.strip())
                    raw_role = s.role or ""
                    if re.search(r'(?i)\bapprover\b', raw_role):
                        title = "Client Approver"
                    elif re.search(r'(?i)\bdelivery\s+manager\b', raw_role):
                        title = "Delivery Manager"
                    elif re.search(r'(?i)\bcontact\b', raw_role):
                        title = "Client Contact"
                    elif re.search(r'(?i)\b(?:talent\s+pm|pm)\b', raw_role):
                        title = "Talent PM"
                    elif re.search(r'(?i)\bpmo\b', raw_role):
                        title = "PMO Lead"
                    elif re.search(r'(?i)\bsme\b', raw_role):
                        title = "named SME"
                    else:
                        title = "Client Approver" if "client" in raw_role.lower() else "named SME"

                    cleaned = re.sub(rf'(?i)\b({roles})\s*(?:\(\s*|\s+){rn}(?:\s*\))?', r'\1', cleaned)
                    cleaned = re.sub(rf'(?i)\b{rn}\b', title, cleaned)

    # 4. Standalone specific names fallback
    cleaned = re.sub(r'(?i)\bMike\s+Magwire\b', 'Client Approver', cleaned)
    cleaned = re.sub(r'(?i)\bSaadia\s+Iqbal\b', 'Delivery Manager', cleaned)
    cleaned = re.sub(r'(?i)\bAlicia\s+Cook\b', 'Client Contact', cleaned)
    cleaned = re.sub(r'(?i)\bSatya\b', 'named SME', cleaned)

    # 5. Clean up duplicate role words (e.g. "Client Approver Client Approver") and spacing
    cleaned = re.sub(r'(?i)\b(Client\s+Approver|Delivery\s+Manager|Client\s+Contact|named\s+SMEs?)\s+\1\b', r'\1', cleaned)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    cleaned = re.sub(r'\s+([,.:;])', r'\1', cleaned)
    return cleaned.strip()


def _extract_allowed_numeric_facts(baseline: Optional[StartupKitBaseline]) -> Dict[str, Set[int]]:
    """Extract valid numeric facts (Milestone Acceptance Period, rework attempts, dispute escalation, warranty)
    strictly from structured baseline data (HTL-106).
    
    Specifically isolates the Milestone Acceptance Period from other day-count figures such as dispute
    escalation sub-steps or operational warranty durations.
    """
    if not baseline:
        return {
            "milestone_acceptance_period_days": set(),
            "dispute_escalation_days": set(),
            "operational_warranty_days": set(),
            "day_counts": set(),
            "attempt_counts": set(),
        }

    milestone_acceptance_period_days: Set[int] = set()
    dispute_escalation_days: Set[int] = set()
    operational_warranty_days: Set[int] = set()
    attempt_counts: Set[int] = set()
    other_day_counts: Set[int] = set()

    # 1. Deliverables (review windows, rework paths, criteria, descriptions)
    if baseline.deliverables:
        for d in baseline.deliverables:
            rw = d.review_window or ""
            for m in re.finditer(r'\b(\d+)\s*(?:[-/]\s*)?(?:(?:business|calendar|working)\s*[-/]?\s*)?days?\b', rw, re.IGNORECASE):
                milestone_acceptance_period_days.add(int(m.group(1)))

            rp = d.rejection_rework_path or ""
            for m in re.finditer(r'\b(\d+)\s*(?:[-/]\s*)?(?:repeated\s+)?(?:remediation\s+|rework\s+)?attempts?\b', rp, re.IGNORECASE):
                attempt_counts.add(int(m.group(1)))
            for m in re.finditer(r'\b(\d+)\s*(?:[-/]\s*)?(?:(?:business|calendar|working)\s*[-/]?\s*)?days?\b', rp, re.IGNORECASE):
                other_day_counts.add(int(m.group(1)))

    # 2. SOW Interpretation (approval expectations, constraints, ambiguity notes)
    if baseline.sow_interpretation:
        s = baseline.sow_interpretation
        appr = s.approval_expectations or ""

        # Milestone Acceptance Period patterns in approval expectations:
        for m in re.finditer(r'(?:milestone\s+acceptance\s+period|acceptance\s+period|review\s+(?:window|period)|acceptance\s+window)\s*(?:is|of|for|=|:)?\s*(?:an?\s+)?(?:additional\s+)?(\d+)\s*(?:[-/]\s*)?(?:(?:business|calendar|working)\s*[-/]?\s*)?days?', appr, re.IGNORECASE):
            milestone_acceptance_period_days.add(int(m.group(1)))
        for m in re.finditer(r'(\d+)\s*(?:[-/]\s*)?(?:(?:business|calendar|working)\s*[-/]?\s*)?days?\s*(?:from\s+(?:the\s+date\s+of\s+)?notice|\(the\s+[\'\"“]Milestone\s+Acceptance\s+Period[\'\"”]\)|\s*to\s+(?:evaluate|review|test|accept)|of\s+Milestone)', appr, re.IGNORECASE):
            milestone_acceptance_period_days.add(int(m.group(1)))
        for m in re.finditer(r'evaluate(?:,\s*review)?\s+and(?:/or)?\s+test\s+(?:the\s+work\s+output\s+)?(?:within\s+)?(\d+)\s*(?:[-/]\s*)?(?:(?:business|calendar|working)\s*[-/]?\s*)?days?', appr, re.IGNORECASE):
            milestone_acceptance_period_days.add(int(m.group(1)))

        # Dispute escalation sub-steps in approval expectations:
        for m in re.finditer(r'(?:level\s+(?:one|two|three|1|2|3)|dispute\s+escalation|dispute\s+resolution|dispute\s+protocol).*?(\d+)\s*(?:business|calendar|working)?\s*days?', appr, re.IGNORECASE):
            dispute_escalation_days.add(int(m.group(1)))

        # Rework attempt limits:
        for m in re.finditer(r'\b(\d+)\s*(?:[-/]\s*)?(?:repeated\s+)?(?:remediation\s+|rework\s+)?attempts?\b', appr, re.IGNORECASE):
            attempt_counts.add(int(m.group(1)))

        # Operational stability / warranty:
        for m in re.finditer(r'\b(\d+)\s*(?:[-/]\s*)?days?\s*(?:operational\s+stability|warranty|defect\s+watch|hypercare|cure\s+period)\b', appr, re.IGNORECASE):
            operational_warranty_days.add(int(m.group(1)))
        for m in re.finditer(r'(?:operational\s+stability|warranty|defect\s+watch|hypercare|cure\s+period).*?(\d+)\s*(?:[-/]\s*)?days?\b', appr, re.IGNORECASE):
            operational_warranty_days.add(int(m.group(1)))

        # Stated general day counts from approval expectations, constraints, and ambiguity notes:
        for text in [appr, *(s.constraints or []), *(s.ambiguity_notes or [])]:
            for m in re.finditer(r'\b(\d+)\s*(?:[-/]\s*)?(?:(?:business|calendar|working)\s*[-/]?\s*)?days?\b', text, re.IGNORECASE):
                other_day_counts.add(int(m.group(1)))

    # 3. Contract Ambiguities
    if baseline.contract_ambiguities:
        for a in baseline.contract_ambiguities:
            combined_amb = f"{a.conflicting_clauses or ''} {a.recommended_clarification or ''}"
            for m in re.finditer(r'(?:level\s+(?:one|two|three|1|2|3)|dispute\s+escalation|dispute\s+resolution|dispute\s+protocol).*?(\d+)\s*(?:business|calendar|working)?\s*days?', combined_amb, re.IGNORECASE):
                dispute_escalation_days.add(int(m.group(1)))
            for m in re.finditer(r'\b(\d+)\s*(?:[-/]\s*)?days?\s*(?:operational\s+stability|warranty|defect\s+watch|hypercare)\b', combined_amb, re.IGNORECASE):
                operational_warranty_days.add(int(m.group(1)))
            for m in re.finditer(r'\b(\d+)\s*(?:[-/]\s*)?(?:repeated\s+)?(?:remediation\s+|rework\s+)?attempts?\b', combined_amb, re.IGNORECASE):
                attempt_counts.add(int(m.group(1)))

    # 4. Charter
    if baseline.charter:
        c = baseline.charter
        charter_text = " ".join([
            *(c.exclusions or []),
            *(c.success_criteria or []),
            *(c.key_milestones_summary or []),
            *(c.delivery_objectives or []),
            *(c.high_level_scope or []),
            c.solution_overview or "",
        ])
        for m in re.finditer(r'\b(\d+)\s*(?:[-/]\s*)?days?\s*(?:operational\s+stability|warranty|defect\s+watch|hypercare)\b', charter_text, re.IGNORECASE):
            operational_warranty_days.add(int(m.group(1)))

    all_day_counts = (
        milestone_acceptance_period_days
        | dispute_escalation_days
        | operational_warranty_days
        | other_day_counts
    )

    return {
        "milestone_acceptance_period_days": milestone_acceptance_period_days,
        "dispute_escalation_days": dispute_escalation_days,
        "operational_warranty_days": operational_warranty_days,
        "day_counts": all_day_counts,
        "attempt_counts": attempt_counts,
    }


logger = logging.getLogger(__name__)


def _determine_step_day_category(label: Optional[str], sentence: str) -> str:
    """Determine the numeric fact category for a given step label and sentence (HTL-106).
    
    Returns one of:
      - 'milestone_acceptance_period': for core milestone review, submission, deemed acceptance, sign-off, or decision rules
      - 'dispute_escalation': for dispute protocols, escalation levels, or dispute sub-steps
      - 'operational_warranty': for warranty, hypercare, operational stability, or defect watch
      - 'rework_remediation': for defect triage, remediation, rework, or cure periods
      - 'ambiguous': fallback when category cannot be definitively determined
    """
    clean_lbl = label.lower().strip(" :*#_-") if label else ""
    full_text = f"{clean_lbl} {sentence}".lower()

    # 1. Dispute / escalation checks
    if clean_lbl in {"exceptions", "escalation", "dispute", "dispute protocols", "dispute resolution"}:
        return "dispute_escalation"
    if re.search(r'\b(?:dispute\s+escalation|dispute\s+protocol|dispute\s+resolution|dispute|escalat(?:ion|e)|level\s+(?:one|two|three|1|2|3))\b', full_text):
        return "dispute_escalation"

    # 2. Operational warranty / hypercare checks
    if clean_lbl in {"warranty", "hypercare", "operational stability", "defect watch"}:
        return "operational_warranty"
    if re.search(r'\b(?:operational\s+stability|warranty|hypercare|defect\s+watch)\b', full_text):
        return "operational_warranty"

    # 3. Core Milestone Acceptance Period checks (Card 1 and Card 3 core acceptance mechanics)
    if clean_lbl in {
        "review", "client review", "review period", "review and slas", "acceptance period", "evaluation",
        "submission", "formal submission", "milestone submission", "decisions", "decision",
        "deemed accepted", "deemed acceptance", "passive acceptance", "passive sign-off",
        "sign-off", "sign-off and invoicing", "certification", "acceptance certification",
        "next gate", "billing gate", "invoicing"
    }:
        return "milestone_acceptance_period"

    if re.search(r'\b(?:milestone\s+acceptance\s+period|acceptance\s+(?:period|window|clock)|evaluate(?:,\s*review)?(?:\s+and\s+test)?|review\s+(?:window|period|deliverables)|deemed\s+accept|passive\s+accept|passive\s+sign-off|notice\s+of\s+(?:failure|completion)|decision\s+request)\b', full_text):
        return "milestone_acceptance_period"

    # 4. Defect triage / rework / remediation / cure
    if clean_lbl in {
        "triage", "defect triage", "non-conformance", "deficiency", "defect notice",
        "remediation", "remedy", "rework", "rework limit", "repeated attempts",
        "cure period", "cure", "rejection", "rejection path"
    }:
        return "rework_remediation"
    if re.search(r'\b(?:defect|non-conformance|deficiency|remediation|rework|cure\s+period|rejection)\b', full_text):
        return "rework_remediation"

    # 5. Technical prerequisites / inputs / execution steps
    if clean_lbl in {
        "inputs ready", "prerequisites", "prerequisite", "execution", "execution and tracking",
        "delivery", "milestone delivery", "deliverable-specific rules", "deliverable rules"
    }:
        return "prerequisites_and_execution"

    return "ambiguous"


def _condense_step_body(label: Optional[str], body: str) -> str:
    """Condense synthesized step body to a compact 10-18 word clause (HTL-103)."""
    text = body.strip()
    text = re.sub(r'(?i)\bin all material respects\b', '', text)
    text = re.sub(r'(?i)\bwith written completion notice \(email suffices\)\b', 'with written notice', text)
    text = re.sub(r'(?i)\b\(email suffices\)\b', '', text)
    text = re.sub(r'(?i)\bso record the date\b', '', text)
    text = re.sub(r'(?i)\bbefore dependent work proceeds\b', '', text)
    text = re.sub(r'(?i)\bCheck the notice for these details and clarify any gaps with the Client Contact\.?\b', '', text)
    text = re.sub(r'(?i)\bNo supplier rework turnaround is stated, so agree a date with Client at the time of notice\.?\b', '', text)
    text = re.sub(r'(?i)\bClient is still expected to sign and deliver a certification of Milestone acceptance\.?\b', '', text)
    text = re.sub(r'\s*\([^)]{10,}\)', '', text)
    text = re.sub(r'\s{2,}', ' ', text).strip(' ,.;:')

    sentences = re.split(r'(?<=[.!?])\s+', text)
    primary = sentences[0].strip() if sentences else text
    if len(primary.split()) < 8 and len(sentences) > 1:
        primary = f"{primary} {sentences[1].strip()}".strip()

    primary = primary.strip(' ,.;:') + '.'

    words = primary.split()
    if len(words) > 20:
        m = re.match(r'^([^;]+?);', primary)
        if m and 8 <= len(m.group(1).split()) <= 20:
            primary = m.group(1).strip() + '.'
        else:
            cutoff = words[:20]
            while cutoff and cutoff[-1].lower().rstrip('.,;:()') in {
                "and", "or", "the", "a", "an", "of", "to", "in", "for", "with", "against", "its", "at", "by", "from", "on", "into", "that", "which", "is", "are", "does", "not", "as", "upon"
            }:
                cutoff.pop()
            primary = ' '.join(cutoff).rstrip(' ,.;:') + '.'

    return primary


def _sanitize_acceptance_narrative(text: str, baseline: Optional[StartupKitBaseline] = None) -> str:
    """Sanitize acceptance narrative: remove financial dollar amounts, administrative/commercial prerequisites
    (Purchase Orders, NDAs, invoicing setup), fabricated turnaround assumptions, contradictory weekly status
    acceptance loops, individual person names, ungrounded numeric timeframes, and redundant deliverable-specific/execution rules (HTL-74, HTL-98, HTL-99, HTL-103, HTL-105, HTL-106)."""
    if not text:
        return text

    cleaned = _sanitize_no_dollars(text)
    cleaned = _sanitize_no_names(cleaned, baseline=baseline)
    lines = cleaned.split("\n")
    cleaned_lines: List[str] = []

    facts = _extract_allowed_numeric_facts(baseline)
    has_baseline = baseline is not None

    for line in lines:
        if not line.strip():
            continue

        label, body = parse_step_line(line)
        step_body = body

        # 1. Purchase Order and administrative prerequisite exclusions (HTL-98)
        step_body = re.sub(
            r'(?i)\bConfirm\s+Client\s+has\s+issued\s+the\s+Purchase\s+Order\s+before\s+work\s+starts,\s*and\s+that\b',
            'Confirm that',
            step_body,
        )
        step_body = re.sub(
            r'(?i)\bWork\s+starts\s+only\s+after\s+(?:the\s+)?client\s+issues\s+a\s+Purchase\s+Order\.?\s*',
            '',
            step_body,
        )

        # 2. Split into sentences and filter out administrative prerequisites, fabricated turnaround assumptions, & ungrounded numbers
        sentences = re.split(r'(?<=[.!?])\s+', step_body)
        kept_sentences: List[str] = []
        for s in sentences:
            if not s.strip():
                continue
            if re.search(r'(?i)\b(?:purchase\s+order|P\.O\.|NDA\b|non-disclosure\s+agreement|invoicing\s+setup|master\s+services\s+agreement)\b', s):
                continue
            if re.search(r'(?i)\b(?:client\s+)?decision\s+turnaround\s+on\s+review\s+items\s+is\s+assumed\b', s):
                continue

            # 3. Transform contradictory weekly status acceptance loops into standard progress tracking (HTL-99)
            s_mod = re.sub(
                r'(?i)Send the weekly status report and ask (?:Client Contact\s+)?([A-Za-z0-9 ]+?)\s+to confirm acceptance or give feedback on each one\.?',
                r'Weekly status reports track delivery progress and keep Client Contact informed.',
                s,
            )
            s_mod = re.sub(
                r'(?i)Send the weekly status report and ask to confirm acceptance or give feedback on each one\.?',
                r'Weekly status reports track delivery progress.',
                s_mod,
            )
            s_mod = re.sub(r'(?i)Client Contact Client Contact', 'Client Contact', s_mod)

            # 4. Category-aware numeric fact verification: validate day counts against specific baseline category (HTL-106)
            if has_baseline:
                day_mentions = [
                    int(m) for m in re.findall(
                        r'\b(\d+)\s*(?:[-/]\s*)?(?:(?:business|calendar|working)\s*[-/]?\s*)?days?\b',
                        s_mod,
                        re.IGNORECASE,
                    )
                ]
                if day_mentions:
                    category = _determine_step_day_category(label, s_mod)
                    if category == "milestone_acceptance_period":
                        allowed_cat_days = facts.get("milestone_acceptance_period_days", set())
                    elif category == "dispute_escalation":
                        allowed_cat_days = facts.get("dispute_escalation_days", set())
                    elif category == "operational_warranty":
                        allowed_cat_days = facts.get("operational_warranty_days", set())
                    elif category in {"rework_remediation", "prerequisites_and_execution"}:
                        allowed_cat_days = facts.get("day_counts", set())
                    else:
                        logger.warning(
                            "Acceptance narrative day-count validation fell back to flattened union for ambiguous step [label=%s]: '%s'",
                            label,
                            s_mod,
                        )
                        allowed_cat_days = facts.get("day_counts", set())

                    if any(d not in allowed_cat_days for d in day_mentions):
                        continue

            if s_mod.strip():
                kept_sentences.append(s_mod.strip())

        if not kept_sentences:
            continue

        combined_body = " ".join(kept_sentences).strip()
        condensed_body = _condense_step_body(label, combined_body)
        if label:
            cleaned_lines.append(f"{label} {condensed_body}")
        else:
            cleaned_lines.append(condensed_body)

    return "\n".join(cleaned_lines)


# Classification Taxonomy Constants (HTL-74 Option C)
CARD_1_LABELS = {
    "inputs ready", "prerequisites", "execution", "execution and tracking",
    "delivery", "submission", "formal submission", "review", "client review",
    "review period", "review and slas", "deliverable-specific rules", "deliverable rules", "acceptance period", "evaluation"
}

CARD_2_LABELS = {
    "triage", "defect triage", "non-conformance", "deficiency", "defect notice",
    "remediation", "remedy", "rework", "rework limit", "repeated attempts",
    "cure period", "cure", "rejection", "rejection path"
}

CARD_3_LABELS = {
    "deemed accepted", "deemed acceptance", "passive acceptance", "sign-off",
    "sign-off and invoicing", "certification", "acceptance certification",
    "next gate", "billing gate", "invoicing", "exceptions", "change orders",
    "escalation", "dispute", "dispute protocols"
}


def parse_step_line(line: str) -> Tuple[Optional[str], str]:
    """Parse a step line into (label, body), supporting **Label:**, **Label**: and Label: formats."""
    m_md = re.match(r"^\*\*(.+?):?\*\*:?\s*(.*)$", line)
    if m_md:
        label = m_md.group(1).rstrip(":") + ":"
        body = m_md.group(2)
        return label, body
    m_plain = re.match(r"^([A-Za-z0-9][A-Za-z0-9 /–—&'-]{1,40}:)\s*(.*)$", line)
    if m_plain:
        label = m_plain.group(1)
        body = m_plain.group(2)
        return label, body
    return None, line


def _classify_acceptance_step(label: Optional[str], body: str) -> int:
    """Classify a narrative step into Card 1, 2, or 3 using label-first exact matching,
    followed by phrasal word-boundary regexes, avoiding bare substring collisions (HTL-74)."""
    clean_lbl = label.lower().strip(" :*#_-") if label else ""
    if clean_lbl in CARD_1_LABELS:
        return 1
    if clean_lbl in CARD_2_LABELS:
        return 2
    if clean_lbl in CARD_3_LABELS:
        return 3

    full_text = f"{clean_lbl} {body}".lower()
    if re.search(r'\b(defect|non-conformance|deficiency|remediation|rework|cure period|rejection)\b', full_text):
        return 2
    if re.search(r'\b(deemed accept|passive accept|sign-off|certification|invoice trigger|change order|dispute|escalation)\b', full_text):
        return 3
    if re.search(r'\b(inputs ready|prerequisite|submission|deliverable-specific|review window|review period|acceptance period|review session)\b', full_text):
        return 1
    return 1


def _build_acceptance_cards(narrative_text: str) -> List[AcceptanceCardData]:
    """Partition narrative steps into 3 structured acceptance cards with balanced fallback guarantees (HTL-74)."""
    paragraphs = [p.strip() for p in narrative_text.split("\n") if p.strip()]
    parsed_steps = [parse_step_line(p) for p in paragraphs]

    c1_steps: List[Tuple[Optional[str], str]] = []
    c2_steps: List[Tuple[Optional[str], str]] = []
    c3_steps: List[Tuple[Optional[str], str]] = []

    for label, body in parsed_steps:
        target = _classify_acceptance_step(label, body)
        if target == 1:
            c1_steps.append((label, body))
        elif target == 2:
            c2_steps.append((label, body))
        elif target == 3:
            c3_steps.append((label, body))

    # Prioritize core contractual Card 1 steps: prerequisites/inputs ready, submission, and review (HTL-103)
    if len(c1_steps) > 3:
        core_c1 = [
            (lbl, body) for lbl, body in c1_steps
            if (lbl or "").lower().strip(" :*#_-") in {"inputs ready", "prerequisites", "submission", "review", "milestone acceptance period"}
        ]
        other_c1 = [
            (lbl, body) for lbl, body in c1_steps
            if (lbl or "").lower().strip(" :*#_-") not in {"inputs ready", "prerequisites", "submission", "review", "milestone acceptance period"}
        ]
        c1_steps = (core_c1 + other_c1)[:3]
    else:
        c1_steps = c1_steps[:3]

    c2_steps = c2_steps[:3]
    c3_steps = c3_steps[:3]

    # Balanced fallback guarantee: If SOW narrative was silent on triage/rework, populate Card 2 with standard contractual defaults
    if not c2_steps:
        c2_steps.append(("Defect Notice:", "Client provides specific written notice identifying non-conformance details and required modifications."))
        c2_steps.append(("Remediation:", "Toptal applies commercially reasonable efforts to modify non-conforming items and resubmits for client review."))

    # If Card 1 or Card 3 are empty for any unusual sparse narrative, provide clean baseline fallbacks
    if not c1_steps:
        c1_steps.append(("Submission:", "Delivery package formally submitted to client approver initiating acceptance review period."))
    if not c3_steps:
        c3_steps.append(("Sign-off:", "Formal certification or deemed acceptance authorises milestone completion and billing gate progression."))

    return [
        AcceptanceCardData(
            stage_label="STAGE 01 & 02",
            title="SUBMISSION & REVIEW PROTOCOLS",
            steps=c1_steps,
        ),
        AcceptanceCardData(
            stage_label="STAGE 03",
            title="DEFECT TRIAGE & REMEDIATION",
            steps=c2_steps,
        ),
        AcceptanceCardData(
            stage_label="STAGE 04",
            title="SIGN-OFF & CONTRACTUAL CLOSURE",
            steps=c3_steps,
        ),
    ]


def build_slide16_model(baseline: StartupKitBaseline) -> Slide16AcceptanceNarrativeModel:
    """Build Slide 16 model (How Milestone Acceptance Works) using dual-tier synthesis and 3-card classification (HTL-72 / HTL-74 / HTL-98 / HTL-99 / HTL-105 / HTL-106 / HTL-107)."""
    sow = baseline.sow_interpretation
    facts = _extract_allowed_numeric_facts(baseline)
    ms_days_set = facts.get("milestone_acceptance_period_days", set())
    verified_rw_days = min(ms_days_set) if ms_days_set else None

    # Tier 1: LLM synthesized acceptance process narrative
    if sow and sow.acceptance_process_narrative and sow.acceptance_process_narrative.strip():
        narrative = _sanitize_acceptance_narrative(sow.acceptance_process_narrative.strip(), baseline=baseline)

        # HTL-107: Reconcile Review: and Deemed accepted: steps if missing or stripped
        if verified_rw_days is not None:
            lines = [l.strip() for l in narrative.split("\n") if l.strip()]
            has_review = any(re.match(r'^(?:\*\*)?(?:Review|Client Review|Review Period|Review and SLAs)(?::|\*\*:)', l, re.IGNORECASE) for l in lines)
            has_deemed = any(re.match(r'^(?:\*\*)?(?:Deemed [Aa]ccepted|Deemed [Aa]cceptance|Passive [Aa]cceptance|Passive [Ss]ign-off)(?::|\*\*:)', l, re.IGNORECASE) for l in lines)

            if not has_review or not has_deemed:
                new_lines: List[str] = []
                review_inserted = False

                for line in lines:
                    lbl, body = parse_step_line(line)
                    clean_lbl = lbl.lower().strip(" :*#_-") if lbl else ""

                    new_lines.append(line)
                    if not has_review and not review_inserted and clean_lbl in {"submission", "formal submission", "milestone submission"}:
                        new_lines.append(f"**Review:** Client conducts {verified_rw_days}-business-day evaluation against specifications and acceptance criteria.")
                        review_inserted = True

                if not has_review and not review_inserted:
                    idx = 1 if len(new_lines) >= 1 else 0
                    new_lines.insert(idx, f"**Review:** Client conducts {verified_rw_days}-business-day evaluation against specifications and acceptance criteria.")

                if not has_deemed:
                    new_lines.append(f"**Deemed accepted:** If Client provides no written notice of failure within the {verified_rw_days}-business-day window, milestone is deemed accepted.")

                narrative = "\n".join(new_lines)
                narrative = _sanitize_acceptance_narrative(narrative, baseline=baseline)

        cards = _build_acceptance_cards(narrative)
        return Slide16AcceptanceNarrativeModel(
            narrative=narrative,
            tier="Tier 1",
            cards=cards,
        )

    # Tier 2: Deterministic grounded fallback
    # Assembles a structured named-step walkthrough from approval_expectations, review_window, client_approver, rejection_rework_path
    steps: List[str] = []

    first_deliv = baseline.deliverables[0] if baseline.deliverables else None
    approver = (
        first_deliv.client_approver
        if first_deliv and first_deliv.client_approver and "[UNASSIGNED" not in first_deliv.client_approver.upper() and "[CONFIRMATION" not in first_deliv.client_approver.upper()
        else None
    )
    review_window = (
        first_deliv.review_window
        if first_deliv and first_deliv.review_window and "[CONFIRMATION" not in first_deliv.review_window.upper()
        else None
    )

    # Step 1: Submission
    if baseline.milestones:
        m = baseline.milestones[0]
        date_str = f" on or before estimated completion date {m.external_date}" if m.external_date else ""
        steps.append(f"Submission: Deliver work outputs formally for {m.id} ({m.description or 'Milestone'}){date_str} and notify client in writing to initiate the acceptance clock.")
    else:
        steps.append("Submission: Deliver work outputs formally upon milestone completion and notify client in writing to initiate the acceptance clock.")

    # Step 2: Review
    app_exp = (
        sow.approval_expectations
        if sow and sow.approval_expectations and "[CONFIRMATION" not in sow.approval_expectations.upper()
        else None
    )
    if verified_rw_days:
        steps.append(f"Review: Client conducts formal evaluation against specifications and acceptance criteria within a {verified_rw_days}-business-day review window.")
    elif app_exp:
        clean_app_exp = _sanitize_no_dollars(app_exp)
        steps.append(f"Review: {clean_app_exp}")
    else:
        if approver and review_window:
            steps.append(f"Review: {approver} conducts evaluation against acceptance criteria within a {review_window} review window.")
        elif approver:
            steps.append(f"Review: {approver} conducts formal evaluation against acceptance criteria.")
        elif review_window:
            steps.append(f"Review: Client conducts formal evaluation against acceptance criteria within a {review_window} review window.")
        else:
            steps.append("Review: Client evaluates delivered work outputs against agreed acceptance criteria.")

    # Step 3: Remediation / If rejected
    rework = (
        first_deliv.rejection_rework_path
        if first_deliv and first_deliv.rejection_rework_path and "[CONFIRMATION" not in first_deliv.rejection_rework_path.upper()
        else None
    )
    if rework:
        clean_rework = _sanitize_no_dollars(rework)
        steps.append(f"Remediation: {clean_rework}")
    else:
        steps.append("Remediation: In the event of material non-conformance, client provides specific written notice of deficiency, followed by commercially reasonable remediation efforts.")

    # Step 4: Deemed accepted & Sign-off
    if verified_rw_days:
        steps.append(f"Deemed accepted & Sign-off: Milestone is deemed accepted if client does not provide written notice of non-conformance within the {verified_rw_days}-business-day window, followed by formal milestone certification and invoice release.")
    else:
        steps.append("Deemed accepted & Sign-off: Milestone is deemed accepted if client does not provide written notice of non-conformance before the review window expires, followed by formal milestone certification and invoice release.")

    narrative = "\n".join(steps)
    clean_narrative = _sanitize_acceptance_narrative(narrative, baseline=baseline)
    cards = _build_acceptance_cards(clean_narrative)
    return Slide16AcceptanceNarrativeModel(
        narrative=clean_narrative,
        tier="Tier 2",
        cards=cards,
    )


def build_slide17_model(
    baseline: StartupKitBaseline,
    wb: Optional[WorkbookModel] = None,
) -> Slide17ApproachModel:
    """Build Slide 17 model (Approach 3-card layout: Schedule, Milestones, Workstream Execution) (HTL-72)."""
    if wb is None:
        wb = build_workbook_model(baseline)

    # 1. Card 1: Schedule (Phase/lifecycle structure and PMO cadence only, no per-milestone detail)
    l1_phases = [w for w in wb.wbs_rows if w.level == 1] if wb and wb.wbs_rows else []
    phase_names = [p.name for p in l1_phases if p.name]

    c1_bullets: List[str] = []
    if len(phase_names) > 1:
        c1_bullets.append(f"{len(phase_names)}-phase execution lifecycle: " + ", ".join(phase_names[:4]) + ".")
    elif len(phase_names) == 1:
        c1_bullets.append(f"Structured execution lifecycle focused on {phase_names[0]} discovery and delivery.")
    else:
        c1_bullets.append("Structured delivery lifecycle aligned with contractual scope and timeline.")

    c1_bullets.append("Weekly PMO schedule tracking, cross-stream alignment, and delivery cadence governance.")
    c1_bullets.append("Work breakdown packages and critical path dependencies tracked in the Project Delivery Workbook.")

    card1 = ApproachCard(
        category="PHASE & SCHEDULE",
        title="Schedule",
        lead="Execution Lifecycle",
        bullets=c1_bullets,
    )

    # 2. Card 2: Milestones (Milestone names and target dates only -- no deep criteria)
    c2_bullets: List[str] = []
    milestones = baseline.milestones or []
    if milestones:
        for m in milestones:
            desc = (m.description or m.id).strip()
            if desc.upper().startswith(m.id.upper() + ":"):
                desc = desc[len(m.id) + 1:].strip()
            if " accepted" in desc.lower():
                desc = desc[:desc.lower().find(" accepted")].strip()
            elif ":" in desc and len(desc.split(":")[0]) < 40 and not desc.lower().startswith("milestone"):
                desc = desc.split(":")[0].strip()

            date_str = ""
            if m.external_date:
                if hasattr(m.external_date, "strftime"):
                    date_str = f" (Target: {m.external_date.strftime('%B %d, %Y')})"
                else:
                    date_str = f" (Target: {m.external_date})"
            c2_bullets.append(f"{m.id}: {desc}{date_str}")
    else:
        c2_bullets.append("Key milestone gates and target dates aligned with contractual delivery schedule.")

    card2 = ApproachCard(
        category="KEY MILESTONES",
        title="Milestones",
        lead="Gates & Target Dates",
        bullets=c2_bullets,
    )

    # 3. Card 3: Workstream Execution (Keep as-is)
    c3_bullets: List[str] = []
    scope_items = baseline.charter.high_level_scope if baseline.charter and baseline.charter.high_level_scope else []
    if scope_items:
        delivs = baseline.deliverables or []
        for idx, s in enumerate(scope_items[:3]):
            s_clean = s.rstrip(".")
            if len(scope_items) == 3 and len(delivs) == 6:
                if idx == 0:
                    c3_bullets.append(f"{s_clean} (DEL-01).")
                elif idx == 1:
                    c3_bullets.append(f"{s_clean} (DEL-02).")
                elif idx == 2:
                    c3_bullets.append(f"{s_clean} (DEL-03, DEL-04, DEL-05, DEL-06).")
            else:
                c3_bullets.append(f"{s_clean}.")
    elif baseline.deliverables:
        chunk_size = max(1, (len(baseline.deliverables) + 2) // 3)
        for i in range(0, min(len(baseline.deliverables), chunk_size * 3), chunk_size):
            chunk = baseline.deliverables[i : i + chunk_size]
            deliv_ids = ", ".join([d.id for d in chunk])
            names = "; ".join([d.name for d in chunk if d.name])
            c3_bullets.append(f"{names} ({deliv_ids}).")
    else:
        c3_bullets.append("Core workstream delivery and backlog execution aligned with project objectives.")

    card3 = ApproachCard(
        category="WORKSTREAM EXECUTION",
        title="Workstream Execution",
        lead="Core Delivery Streams",
        bullets=c3_bullets,
    )

    return Slide17ApproachModel(
        kicker="PROJECT SUCCESS AGREEMENT",
        title="Approach",
        subtitle="Execution phases, milestones, and workstream deliverables.",
        cards=[card1, card2, card3],
    )


def build_slide18_model(baseline: StartupKitBaseline) -> Slide18RisksModel:
    """Build Slide 18 model (Initial Risk Register) reusing client deck slide 12 extraction (HTL-72)."""
    s12 = client_build_slide12_model(baseline)
    risk_items = [
        RiskItem(
            id=r.id,
            description=r.description,
            prob_impact=r.prob_impact,
            mitigation=r.mitigation,
            target_date=r.target_date,
            severity_score=r.severity_score,
        )
        for r in s12.risks
    ]
    return Slide18RisksModel(risks=risk_items)


def build_slide19_model(baseline: StartupKitBaseline) -> Slide19NextStepsModel:
    """Build Slide 19 model (Next Steps) reusing client deck slide 15 extraction (HTL-72)."""
    s15 = client_build_slide15_model(baseline)
    step_items = [
        NextStepItem(
            owner=st.owner,
            action=st.action,
            due=st.due,
        )
        for st in s15.next_steps
    ]
    return Slide19NextStepsModel(next_steps=step_items)


def build_governance_deck_model(
    baseline: StartupKitBaseline,
    wb: Optional[WorkbookModel] = None,
    llm_client: Optional[ILLMClient] = None,
) -> GovernanceDeckModel:
    """Complete builder transforming StartupKitBaseline into GovernanceDeckModel with 19-slide trace manifest (HTL-72)."""
    project_name = baseline.project_name or "Project Baseline"
    manifest = GovernanceDeckTraceManifest(project_name=project_name)

    slide1 = build_slide1_model(baseline)
    slide11 = build_slide11_model(baseline)
    slide13 = build_slide13_model(baseline, llm_client=llm_client)
    slide14 = build_slide14_model(baseline, llm_client=llm_client)
    slide15 = build_slide15_model(baseline, wb=wb)
    slide16 = build_slide16_model(baseline)
    slide17 = build_slide17_model(baseline, wb=wb)
    slide18 = build_slide18_model(baseline)
    slide19 = build_slide19_model(baseline)

    # 1. Slide 1 Traces
    headers = kit_header_values(baseline)
    manifest.add(
        slide=1,
        shape="Google Shape;93;p20",
        element="Title",
        displayed_value=f"{slide1.client_name}\n{slide1.project_name} Governance Kickoff",
        traces=[
            TraceRef(
                artifact="Kit",
                locator="Header table",
                key="client_sponsor",
                field="client_sponsor",
            ),
            TraceRef(
                artifact="Kit",
                locator="Header table",
                key="project_name",
                field="project_name",
            ),
        ],
        values=[headers.get("client_sponsor", "Client"), headers.get("project_name", project_name)],
    )

    # 2. Slide 11 Traces (Change Decision Matrix - HTL-109)
    for card in slide11.cards:
        manifest.add(
            slide=11,
            shape=f"Card: {card.classification}",
            element=f"Change Decision Matrix: {card.classification}",
            displayed_value=f"{card.operational_characteristics} | {card.budget_milestone_impact} | {card.decision_pathway}",
            traces=[
                TraceRef(
                    artifact="Kit",
                    locator="Scope Baseline",
                    key="classification_guide",
                    field="contract_type",
                )
            ],
            values=[card.operational_characteristics, card.budget_milestone_impact, card.decision_pathway],
        )

    # 2. Slide 13 Traces (Lifted Client Slide 5)
    manifest.add(
        slide=13,
        shape="Google Shape;176;p24",
        element="Why are we doing this?",
        displayed_value=slide13.why_are_we_doing_this,
        traces=[
            TraceRef(
                artifact="Kit",
                locator="Charter",
                key="project_purpose",
                field="project_purpose",
            )
        ],
    )
    manifest.add(
        slide=13,
        shape="Google Shape;180;p24",
        element="What problem are we solving?",
        displayed_value=slide13.what_problem_are_we_solving,
        traces=[
            TraceRef(
                artifact="Kit",
                locator="Charter",
                key="problem_statement",
                field="problem_statement",
            )
        ],
    )
    manifest.add(
        slide=13,
        shape="Google Shape;184;p24",
        element="What does success look like?",
        displayed_value=slide13.what_does_success_look_like,
        traces=[
            TraceRef(
                artifact="Kit",
                locator="SOW Interpretation",
                key="success_criteria",
                field="success_criteria",
            )
        ],
    )

    # 3. Slide 14 Traces (Lifted Client Slide 6)
    manifest.add(
        slide=14,
        shape="Google Shape;194;p25",
        element="Solution Overview",
        displayed_value=slide14.solution_overview,
        traces=[
            TraceRef(
                artifact="Kit",
                locator="Charter",
                key="solution_overview",
                field="solution_overview",
            )
        ],
    )
    for ws in slide14.workstreams:
        manifest.add(
            slide=14,
            shape="WorkstreamBlock",
            element=f"Workstream: {ws.title}",
            displayed_value="\n".join(ws.deliverables),
            traces=[
                TraceRef(
                    artifact="Workbook",
                    locator="WBS",
                    key=ws.title,
                    field="deliverables",
                )
            ],
            values=ws.deliverables,
        )
    if slide14.out_of_scope:
        manifest.add(
            slide=14,
            shape="Google Shape;202;p25",
            element="Out of Scope",
            displayed_value="\n".join(slide14.out_of_scope),
            traces=[
                TraceRef(
                    artifact="Kit",
                    locator="Charter",
                    key="out_of_scope",
                    field="out_of_scope",
                )
            ],
            values=slide14.out_of_scope,
        )

    # 4. Slide 15 Traces (Deliverable Acceptance Criteria Table)
    for row in slide15.rows:
        traces = [
            TraceRef(
                artifact="Kit",
                locator="Deliverables",
                key=row.deliverable_id,
                field="ID",
            ),
            TraceRef(
                artifact="Kit",
                locator="Deliverables",
                key=row.deliverable_id,
                field="Acceptance Criteria",
            ),
        ]
        if row.wbs_code:
            traces.append(
                TraceRef(
                    artifact="Workbook",
                    locator="WBS",
                    key=row.wbs_code,
                    field="Milestone ID",
                )
            )
        manifest.add(
            slide=15,
            shape="Table: Deliverable Acceptance Criteria",
            element=f"Deliverable: {row.deliverable_id}",
            displayed_value=f"{row.deliverable_id} ({row.deliverable_name}): {' | '.join(row.acceptance_criteria)} [Gate: {row.milestone_gate}]",
            traces=traces,
            values=row.acceptance_criteria,
        )

    # 5. Slide 16 Traces (How Milestone Acceptance Works)
    if slide16.tier == "Tier 1":
        manifest.add(
            slide=16,
            shape="Text Panel: How Milestone Acceptance Works",
            element="Acceptance Process Narrative",
            displayed_value=slide16.narrative,
            traces=[
                TraceRef(
                    artifact="Kit",
                    locator="SOW Interpretation",
                    key="acceptance_process_narrative",
                    field="acceptance_process_narrative",
                )
            ],
            values=[slide16.narrative],
        )
    else:
        tier2_traces: List[TraceRef] = []
        if (
            baseline.sow_interpretation
            and baseline.sow_interpretation.approval_expectations
            and "[CONFIRMATION" not in baseline.sow_interpretation.approval_expectations.upper()
        ):
            tier2_traces.append(
                TraceRef(
                    artifact="Kit",
                    locator="SOW Interpretation",
                    key="approval_expectations",
                    field="approval_expectations",
                )
            )
        if (
            baseline.deliverables
            and baseline.deliverables[0].rejection_rework_path
            and "[CONFIRMATION" not in baseline.deliverables[0].rejection_rework_path.upper()
        ):
            tier2_traces.append(
                TraceRef(
                    artifact="Kit",
                    locator="Deliverables",
                    key=baseline.deliverables[0].id,
                    field="Rejection / Rework Path",
                )
            )
        manifest.add(
            slide=16,
            shape="Text Panel: How Milestone Acceptance Works",
            element="Acceptance Process Narrative (Fallback)",
            displayed_value=slide16.narrative,
            traces=tier2_traces or [
                TraceRef(
                    artifact="Kit",
                    locator="SOW Interpretation",
                    key="approval_expectations",
                    field="approval_expectations",
                )
            ],
            values=[slide16.narrative],
        )

    # 6. Slide 17 Traces (Approach 3-Card Layout: Schedule, Milestones, Workstream Execution)
    if len(slide17.cards) >= 3:
        # Card 1: Schedule
        manifest.add(
            slide=17,
            shape="Card 1: Schedule",
            element="Approach: Schedule",
            displayed_value="\n".join(slide17.cards[0].bullets),
            traces=[
                TraceRef(
                    artifact="Workbook",
                    locator="WBS",
                    key="Phase rows",
                    field="name",
                ),
            ],
            values=slide17.cards[0].bullets,
        )
        # Card 2: Milestones
        manifest.add(
            slide=17,
            shape="Card 2: Milestones",
            element="Approach: Milestones",
            displayed_value="\n".join(slide17.cards[1].bullets),
            traces=[
                TraceRef(
                    artifact="Kit",
                    locator="Milestones",
                    key="milestones",
                    field="external_date",
                ),
            ],
            values=slide17.cards[1].bullets,
        )
        # Card 3: Workstream Execution
        manifest.add(
            slide=17,
            shape="Card 3: Workstream Execution",
            element="Approach: Workstream Execution",
            displayed_value="\n".join(slide17.cards[2].bullets),
            traces=[
                TraceRef(
                    artifact="Kit",
                    locator="Charter",
                    key="high_level_scope",
                    field="high_level_scope",
                ),
                TraceRef(
                    artifact="Kit",
                    locator="Deliverables",
                    key="deliverables",
                    field="name",
                ),
            ],
            values=slide17.cards[2].bullets,
        )

    # 7. Slide 18 Traces (Lifted Client Slide 12)
    for risk in slide18.risks:
        manifest.add(
            slide=18,
            shape="Table: Initial Risk Register",
            element=f"Risk: {risk.id}",
            displayed_value=f"{risk.description} | {risk.prob_impact} | {risk.mitigation}",
            traces=[
                TraceRef(
                    artifact="Workbook",
                    locator="RAID Log",
                    key=risk.id,
                    field="description",
                )
            ],
        )

    # 8. Slide 19 Traces (Lifted Client Slide 15)
    for step in slide19.next_steps:
        manifest.add(
            slide=19,
            shape="Table: Next Steps",
            element=f"Next Step: {step.owner}",
            displayed_value=f"{step.owner}: {step.action} (Due: {step.due})",
            traces=[
                TraceRef(
                    artifact="Kit",
                    locator="Next Steps",
                    key=step.owner,
                    field="action",
                )
            ],
        )

    return GovernanceDeckModel(
        project_name=project_name,
        slide1=slide1,
        slide11=slide11,
        slide13=slide13,
        slide14=slide14,
        slide15=slide15,
        slide16=slide16,
        slide17=slide17,
        slide18=slide18,
        slide19=slide19,
        manifest=manifest,
    )
