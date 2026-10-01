"""Baseline aggregator and business rules engine."""

import logging
import re
from datetime import timedelta, date
from typing import List, Optional, Set
from src.config import sanitize_report_text, extract_sow_references, detect_sow_reference_kind
from src.generators.pmo_workbook.mapping import tokenize_v2, natural_sort_key, strip_work_package_prefix
from src.generators.pmo_workbook.builder import extract_story_ids_for_deliverable
from src.core.models import (
    CharterExtraction,
    DeliverablesExtraction,
    MilestonesExtraction,
    RAIDExtraction,
    QuestionsExtraction,
    SOWInterpretationExtraction,
    ScopeDecompositionExtraction,
    AcceptanceProcessExtraction,
    StakeholdersExtraction,
    CommunicationsExtraction,
    CommercialGuardrailsExtraction,
    TalentOnboardingExtraction,
    DecisionsExtraction,
    GovernanceContext,
    StartupKitBaseline,
    ProjectStartupCharter,
    SOWInterpretationSummary,
    Deliverable,
    Milestone,
    RiskAssumption,
    DependencyAssumptionItem,
    DecisionItem,
    WorkPackageSeed,
    SOWStoryItem,
    SOWWorkItem,
    CommunicationsPlanItem,
    Stakeholder,
    RACIItem,
    CommercialGuardrail,
    TalentOnboardingRecord,
    TalentMember,
    ReadinessChecklistItem,
    GateDecision,
    SourceReference,
    ContractAmbiguityItem,
    ContractConflictsExtraction,
    ReadinessWorkflowState,
    ActionRequiredItem,
)
from src.scoring.readiness_engine import ReadinessScoringEngine

logger = logging.getLogger(__name__)


