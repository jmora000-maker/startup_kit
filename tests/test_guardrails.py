"""Tests for CHK-06 Fixed Bid commercial guardrails formatting and status strings."""

import pytest
from pathlib import Path
from src.core.models import (
    StartupKitBaseline,
    CommercialGuardrail,
)
from src.generators.docx_generator import DocxGenerator
from src.tools.normalizers import normalize_docx_tables


def test_fixed_bid_guardrails_status_wording(tmp_path):
    """Verify that Fixed Bid guardrails status column uses exact CHK-06 wording and has no effort terms."""
    cg = CommercialGuardrail(
        contract_type_implication="Fixed scope and milestone gates.",
        billing_consumption_assumption="Milestone acceptance invoicing.",
        staffing_assumption="Fixed team roster.",
        approved_work_rule="Only contracted scope.",
        non_approved_work_rule="Out of scope work strictly prohibited.",
        work_at_risk_rule="Pre-approval required.",
        change_control_trigger="Scope changes require formal Change Order.",
        change_order_route="DM aligns client -> PMO approves.",
        budget_baseline="Fixed price contract cap.",
        variance_indicator="On track",
        margin_risk_indicator="Low",
        escalation_threshold="Milestone slip > 3 days."
    )
    baseline = StartupKitBaseline(
        project_name="Guardrails Test",
        contract_type="Fixed Bid",
        commercial_guardrails=cg,
    )

    writer = DocxGenerator()
    chk_path = writer.write_checklist_docx(baseline, tmp_path)

    tables = normalize_docx_tables(chk_path)
    # Find guardrails table
    guardrail_table = None
    for t in tables:
        for r in t["rows"]:
            if "Commercial Guardrail Area" in r:
                guardrail_table = t
                break
        if guardrail_table:
            break

    assert guardrail_table is not None, "Commercial guardrails table not found in Checklist."

    # Verify status column wording
    table_text = " ".join(" ".join(r) for r in guardrail_table["rows"])
    assert "Schedule slip > 3 days or acceptance rejection" in table_text
    assert "Milestone acceptance and Change Order log review" in table_text
