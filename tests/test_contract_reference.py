"""Test v3 A7: Contract reference column, intact description, and text hygiene for ambiguities."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model, CONTRACT_REF_REGEX


def test_contract_ref_regex_parsing():
    raw = "[V1] Exhibit A - Arc Genomics Platform.pdf, Section 4 (Latency Acceptance Criteria): test-suite acceptance criteria latency must be under 200ms"
    match = CONTRACT_REF_REGEX.match(raw)
    assert match is not None
    assert match.group("doc").strip() == "Exhibit A - Arc Genomics Platform.pdf"
    assert match.group("ref").strip() == "Section 4 (Latency Acceptance Criteria)"
    assert match.group("text").strip() == "test-suite acceptance criteria latency must be under 200ms"


def test_v3_contract_ambiguity_rows_in_raid(arc_baseline):
    model = build_workbook_model(arc_baseline, start_date=date(2026, 10, 5))

    amb_rows = [r for r in model.raid_rows if r.category == "Contract Clarification"]
    assert len(amb_rows) == 15

    # Check AMB-01 (RAID-20)
    amb_01 = next(r for r in amb_rows if r.source_id == "AMB-01")
    assert "Exhibit A - Arc Genomics Platform.pdf" in amb_01.contract_reference
    assert "Sections: 4" in amb_01.contract_reference
    assert "test-suite acceptance criteria latency must be under 200ms" in amb_01.description
    assert ",:" not in amb_01.description
    assert "as described " not in amb_01.description

    # Check AMB-15 (RAID-34)
    amb_15 = next(r for r in amb_rows if r.source_id == "AMB-15")
    assert "Exhibit A - Arc Genomics Platform.pdf" in amb_15.contract_reference
    assert "Sections: 7" in amb_15.contract_reference
    assert "responsibility for end-user scientist training delivery vs materials authoring" in amb_15.description
    assert amb_15.owner == "Talent PM"
    assert amb_15.status == "Open"
