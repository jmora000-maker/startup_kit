"""Deterministic parser extracting StartupKitBaseline from an existing Startup Kit Word (.docx) document."""

import re
import logging
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

import docx
from docx.table import Table, _Cell

from src.core.interfaces import IStartupKitDocxParser
from src.core.models import (
    StartupKitBaseline,
    ProjectStartupCharter,
    Deliverable,
    Milestone,
    RiskAssumption,
    DependencyAssumptionItem,
    DecisionItem,
    WorkPackageSeed,
    Stakeholder,
    RACIItem,
    CommunicationsPlanItem,
    CommercialGuardrail,
    TalentOnboardingRecord,
    TalentMember,
    ReadinessChecklistItem,
    GateDecision,
    GovernanceContext,
    SourceReference,
    SOWInterpretationSummary,
    ContractAmbiguityItem,
)

logger = logging.getLogger(__name__)


def parse_date_safely(date_str: Optional[str]) -> Optional[date]:
    """Parse date from string with multiple format attempts; returns None on failure/placeholder."""
    if not date_str:
        return None
    cleaned = date_str.strip()
    if cleaned.upper() in ("", "NONE", "N/A", "TBD", "TO BE DETERMINED", "[CONFIRMATION REQUIRED]", "UNASSIGNED"):
        return None

    # Strip day names or extra notes like "(Day 5)"
    cleaned = re.sub(r'\(.*?\)', '', cleaned).strip()

    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue

    # Try regex match for YYYY-MM-DD anywhere in string
    match = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', cleaned)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass

    return None