class BaselineAggregator:
    """Aggregates intermediate domain extractions and enforces PMO startup business rules."""

    def aggregate(
        self,
        charter: CharterExtraction,
        deliverables_ext: DeliverablesExtraction,
        milestones_ext: MilestonesExtraction,
        raid_ext: RAIDExtraction,
        questions_ext: Optional[QuestionsExtraction] = None,
        sow_interpretation_ext: Optional[SOWInterpretationExtraction] = None,
        backlog_ext: Optional[ScopeDecompositionExtraction] = None,
        acceptance_ext: Optional[AcceptanceProcessExtraction] = None,
        stakeholders_ext: Optional[StakeholdersExtraction] = None,
        communications_ext: Optional[CommunicationsExtraction] = None,
        commercial_ext: Optional[CommercialGuardrailsExtraction] = None,
        talent_ext: Optional[TalentOnboardingExtraction] = None,
        decisions_ext: Optional[DecisionsExtraction] = None,
        conflicts_ext: Optional[ContractConflictsExtraction] = None,
        sow_awarded_date: Optional[date] = None,
        kit_drafted_date: Optional[date] = None,
    ) -> StartupKitBaseline:
        """Combine extractions and apply validation and business rules."""
        questions: List[str] = [sanitize_report_text(q) for q in questions_ext.open_questions] if questions_ext else []
        seen_questions: Set[str] = set(questions)

        def add_question(q: str):
            clean_q = sanitize_report_text(q)
            if clean_q and clean_q not in seen_questions:
                seen_questions.add(clean_q)
                questions.append(clean_q)

        # 1. Process Deliverables and check acceptance criteria & ownership (v4 B1, B10, v5 B11, B12, B16)
        deliverables: List[Deliverable] = [d.model_copy() for d in deliverables_ext.deliverables]
        acc_items = []
        if acceptance_ext:
            acc_items = getattr(acceptance_ext, "acceptance_matrix_items", None) or getattr(acceptance_ext, "acceptance_items", None) or []

        # Default review window from SOW approval expectations (v5 B12, v6 B3)
        default_review_window = "Not specified; reviewed at the end-of-milestone Acceptance Review"
        if sow_interpretation_ext and sow_interpretation_ext.approval_expectations:
            app_exp = sow_interpretation_ext.approval_expectations.strip()
            if app_exp and "[CONFIRMATION REQUIRED]" not in app_exp:
                first_sent = app_exp.split(".")[0].strip()
                if first_sent:
                    first_sent = f"{first_sent}."
                if len(first_sent) > 120:
                    first_sent = first_sent[:117] + "..."
                default_review_window = sanitize_report_text(first_sent)

        if acc_items:
            # First pass: shared SOW work item references (v6 B2)
            matched_acc_indices: Set[int] = set()
            for a_idx, acc_item in enumerate(acc_items):
                acc_name = getattr(acc_item, "name", "") or getattr(acc_item, "deliverable_name", "") or getattr(acc_item, "description", "") or ""
                acc_stories = set(s for s in extract_sow_references(f"{acc_name} {getattr(acc_item, 'description', '') or ''} {getattr(acc_item, 'sow_reference', '') or ''}") if detect_sow_reference_kind(s) != "Section")
                if not acc_stories:
                    continue

                target_delivs = []
                for d in deliverables:
                    d_stories = set(s for s in extract_sow_references(f"{d.name or ''} {d.description or ''} {d.sow_reference or ''}") if detect_sow_reference_kind(s) != "Section")
                    if acc_stories & d_stories:
                        target_delivs.append(d)

                if target_delivs:
                    matched_acc_indices.add(a_idx)
                    for d in target_delivs:
                        ev_text = getattr(acc_item, "evidence_required", "") or getattr(acc_item, "acceptance_criteria", "") or ""
                        if ev_text and "[CONFIRMATION REQUIRED]" not in ev_text:
                            if len(target_delivs) > 1:
                                shared_note = f"Shared evidence item covering {', '.join(sorted(acc_stories))}"
                                if not d.evidence_required or "[CONFIRMATION REQUIRED]" in d.evidence_required:
                                    d.evidence_required = sanitize_report_text(f"{ev_text} ({shared_note})")
                                elif shared_note not in d.evidence_required:
                                    d.evidence_required = sanitize_report_text(f"{d.evidence_required}; {ev_text} ({shared_note})")
                            else:
                                if not d.evidence_required or "[CONFIRMATION REQUIRED]" in d.evidence_required:
                                    d.evidence_required = sanitize_report_text(ev_text)

                        if getattr(acc_item, "client_approver", None) and (not d.client_approver or d.client_approver in ("Unassigned", "[UNASSIGNED - TO BE CONFIRMED]", "[CONFIRMATION REQUIRED]")):
                            d.client_approver = getattr(acc_item, "client_approver")
                        if getattr(acc_item, "acceptance_criteria", None) and not d.acceptance_criteria:
                            d.acceptance_criteria = getattr(acc_item, "acceptance_criteria")
                        if getattr(acc_item, "owner", None) and (not d.owner or d.owner in ("Unassigned", "[UNASSIGNED - TO BE CONFIRMED]")):
                            d.owner = getattr(acc_item, "owner")
                        if getattr(acc_item, "sow_reference", None) and not getattr(d, "sow_reference", None):
                            d.sow_reference = getattr(acc_item, "sow_reference")
                        if getattr(acc_item, "rejection_rework_path", None) and not d.rejection_rework_path:
                            d.rejection_rework_path = getattr(acc_item, "rejection_rework_path")
                        rw_val = getattr(acc_item, "review_window", None)
                        if rw_val and "[CONFIRMATION REQUIRED]" not in rw_val and rw_val.strip().lower() != "5 business days":
                            d.review_window = sanitize_report_text(rw_val)

            # Second pass: greedy one-to-one name similarity for unmatched acceptance items
            unmatched_acc_items = [(idx, item) for idx, item in enumerate(acc_items) if idx not in matched_acc_indices]
            unmatched_delivs = [d for d in deliverables if not d.evidence_required or "[CONFIRMATION REQUIRED]" in d.evidence_required or not d.acceptance_criteria]

            candidate_pairs = []
            for a_idx, acc_item in unmatched_acc_items:
                acc_name = getattr(acc_item, "name", "") or getattr(acc_item, "deliverable_name", "") or getattr(acc_item, "description", "") or ""
                acc_tokens = tokenize_v2(acc_name)
                for d_idx, d in enumerate(unmatched_delivs):
                    d_name = d.name or d.description or ""
                    d_tokens = tokenize_v2(d_name)
                    if acc_tokens and d_tokens:
                        s1, s2 = set(acc_tokens), set(d_tokens)
                        jaccard = (len(s1 & s2) / len(s1 | s2)) if (s1 or s2) else 0.0
                        if jaccard >= 0.35:
                            candidate_pairs.append((jaccard, a_idx, d_idx, acc_item, d))

            candidate_pairs.sort(key=lambda c: (-c[0], natural_sort_key(getattr(c[3], "id", "")), natural_sort_key(c[4].id)))
            assigned_acc: Set[int] = set()
            assigned_deliv: Set[str] = set()

            for score, a_idx, d_idx, acc_item, d in candidate_pairs:
                if a_idx not in assigned_acc and d.id not in assigned_deliv:
                    assigned_acc.add(a_idx)
                    assigned_deliv.add(d.id)

                    if acc_item.client_approver and "UNASSIGNED" not in acc_item.client_approver.upper() and "[CONFIRMATION REQUIRED]" not in acc_item.client_approver:
                        d.client_approver = acc_item.client_approver
                    if acc_item.evidence_required and "[CONFIRMATION REQUIRED]" not in acc_item.evidence_required:
                        d.evidence_required = acc_item.evidence_required
                    if not d.acceptance_criteria and acc_item.acceptance_criteria and "[CONFIRMATION REQUIRED]" not in acc_item.acceptance_criteria:
                        d.acceptance_criteria = acc_item.acceptance_criteria
                    if acc_item.review_window and acc_item.review_window.strip() and acc_item.review_window.strip().lower() != "5 business days":
                        d.review_window = acc_item.review_window
                    if acc_item.rejection_rework_path:
                        d.rejection_rework_path = acc_item.rejection_rework_path
                    if (not d.owner or d.owner in ("Unassigned", "[UNASSIGNED - TO BE CONFIRMED]")) and acc_item.owner and acc_item.owner not in ("Unassigned", "[UNASSIGNED - TO BE CONFIRMED]"):
                        d.owner = acc_item.owner
                    if getattr(acc_item, "sow_reference", None) and not getattr(d, "sow_reference", None):
                        d.sow_reference = getattr(acc_item, "sow_reference")

            for d in deliverables:
                if not d.review_window or d.review_window.strip().lower() == "5 business days" or "[CONFIRMATION REQUIRED]" in d.review_window:
                    d.review_window = default_review_window
        else:
            for d in deliverables:
                if not d.review_window or d.review_window.strip().lower() == "5 business days":
                    d.review_window = default_review_window

        # Granularity check (v5 B16)
        for d in deliverables:
            text_block = f"{d.name or ''} {d.description or ''} {d.sow_reference or ''}"
            d_stories = set(extract_sow_references(text_block))
            if len(d_stories) > 5:
                logger.warning("Deliverable '%s' carries %d stories (> 5 stories threshold) - review grouping", d.id, len(d_stories))

        # Completeness check for SOW story IDs (v4 B10)
        covered_stories: Set[str] = set()
        for d in deliverables:
            text_block = f"{d.name or ''} {d.description or ''} {d.sow_reference or ''}"
            for s in extract_sow_references(text_block):
                covered_stories.add(s)

        if conflicts_ext and conflicts_ext.ambiguities:
            for ca in conflicts_ext.ambiguities:
                for s in extract_sow_references(ca.conflicting_clauses or ""):
                    if s not in covered_stories:
                        add_question(f"SOW work item '{s}' cited in contract ambiguity {ca.anomaly_id} is not mapped to any baseline deliverable. [CONFIRMATION REQUIRED]")

        for deliv in deliverables:
            deliv.description = sanitize_report_text(deliv.description)
            deliv.name = sanitize_report_text(deliv.name or deliv.description)
            if deliv.acceptance_criteria:
                deliv.acceptance_criteria = sanitize_report_text(deliv.acceptance_criteria)
            if not deliv.acceptance_criteria:
                deliv.acceptance_criteria = None
                add_question(
                    f"Deliverable '{deliv.id}: {deliv.description}' is missing explicit acceptance criteria. [CONFIRMATION REQUIRED]"
                )
            if not deliv.owner or deliv.owner in ("Unassigned", "[UNASSIGNED - TO BE CONFIRMED]"):
                deliv.owner = "[UNASSIGNED - TO BE CONFIRMED]"
                add_question(
                    f"Deliverable '{deliv.id}: {deliv.description}' owner is unassigned. [CONFIRMATION REQUIRED]"
                )
            if deliv.source_reference and deliv.source_reference.confidence_score < 0.7:
                add_question(
                    f"[Low Confidence: {deliv.source_reference.confidence_score:.2f}] Review deliverable '{deliv.id}' scope and acceptance criteria."
                )

        # 2. Process Milestones and calculate internal buffers if needed
        milestones: List[Milestone] = [m.model_copy() for m in milestones_ext.milestones]
        buffer_days = 7
        if charter.governance_tier == "Elevated":
            buffer_days = 10
        elif charter.governance_tier == "Guided":
            buffer_days = 3

        for ms in milestones:
            ms.description = sanitize_report_text(ms.description)
            if ms.external_date is None:
                add_question(
                    f"Confirm committed external completion date for {ms.id}. [CONFIRMATION REQUIRED]"
                )
            elif ms.internal_buffer_date is None:
                ms.internal_buffer_date = ms.external_date - timedelta(days=buffer_days)

            if ms.source_reference and ms.source_reference.confidence_score < 0.7:
                add_question(
                    f"[Low Confidence: {ms.source_reference.confidence_score:.2f}] Review milestone '{ms.id}' target delivery date."
                )

        # 3. Separate RAID, Dependencies/Assumptions, and Decisions (v4 B2)
        raw_raid_items = [r.model_copy() for r in raid_ext.items]
        raid_items: List[RiskAssumption] = []
        dependencies_assumptions: List[DependencyAssumptionItem] = []

        dep_idx = 1
        asm_idx = 1
        for item in raw_raid_items:
            item.description = sanitize_report_text(item.description)
            if item.source_reference and item.source_reference.confidence_score < 0.7:
                add_question(
                    f"[Low Confidence: {item.source_reference.confidence_score:.2f}] Review {item.type} '{item.description}'."
                )

            if item.type in ("Dependency", "Assumption"):
                item_id = f"DEP-{dep_idx:02d}" if item.type == "Dependency" else f"ASM-{asm_idx:02d}"
                if item.type == "Dependency":
                    dep_idx += 1
                else:
                    asm_idx += 1

                # Link only if item text explicitly names milestone phase code or deliverable ID (v4 B2)
                matched_ms_id = None
                matched_deliv_id = None
                for m in milestones:
                    if re.search(r"\b" + re.escape(m.id) + r"\b", item.description, re.IGNORECASE):
                        matched_ms_id = m.id
                        break
                for d in deliverables:
                    if re.search(r"\b" + re.escape(d.id) + r"\b", item.description, re.IGNORECASE):
                        matched_deliv_id = d.id
                        break

                da_item = DependencyAssumptionItem(
                    id=item_id,
                    type=item.type,
                    description=item.description,
                    category=item.category if hasattr(item, "category") and item.category else "Technical",
                    source_reference=item.source_reference,
                    owner=item.owner if item.owner != "Unassigned" else "[UNASSIGNED - TO BE CONFIRMED]",
                    status=item.status or "Open",
                    impact_if_unmet="Delivery delay / milestone impediment",
                    escalation_trigger="Milestone slip or unconfirmed prerequisite",
                    linked_milestone=matched_ms_id,
                    linked_deliverable=matched_deliv_id,
                )
                dependencies_assumptions.append(da_item)
            else:
                # Risk or Issue remains in RAID Log
                raid_items.append(item)

        # 4. Process Contract Ambiguities
        contract_ambiguities: List[ContractAmbiguityItem] = []
        if conflicts_ext and conflicts_ext.ambiguities:
            contract_ambiguities = [a.model_copy() for a in conflicts_ext.ambiguities]
        elif sow_interpretation_ext and hasattr(sow_interpretation_ext, "contract_ambiguities") and sow_interpretation_ext.contract_ambiguities:
            contract_ambiguities = [a.model_copy() for a in sow_interpretation_ext.contract_ambiguities]

        # 5. Process Decisions (v4 B3: renumber when repeated or default)
        decisions: List[DecisionItem] = []
        if decisions_ext and decisions_ext.decisions:
            raw_decs = decisions_ext.decisions
            seen_ids: Set[str] = set()
            needs_renumbering = False
            for d in raw_decs:
                if not d.id or d.id == "DEC-01" or d.id in seen_ids:
                    if seen_ids:
                        needs_renumbering = True
                seen_ids.add(d.id)
            if len(raw_decs) > 1 and len(seen_ids) < len(raw_decs):
                needs_renumbering = True

            dec_id_map = {}
            for idx, d in enumerate(raw_decs, 1):
                old_id = d.id
                new_id = f"DEC-{idx:02d}" if needs_renumbering else (d.id or f"DEC-{idx:02d}")
                dec_id_map[old_id] = new_id
                decisions.append(
                    DecisionItem(
                        id=new_id,
                        decision_text=sanitize_report_text(d.decision_text),
                        decision_owner=d.decision_owner,
                        status=d.status,
                        rationale=sanitize_report_text(d.rationale),
                        source_reference=d.source_reference
                    )
                )

            # Update any linked_decision references in RAID items
            for r in raid_items:
                if hasattr(r, "linked_decision") and r.linked_decision and r.linked_decision in dec_id_map:
                    r.linked_decision = dec_id_map[r.linked_decision]
        else:
            decisions = [
                DecisionItem(
                    id="DEC-01",
                    decision_text=f"Project Governance Tier baselined as '{charter.governance_tier}' with standard PMO cadence.",
                    decision_owner=charter.pmo_lead or "[UNASSIGNED - TO BE CONFIRMED]",
                    status="Approved",
                    rationale="Assigned based on project scope, delivery model, and risk profile.",
                    source_reference=charter.source_reference
                ),
                DecisionItem(
                    id="DEC-02",
                    decision_text=f"Contract baseline established under '{charter.contract_type}' terms.",
                    decision_owner=charter.delivery_manager or "Delivery Manager",
                    status="Approved",
                    rationale="Aligned to project baseline scope and commercial boundaries.",
                    source_reference=charter.source_reference
                )
            ]

        # 6. Check role assignments
        if not charter.delivery_manager or charter.delivery_manager == "[UNASSIGNED - TO BE CONFIRMED]":
            add_question("Delivery Manager role is unassigned. [CONFIRMATION REQUIRED]")
        if not charter.talent_pm or charter.talent_pm == "[UNASSIGNED - TO BE CONFIRMED]":
            add_question("Talent PM role is unassigned. [CONFIRMATION REQUIRED]")
        if not charter.pmo_lead or charter.pmo_lead == "[UNASSIGNED - TO BE CONFIRMED]":
            add_question("PMO Lead role is unassigned. [CONFIRMATION REQUIRED]")

        # 7. Build Project Startup Charter (Layer 1)
        charter_obj = ProjectStartupCharter(
            project_name=charter.project_name or "Project Baseline",
            client_name=charter.client_name,
            project_purpose=sanitize_report_text(charter.project_purpose or charter.executive_summary or "[CONFIRMATION REQUIRED]"),
            delivery_objectives=[sanitize_report_text(o) for o in charter.delivery_objectives] if charter.delivery_objectives else [
                f"Successfully deliver and validate {d.name or d.description}" for d in deliverables[:4]
            ],
            success_criteria=[sanitize_report_text(s) for s in charter.success_criteria] if charter.success_criteria else [
                "Agreed deliverables accepted by designated client sponsor within review window",
                "Milestone delivery achieved within agreed external dates and internal buffers",
                "Adherence to project governance cadence and margin guardrails"
            ],
            high_level_scope=[sanitize_report_text(s) for s in charter.high_level_scope] if charter.high_level_scope else [d.name or d.description for d in deliverables],
            exclusions=[sanitize_report_text(e) for e in charter.exclusions] if charter.exclusions else [
                "Custom infrastructure outside documented cloud provider scope",
                "Unapproved out-of-scope feature requests without formal Change Order"
            ],
            key_deliverables_summary=[f"{d.id}: {d.name or d.description}" for d in deliverables],
            key_milestones_summary=[
                f"{m.id}: {m.description} ({m.external_date.strftime('%Y-%m-%d') if m.external_date else '[DATE TBD]'})"
                for m in milestones
            ],
            contract_type=charter.contract_type,
            governance_tier=charter.governance_tier,
            delivery_model="Toptal Talent Team (Agile/Milestone Hybrid)",
            governance_model=f"PMO {charter.governance_tier} Tier Governance Model",
            major_startup_risks=[r.description for r in raid_items if r.type == "Risk"][:3] or [
                "Client access provisioning and environment availability delays",
                "Timely client feedback and deliverable sign-off turnaround"
            ],
            delivery_manager=charter.delivery_manager or "[UNASSIGNED - TO BE CONFIRMED]",
            talent_pm=charter.talent_pm or "[UNASSIGNED - TO BE CONFIRMED]",
            pmo_lead=charter.pmo_lead or "[UNASSIGNED - TO BE CONFIRMED]",
            escalation_path="Talent PM / Delivery Manager -> PMO Lead -> Director, PMO",
            unresolved_assumptions_status=(
                f"{len(dependencies_assumptions)} dependencies/assumptions logged, awaiting mobilization validation"
                if dependencies_assumptions else "No critical open assumptions"
            ),
            source_reference=charter.source_reference
        )

        # 8. Build Scope & Baseline Interpretation Summary (Layer 1)
        if sow_interpretation_ext:
            sow_summary = SOWInterpretationSummary(
                contracted_deliverables=[sanitize_report_text(x) for x in (sow_interpretation_ext.contracted_deliverables or [d.name or d.description for d in deliverables])],
                out_of_scope_items=[sanitize_report_text(x) for x in (sow_interpretation_ext.out_of_scope_items or charter_obj.exclusions)],
                customer_obligations=[sanitize_report_text(x) for x in (sow_interpretation_ext.customer_obligations or [
                    "Provision cloud accounts, IAM roles, and environment access",
                    "Timely review and formal sign-offs within agreed review window",
                    "Provide technical architecture specifications and sample datasets"
                ])],
                assumptions=[sanitize_report_text(x) for x in (sow_interpretation_ext.assumptions or [da.description for da in dependencies_assumptions if da.type == "Assumption"])],
                constraints=[sanitize_report_text(x) for x in (sow_interpretation_ext.constraints or [
                    f"Governance tier cadence: {charter.governance_tier}",
                    f"Delivery model: {charter.contract_type}"
                ])],
                platform_environment_commitments=[sanitize_report_text(x) for x in (sow_interpretation_ext.platform_environment_commitments or [
                    "[UNDEFINED]"
                ])],
                dependencies=[sanitize_report_text(x) for x in (sow_interpretation_ext.dependencies or [da.description for da in dependencies_assumptions if da.type == "Dependency"])],
                approval_expectations=sanitize_report_text(sow_interpretation_ext.approval_expectations or "Written sign-off by Client Approver within 5 business days of submission."),
                ambiguity_notes=[sanitize_report_text(x) for x in (sow_interpretation_ext.ambiguity_notes or [q for q in questions if "[CONFIRMATION REQUIRED]" in q])],
                confirmation_required_items=[q for q in questions if "[CONFIRMATION REQUIRED]" in q],
                contract_ambiguities=contract_ambiguities,
                source_reference=sow_interpretation_ext.source_reference or charter.source_reference
            )
        else:
            sow_summary = SOWInterpretationSummary(
                contracted_deliverables=[d.name or d.description for d in deliverables],
                out_of_scope_items=charter_obj.exclusions,
                customer_obligations=[
                    "Provision cloud accounts, IAM roles, and environment access",
                    "Timely review and formal sign-offs within agreed review window",
                    "Provide technical architecture specifications and sample datasets"
                ],
                assumptions=[da.description for da in dependencies_assumptions if da.type == "Assumption"] or [
                    "Standard working hours and remote talent team execution",
                    "Client environment availability in advance of milestone execution"
                ],
                constraints=[
                    f"Governance tier cadence: {charter.governance_tier}",
                    f"Delivery model: {charter.contract_type}"
                ],
                platform_environment_commitments=[
                    "[UNDEFINED]"
                ],
                dependencies=[da.description for da in dependencies_assumptions if da.type == "Dependency"] or [
                    "Third-party API access tokens and enterprise credentials",
                    "Architecture review board sign-off"
                ],
                approval_expectations="Written sign-off by Client Approver within 5 business days of submission.",
                ambiguity_notes=[q for q in questions if "[CONFIRMATION REQUIRED]" in q],
                confirmation_required_items=[q for q in questions if "[CONFIRMATION REQUIRED]" in q],
                contract_ambiguities=contract_ambiguities,
                source_reference=charter.source_reference
            )

        # 9. Build SOW Story / Work Item Catalogue & Scope Decomposition Backlog Seed (Layer 2, v4 B4, v5 B13, v6 Section 1.1)
        sow_stories_catalogue: List[SOWWorkItem] = []
        seen_catalogue_stories: Set[str] = set()

        for d in deliverables:
            text_block = f"{d.name or ''} {d.description or ''} {d.sow_reference or ''}"
            for s_id in extract_sow_references(text_block):
                if s_id not in seen_catalogue_stories:
                    seen_catalogue_stories.add(s_id)
                    sow_stories_catalogue.append(SOWWorkItem(
                        reference=s_id,
                        reference_kind=detect_sow_reference_kind(s_id) or "Story ID",
                        title="",
                        phase="",
                        owner="Toptal",
                        type="Build",
                        deliverable_id=d.id,
                        source_reference=d.source_reference
                    ))

        backlog_seed: List[WorkPackageSeed] = []
        deliv_id_set = {d.id for d in deliverables}
        if backlog_ext and backlog_ext.work_packages:
            for wp in backlog_ext.work_packages:
                wp_copy = wp.model_copy()
                wp_copy.title = strip_work_package_prefix(wp_copy.title)
                if wp_copy.parent_deliverable_id and wp_copy.parent_deliverable_id not in deliv_id_set:
                    logger.warning("Work package %s parent deliverable '%s' does not exist in deliverables; clearing parent.", wp_copy.id, wp_copy.parent_deliverable_id)
                    wp_copy.parent_deliverable_id = None
                backlog_seed.append(wp_copy)
        else:
            # Build backlog from SOW stories if present on deliverables (v5 B13)
            wp_counter = 0
            for deliv in deliverables:
                d_story_ids = extract_story_ids_for_deliverable(deliv)
                if d_story_ids:
                    for s_id in d_story_ids:
                        wp_counter += 1
                        wp = WorkPackageSeed(
                            id=f"WP-{wp_counter:02d}",
                            parent_deliverable_id=deliv.id,
                            title=f"Build {s_id}",
                            description=f"Implementation story {s_id} for {deliv.id}.",
                            preliminary_sequence=wp_counter,
                            owner="Toptal Delivery Team",
                            dependency_references=[da.id for da in dependencies_assumptions[:2]],
                            linked_milestones=[],
                            linked_acceptance_items=[deliv.acceptance_criteria or "[CONFIRMATION REQUIRED]"],
                            uncertain_scope=deliv.acceptance_criteria is None,
                            sow_reference=s_id,
                            status="Draft"
                        )
                        backlog_seed.append(wp)
                else:
                    wp_counter += 1
                    wp = WorkPackageSeed(
                        id=f"WP-{wp_counter:02d}",
                        parent_deliverable_id=deliv.id,
                        title=f"{deliv.name or deliv.description}",
                        description=f"Decomposition and implementation tasks for {deliv.id}.",
                        preliminary_sequence=wp_counter,
                        owner="Toptal Delivery Team",
                        dependency_references=[da.id for da in dependencies_assumptions[:2]],
                        linked_milestones=[],
                        linked_acceptance_items=[deliv.acceptance_criteria or "[CONFIRMATION REQUIRED]"],
                        uncertain_scope=deliv.acceptance_criteria is None,
                        status="Draft"
                    )
                    backlog_seed.append(wp)

        # 10. Build Communications Plan (Layer 2)
        communications_plan: List[CommunicationsPlanItem] = []
        if communications_ext and communications_ext.communications:
            communications_plan = list(communications_ext.communications)
        else:
            communications_plan = [
                CommunicationsPlanItem(
                    id="COM-01",
                    name="Weekly Check-in (30 min)",
                    audience="Talent PM, Delivery Manager, PMO Lead",
                    content_owner=charter.talent_pm or "Talent PM",
                    cadence="Weekly (30 min)",
                    governance_tier_applicability="All Tiers",
                    format="Virtual Meeting",
                    delivery_day="Every Tuesday",
                    escalation_route="PMO Lead -> Director, PMO",
                    pmo_health_rating_notes="Evidence is exchanged at the weekly check-in; PMO Lead assesses project health."
                ),
                CommunicationsPlanItem(
                    id="COM-02",
                    name="Weekly Project Status Report (PSR)",
                    audience="Client Sponsor, Delivery Manager, PMO Lead",
                    content_owner=charter.talent_pm or "Talent PM",
                    cadence="Weekly",
                    governance_tier_applicability="All Tiers",
                    format="Written Report (Email / Portal)",
                    delivery_day="Every Friday COB",
                    escalation_route="PMO Lead -> Director, PMO",
                    pmo_health_rating_notes="PMO Lead independently issues health rating before executive distribution."
                )
            ]
            if charter.governance_tier in ("Partnered", "Elevated"):
                communications_plan.append(
                    CommunicationsPlanItem(
                        id="COM-03",
                        name="Monthly / Quarterly Business Review (MBR/QBR - G-07)",
                        audience="Executive Sponsors, Director PMO, Client VP",
                        content_owner=charter.delivery_manager or "Delivery Manager",
                        cadence="Monthly",
                        governance_tier_applicability="Partnered, Elevated",
                        format="Executive Presentation Deck",
                        delivery_day="Last Thursday of Month",
                        escalation_route="Director, PMO",
                        pmo_health_rating_notes="Strategic governance, milestone progress, and budget burndown review."
                    )
                )
            if charter.governance_tier == "Elevated":
                communications_plan.append(
                    CommunicationsPlanItem(
                        id="COM-04",
                        name="Daily Standup & Blocker Sync",
                        audience="Delivery Team, Talent PM, Tech Lead",
                        content_owner=charter.talent_pm or "Talent PM",
                        cadence="Daily (15 min)",
                        governance_tier_applicability="Elevated",
                        format="Virtual Standup",
                        delivery_day="Monday - Friday",
                        escalation_route="Talent PM -> Delivery Manager",
                        pmo_health_rating_notes="Immediate impediment clearing and blocker escalation."
                    )
                )

        # 11. Build Stakeholder Model and RACI Matrix (Layer 3 - including PMO)
        pmo_lead_name = charter.pmo_lead or "[UNASSIGNED - TO BE CONFIRMED]"
        dir_pmo_name = "Director, PMO"

        stakeholders: List[Stakeholder] = []
        if stakeholders_ext and stakeholders_ext.stakeholders:
            stakeholders = list(stakeholders_ext.stakeholders)
            # Ensure PMO Lead and Director, PMO exist
            has_pmo = any("pmo lead" in s.role.lower() for s in stakeholders)
            has_dir = any("director" in s.role.lower() and "pmo" in s.role.lower() for s in stakeholders)
            if not has_pmo:
                stakeholders.insert(0, Stakeholder(
                    name=pmo_lead_name,
                    role="PMO Lead",
                    organization="Toptal PMO",
                    decision_rights="G-01 Gate Sign-off, Talent Staffing/Replacement, Work-at-Risk Approvals, Delivery Risk & Recovery",
                    approver_responsibilities="G-01 Gate, Baseline Exceptions, PMO Health Ratings, Talent Baseline Sign-off",
                    escalation_responsibility="Director, PMO",
                    reporting_accountability="Independent Weekly Health Rating, Leadership Rollup"
                ))
            if not has_dir:
                stakeholders.insert(1, Stakeholder(
                    name=dir_pmo_name,
                    role="Director, PMO",
                    organization="Toptal PMO Leadership",
                    decision_rights="Elevated Tier Approvals, Major Commercial Exception Sign-offs, Executive Escalations",
                    approver_responsibilities="Elevated Tier G-01 Concurrence, Governance Policy Exceptions",
                    escalation_responsibility="VP, Delivery / Executive Leadership",
                    reporting_accountability="Executive PMO Portfolio Review"
                ))
        else:
            stakeholders = [
                Stakeholder(
                    name=pmo_lead_name,
                    role="PMO Lead",
                    organization="Toptal PMO",
                    decision_rights="G-01 Gate Sign-off, Talent Staffing/Replacement, Work-at-Risk Approvals, Delivery Risk & Recovery",
                    approver_responsibilities="G-01 Gate, Baseline Exceptions, PMO Health Ratings, Talent Baseline Sign-off",
                    escalation_responsibility="Director, PMO",
                    reporting_accountability="Independent Weekly Health Rating, Leadership Rollup"
                ),
                Stakeholder(
                    name=dir_pmo_name,
                    role="Director, PMO",
                    organization="Toptal PMO Leadership",
                    decision_rights="Elevated Tier Approvals, Major Commercial Exception Sign-offs, Executive Escalations",
                    approver_responsibilities="Elevated Tier G-01 Concurrence, Governance Policy Exceptions",
                    escalation_responsibility="VP, Delivery / Executive Leadership",
                    reporting_accountability="Executive PMO Portfolio Review"
                ),
                Stakeholder(
                    name=charter.delivery_manager or "[UNASSIGNED - TO BE CONFIRMED]",
                    role="Delivery Manager",
                    organization="Toptal",
                    decision_rights="Voice of the customer, scope accountability, client alignment",
                    approver_responsibilities="Scope change alignment, handoff readiness",
                    escalation_responsibility="PMO Lead",
                    reporting_accountability="Weekly PSR Review"
                ),
                Stakeholder(
                    name=charter.talent_pm or "[UNASSIGNED - TO BE CONFIRMED]",
                    role="Talent PM",
                    organization="Toptal",
                    decision_rights="Project delivery, sprint coordination, day-to-day execution",
                    approver_responsibilities="Work package progress, deliverable submission drafts",
                    escalation_responsibility="Delivery Manager",
                    reporting_accountability="Weekly PSR Author"
                ),
                Stakeholder(
                    name=charter.client_name or "[CLIENT SPONSOR - TO BE CONFIRMED]",
                    role="Client Sponsor / Approver",
                    organization="Client",
                    decision_rights="Contractual approvals, deliverable sign-offs, change orders",
                    approver_responsibilities="Deliverables acceptance, scope amendments",
                    escalation_responsibility="Client Executive Leadership",
                    reporting_accountability="Recipient of Weekly PSR & MBR"
                )
            ]

        raci_matrix = [
            RACIItem(decision_or_activity="Startup readiness (G-01 gate)", pmo_lead="R, A", delivery_manager="C", talent_pm="C", sales_accounts="C", client="I"),
            RACIItem(decision_or_activity="Talent staffing & replacement", pmo_lead="R, A", delivery_manager="C", talent_pm="C", sales_accounts="C", client="I"),
            RACIItem(decision_or_activity="Work at risk / commercial exceptions", pmo_lead="R, A", delivery_manager="I", talent_pm="I", sales_accounts="C", client="I"),
            RACIItem(decision_or_activity="Scope & change", pmo_lead="R", delivery_manager="A", talent_pm="—", sales_accounts="C, R", client="A"),
            RACIItem(decision_or_activity="Delivery risk & recovery", pmo_lead="R, A", delivery_manager="C", talent_pm="R", sales_accounts="I", client="I"),
        ]

        # 12. Build Commercial Guardrails (Layer 3)
        if commercial_ext and commercial_ext.commercial_guardrails:
            commercial_guardrails = commercial_ext.commercial_guardrails
        elif charter.contract_type == "Fixed Bid":
            commercial_guardrails = CommercialGuardrail(
                contract_type_implication="Fixed Bid contract: Fixed Price engagement with milestone-linked delivery gates.",
                billing_consumption_assumption="Fixed Price milestone billing upon formal client gate sign-off.",
                staffing_assumption="Delivery team staffed by Toptal across scheduled milestone windows.",
                commercial_exposure_note="Delivery delays directly erode project margin. Scope creep without Change Order is prohibited.",
                approved_work_rule="Approved work is strictly defined by SOW deliverables. Any out-of-scope tasks require formal Change Order.",
                non_approved_work_rule="Zero execution of out-of-scope requests without executed Change Order.",
                work_at_risk_rule="Work-at-risk strictly forbidden on Fixed Bid without written PMO Lead and Director sign-off.",
                change_control_trigger="Any requirement change, client delay > 3 days, or deliverable rework exceeding standard window.",
                change_order_route="PMO Lead leads -> DM aligns client -> Client approves -> Contracting issues change order.",
                budget_baseline="[CONFIRMATION REQUIRED - CONTRACT FIXED PRICE]",
                variance_indicator="Green (<5% scope variance)",
                margin_risk_indicator="Medium" if charter.governance_tier == "Elevated" else "Low",
                escalation_threshold="Milestone slip > 3 days or client acceptance rejection."
            )
        else:
            commercial_guardrails = CommercialGuardrail(
                contract_type_implication="Time and Materials contract: Emphasizes burn visibility, weekly timesheet oversight, staffing allocation efficiency, and customer dependency tracking.",
                billing_consumption_assumption="Weekly timesheet approval and hourly/daily burn rate tracking against budget cap.",
                staffing_assumption="Dedicated talent staffing as agreed; rate card billing per active role.",
                commercial_exposure_note="Client dependency delays must be logged immediately to prevent unfunded team standby burn.",
                approved_work_rule="Work executed according to prioritized backlog agreed in weekly check-ins.",
                non_approved_work_rule="Tasks exceeding agreed monthly burn ceiling require client written authorization.",
                work_at_risk_rule="Work-at-risk requires PMO Lead confirmation if PO or budget ceiling is exhausted.",
                change_control_trigger="Budget burndown exceeding forecast by >10% or scope change requiring talent roster adjustments.",
                change_order_route="PMO Lead leads -> DM aligns client -> Client approves -> Contracting issues change order.",
                budget_baseline=f"${250000:,} USD Budget Cap" if (charter.delivery_manager and "UNASSIGNED" not in charter.delivery_manager and charter.talent_pm and "UNASSIGNED" not in charter.talent_pm) else "[CONFIRMATION REQUIRED - T&M BUDGET CAP]",
                variance_indicator="Green (<5% variance)",
                margin_risk_indicator="Low",
                escalation_threshold="Burn rate variance > 10% or client dependency blocker > 2 days."
            )

        # 13. Build Talent Onboarding Record (Layer 3)
        ext_roster = getattr(talent_ext, "delivery_talent_roster", None) if talent_ext else None
        ext_onboarding = talent_ext.talent_onboarding if talent_ext else None
        if ext_onboarding or ext_roster:
            talent_onboarding = ext_onboarding or TalentOnboardingRecord(
                talent_pm=charter.talent_pm or "[UNASSIGNED - TO BE CONFIRMED]",
                delivery_manager=charter.delivery_manager or "[UNASSIGNED - TO BE CONFIRMED]",
                pmo_lead=pmo_lead_name,
                delivery_talent_roster=list(ext_roster) if ext_roster else [],
            )
            if ext_roster and not talent_onboarding.delivery_talent_roster:
                talent_onboarding.delivery_talent_roster = list(ext_roster)
            if charter.delivery_manager:
                talent_onboarding.delivery_manager = charter.delivery_manager
            if charter.talent_pm:
                talent_onboarding.talent_pm = charter.talent_pm
            if charter.pmo_lead:
                talent_onboarding.pmo_lead = charter.pmo_lead
            if talent_onboarding.delivery_talent_roster:
                for tm in talent_onboarding.delivery_talent_roster:
                    if tm.role.lower() in ("delivery manager", "delivery lead"):
                        if "UNASSIGNED" in str(charter.delivery_manager).upper() or not charter.delivery_manager:
                            tm.name = charter.delivery_manager or "[UNASSIGNED - TO BE CONFIRMED]"
                            tm.status = "Staffing Required"
                    elif tm.role.lower() in ("talent pm", "project manager"):
                        if "UNASSIGNED" in str(charter.talent_pm).upper() or not charter.talent_pm:
                            tm.name = charter.talent_pm or "[UNASSIGNED - TO BE CONFIRMED]"
                            tm.status = "Staffing Required"
        else:
            talent_onboarding = TalentOnboardingRecord(
                talent_pm=charter.talent_pm or "[UNASSIGNED - TO BE CONFIRMED]",
                delivery_manager=charter.delivery_manager or "[UNASSIGNED - TO BE CONFIRMED]",
                pmo_lead=pmo_lead_name,
                onboarding_completion_date=None,
                onboarding_attendees=[
                    pmo_lead_name,
                    charter.delivery_manager or "Delivery Manager",
                    charter.talent_pm or "Talent PM"
                ],
                artifacts_walked_through=[
                    "Startup Readiness Checklist (G-01)",
                    "Project Startup Charter",
                    "Scope & Baseline Interpretation Summary",
                    "Milestone Delivery Plan",
                    "Scope Decomposition / Backlog Seed",
                    "Deliverables and Acceptance Matrix",
                    "Dependency and Assumption Log",
                    "RAID Log & Decision Log Seed",
                    "Communications and Reporting Plan",
                    "Stakeholder and Responsibility Model (including PMO)",
                    "RACI / Decision Rights Matrix",
                    "Commercial and Margin Guardrails"
                ],
                delivery_talent_roster=[
                    TalentMember(
                        role="Delivery Manager",
                        name=charter.delivery_manager or "[UNASSIGNED - TO BE CONFIRMED]",
                        required_skills="Delivery Governance, Client Management",
                        status="Confirmed" if charter.delivery_manager and "UNASSIGNED" not in charter.delivery_manager else "Staffing Required"
                    ),
                    TalentMember(
                        role="Talent PM",
                        name=charter.talent_pm or "[UNASSIGNED - TO BE CONFIRMED]",
                        required_skills="Agile Coordination, PMO Delivery",
                        status="Confirmed" if charter.talent_pm and "UNASSIGNED" not in charter.talent_pm else "Staffing Required"
                    ),
                    TalentMember(
                        role="Technical Lead / Senior Engineer",
                        name="Technical Lead" if (charter.delivery_manager and "UNASSIGNED" not in charter.delivery_manager and charter.talent_pm and "UNASSIGNED" not in charter.talent_pm) else "[UNASSIGNED - TO BE CONFIRMED]",
                        required_skills="Architecture, Cloud Infrastructure, CI/CD",
                        status="Confirmed" if (charter.delivery_manager and "UNASSIGNED" not in charter.delivery_manager and charter.talent_pm and "UNASSIGNED" not in charter.talent_pm) else "Staffing Required"
                    )
                ],
                required_roles=["Delivery Manager", "Talent PM", "Technical Lead / Senior Engineer"],
                required_skills=["Cloud Architecture", "Agile Execution", "DevOps / CI/CD", "Stakeholder Governance"],
                staffing_gaps=[
                    "Delivery team staffing roster to be confirmed during Readiness."
                ] if any("UNASSIGNED" in str(x) for x in [charter.delivery_manager, charter.talent_pm]) else [],
                replacement_plan="PMO Lead coordinates talent matching within 5 business days if replacement needed.",
                team_baseline_review_confirmation=True
            )

        # 14. 1-Day Creation SLA Tracking & Segregation of Duties
        awarded_dt = sow_awarded_date or (date.today() - timedelta(days=1))
        drafted_dt = kit_drafted_date or date.today()
        sla_met = (drafted_dt - awarded_dt).days <= 1

        author_name = pmo_lead_name
        dm_name = charter.delivery_manager or "Delivery Manager"
        tech_lead_name = "Technical Lead"
        reviewer_names = [dm_name, tech_lead_name]
        approver_name = author_name
        concurring_approver = dir_pmo_name if charter.governance_tier == "Elevated" else None
        segregation_verified = (author_name not in reviewer_names)

        # 15. Build G-01 Startup Readiness Checklist
        has_unconfirmed_delivs = any(d.acceptance_criteria is None for d in deliverables)
        has_unconfirmed_dates = any(m.external_date is None for m in milestones)
        has_unassigned_roles = any("UNASSIGNED" in str(x) for x in [charter.delivery_manager, charter.talent_pm])
        has_ambiguities = len(contract_ambiguities) > 0

        readiness_checklist = [
            ReadinessChecklistItem(
                item_id="G01-01",
                gate_criterion="Startup Kit created within 1 day of delivery handoff (SLA)",
                related_section4_artifact="Project Startup Charter",
                owner=author_name,
                status="Complete" if sla_met else "Exception Required",
                evidence=f"Startup Kit drafted on {drafted_dt.strftime('%Y-%m-%d')} (Project awarded {awarded_dt.strftime('%Y-%m-%d')}). SLA {'Met' if sla_met else 'Breached'}.",
                exception_required=not sla_met,
                exception_details="Startup Kit creation exceeded 1 business day SLA." if not sla_met else None,
                approval_status="Approved" if sla_met else "Exception Required"
            ),
            ReadinessChecklistItem(
                item_id="G01-02",
                gate_criterion="Governance tier assigned and cadence established",
                related_section4_artifact="Project Startup Charter",
                owner=author_name,
                status="Complete",
                evidence=f"Governance Tier confirmed as '{charter.governance_tier}' with tailored buffers and reporting.",
                approval_status="Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-03",
                gate_criterion="Deliverables mapped to owners with explicit acceptance routes",
                related_section4_artifact="Deliverables and Acceptance Matrix",
                owner=charter.talent_pm or "Talent PM",
                status="Review Required" if has_unconfirmed_delivs else "Complete",
                evidence=f"{len(deliverables)} deliverables mapped to acceptance routes and evidence expectations.",
                exception_required=has_unconfirmed_delivs,
                exception_details="Unstated acceptance criteria or unassigned owners flagged for client confirmation." if has_unconfirmed_delivs else None,
                approval_status="Pending Review" if has_unconfirmed_delivs else "Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-04",
                gate_criterion="Milestone delivery plan with external dates and internal buffers committed",
                related_section4_artifact="Milestone Delivery Plan",
                owner=dm_name,
                status="Confirmation Required" if has_unconfirmed_dates else "Complete",
                evidence=f"{len(milestones)} milestones mapped with external dates and internal buffer calculations.",
                exception_required=has_unconfirmed_dates,
                exception_details="Uncommitted milestone dates require client confirmation." if has_unconfirmed_dates else None,
                approval_status="Pending Confirmation" if has_unconfirmed_dates else "Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-05",
                gate_criterion="Risks, Assumptions, Issues, and Dependencies seeded and owned",
                related_section4_artifact="RAID Log",
                owner=charter.talent_pm or "Talent PM",
                status="Review Required" if any(r.owner in ("Unassigned", "[UNASSIGNED - TO BE CONFIRMED]") for r in raid_items) else "Complete",
                evidence=f"{len(raid_items)} RAID items and {len(dependencies_assumptions)} dependencies/assumptions baselined.",
                exception_required=any(r.owner in ("Unassigned", "[UNASSIGNED - TO BE CONFIRMED]") for r in raid_items),
                exception_details="RAID log items or dependencies pending owner assignment." if any(r.owner in ("Unassigned", "[UNASSIGNED - TO BE CONFIRMED]") for r in raid_items) else None,
                approval_status="Pending Review" if any(r.owner in ("Unassigned", "[UNASSIGNED - TO BE CONFIRMED]") for r in raid_items) else "Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-06",
                gate_criterion="Talent PM and DM briefed on governance cadence and KO decks",
                related_section4_artifact="Talent Onboarding Record",
                owner=author_name,
                status="In Progress" if has_unassigned_roles else "Complete",
                evidence="Talent onboarding walkthrough session mapped against Section 4 artifacts.",
                exception_required=has_unassigned_roles,
                exception_details="Talent PM / Delivery Manager onboarding briefing pending." if has_unassigned_roles else None,
                approval_status="Pending Review" if has_unassigned_roles else "Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-07",
                gate_criterion="Client onboarding dependencies and prerequisites mapped",
                related_section4_artifact="SOW Interpretation Summary",
                owner=dm_name,
                status="Review Required" if (not sow_summary.customer_obligations or "[CONFIRMATION REQUIRED]" in str(sow_summary.customer_obligations)) else "Complete",
                evidence=f"Customer obligations ({len(sow_summary.customer_obligations)}) and prerequisites documented.",
                exception_required=bool(not sow_summary.customer_obligations or "[CONFIRMATION REQUIRED]" in str(sow_summary.customer_obligations)),
                exception_details="Customer prerequisites and environment access pending confirmation." if (not sow_summary.customer_obligations or "[CONFIRMATION REQUIRED]" in str(sow_summary.customer_obligations)) else None,
                approval_status="Pending Confirmation" if (not sow_summary.customer_obligations or "[CONFIRMATION REQUIRED]" in str(sow_summary.customer_obligations)) else "Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-08",
                gate_criterion="Talent roster staffed with named leads and delivery talent",
                related_section4_artifact="Talent Onboarding Record",
                owner=charter.talent_pm or "Talent PM",
                status="In Progress" if has_unassigned_roles else "Complete",
                evidence=f"{len(talent_onboarding.delivery_talent_roster)} delivery talent roles listed; {sum(1 for tm in talent_onboarding.delivery_talent_roster if tm.name and 'UNASSIGNED' not in tm.name.upper() and tm.name != 'Unassigned' and tm.status.lower() not in ('pending', 'needs alignment', 'unassigned', 'staffing required'))} named",
                exception_required=has_unassigned_roles,
                exception_details="Talent roster staffing in progress." if has_unassigned_roles else None,
                approval_status="Pending Review" if has_unassigned_roles else "Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-09",
                gate_criterion="Client sponsor and decision escalation path identified",
                related_section4_artifact="Stakeholder and Responsibility Model",
                owner=dm_name,
                status="Complete",
                evidence=f"{len(stakeholders)} key stakeholder roles (including PMO Lead & Director) and escalation paths identified.",
                approval_status="Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-10",
                gate_criterion="RACI and PMO decision rights matrix baselined",
                related_section4_artifact="RACI / Decision Rights Matrix",
                owner=author_name,
                status="Complete",
                evidence="Standard PMO decision rights and AR-10 accountability model baselined.",
                approval_status="Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-11",
                gate_criterion="Communications and reporting plan cadence defined",
                related_section4_artifact="Communications and Reporting Plan",
                owner=charter.talent_pm or "Talent PM",
                status="Complete",
                evidence=f"Weekly check-in, weekly PSR, and MBR cadence defined for {charter.governance_tier} tier.",
                approval_status="Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-12",
                gate_criterion="Commercial guardrails and margin protections established",
                related_section4_artifact="Commercial and Margin Guardrails",
                owner=author_name,
                status="Complete",
                evidence=f"Commercial controls and work-at-risk rules defined for {charter.contract_type}.",
                approval_status="Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-13",
                gate_criterion="Change control procedure and written sign-off route defined",
                related_section4_artifact="Change Control Procedure",
                owner=author_name,
                status="Complete",
                evidence="Formal Change Order route and threshold rules configured.",
                approval_status="Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-14",
                gate_criterion="Contractual ambiguities and conflicts logged with risk-impact mitigations",
                related_section4_artifact="Contract Ambiguity & Conflict Analysis",
                owner=author_name,
                status="Complete",
                evidence="No contractual ambiguities flagged.",
                exception_required=False,
                exception_details=None,
                approval_status="Approved"
            ),
            ReadinessChecklistItem(
                item_id="G01-15",
                gate_criterion="Unresolved ambiguities and open questions listed",
                related_section4_artifact="Startup Readiness Checklist",
                owner=author_name,
                status="Review Required" if questions else "Complete",
                evidence=f"{len(questions)} validation points logged for mobilization confirmation.",
                approval_status="Pending Review" if questions else "Approved"
            ),
        ]

        # 16. Calculate Startup Readiness Score and Gate Decision via ReadinessScoringEngine
        initial_baseline = StartupKitBaseline(
            project_name=charter_obj.project_name,
            governance_tier=charter_obj.governance_tier,
            contract_type=charter_obj.contract_type,
            charter=charter_obj,
            sow_interpretation=sow_summary,
            deliverables=deliverables,
            milestones=milestones,
            backlog_seed=backlog_seed,
            dependencies_assumptions=dependencies_assumptions,
            raid_items=raid_items,
            decisions=decisions,
            communications_plan=communications_plan,
            stakeholders=stakeholders,
            raci_matrix=raci_matrix,
            commercial_guardrails=commercial_guardrails,
            talent_onboarding=talent_onboarding,
            readiness_checklist=readiness_checklist,
            open_questions=questions,
            contract_ambiguities=contract_ambiguities,
            sow_stories_catalogue=sow_stories_catalogue,
            sow_awarded_date=awarded_dt,
            kit_drafted_date=drafted_dt,
            sla_met=sla_met,
            author_name=author_name,
            reviewer_names=reviewer_names,
            approver_name=approver_name,
            concurring_approver_name=concurring_approver,
            segregation_of_duties_verified=segregation_verified,
        )

        # Synchronize checklist items with baseline artifacts state
        ReadinessScoringEngine.synchronize_checklist_with_artifacts(initial_baseline)

        composite_score, readiness_breakdown = ReadinessScoringEngine.compute_scores(initial_baseline)
        open_exceptions = [i for i in initial_baseline.readiness_checklist if i.exception_required or i.status == "Exception Required"]

        gate_decision, workflow_state = ReadinessScoringEngine.determine_gate_decision(
            composite_score=composite_score,
            open_exceptions_count=len(open_exceptions),
            has_questions=bool(questions),
            sla_met=sla_met,
            segregation_verified=segregation_verified,
            author_name=author_name,
            reviewer_names=reviewer_names,
            concurring_approver=concurring_approver,
            comments_prefix="Readiness baseline verified against Section 4 requirements.",
        )
        gate_decision.readiness_breakdown = readiness_breakdown

        initial_baseline.readiness_score = composite_score
        initial_baseline.readiness_breakdown = readiness_breakdown
        initial_baseline.workflow_state = workflow_state
        initial_baseline.gate_decision = gate_decision

        action_required_items = ReadinessScoringEngine.generate_action_required_items(initial_baseline)
        initial_baseline.action_required_items = action_required_items
        ReadinessScoringEngine.link_action_items_to_artifacts(initial_baseline)

        # 18. Build Governance Context (for backwards compatibility)
        gov_context = GovernanceContext(
            project_name=charter_obj.project_name,
            governance_tier=charter_obj.governance_tier,
            contract_type=charter_obj.contract_type,
            client_name=charter_obj.client_name,
            delivery_manager=charter_obj.delivery_manager,
            talent_pm=charter_obj.talent_pm,
            pmo_lead=charter_obj.pmo_lead,
            executive_summary=charter.executive_summary or charter_obj.project_purpose,
            workflow_state=workflow_state,
            sla_met=sla_met,
        )
        initial_baseline.governance_context = gov_context

        return initial_baseline

    def recalculate_readiness(self, baseline: StartupKitBaseline) -> StartupKitBaseline:
        """Recalculate dimensional readiness scores and G-01 Gate Decision for an existing or updated baseline."""
        ReadinessScoringEngine.synchronize_open_questions_with_artifacts(baseline)

        # Synchronize checklist items with baseline data state using the unified engine method
        ReadinessScoringEngine.synchronize_checklist_with_artifacts(baseline)

        pmo_val = (
            (baseline.charter.pmo_lead if baseline.charter else None)
            or (baseline.talent_onboarding.pmo_lead if baseline.talent_onboarding else None)
            or baseline.author_name
            or "PMO Lead"
        )
        dm_val = (
            (baseline.charter.delivery_manager if baseline.charter else None)
            or (baseline.talent_onboarding.delivery_manager if baseline.talent_onboarding else None)
            or "Delivery Manager"
        )
        tier_val = baseline.governance_tier or (baseline.charter.governance_tier if baseline.charter else "Partnered")
        dir_pmo_name = "Director, PMO"
        author_name = pmo_val
        reviewer_names = [dm_val, "Technical Lead"]
        concurring_approver = dir_pmo_name if tier_val == "Elevated" else None
        segregation_verified = (author_name not in reviewer_names)

        # Delegate scoring to ReadinessScoringEngine
        composite_score, readiness_breakdown = ReadinessScoringEngine.compute_scores(baseline)
        open_exceptions = [
            i for i in baseline.readiness_checklist if i.exception_required or i.status == "Exception Required"
        ]

        gate_decision, workflow_state = ReadinessScoringEngine.determine_gate_decision(
            composite_score=composite_score,
            open_exceptions_count=len(open_exceptions),
            has_questions=bool(baseline.open_questions),
            sla_met=baseline.sla_met,
            segregation_verified=segregation_verified,
            author_name=author_name,
            reviewer_names=reviewer_names,
            concurring_approver=concurring_approver,
            comments_prefix="Readiness baseline recalculated against Section 4 requirements.",
        )
        gate_decision.readiness_breakdown = readiness_breakdown

        baseline.readiness_score = composite_score
        baseline.readiness_breakdown = readiness_breakdown
        baseline.workflow_state = workflow_state
        baseline.gate_decision = gate_decision
        baseline.author_name = author_name
        baseline.reviewer_names = reviewer_names
        baseline.approver_name = author_name
        baseline.concurring_approver_name = concurring_approver
        baseline.segregation_of_duties_verified = segregation_verified
        if baseline.governance_context:
            baseline.governance_context.workflow_state = workflow_state

        action_required_items = ReadinessScoringEngine.generate_action_required_items(baseline)
        baseline.action_required_items = action_required_items
        ReadinessScoringEngine.link_action_items_to_artifacts(baseline)

        return baseline
