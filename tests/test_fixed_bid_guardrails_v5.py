"""Tests for Fixed Bid commercial guardrails and milestone date questions (spec v5 B15)."""

from datetime import date
from src.generators.checklist import G01ChecklistRenderer
from src.core.models import (
    StartupKitBaseline,
    ProjectStartupCharter,
    Deliverable,
    Milestone,
    CommercialGuardrail,
    SourceReference,
)
import docx


def test_fixed_bid_guardrails_wording_in_checklist(tmp_path):
    """Test Fixed Bid guardrails replace legacy wording and mark standard defaults."""
    ref = SourceReference(document_name="SOW.pdf", clause_or_slide="Sec 1", confidence_score=0.9)

    baseline = StartupKitBaseline(
        project_name="Fixed Bid Project",
        contract_type="Fixed Bid",
        charter=ProjectStartupCharter(project_name="Fixed Bid Project", contract_type="Fixed Bid"),
        commercial_guardrails=CommercialGuardrail(),
        milestones=[
            Milestone(id="M1", description="Phase 1", external_date=None, internal_buffer_date=None, source_reference=ref),
            Milestone(id="M2", description="Phase 2", external_date=None, internal_buffer_date=None, source_reference=ref),
        ],
        deliverables=[
            Deliverable(id="DEL-01", name="Service 1", source_reference=ref)
        ]
    )

    renderer = G01ChecklistRenderer()
    doc = docx.Document()
    renderer.render_commercial_guardrails_table(doc, baseline)

    cg_table = doc.tables[0]
    cg_text = " ".join(c.text for row in cg_table.rows for c in row.cells)

    # Required replacements
    assert "Milestone-acceptance invoicing" in cg_text
    assert "Fixed scope; changes by Change Order" in cg_text
    assert "[Standard PMO guardrail - confirm]" in cg_text

    # Forbidden legacies on Fixed Bid
    assert "Periodic Invoicing / Burn Tracking" not in cg_text
    assert "Roster Locked & Rate Realization" not in cg_text
    assert "rework effort > 10% of deliverable budget" not in cg_text
