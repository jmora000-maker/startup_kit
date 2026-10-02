"""Values the Startup Kit displays, shared by the Kit writer and the deck builder (DECK-03).

Kept free of heavy imports so both can use it without circular imports.
"""

import re

from src.core.models import StartupKitBaseline


def kit_sanitize_filename(name: str) -> str:
    """Project name as it appears in the Kit file name."""
    s = re.sub(r'[^a-zA-Z0-9_\- ]+', '', name).strip()
    return s.replace(' ', '_') or "Project"


def kit_header_values(baseline: StartupKitBaseline) -> dict:
    """The values the Kit header table shows for the people and client fields (also used by the deck, DECK-03)."""
    ctx = baseline.governance_context
    charter = baseline.charter
    talent_rec = baseline.talent_onboarding
    dm_meta = (ctx.delivery_manager if ctx and ctx.delivery_manager else None) or (charter.delivery_manager if charter and charter.delivery_manager else None) or (talent_rec.delivery_manager if talent_rec and talent_rec.delivery_manager else None) or "[UNASSIGNED - TO BE CONFIRMED]"
    tpm_meta = (ctx.talent_pm if ctx and ctx.talent_pm else None) or (charter.talent_pm if charter and charter.talent_pm else None) or (talent_rec.talent_pm if talent_rec and talent_rec.talent_pm else None) or "[UNASSIGNED - TO BE CONFIRMED]"
    pmo_meta = (ctx.pmo_lead if ctx and ctx.pmo_lead else None) or (charter.pmo_lead if charter and charter.pmo_lead else None) or (talent_rec.pmo_lead if talent_rec and talent_rec.pmo_lead else None) or (baseline.author_name if baseline.author_name else None) or "[UNASSIGNED - TO BE CONFIRMED]"
    client_meta = (ctx.client_name if ctx and ctx.client_name else None) or (charter.client_name if charter and charter.client_name else None) or "N/A"
    return {
        "project_name": baseline.project_name,
        "client_sponsor": client_meta,
        "governance_tier": baseline.governance_tier,
        "contract_type": baseline.contract_type,
        "delivery_manager": dm_meta,
        "talent_pm": tpm_meta,
        "pmo_lead": pmo_meta,
    }
