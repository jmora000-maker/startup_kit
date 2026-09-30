"""Tests for story index and RAID deliverable linking (spec v4 A17)."""

from datetime import date
from src.core.models import Deliverable, SourceReference
from src.generators.pmo_workbook.builder import build_workbook_model


def test_story_links_with_sow_references(arc_run2):
    """Test that RAID items link to deliverables when deliverables contain story references."""
    # Add story reference HS-4828 to DEL-16 (UAT) and HS-4943 to DEL-17 (Hardening)
    ref = SourceReference(document_name="ARC_Genomics_SOW.pdf", clause_or_slide="Section 3", confidence_score=0.95)
    updated_deliverables = []
    for d in arc_run2.deliverables:
        if d.id == "DEL-16":
            updated_deliverables.append(Deliverable(
                id=d.id, name=d.name, description=f"{d.description} Stories: HS-4828",
                acceptance_criteria=d.acceptance_criteria, evidence_required=d.evidence_required,
                owner=d.owner, source_reference=ref, sow_reference="HS-4828"
            ))
        elif d.id == "DEL-17":
            updated_deliverables.append(Deliverable(
                id=d.id, name=d.name, description=f"{d.description} Stories: HS-4943",
                acceptance_criteria=d.acceptance_criteria, evidence_required=d.evidence_required,
                owner=d.owner, source_reference=ref, sow_reference="HS-4943"
            ))
        else:
            updated_deliverables.append(d)

    baseline = arc_run2.model_copy(update={"deliverables": updated_deliverables})
    model = build_workbook_model(baseline, start_date=date(2026, 10, 5))

    amb_map = {r.source_id: r for r in model.raid_rows if r.category == "Contract Clarification"}
    assert "AMB-08" in amb_map
    amb_08 = amb_map["AMB-08"]
    assert "DEL-16" in amb_08.linked_deliverables
    assert "DEL-17" in amb_08.linked_deliverables

    # Check back-links on WBS deliverable rows
    deliv_wbs = {w.deliverable_id: w for w in model.wbs_rows if w.element_type == "Deliverable"}
    assert "RAID-27" in deliv_wbs["DEL-16"].linked_raid_ids or amb_08.raid_id in deliv_wbs["DEL-16"].linked_raid_ids
    assert "RAID-27" in deliv_wbs["DEL-17"].linked_raid_ids or amb_08.raid_id in deliv_wbs["DEL-17"].linked_raid_ids
