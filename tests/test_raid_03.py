"""Tests for RAID-03 contract reference formatting, plural citations, and no-information-loss invariant."""

import pytest
from datetime import date
from src.generators.pmo_workbook.builder import extract_contract_reference, strip_citation_from_clause, build_workbook_model
from src.tools.check_artifacts import check_artifacts_directory
import json


def test_raid_03_contract_reference_formatting():
    """RAID-03: SOW refs: label, section lists, .txt and .md citations."""
    # 1. SOW refs: label for story IDs and Deliverable N.N
    ref1, _ = extract_contract_reference("sow.txt, Section 2 and Section 3 (Deliverable 3.2): Phases and Milestones")
    assert ref1 == "sow.txt | SOW refs: Deliverable 3.2 | Sections: 2, 3"

    ref2, _ = extract_contract_reference("notes.md, Section 4: Task 12 and WBS 1.2 details")
    assert "notes.md" in ref2
    assert "SOW refs: Task 12, WBS 1.2" in ref2
    assert "Sections: 4" in ref2

    # 2. Section lists (never trailing comma, never empty parts)
    ref3, _ = extract_contract_reference("Section 2 and Section 3 and Section 5: Scope details")
    assert ref3 == "Sections: 2, 3, 5"
    assert not ref3.endswith(",")
    assert "||" not in ref3


def test_raid_03_plural_section_and_sow_reference_parsing():
    """RAID-03: Plural section and deliverable citations per Rev 6 specification."""
    # "Section 2 and Section 3" gives "2, 3"
    r1, _ = extract_contract_reference("sow.txt, Section 2 and Section 3: Scope details")
    assert r1 == "sow.txt | Sections: 2, 3"

    # "Sections 2 and 4" gives "2, 4"
    r2, _ = extract_contract_reference("sow.txt, Sections 2 and 4: Timeline alignment")
    assert r2 == "sow.txt | Sections: 2, 4"

    # "Sections 1, 2 and 3" gives "1, 2, 3"
    r3, _ = extract_contract_reference("sow.txt, Sections 1, 2 and 3: Methodology across phases")
    assert r3 == "sow.txt | Sections: 1, 2, 3"

    # "Header and Section 2" gives "Sections: Header, 2"
    r4, _ = extract_contract_reference("sow.txt, Header and Section 2: Mobilization timeline")
    assert r4 == "sow.txt | Sections: Header, 2"

    # "Deliverables 2.2 and 3.1" gives "SOW refs: Deliverable 2.2, Deliverable 3.1"
    r5, _ = extract_contract_reference("sow.txt, Section 3 (Deliverables 2.2 and 3.1): Acceptance criteria")
    assert r5 == "sow.txt | SOW refs: Deliverable 2.2, Deliverable 3.1 | Sections: 3"


def test_raid_03_description_citation_stripping_and_no_information_loss():
    """RAID-03: Remove citation from description only when every part of it appears in the Contract Reference."""
    # When fully captured in contract_ref, strip from description
    raw1 = "Scope Contradiction: sow.txt, Section 2 and Section 3 (Deliverable 3.2): Phases and Milestones: P3 is named \"Reconciliation and Final Cutover\"."
    ref1 = "sow.txt | SOW refs: Deliverable 3.2 | Sections: 2, 3"
    cleaned1 = strip_citation_from_clause(raw1, category="Scope Contradiction", contract_ref=ref1)
    assert cleaned1 == "Phases and Milestones: P3 is named \"Reconciliation and Final Cutover\"."

    raw2 = "Ambiguous Acceptance: sow.txt, Section 3 (Deliverable 1.2): Contracted Deliverables: 1.2 is \"Security and Encryption Controls\"."
    ref2 = "sow.txt | SOW refs: Deliverable 1.2 | Sections: 3"
    cleaned2 = strip_citation_from_clause(raw2, category="Ambiguous Acceptance", contract_ref=ref2)
    assert cleaned2 == "Contracted Deliverables: 1.2 is \"Security and Encryption Controls\"."

    # When parts are missing from contract_ref, do not strip (no information loss)
    raw3 = "sow.txt, Section 5: Unextracted detail in description"
    ref3 = "sow.txt | Sections: 2"  # Section 5 missing from ref
    cleaned3 = strip_citation_from_clause(raw3, category=None, contract_ref=ref3)
    assert cleaned3 == "sow.txt, Section 5: Unextracted detail in description"


