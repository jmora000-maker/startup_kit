"""Downstream PMO Operating System Workbook Toolkit Export Payloads (NFR-09)."""

import csv
import json
import logging
from pathlib import Path
from typing import Dict, Any
from src.core.models import StartupKitBaseline

logger = logging.getLogger(__name__)


def sanitize_filename(name: str) -> str:
    """Sanitize project name for safe filename creation."""
    import re
    s = re.sub(r'[^a-zA-Z0-9_\- ]+', '', name).strip()
    return s.replace(' ', '_') or "Project"


def export_raid_csv(baseline: StartupKitBaseline, output_dir: Path) -> Path:
    """Export standard RAID table to CSV for active delivery tracking."""
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_name = sanitize_filename(baseline.project_name)
    file_path = output_dir / f"{clean_name}_PMO_RAID_Log.csv"

    fieldnames = [
        "ID",
        "Type",
        "Description",
        "Category",
        "Owner",
        "Probability",
        "Impact",
        "Severity",
        "Trigger_Early_Warning",
        "Mitigation_Response",
        "Due_Date",
        "Status",
        "Linked_Decision",
        "Linked_Dependency_Assumption"
    ]

    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for idx, item in enumerate(baseline.raid_items):
            item_id = f"RAID-{idx+1:02d}"
            writer.writerow({
                "ID": item_id,
                "Type": item.type,
                "Description": item.description,
                "Category": item.category if hasattr(item, "category") else "Technical",
                "Owner": item.owner,
                "Probability": getattr(item, "probability", "Medium") or "Medium",
                "Impact": getattr(item, "impact", "Medium") or "Medium",
                "Severity": getattr(item, "severity", "Medium") or "Medium",
                "Trigger_Early_Warning": getattr(item, "trigger_or_early_warning", "Startup assessment") or "",
                "Mitigation_Response": getattr(item, "mitigation_or_response", "Active monitoring") or "",
                "Due_Date": item.due_date.isoformat() if getattr(item, "due_date", None) else "",
                "Status": item.status,
                "Linked_Decision": getattr(item, "linked_decision", "") or "",
                "Linked_Dependency_Assumption": getattr(item, "linked_dependency_or_assumption", "") or ""
            })

    logger.info("Exported PMO RAID CSV to: %s", file_path)
    return file_path


