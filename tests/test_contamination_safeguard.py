"""tests/test_contamination_safeguard.py

Comprehensive regression tests for the HTL-69 anti-contamination safeguards:
1. create_test_baseline factory behavior, isolation, and override semantics.
2. assert_no_cross_client_contamination multi-format text extraction (PPTX, DOCX, XLSX).
3. Failure Mode 1: Catching synthetic cross-client pollution (peer client terms).
4. Failure Mode 2: Catching synthetic template residue (HTL-100 keywords like Rimage, JD Edwards).
5. Allowed terms bypass and clean artifact validation.
"""

from pathlib import Path
import docx
import openpyxl
import pptx
from pptx.util import Inches, Pt
import pytest

from src.core.models import StartupKitBaseline
from src.generators.client_deck import export_client_deck
from src.generators.docx_generator import DocxGenerator
from src.generators.governance_deck import export_governance_deck
from src.generators.pmo_workbook import export_pmo_workbook
from tests.contamination import (
    GLOBAL_TEMPLATE_CONTAMINATION_KEYWORDS,
    assert_no_cross_client_contamination,
    extract_artifact_text_segments,
)
from tests.factories.baseline_factory import create_test_baseline


def test_create_test_baseline_defaults():
    """Verify baseline factory produces a valid, clean StartupKitBaseline from scratch."""
    baseline = create_test_baseline()
    assert isinstance(baseline, StartupKitBaseline)
    assert baseline.project_name == "Test Alpha Modernization"
    assert baseline.charter.client_name == "Acme Global Industries"
    assert baseline.governance_tier == "Partnered"
    assert len(baseline.deliverables) == 2
    assert len(baseline.milestones) == 1
    assert baseline.charter.pmo_lead == "Alex PMO"
    assert baseline.interim_checkpoints == []
    assert baseline.decisions == []
    assert baseline.raci_matrix == []


def test_create_test_baseline_custom_overrides():
    """Verify baseline factory supports deep kwargs and model overrides."""
    baseline = create_test_baseline(
        project_name="Custom Beta Integration",
        client_name="Beta Systems Corp",
        governance_tier="Elevated",
        charter={"project_purpose": "Custom purpose definition for Beta Corp."},
    )
    assert baseline.project_name == "Custom Beta Integration"
    assert baseline.charter.client_name == "Beta Systems Corp"
    assert baseline.governance_tier == "Elevated"
    assert baseline.charter.project_purpose == "Custom purpose definition for Beta Corp."


def test_clean_artifacts_pass_contamination_check(tmp_path):
    """Verify clean artifacts generated from factory baseline pass without violations."""
    baseline = create_test_baseline()
    deck_res = export_client_deck(baseline, tmp_path / "client_deck")
    gov_res = export_governance_deck(baseline, tmp_path / "gov_deck")
    kit_path = DocxGenerator(generated_date="2026-11-02").write_kit_docx(baseline, tmp_path / "docx")
    wb_res = export_pmo_workbook(baseline, tmp_path / "xlsx")

    # None of these clean artifacts should contain cross-client or template keywords
    assert_no_cross_client_contamination(
        artifact_path=deck_res.file_path,
        client_name="Acme Global Industries",
        forbidden_keywords=["ARC Genomics", "Portland General Electric", "Syngenta", "Pfizer"],
    )
    assert_no_cross_client_contamination(
        artifact_path=gov_res.file_path,
        client_name="Acme Global Industries",
        forbidden_keywords=["ARC Genomics", "Portland General Electric", "Syngenta", "Pfizer"],
    )
    assert_no_cross_client_contamination(
        artifact_path=kit_path,
        client_name="Acme Global Industries",
        forbidden_keywords=["ARC Genomics", "Portland General Electric", "Syngenta", "Pfizer"],
    )
    assert_no_cross_client_contamination(
        artifact_path=wb_res.file_path,
        client_name="Acme Global Industries",
        forbidden_keywords=["ARC Genomics", "Portland General Electric", "Syngenta", "Pfizer"],
    )


