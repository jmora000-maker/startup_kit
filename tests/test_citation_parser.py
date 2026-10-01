"""Tests for general citation parser across contract clarifications and ambiguities (v6 A28)."""

from datetime import date
from src.generators.pmo_workbook.builder import extract_contract_reference, build_workbook_model


def test_citation_parser_three_formats():
    """Test all three formats of leading citations tried in order."""
    # Format 1: [V1] doc_name, ref: text
    ref1, _ = extract_contract_reference("[V1] SOW_Genomics.pdf, Section 4.2: Acceptance window is 5 days")
    assert ref1 == "SOW_Genomics.pdf, Section 4.2"

    # Format 2: Exhibit / Attachment / Appendix
    ref2, _ = extract_contract_reference("Exhibit A, Client Responsibilities: HS-4763 requires MSAL caching while Section 5 specifies session statelessness")
    assert "Exhibit A, Client Responsibilities" in ref2
    assert "SOW refs: HS-4763" in ref2
    assert "Sections: 5" in ref2

    # Format 3: Document file
    ref3, _ = extract_contract_reference("SOW_Genomics.pdf: Section 3 specifies hourly sync")
    assert "SOW_Genomics.pdf" in ref3
    assert "Sections: 3" in ref3


def test_arc_run4_all_ambiguities_cited(arc_run4):
    """Test that in arc_run4, all 15 contract clarifications have a citation-based Contract Reference (no 'Not cited')."""
    model = build_workbook_model(arc_run4, start_date=date(2026, 10, 5))

    amb_rows = [r for r in model.raid_rows if r.category == "Contract Clarification"]
    assert len(amb_rows) == 15

    for r in amb_rows:
        assert r.contract_reference != "Not cited", f"{r.raid_id} has 'Not cited' contract reference"
        assert "Exhibit A" in r.contract_reference

    # Check AMB-03 (RAID-23) specifically
    r23 = next((r for r in amb_rows if r.source_id == "AMB-03"), None)
    assert r23 is not None
    assert "Exhibit A, Client Responsibilities" in r23.contract_reference
    assert "Sections: 5" in r23.contract_reference