def export_decision_log_csv(baseline: StartupKitBaseline, output_dir: Path) -> Path:
    """Export Decision Log seed to CSV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_name = sanitize_filename(baseline.project_name)
    file_path = output_dir / f"{clean_name}_PMO_Decision_Log.csv"

    fieldnames = [
        "ID",
        "Decision_Text",
        "Decision_Owner",
        "Decision_Date",
        "Rationale",
        "Status",
        "Linked_RAID_Item"
    ]

    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for dec in baseline.decisions:
            writer.writerow({
                "ID": dec.id,
                "Decision_Text": dec.decision_text,
                "Decision_Owner": dec.decision_owner,
                "Decision_Date": dec.decision_date.isoformat() if dec.decision_date else "",
                "Rationale": dec.rationale,
                "Status": dec.status,
                "Linked_RAID_Item": dec.linked_raid_item or ""
            })

    logger.info("Exported PMO Decision Log CSV to: %s", file_path)
    return file_path


def export_milestone_plan_json(baseline: StartupKitBaseline, output_dir: Path) -> Path:
    """Export structured milestone baseline with internal contingency buffers to JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_name = sanitize_filename(baseline.project_name)
    file_path = output_dir / f"{clean_name}_PMO_Milestone_Plan.json"

    milestones_data = []
    for m in baseline.milestones:
        milestones_data.append({
            "id": m.id,
            "description": m.description,
            "external_commitment_date": m.external_date.isoformat() if m.external_date else None,
            "internal_buffer_date": m.internal_buffer_date.isoformat() if m.internal_buffer_date else None,
            "owner": m.owner,
            "key_dependencies": m.key_dependencies,
            "critical_path_assumptions": m.critical_path_assumptions,
            "source_document": m.source_reference.document_name if m.source_reference else "N/A"
        })

    payload = {
        "project_name": baseline.project_name,
        "governance_tier": baseline.governance_tier,
        "contract_type": baseline.contract_type,
        "milestones_count": len(baseline.milestones),
        "milestones": milestones_data
    }

    with open(file_path, mode="w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    logger.info("Exported PMO Milestone Plan JSON to: %s", file_path)
    return file_path


def export_psa_seed_json(baseline: StartupKitBaseline, output_dir: Path) -> Path:
    """Export Project Success Agreement (PSA) seed to JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_name = sanitize_filename(baseline.project_name)
    file_path = output_dir / f"{clean_name}_PMO_PSA_Seed.json"

    charter = baseline.charter
    payload = {
        "project_name": baseline.project_name,
        "client_name": charter.client_name if charter else (baseline.governance_context.client_name if baseline.governance_context else "N/A"),
        "governance_tier": baseline.governance_tier,
        "contract_type": baseline.contract_type,
        "readiness_score": baseline.readiness_score,
        "workflow_state": baseline.workflow_state,
        "project_purpose": charter.project_purpose if charter else "N/A",
        "delivery_objectives": charter.delivery_objectives if charter else [],
        "success_criteria": charter.success_criteria if charter else [],
        "delivery_model": charter.delivery_model if charter else "Toptal Talent Team (Agile/Milestone Hybrid)",
        "governance_model": charter.governance_model if charter else f"PMO {baseline.governance_tier} Tier Governance Model",
        "leadership_roles": {
            "pmo_lead": baseline.author_name or "[UNASSIGNED - TO BE CONFIRMED]",
            "delivery_manager": charter.delivery_manager if charter else "[UNASSIGNED - TO BE CONFIRMED]",
            "talent_pm": charter.talent_pm if charter else "[UNASSIGNED - TO BE CONFIRMED]",
            "approver": baseline.approver_name or "PMO Lead",
            "concurring_approver": baseline.concurring_approver_name
        },
        "escalation_path": charter.escalation_path if charter else "Talent PM / DM -> PMO Lead -> Director, PMO",
        "deliverables_count": len(baseline.deliverables),
        "milestones_count": len(baseline.milestones),
        "open_exceptions_count": len([i for i in baseline.readiness_checklist if i.exception_required or i.status == "Exception Required"])
    }

    with open(file_path, mode="w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    logger.info("Exported PMO PSA Seed JSON to: %s", file_path)
    return file_path


def export_budget_burndown_seed_json(baseline: StartupKitBaseline, output_dir: Path) -> Path:
    """Export Budget Burndown and commercial guardrails seed to JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_name = sanitize_filename(baseline.project_name)
    file_path = output_dir / f"{clean_name}_PMO_Budget_Burndown_Seed.json"

    cg = baseline.commercial_guardrails
    payload = {
        "project_name": baseline.project_name,
        "contract_type": baseline.contract_type,
        "governance_tier": baseline.governance_tier,
        "commercial_guardrails": {
            "contract_type_implication": cg.contract_type_implication if cg else "",
            "billing_consumption_assumption": cg.billing_consumption_assumption if cg else "",
            "staffing_assumption": cg.staffing_assumption if cg else "",
            "approved_work_rule": cg.approved_work_rule if cg else "",
            "non_approved_work_rule": cg.non_approved_work_rule if cg else "",
            "work_at_risk_rule": cg.work_at_risk_rule if cg else "",
            "change_control_trigger": cg.change_control_trigger if cg else "",
            "change_order_route": cg.change_order_route if cg else "",
            "budget_baseline": cg.budget_baseline if cg else "[CONFIRMATION REQUIRED]",
            "variance_indicator": cg.variance_indicator if cg else "Green (<5% variance)",
            "margin_risk_indicator": cg.margin_risk_indicator if cg else "Low",
            "escalation_threshold": cg.escalation_threshold if cg else "Variance > 10%"
        }
    }

    with open(file_path, mode="w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    logger.info("Exported PMO Budget Burndown Seed JSON to: %s", file_path)
    return file_path


def export_all_pmo_tools(baseline: StartupKitBaseline, output_dir: Path) -> Dict[str, Path]:
    """Generate all downstream PMO Operating System workbook toolkit seed files."""
    return {
        "raid_csv": export_raid_csv(baseline, output_dir),
        "decision_log_csv": export_decision_log_csv(baseline, output_dir),
        "milestone_plan_json": export_milestone_plan_json(baseline, output_dir),
        "psa_seed_json": export_psa_seed_json(baseline, output_dir),
        "budget_burndown_seed_json": export_budget_burndown_seed_json(baseline, output_dir)
    }
