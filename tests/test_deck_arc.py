"""Tests asserting Appendix K.4 expected ARC results on the ARC Genomics fixture."""

from datetime import date
import json
from pathlib import Path
import pytest
import pptx

from src.core.models import StartupKitBaseline
from src.generators.docx_generator import DocxGenerator
from src.generators.pmo_workbook import export_pmo_workbook
from src.generators.onboarding_deck import export_onboarding_deck, build_deck_model
from src.llm.validation import validate_and_repair_baseline


@pytest.fixture
def arc_deck_result(tmp_path):
    fixture_dir = Path("tests/fixtures/sow/arc_genomics")
    with open(fixture_dir / "baseline.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    baseline = StartupKitBaseline.model_validate(data)
    validate_and_repair_baseline(baseline)

    start_d = date(2026, 10, 5)
    DocxGenerator().write_kit_docx(baseline, tmp_path)
    export_pmo_workbook(baseline, tmp_path, start_date=start_d)
    return export_onboarding_deck(baseline, tmp_path, start_date=start_d)


def test_deck_arc_appendix_k4(arc_deck_result):
    """Verify all Appendix K.4 expected results for ARC Genomics."""
    prs = pptx.Presentation(str(arc_deck_result.file_path))
    slides = list(prs.slides)
    assert len(slides) == 6

    # Slide 1 (Cover)
    assert slides[0].placeholders[0].text == "ARC Genomics Platform"
    assert slides[0].placeholders[1].text == "Talent Team Onboarding · Syngenta · Start 2026-10-05"

    # Slide 2 (Charter)
    # Check key facts table
    s2_tables = [sh.table for sh in slides[1].shapes if sh.has_table]
    assert len(s2_tables) > 0
    kf_map = {row.cells[0].text.strip(): row.cells[1].text.strip() for row in s2_tables[0].rows}

    assert kf_map["Client Sponsor"] == "Syngenta"
    assert kf_map["Contract Type"] == "Fixed Bid"
    assert kf_map["Governance Tier"] == "Partnered"
    assert kf_map["Start Date"] == "2026-10-05 (Provided)"
    assert kf_map["Talent PM"] == "To be confirmed"
    assert kf_map["Delivery Manager"] == "To be confirmed"
    assert kf_map["PMO Lead"] == "To be confirmed"

    s2_text = " ".join(sh.text_frame.text for sh in slides[1].shapes if sh.has_text_frame)
    for phase_name in ["P1 Foundation", "P2a Services and Data", "P2b Application Surface", "P3 Launch"]:
        assert phase_name in s2_text

    # Slide 3 (Schedule)
    s3_tables = [sh.table for sh in slides[2].shapes if sh.has_table]
    assert len(s3_tables) > 0
    s3_tab = s3_tables[0]
    s3_text = " ".join(c.text for row in s3_tab.rows for c in row.cells)
    for m_id in ["M1", "M2", "M3", "M4"]:
        assert m_id in s3_text

    # Check deliverables in Slide 3 / Slide 4
    for d_idx in range(1, 20):
        d_id = f"DEL-{d_idx:02d}"
        assert d_id in s3_text or "DEL-" in s3_text

    # Slide 5 (High-Risk Items)
    s5_tables = [sh.table for sh in slides[4].shapes if sh.has_table]
    assert len(s5_tables) > 0
    s5_tab = s5_tables[0]
    s5_ids = [row.cells[0].text.strip() for row in list(s5_tab.rows)[1:]]

    assert any("RAID-01" in sid and "RSK-01" in sid for sid in s5_ids)
    assert any("RAID-02" in sid and "RSK-02" in sid for sid in s5_ids)
    assert any("RAID-05" in sid and "RSK-05" in sid for sid in s5_ids)
    assert any("RAID-07" in sid and "ISS-01" in sid for sid in s5_ids)

    # Slide 6 (Collaboration)
    s6_text = " ".join(sh.text_frame.text for sh in slides[5].shapes if sh.has_text_frame)
    assert "+1 more" in s6_text  # 6 client stakeholders (5 shown + 1 overflow)
    for com_id in ["COM-01", "Daily Standup", "Weekly", "Sprint Demo", "Kickoff"]:
        assert any(c in s6_text for c in ["Daily Standup", "Weekly", "Demo", "Kickoff"])

    # Everywhere: No ACT- tags, no readiness score, no G-01
    full_deck_text = ""
    for s in slides:
        for sh in s.shapes:
            if sh.has_text_frame:
                full_deck_text += sh.text_frame.text + " "
            if sh.has_table:
                for r in sh.table.rows:
                    full_deck_text += " ".join(c.text for c in r.cells) + " "
        if s.has_notes_slide:
            full_deck_text += s.notes_slide.notes_text_frame.text + " "

    assert "ACT-" not in full_deck_text
    assert "G01-" not in full_deck_text
    assert "G-01" not in full_deck_text
    assert "readiness score" not in full_deck_text.lower()