class StartupKitDocxParser(IStartupKitDocxParser):
    """Deterministic parser extracting StartupKitBaseline from an existing *_Startup_Kit.docx file."""

    def parse_startup_kit_docx(self, file_path: Path) -> StartupKitBaseline:
        """Parse an existing *_Startup_Kit.docx file into a StartupKitBaseline model."""
        if not file_path.exists():
            raise FileNotFoundError(f"Startup Kit Word document not found at: {file_path}")

        if file_path.suffix.lower() != ".docx":
            raise ValueError(f"Target file must be a .docx file: {file_path}")

        try:
            doc = docx.Document(str(file_path))
        except Exception as e:
            raise ValueError(f"Failed to open Word document {file_path}: {e}") from e

        # Validate basic Startup Kit document signature
        all_text = " ".join(p.text for p in doc.paragraphs)
        tables = doc.tables
        if not tables:
            raise ValueError(f"Ingested Word document does not match expected Startup Kit schema: No tables found in {file_path}")

        # Extract Project Name from subtitle or paragraphs
        project_name = self._extract_project_name(doc)

        # 1. Metadata Header Table
        meta_dict = self._parse_metadata_table(tables)
        if not meta_dict and "STARTUP KIT" not in all_text.upper():
            raise ValueError(f"Ingested Word document does not match expected Startup Kit schema: Missing Startup Kit metadata table in {file_path}")

        project_name = meta_dict.get("project_name") or project_name or "Project"
        client_name = meta_dict.get("client_name") or "[Client Sponsor]"
        governance_tier = meta_dict.get("governance_tier") or "Partnered"
        if governance_tier not in ("Guided", "Partnered", "Elevated"):
            governance_tier = "Partnered"
        contract_type = meta_dict.get("contract_type") or "Time and Materials"
        delivery_manager = meta_dict.get("delivery_manager") or "[UNASSIGNED - TO BE CONFIRMED]"
        talent_pm = meta_dict.get("talent_pm") or "[UNASSIGNED - TO BE CONFIRMED]"
        pmo_lead = meta_dict.get("pmo_lead") or "[UNASSIGNED - TO BE CONFIRMED]"
        sla_met = meta_dict.get("sla_met", True)
        workflow_state = meta_dict.get("workflow_state") or "Ready for G-01 Gate Review"

        src_ref = SourceReference(
            document_name=file_path.name,
            clause_or_slide="Section 4 Baseline",
            confidence_score=1.0
        )

        # 2. Open Questions & Clarifications
        open_questions = self._parse_open_questions(doc)

        # 3. G-01 Checklist Table
        readiness_checklist = self._parse_g01_table(tables, pmo_lead, src_ref)

        # 4. Project Startup Charter
        charter = self._parse_charter(doc, tables, project_name, client_name, governance_tier, contract_type, delivery_manager, talent_pm, pmo_lead, src_ref)

        # 5. SOW Interpretation Summary & Contract Ambiguities
        sow_interpretation, contract_ambiguities = self._parse_sow_interpretation(tables, src_ref)

        # 6. Milestone Delivery Plan
        milestones = self._parse_milestones_table(tables, delivery_manager, src_ref)

        # 7. Scope Decomposition / Backlog Seed
        backlog_seed = self._parse_backlog_table(tables)

        # 8. Deliverables & Acceptance Matrix
        deliverables = self._parse_deliverables_table(tables, src_ref)

        # 9. RAID Items & Decisions
        raid_items, decisions = self._parse_raid_and_decisions_tables(tables, src_ref)

        # 10. Communications Plan
        communications_plan = self._parse_communications_table(tables)

        # 11. Stakeholders & RACI Matrix
        stakeholders, raci_matrix = self._parse_stakeholders_and_raci(tables)

        # 12. Commercial Guardrails
        commercial_guardrails = self._parse_commercial_guardrails(doc, contract_type, src_ref)

        # 13. Talent Onboarding Record & Delivery Roster
        talent_onboarding = self._parse_talent_onboarding(doc, tables, pmo_lead, delivery_manager, talent_pm, src_ref)

        # Build Governance Context
        gov_context = GovernanceContext(
            project_name=project_name,
            governance_tier=governance_tier,
            contract_type=contract_type,
            client_name=client_name,
            delivery_manager=delivery_manager,
            talent_pm=talent_pm,
            pmo_lead=pmo_lead,
            executive_summary=charter.project_purpose,
            workflow_state=workflow_state,
            sla_met=sla_met
        )

        # Build baseline (scores and gate decision will be recalculated by aggregator)
        gate_decision = GateDecision(
            decision_status="Pending",
            target_mobilize_date=date.today(),
            tier_description=governance_tier,
            readiness_score=0.0,
            workflow_state=workflow_state,
            sla_met=sla_met,
            author_name=pmo_lead
        )

        return StartupKitBaseline(
            project_name=project_name,
            governance_tier=governance_tier,
            contract_type=contract_type,
            governance_context=gov_context,
            charter=charter,
            sow_interpretation=sow_interpretation,
            deliverables=deliverables,
            milestones=milestones,
            backlog_seed=backlog_seed,
            dependencies_assumptions=[
                DependencyAssumptionItem(
                    id=r.id,
                    type="Dependency" if r.type == "Dependency" else "Assumption",
                    description=r.description,
                    source_reference=src_ref,
                    owner=r.owner,
                    status=r.status
                )
                for r in raid_items if r.type in ("Assumption", "Dependency")
            ],
            raid_items=raid_items,
            decisions=decisions,
            communications_plan=communications_plan,
            stakeholders=stakeholders,
            raci_matrix=raci_matrix,
            commercial_guardrails=commercial_guardrails,
            talent_onboarding=talent_onboarding,
            readiness_checklist=readiness_checklist,
            gate_decision=gate_decision,
            open_questions=open_questions,
            contract_ambiguities=contract_ambiguities,
            readiness_score=0.0,
            workflow_state=workflow_state,
            sow_awarded_date=date.today(),
            kit_drafted_date=date.today(),
            sla_met=sla_met,
            author_name=pmo_lead
        )

    # -------------------------------------------------------------------------
    # Helper Extraction Methods
    # -------------------------------------------------------------------------

    def _extract_project_name(self, doc: docx.Document) -> str:
        """Extract project name from subtitle run or paragraphs."""
        for p in doc.paragraphs:
            text = p.text.strip()
            if text.startswith("Project Baseline:"):
                return text.replace("Project Baseline:", "").strip()
        return "Project"

    def _parse_metadata_table(self, tables: List[Table]) -> Dict[str, Any]:
        """Extract key metadata properties from the top header table."""
        res: Dict[str, Any] = {}
        for tbl in tables:
            # Metadata table is typically 4 columns and contains 'Project Name' or 'Governance Tier'
            full_tbl_text = " ".join(c.text for row in tbl.rows for c in row.cells).lower()
            if "governance tier" in full_tbl_text and "project name" in full_tbl_text:
                for row in tbl.rows:
                    cells = [c.text.strip() for c in row.cells]
                    if len(cells) >= 4:
                        # Pairs: (cells[0], cells[1]), (cells[2], cells[3])
                        k1, v1 = cells[0].lower(), cells[1]
                        k2, v2 = cells[2].lower(), cells[3]
                        self._map_meta_field(res, k1, v1)
                        self._map_meta_field(res, k2, v2)
                    elif len(cells) >= 2:
                        k1, v1 = cells[0].lower(), cells[1]
                        self._map_meta_field(res, k1, v1)
                break
        return res

    def _map_meta_field(self, res: Dict[str, Any], label: str, value: str) -> None:
        """Map label string to dictionary key."""
        label_clean = label.replace(":", "").strip()
        if "project name" in label_clean:
            res["project_name"] = value
        elif "client sponsor" in label_clean or "client" in label_clean:
            res["client_name"] = value
        elif "governance tier" in label_clean:
            res["governance_tier"] = value
        elif "contract type" in label_clean:
            res["contract_type"] = value
        elif "delivery manager" in label_clean or "delivery lead" in label_clean:
            res["delivery_manager"] = value
        elif "talent pm" in label_clean:
            res["talent_pm"] = value
        elif "pmo lead" in label_clean:
            res["pmo_lead"] = value
        elif "1-day sla status" in label_clean or "sla status" in label_clean:
            res["sla_met"] = not ("breached" in value.lower())
        elif "workflow state" in label_clean:
            res["workflow_state"] = value

    def _parse_open_questions(self, doc: docx.Document) -> List[str]:
        """Extract unresolved open questions from warning callout boxes or paragraphs."""
        questions: List[str] = []
        in_questions_section = False

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue

            if "Unresolved Validation Points" in text or "Clarifications Pending Mobilize" in text or "Open Questions & Clarifications" in text:
                in_questions_section = True
                continue

            # Section headings end questions collection
            if in_questions_section and (text.startswith("Layer ") or text.startswith("Executive Readiness Gateway") or text.startswith("1.") or text.startswith("2.")):
                in_questions_section = False
                continue

            if in_questions_section:
                # Split lines
                for line in text.split("\n"):
                    l_clean = line.strip()
                    if l_clean.startswith("•") or l_clean.startswith("-") or l_clean.startswith("*"):
                        q_text = re.sub(r'^[•\-\*]\s*', '', l_clean).strip()
                        # If explicitly resolved, skip it
                        if q_text and "[RESOLVED]" not in q_text.upper():
                            questions.append(q_text)
                    elif l_clean and not l_clean.startswith("Action Required:"):
                        if "[RESOLVED]" not in l_clean.upper():
                            questions.append(l_clean)

        return questions

    def _find_table_by_header(self, tables: List[Table], header_keywords: List[str]) -> Optional[Table]:
        """Locate table whose header row matches given keyword criteria."""
        for tbl in tables:
            if not tbl.rows:
                continue
            header_text = " ".join(c.text.lower() for c in tbl.rows[0].cells)
            if all(kw.lower() in header_text for kw in header_keywords):
                return tbl
        return None

    def _parse_g01_table(self, tables: List[Table], pmo_lead: str, src_ref: SourceReference) -> List[ReadinessChecklistItem]:
        """Parse G-01 Checklist table from Executive Gateway section."""
        items: List[ReadinessChecklistItem] = []
        tbl = self._find_table_by_header(tables, ["gate id", "gate criterion", "status"])
        if not tbl:
            # Try alternate header: "item id", "criterion"
            tbl = self._find_table_by_header(tables, ["criterion", "status", "owner"])

        if not tbl:
            return items

        # Column indices
        header_cells = [c.text.strip().lower() for c in tbl.rows[0].cells]
        id_idx = next((i for i, h in enumerate(header_cells) if "id" in h), 0)
        crit_idx = next((i for i, h in enumerate(header_cells) if "criterion" in h), 1)
        art_idx = next((i for i, h in enumerate(header_cells) if "artifact" in h), 2)
        status_idx = next((i for i, h in enumerate(header_cells) if "status" in h), 3)
        owner_idx = next((i for i, h in enumerate(header_cells) if "owner" in h), 4)
        rev_idx = next((i for i, h in enumerate(header_cells) if "reviewer" in h), 5)
        app_idx = next((i for i, h in enumerate(header_cells) if "approver" in h), 6)
        ev_idx = next((i for i, h in enumerate(header_cells) if "evidence" in h or "exception" in h), 7)

        for row in tbl.rows[1:]:
            cells = [c.text.strip() for c in row.cells]
            if len(cells) < 4:
                continue
            item_id = cells[id_idx] if id_idx < len(cells) else f"G01-{len(items)+1:02d}"
            criterion = cells[crit_idx] if crit_idx < len(cells) else ""
            artifact = cells[art_idx] if art_idx < len(cells) else ""
            status = cells[status_idx] if status_idx < len(cells) else "Review Required"
            owner = cells[owner_idx] if owner_idx < len(cells) else pmo_lead
            reviewer = cells[rev_idx] if rev_idx < len(cells) else "Delivery Manager"
            approver = cells[app_idx] if app_idx < len(cells) else pmo_lead
            ev_text = cells[ev_idx] if ev_idx < len(cells) else ""

            # Extract exception info if embedded
            exception_required = (status == "Exception Required")
            exception_details = None
            if "[EXCEPTION:" in ev_text:
                m = re.search(r'\[EXCEPTION:\s*(.*?)\]', ev_text)
                if m:
                    exception_details = m.group(1).strip()
                    exception_required = True
            elif exception_required:
                exception_details = ev_text

            items.append(ReadinessChecklistItem(
                item_id=item_id,
                gate_criterion=criterion,
                related_section4_artifact=artifact,
                owner=owner,
                reviewer=reviewer,
                approver=approver,
                status=status,
                evidence=ev_text,
                exception_required=exception_required,
                exception_details=exception_details,
                approval_status="Approved" if status in ("Complete", "Approved") else ("Exception Required" if exception_required else "Pending Review")
            ))

        return items

    def _parse_charter(
        self,
        doc: docx.Document,
        tables: List[Table],
        project_name: str,
        client_name: str,
        tier: str,
        contract_type: str,
        dm: str,
        tpm: str,
        pmo: str,
        src_ref: SourceReference
    ) -> ProjectStartupCharter:
        """Parse Charter details from paragraphs, callout boxes, and list items."""
        project_purpose = f"Delivery mobilization and execution of {project_name}."
        delivery_model = f"Toptal {tier} Managed Delivery"
        governance_model = f"PMO {tier} Governance Framework"
        escalation_path = f"Talent PM ({tpm}) -> Delivery Manager ({dm}) -> PMO Lead ({pmo}) -> Director, PMO"
        unresolved_assumptions = "Logged in Startup RAID log"
        delivery_objectives: List[str] = []
        success_criteria: List[str] = []
        exclusions: List[str] = []

        in_charter = False
        in_objectives = False
        in_exclusions = False

        for p in doc.paragraphs:
            t = p.text.strip()
            if not t:
                continue

            if "Project Startup Charter" in t or "Startup Charter & Delivery Purpose" in t:
                in_charter = True
                continue
            elif "SOW Interpretation Summary" in t or "Layer 2" in t:
                in_charter = False
                in_objectives = False
                in_exclusions = False
                continue

            if in_charter:
                if "Project Purpose:" in t:
                    m = re.search(r'Project Purpose:\s*(.*?)(?:\n|$)', t)
                    if m and m.group(1).strip():
                        project_purpose = m.group(1).strip()
                if "Delivery Model:" in t:
                    m = re.search(r'Delivery Model:\s*(.*?)(?:\s*\|\s*Governance Model:|$)', t)
                    if m and m.group(1).strip():
                        delivery_model = m.group(1).strip()
                if "Governance Model:" in t:
                    m = re.search(r'Governance Model:\s*(.*?)(?:\n|$)', t)
                    if m and m.group(1).strip():
                        governance_model = m.group(1).strip()
                if "Escalation Path:" in t:
                    m = re.search(r'Escalation Path:\s*(.*?)(?:\n|$)', t)
                    if m and m.group(1).strip():
                        escalation_path = m.group(1).strip()
                if "Unresolved Assumptions Status:" in t:
                    m = re.search(r'Unresolved Assumptions Status:\s*(.*?)(?:\n|$)', t)
                    if m and m.group(1).strip():
                        unresolved_assumptions = m.group(1).strip()

                if "Delivery Objectives & Success Criteria:" in t:
                    in_objectives = True
                    in_exclusions = False
                    continue
                elif "High-Level Scope Exclusions:" in t:
                    in_exclusions = True
                    in_objectives = False
                    continue

                if in_objectives:
                    clean_line = re.sub(r'^[•\-\*]\s*', '', t).strip()
                    if clean_line:
                        if clean_line.lower().startswith("success criteria:"):
                            success_criteria.append(re.sub(r'^success criteria:\s*', '', clean_line, flags=re.I).strip())
                        else:
                            delivery_objectives.append(clean_line)
                elif in_exclusions:
                    clean_line = re.sub(r'^[•\-\*]\s*', '', t).strip()
                    if clean_line:
                        exclusions.append(clean_line)

        return ProjectStartupCharter(
            project_name=project_name,
            client_name=client_name,
            governance_tier=tier,
            contract_type=contract_type,
            delivery_manager=dm,
            talent_pm=tpm,
            pmo_lead=pmo,
            project_purpose=project_purpose,
            delivery_model=delivery_model,
            governance_model=governance_model,
            escalation_path=escalation_path,
            unresolved_assumptions_status=unresolved_assumptions,
            delivery_objectives=delivery_objectives or [f"Deliver {project_name} within baseline commitments."],
            success_criteria=success_criteria or ["Formal client acceptance and sign-off."],
            high_level_scope=[f"Delivery scope defined in {project_name} SOW baseline."],
            exclusions=exclusions or ["Out-of-scope tasks defined in SOW."],
            source_reference=src_ref
        )

    def _parse_sow_interpretation(
        self,
        tables: List[Table],
        src_ref: SourceReference
    ) -> Tuple[SOWInterpretationSummary, List[ContractAmbiguityItem]]:
        """Parse SOW Interpretation summary table and contract ambiguities table."""
        contracted_delivs: List[str] = []
        exclusions: List[str] = []
        obligations: List[str] = []
        assumptions: List[str] = []
        constraints: List[str] = []
        platforms: List[str] = []
        dependencies: List[str] = []
        approval_expectations: Optional[str] = "Client sign-off required within 5 business days."
        ambiguity_notes: List[str] = []

        tbl = self._find_table_by_header(tables, ["sow interpretation dimension", "contractual summary"])
        if tbl:
            for row in tbl.rows[1:]:
                cells = [c.text.strip() for c in row.cells]
                if len(cells) < 2:
                    continue
                dim, val = cells[0].lower(), cells[1]
                items = [re.sub(r'^[•\-]\s*', '', line).strip() for line in val.split("\n") if line.strip()]

                if "deliverables" in dim:
                    contracted_delivs.extend(items)
                elif "exclusions" in dim or "out-of-scope" in dim:
                    exclusions.extend(items)
                elif "obligations" in dim or "prerequisites" in dim:
                    obligations.extend(items)
                elif "assumptions" in dim or "constraints" in dim:
                    assumptions.extend(items)
                elif "platform" in dim or "environment" in dim:
                    platforms.extend(items)
                elif "dependencies" in dim:
                    dependencies.extend(items)
                elif "approval" in dim or "acceptance" in dim:
                    approval_expectations = val
                elif "ambiguities" in dim:
                    ambiguity_notes.extend(items)

        # Parse contract ambiguities table
        ambiguities: List[ContractAmbiguityItem] = []
        amb_tbl = self._find_table_by_header(tables, ["ambiguity id", "clause / topic", "identified conflict"])
        if amb_tbl:
            for row in amb_tbl.rows[1:]:
                cells = [c.text.strip() for c in row.cells]
                if len(cells) >= 5:
                    ambiguities.append(ContractAmbiguityItem(
                        ambiguity_id=cells[0],
                        clause_or_topic=cells[1],
                        identified_conflict=cells[2],
                        operational_impact=cells[3],
                        recommended_alignment=cells[4]
                    ))

        summary = SOWInterpretationSummary(
            contracted_deliverables=contracted_delivs,
            out_of_scope_items=exclusions,
            customer_obligations=obligations,
            assumptions=assumptions,
            constraints=constraints,
            platform_environment_commitments=platforms,
            dependencies=dependencies,
            approval_expectations=approval_expectations,
            ambiguity_notes=ambiguity_notes,
            source_reference=src_ref
        )
        return summary, ambiguities

    def _parse_milestones_table(
        self,
        tables: List[Table],
        default_owner: str,
        src_ref: SourceReference
    ) -> List[Milestone]:
        """Parse Milestone Delivery Plan table."""
        milestones: List[Milestone] = []
        tbl = self._find_table_by_header(tables, ["milestone id", "description", "date"])
        if not tbl:
            tbl = self._find_table_by_header(tables, ["milestone", "date"])
        if not tbl:
            tbl = self._find_table_by_header(tables, ["milestone id", "description"])

        if not tbl:
            return milestones

        header_cells = [c.text.strip().lower() for c in tbl.rows[0].cells]
        id_idx = next((i for i, h in enumerate(header_cells) if "id" in h), 0)
        desc_idx = next((i for i, h in enumerate(header_cells) if "desc" in h or "name" in h or "milestone" in h), 1)
        ext_date_idx = next((i for i, h in enumerate(header_cells) if "target" in h or "external" in h), 2)
        buf_date_idx = next((i for i, h in enumerate(header_cells) if "buffer" in h or "internal" in h), 3)
        owner_idx = next((i for i, h in enumerate(header_cells) if "owner" in h), 4)
        dep_idx = next((i for i, h in enumerate(header_cells) if "dep" in h), 5)

        for row in tbl.rows[1:]:
            cells = [c.text.strip() for c in row.cells]
            if len(cells) < 2:
                continue
            m_id = cells[id_idx] if id_idx < len(cells) else f"M{len(milestones)+1:02d}"
            m_desc = cells[desc_idx] if desc_idx < len(cells) else ""
            ext_date_str = cells[ext_date_idx] if ext_date_idx < len(cells) else None
            buf_date_str = cells[buf_date_idx] if buf_date_idx < len(cells) else None
            owner = cells[owner_idx] if owner_idx < len(cells) else default_owner
            dep_str = cells[dep_idx] if dep_idx < len(cells) else ""

            milestones.append(Milestone(
                id=m_id,
                description=m_desc,
                external_date=parse_date_safely(ext_date_str),
                internal_buffer_date=parse_date_safely(buf_date_str),
                owner=owner or default_owner,
                key_dependencies=[d.strip() for d in dep_str.split(",") if d.strip()] if dep_str else [],
                source_reference=src_ref
            ))

        return milestones

    def _parse_backlog_table(self, tables: List[Table]) -> List[WorkPackageSeed]:
        """Parse Scope Decomposition / Backlog Seed table."""
        backlog: List[WorkPackageSeed] = []
        tbl = self._find_table_by_header(tables, ["wp id", "parent deliv", "work package title"])
        if not tbl:
            tbl = self._find_table_by_header(tables, ["work package", "parent", "status"])

        if not tbl:
            return backlog

        for row in tbl.rows[1:]:
            cells = [c.text.strip() for c in row.cells]
            if len(cells) >= 3:
                wp_id = cells[0]
                parent_id = cells[1]
                title = cells[2]
                seq = int(cells[3]) if len(cells) > 3 and cells[3].isdigit() else 1
                owner = cells[4] if len(cells) > 4 else "[UNASSIGNED - TO BE CONFIRMED]"
                status = cells[5] if len(cells) > 5 else "Draft"

                backlog.append(WorkPackageSeed(
                    id=wp_id,
                    parent_deliverable_id=parent_id,
                    title=title,
                    description=title,
                    preliminary_sequence=seq,
                    owner=owner,
                    status=status
                ))

        return backlog

    def _parse_deliverables_table(
        self,
        tables: List[Table],
        src_ref: SourceReference
    ) -> List[Deliverable]:
        """Parse Deliverables and Acceptance Matrix table."""
        deliverables: List[Deliverable] = []
        tbl = self._find_table_by_header(tables, ["deliverable name", "internal owner", "acceptance criteria"])
        if not tbl:
            tbl = self._find_table_by_header(tables, ["deliverable", "criteria", "approver"])

        if not tbl:
            return deliverables

        header_cells = [c.text.strip().lower() for c in tbl.rows[0].cells]
        id_idx = next((i for i, h in enumerate(header_cells) if "id" in h), 0)
        desc_idx = next((i for i, h in enumerate(header_cells) if "name" in h or "desc" in h or "deliverable" in h), 1)
        owner_idx = next((i for i, h in enumerate(header_cells) if "owner" in h), 2)
        crit_idx = next((i for i, h in enumerate(header_cells) if "criteria" in h or "acceptance" in h), 3)
        app_idx = next((i for i, h in enumerate(header_cells) if "approver" in h or "client" in h), 4)
        signoff_idx = next((i for i, h in enumerate(header_cells) if "sign-off" in h or "mechanism" in h or "review" in h), 5)

        for row in tbl.rows[1:]:
            cells = [c.text.strip() for c in row.cells]
            if len(cells) < 2:
                continue
            d_id = cells[id_idx] if id_idx < len(cells) else f"DEL-{len(deliverables)+1:02d}"
            d_name = cells[desc_idx] if desc_idx < len(cells) else ""
            owner = cells[owner_idx] if owner_idx < len(cells) else "Unassigned"
            criteria_str = cells[crit_idx] if crit_idx < len(cells) else None
            app_str = cells[app_idx] if app_idx < len(cells) else "[UNASSIGNED - TO BE CONFIRMED]"
            signoff_str = cells[signoff_idx] if signoff_idx < len(cells) else "Formal written sign-off"

            deliverables.append(Deliverable(
                id=d_id,
                name=d_name,
                description=d_name,
                source_reference=src_ref,
                owner=owner,
                acceptance_criteria=criteria_str,
                client_approver=app_str,
                review_window=signoff_str,
                rejection_rework_path="Talent PM / Team rework within 3 business days of notice"
            ))

        return deliverables

    def _parse_raid_and_decisions_tables(
        self,
        tables: List[Table],
        src_ref: SourceReference
    ) -> Tuple[List[RiskAssumption], List[DecisionItem]]:
        """Parse RAID Log and Decision Log tables."""
        raid_items: List[RiskAssumption] = []
        decisions: List[DecisionItem] = []

        # RAID table
        tbl = self._find_table_by_header(tables, ["type", "description", "mitigation"])
        if not tbl:
            tbl = self._find_table_by_header(tables, ["raid", "owner", "status"])

        if tbl:
            header_cells = [c.text.strip().lower() for c in tbl.rows[0].cells]
            type_idx = next((i for i, h in enumerate(header_cells) if "type" in h), 0)
            id_idx = next((i for i, h in enumerate(header_cells) if "id" in h), 1)
            desc_idx = next((i for i, h in enumerate(header_cells) if "desc" in h), 2)
            owner_idx = next((i for i, h in enumerate(header_cells) if "owner" in h), 3)
            status_idx = next((i for i, h in enumerate(header_cells) if "status" in h), 4)
            mit_idx = next((i for i, h in enumerate(header_cells) if "mitigation" in h or "strategy" in h), 5)
            imp_idx = next((i for i, h in enumerate(header_cells) if "impact" in h or "severity" in h), 6)

            for row in tbl.rows[1:]:
                cells = [c.text.strip() for c in row.cells]
                if len(cells) < 3:
                    continue
                r_type = cells[type_idx] if type_idx < len(cells) else "Risk"
                if r_type not in ("Risk", "Assumption", "Issue", "Dependency"):
                    r_type = "Risk"
                r_id = cells[id_idx] if id_idx < len(cells) else f"RAID-{len(raid_items)+1:02d}"
                r_desc = cells[desc_idx] if desc_idx < len(cells) else ""
                r_owner = cells[owner_idx] if owner_idx < len(cells) else "Delivery Manager"
                r_status = cells[status_idx] if status_idx < len(cells) else "Open"
                r_mit = cells[mit_idx] if mit_idx < len(cells) else "Active monitoring"
                r_imp = cells[imp_idx] if imp_idx < len(cells) else "Medium"

                raid_items.append(RiskAssumption(
                    id=r_id,
                    type=r_type,
                    description=r_desc,
                    owner=r_owner,
                    status=r_status,
                    mitigation_strategy=r_mit,
                    impact=r_imp,
                    source_reference=src_ref
                ))

        # Decision log table
        dec_tbl = self._find_table_by_header(tables, ["decision id", "decision text", "status"])
        if dec_tbl:
            for row in dec_tbl.rows[1:]:
                cells = [c.text.strip() for c in row.cells]
                if len(cells) >= 4:
                    decisions.append(DecisionItem(
                        id=cells[0],
                        decision_text=cells[1],
                        decision_owner=cells[2],
                        status=cells[3]
                    ))

        return raid_items, decisions

    def _parse_communications_table(self, tables: List[Table]) -> List[CommunicationsPlanItem]:
        """Parse Communications and Reporting Plan table."""
        comms: List[CommunicationsPlanItem] = []
        tbl = self._find_table_by_header(tables, ["report / meeting", "audience", "cadence"])
        if not tbl:
            tbl = self._find_table_by_header(tables, ["communication", "audience", "cadence"])

        if tbl:
            for row in tbl.rows[1:]:
                cells = [c.text.strip() for c in row.cells]
                if len(cells) >= 6:
                    c_id = f"COM-{len(comms)+1:02d}"
                    comms.append(CommunicationsPlanItem(
                        id=c_id,
                        name=cells[0],
                        audience=cells[1],
                        content_owner=cells[2],
                        cadence=cells[3],
                        format=cells[4],
                        delivery_day=cells[5]
                    ))

        return comms

    def _parse_stakeholders_and_raci(
        self,
        tables: List[Table]
    ) -> Tuple[List[Stakeholder], List[RACIItem]]:
        """Parse Stakeholders table and RACI matrix table."""
        stakeholders: List[Stakeholder] = []
        raci: List[RACIItem] = []

        # Stakeholders
        tbl = self._find_table_by_header(tables, ["stakeholder name", "role", "decision rights"])
        if tbl:
            for row in tbl.rows[1:]:
                cells = [c.text.strip() for c in row.cells]
                if len(cells) >= 5:
                    stakeholders.append(Stakeholder(
                        name=cells[0],
                        role=cells[1],
                        organization=cells[2],
                        decision_rights=cells[3],
                        escalation_responsibility=cells[4]
                    ))

        # RACI Matrix
        raci_tbl = self._find_table_by_header(tables, ["startup control", "pmo lead", "delivery manager"])
        if not raci_tbl:
            raci_tbl = self._find_table_by_header(tables, ["decision or activity", "pmo", "delivery manager"])

        if raci_tbl:
            for row in raci_tbl.rows[1:]:
                cells = [c.text.strip() for c in row.cells]
                if len(cells) >= 6:
                    raci.append(RACIItem(
                        decision_or_activity=cells[0],
                        pmo_lead=cells[1],
                        delivery_manager=cells[2],
                        talent_pm=cells[3],
                        sales_accounts=cells[4],
                        client=cells[5]
                    ))

        return stakeholders, raci

    def _parse_commercial_guardrails(
        self,
        doc: docx.Document,
        contract_type: str,
        src_ref: SourceReference
    ) -> CommercialGuardrail:
        """Parse Commercial Guardrails callout box or fallback to defaults."""
        contract_implications = f"Managed delivery under {contract_type} governance rules."
        approved_rule = "All delivery milestones and billable hours must map directly to contracted SOW deliverables."
        non_approved_rule = "Any activity outside agreed scope requires an approved Change Order."
        work_at_risk = "Work-at-risk strictly prohibited without written PMO Director approval."
        change_trigger = "Material scope modifications, milestone shifts > 5 business days, or client delay."
        change_route = "Talent PM -> Delivery Manager -> PMO Lead -> Sales / Accounts -> Client sign-off"
        budget_baseline = "Established from SOW financial schedule"
        variance_ind = "Monthly budget vs actuals review"
        margin_risk = "Tracked via weekly delivery margin variance analysis"
        escalation_thresh = "Budget variance > 5% or milestone delay > 3 days"

        for p in doc.paragraphs:
            t = p.text.strip()
            if "Commercial Guardrails & Margin Protection Rules" in t or "Commercial and Margin Guardrails" in t:
                if "Contract Implications:" in t:
                    m = re.search(r'Contract Implications:\s*(.*?)(?:\n|$)', t)
                    if m and m.group(1).strip():
                        contract_implications = m.group(1).strip()
                if "Approved Work Rule:" in t:
                    m = re.search(r'Approved Work Rule:\s*(.*?)(?:\n|$)', t)
                    if m and m.group(1).strip():
                        approved_rule = m.group(1).strip()
                if "Non-Approved Work Rule:" in t:
                    m = re.search(r'Non-Approved Work Rule:\s*(.*?)(?:\n|$)', t)
                    if m and m.group(1).strip():
                        non_approved_rule = m.group(1).strip()
                if "Work-at-Risk Policy:" in t:
                    m = re.search(r'Work-at-Risk Policy:\s*(.*?)(?:\n|$)', t)
                    if m and m.group(1).strip():
                        work_at_risk = m.group(1).strip()
                if "Change Control Triggers:" in t:
                    m = re.search(r'Change Control Triggers:\s*(.*?)(?:\n|$)', t)
                    if m and m.group(1).strip():
                        change_trigger = m.group(1).strip()
                if "Change Order Route:" in t:
                    m = re.search(r'Change Order Route:\s*(.*?)(?:\n|$)', t)
                    if m and m.group(1).strip():
                        change_route = m.group(1).strip()
                if "Escalation Threshold:" in t:
                    m = re.search(r'Escalation Threshold:\s*(.*?)(?:\n|$)', t)
                    if m and m.group(1).strip():
                        escalation_thresh = m.group(1).strip()

        return CommercialGuardrail(
            contract_type_implication=contract_implications,
            approved_work_rule=approved_rule,
            non_approved_work_rule=non_approved_rule,
            work_at_risk_rule=work_at_risk,
            change_control_trigger=change_trigger,
            change_order_route=change_route,
            budget_baseline=budget_baseline,
            variance_indicator=variance_ind,
            margin_risk_indicator=margin_risk,
            escalation_threshold=escalation_thresh,
            source_reference=src_ref
        )

    def _parse_talent_onboarding(
        self,
        doc: docx.Document,
        tables: List[Table],
        pmo_lead: str,
        dm: str,
        tpm: str,
        src_ref: SourceReference
    ) -> TalentOnboardingRecord:
        """Parse Talent Onboarding record and talent roster table."""
        roster: List[TalentMember] = []

        # Check for leadership paragraph overrides in Section 3.4
        for p in doc.paragraphs:
            t = p.text.strip()
            if "Onboarding Leadership:" in t:
                m_tpm = re.search(r'Talent PM:\s*([^|]+)', t)
                m_dm = re.search(r'Delivery Manager:\s*([^|]+)', t)
                m_pmo = re.search(r'PMO Lead:\s*([^|]+)', t)
                if m_tpm and m_tpm.group(1).strip():
                    tpm = m_tpm.group(1).strip()
                if m_dm and m_dm.group(1).strip():
                    dm = m_dm.group(1).strip()
                if m_pmo and m_pmo.group(1).strip():
                    pmo_lead = m_pmo.group(1).strip()

        # Parse Roster table
        tbl = self._find_table_by_header(tables, ["role", "named talent", "staffing status"])
        if not tbl:
            tbl = self._find_table_by_header(tables, ["named talent", "skills", "status"])

        if tbl:
            for row in tbl.rows[1:]:
                cells = [c.text.strip() for c in row.cells]
                if len(cells) >= 4:
                    status_val = cells[3]
                    if status_val not in ("Confirmed", "Pending", "Needs Alignment"):
                        status_val = "Confirmed" if status_val.lower() in ("confirmed", "active", "approved") else "Pending"

                    roster.append(TalentMember(
                        role=cells[0],
                        name=cells[1],
                        required_skills=cells[2],
                        status=status_val
                    ))

        return TalentOnboardingRecord(
            pmo_lead=pmo_lead,
            delivery_manager=dm,
            talent_pm=tpm,
            delivery_talent_roster=roster,
            source_reference=src_ref
        )
