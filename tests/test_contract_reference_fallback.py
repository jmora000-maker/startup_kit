"""Tests for contract reference fallback parsing (spec v4 A16)."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model, extract_contract_reference


def test_extract_contract_reference_direct():
    """Test extract_contract_reference standalone function."""
    ref1, note1 = extract_contract_reference("HS-4828 and HS-4943 UAT test scenarios mention legacy MTA store")
    assert ref1 == "SOW refs: HS-4828, HS-4943"
    assert note1 is None

    ref2, note2 = extract_contract_reference("Section 5 requires Snowflake schema completion in HS-4781 while Section 6 lists schema validation in P2a")
    assert ref2 == "SOW refs: HS-4781 | Sections: 5, 6"
    assert note2 is None

    ref3, note3 = extract_contract_reference("Client data ingestion pipeline defect remediation ownership is unassigned")
    assert ref3 == "Not cited"
    assert note3 == "No clause reference in baseline"


def test_contract_reference_ambiguities_in_model(arc_run2):
    """Test contract reference extraction across ambiguities in arc_run2."""
    model = build_workbook_model(arc_run2, start_date=date(2026, 10, 5))
    
    amb_rows = [r for r in model.raid_rows if r.category == "Contract Clarification"]
    assert len(amb_rows) == 15

    amb_map = {r.source_id: r for r in amb_rows}
    assert amb_map["AMB-08"].contract_reference == "SOW refs: HS-4828, HS-4943"
    assert amb_map["AMB-02"].contract_reference == "SOW refs: HS-4781 | Sections: 5, 6"
    assert amb_map["AMB-05"].contract_reference == "Not cited"

    not_cited_count = sum(1 for r in amb_rows if r.contract_reference == "Not cited")
    assert not_cited_count == 6