def test_raid_03_no_story_ids_and_numbered_deliverables_rows():
    """RAID-03: Verify no_story_ids (RAID-08 to RAID-15) and numbered_deliverables (RAID-11) rows."""
    from src.core.models import StartupKitBaseline
    from src.llm.validation import validate_and_repair_baseline

    # 1. Test no_story_ids baseline
    with open("tests/fixtures/sow/no_story_ids/baseline.json", "r", encoding="utf-8") as f:
        data_ns = json.load(f)
    baseline_ns = StartupKitBaseline.model_validate(data_ns)
    validate_and_repair_baseline(baseline_ns)
    model_ns = build_workbook_model(baseline_ns, start_date=date(2026, 10, 5))
    raid_map_ns = {r.raid_id: r for r in model_ns.raid_rows}

    # RAID-05 to RAID-15 checks on no_story_ids (AMB-01 to AMB-11)
    assert "RAID-05" in raid_map_ns
    r5 = raid_map_ns["RAID-05"]
    assert "sow.txt" in r5.contract_reference
    assert "Sections: 2, 4" in r5.contract_reference

    assert "RAID-07" in raid_map_ns
    r7 = raid_map_ns["RAID-07"]
    assert "Sections: 2, 3" in r7.contract_reference

    assert "RAID-08" in raid_map_ns
    r8 = raid_map_ns["RAID-08"]
    assert "Sections: 1, 2, 3" in r8.contract_reference

    assert "RAID-12" in raid_map_ns
    r12 = raid_map_ns["RAID-12"]
    assert "Sections: Header, 2" in r12.contract_reference

    assert "RAID-13" in raid_map_ns
    r13 = raid_map_ns["RAID-13"]
    assert "Sections: 2, 3, 4" in r13.contract_reference

    # 2. Test numbered_deliverables baseline
    with open("tests/fixtures/sow/numbered_deliverables/baseline.json", "r", encoding="utf-8") as f:
        data_nd = json.load(f)
    baseline_nd = StartupKitBaseline.model_validate(data_nd)
    validate_and_repair_baseline(baseline_nd)
    model_nd = build_workbook_model(baseline_nd, start_date=date(2026, 10, 5))
    raid_map_nd = {r.raid_id: r for r in model_nd.raid_rows}

    # RAID-11 in numbered_deliverables (AMB-08: Deliverables 2.2 and 3.1)
    assert "RAID-11" in raid_map_nd
    r11_nd = raid_map_nd["RAID-11"]
    assert "Deliverable 2.2" in r11_nd.contract_reference
    assert "Deliverable 3.1" in r11_nd.contract_reference
    assert "DEL-04" in r11_nd.linked_deliverables
    assert "DEL-05" in r11_nd.linked_deliverables


def test_raid_03_no_information_loss_invariant_across_fixtures():
    """RAID-03 Invariant: Every section number and SOW reference in raw conflicting_clauses appears in Contract Reference or Description."""
    import re
    from pathlib import Path
    from src.core.models import StartupKitBaseline
    from src.llm.validation import validate_and_repair_baseline
    from src.config import extract_sow_references

    fixtures_dir = Path("tests/fixtures/sow")
    for b_path in fixtures_dir.glob("*/baseline.json"):
        with open(b_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        baseline = StartupKitBaseline.model_validate(data)
        validate_and_repair_baseline(baseline)
        model = build_workbook_model(baseline, start_date=date(2026, 10, 5))

        clarification_rows = [r for r in model.raid_rows if r.category == "Contract Clarification"]
        for r in clarification_rows:
            combined_output = f"{r.contract_reference} {r.description}"
            # Check sections mentioned in raw conflicting clauses
            raw_clauses = ""
            for amb in (baseline.contract_ambiguities or []):
                amb_id = amb.anomaly_id or getattr(amb, "id", "")
                if amb_id == r.source_id:
                    raw_clauses = amb.conflicting_clauses or ""
                    break

            if raw_clauses:
                raw_sections = re.findall(r"\b(?:Sections?|Clauses?|§§?)\s*(\d+(?:\.\d+)*)\b", raw_clauses, re.IGNORECASE)
                for sec in raw_sections:
                    assert sec in combined_output, (
                        f"Section {sec} from raw clause '{raw_clauses}' lost in row {r.raid_id} (ref: {r.contract_reference}, desc: {r.description})"
                    )

                raw_stories = extract_sow_references(raw_clauses)
                for st in raw_stories:
                    assert st in combined_output or any(part in combined_output for part in st.split()), (
                        f"SOW reference {st} from raw clause '{raw_clauses}' lost in row {r.raid_id}"
                    )


def test_raid_03_arc_genomics_citations():
    """RAID-03: Verify ARC RAID-21, RAID-24, and RAID-26 contract references and SOW refs formatting."""
    from src.core.models import StartupKitBaseline
    from src.llm.validation import validate_and_repair_baseline

    with open("tests/fixtures/sow/arc_genomics/baseline.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    baseline = StartupKitBaseline.model_validate(data)
    validate_and_repair_baseline(baseline)
    model = build_workbook_model(baseline, start_date=date(2026, 10, 5))
    raid_map = {r.raid_id: r for r in model.raid_rows}

    # RAID-21: cites HS-4781, Sections 7, 6
    assert "RAID-21" in raid_map
    r21 = raid_map["RAID-21"]
    assert "Exhibit A - Arc Genomics Platform.pdf" in r21.contract_reference
    assert "SOW refs: HS-4781" in r21.contract_reference
    assert "Sections: 7, 6" in r21.contract_reference

    # RAID-24: cites HS-4779, HS-4775, HS-4794, HS-4804, HS-4825, Sections 3, 4
    assert "RAID-24" in raid_map
    r24 = raid_map["RAID-24"]
    assert "Exhibit A - Arc Genomics Platform.pdf" in r24.contract_reference
    assert "SOW refs: HS-4779, HS-4775, HS-4794, HS-4804, HS-4825" in r24.contract_reference
    assert "Sections: 3, 4" in r24.contract_reference

    # RAID-26: cites HS-4762, HS-4772, HS-4775, HS-4825, HS-4942, Section 4
    assert "RAID-26" in raid_map
    r26 = raid_map["RAID-26"]
    assert "Exhibit A - Arc Genomics Platform.pdf" in r26.contract_reference
    assert "SOW refs: HS-4762, HS-4772, HS-4775, HS-4825, HS-4942" in r26.contract_reference
    assert "Sections: 4" in r26.contract_reference