def test_failure_mode_1_cross_client_pollution_detected_in_pptx(tmp_path):
    """Failure Mode 1: Catches peer-client terms injected into PPTX presentation."""
    prs = pptx.Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout
    tx_box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(5), Inches(2))
    tf = tx_box.text_frame
    tf.text = "Deliverables for Portland General Electric migration including ARC Genomics pipeline specs."
    pptx_path = tmp_path / "contaminated_deck.pptx"
    prs.save(str(pptx_path))

    with pytest.raises(AssertionError) as exc_info:
        assert_no_cross_client_contamination(
            artifact_path=pptx_path,
            client_name="Portland General Electric",
            forbidden_keywords=["ARC Genomics", "Syngenta"],
        )
    err_msg = str(exc_info.value)
    assert "Cross-client / template contamination detected" in err_msg
    assert "contaminated_deck.pptx" in err_msg
    assert "Portland General Electric" in err_msg
    assert "Found forbidden term 'ARC Genomics'" in err_msg


def test_failure_mode_1_cross_client_pollution_detected_in_docx_table(tmp_path):
    """Failure Mode 1: Catches peer-client terms injected into DOCX table."""
    doc = docx.Document()
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Workstream"
    table.cell(0, 1).text = "Owner"
    table.cell(1, 0).text = "Bioinformatics Pipeline (Syngenta Crop Protection, LLC)"
    table.cell(1, 1).text = "Lead Architect"
    docx_path = tmp_path / "contaminated_doc.docx"
    doc.save(str(docx_path))

    with pytest.raises(AssertionError) as exc_info:
        assert_no_cross_client_contamination(
            artifact_path=docx_path,
            client_name="Acme Global",
            forbidden_keywords=["Syngenta", "ARC Genomics"],
        )
    assert "Found forbidden term 'Syngenta'" in str(exc_info.value)


def test_failure_mode_1_cross_client_pollution_detected_in_xlsx(tmp_path):
    """Failure Mode 1: Catches peer-client terms injected into XLSX cell."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Milestones"
    ws["A1"] = "Milestone Name"
    ws["A2"] = "Pfizer Global Analytics Migration Gate 1"
    xlsx_path = tmp_path / "contaminated_sheet.xlsx"
    wb.save(str(xlsx_path))

    with pytest.raises(AssertionError) as exc_info:
        assert_no_cross_client_contamination(
            artifact_path=xlsx_path,
            client_name="Acme Global",
            forbidden_keywords=["Pfizer", "ARC Genomics"],
        )
    assert "Found forbidden term 'Pfizer'" in str(exc_info.value)


def test_failure_mode_2_template_residue_detected_automatically(tmp_path):
    """Failure Mode 2: Catches global template keywords (HTL-100) even with empty caller forbidden_keywords."""
    prs = pptx.Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    tx_box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(5), Inches(2))
    tx_box.text_frame.text = "Architecture involves JD Edwards ERP integration and OCI landing zone configuration."
    pptx_path = tmp_path / "template_leak_deck.pptx"
    prs.save(str(pptx_path))

    # Caller provides empty forbidden_keywords, but template keywords must catch it
    with pytest.raises(AssertionError) as exc_info:
        assert_no_cross_client_contamination(
            artifact_path=pptx_path,
            client_name="Acme Global",
            forbidden_keywords=[],
            include_template_keywords=True,
        )
    err_msg = str(exc_info.value)
    assert "Found forbidden term 'JD Edwards'" in err_msg or "Found forbidden term 'OCI landing zone'" in err_msg


def test_allowed_terms_bypass(tmp_path):
    """Verify explicitly allowed terms are not flagged as violations."""
    prs = pptx.Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    tx_box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(5), Inches(2))
    tx_box.text_frame.text = "Legacy Rimage CD publisher decommission project."
    pptx_path = tmp_path / "rimage_client_deck.pptx"
    prs.save(str(pptx_path))

    # Allowed terms includes "Rimage", so it shouldn't raise even though Rimage is a global template keyword
    assert_no_cross_client_contamination(
        artifact_path=pptx_path,
        client_name="Rimage Corporation",
        forbidden_keywords=[],
        allowed_terms=["Rimage"],
    )


def test_missing_file_raises_filenotfound():
    """Verify non-existent artifact path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        assert_no_cross_client_contamination(
            artifact_path="non_existent_file.pptx",
            client_name="Acme",
            forbidden_keywords=["ARC"],
        )
