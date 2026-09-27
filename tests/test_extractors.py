"""Unit tests for document extractors and ingestion service."""

import pytest
from pathlib import Path
import pymupdf as fitz
import docx
from pptx import Presentation
from pptx.util import Inches

from src.extractors.base import BaseDocumentExtractor
from src.extractors.pdf_extractor import PDFExtractor
from src.extractors.docx_extractor import DocxExtractor
from src.extractors.pptx_extractor import PPTXExtractor
from src.extractors.txt_extractor import TxtExtractor
from src.extractors.service import IngestionService
from src.core.models import ExtractedDocument, DocumentSection


@pytest.fixture
def temp_test_dir(tmp_path):
    d = tmp_path / "test_inputs"
    d.mkdir()
    return d


def test_txt_extractor(temp_test_dir):
    txt_file = temp_test_dir / "context.txt"
    txt_file.write_text("Project Sponsor: John Doe\nBudget: $500k", encoding="utf-8")

    extractor = TxtExtractor()
    assert extractor.supports(txt_file) is True

    doc = extractor.extract(txt_file)
    assert doc.file_name == "context.txt"
    assert doc.file_type == "txt"
    assert "Project Sponsor: John Doe" in doc.text_content
    assert len(doc.sections) == 1


def test_pdf_extractor(temp_test_dir):
    pdf_file = temp_test_dir / "test_sow.pdf"
    doc_fitz = fitz.open()
    page1 = doc_fitz.new_page()
    page1.insert_text((50, 50), "Statement of Work: Project Apollo\nDeliverable: Cloud Architecture")
    page2 = doc_fitz.new_page()
    page2.insert_text((50, 50), "Milestone M1: Kickoff by 2026-10-01")
    doc_fitz.save(str(pdf_file))
    doc_fitz.close()

    extractor = PDFExtractor()
    assert extractor.supports(pdf_file) is True

    extracted = extractor.extract(pdf_file)
    assert extracted.file_name == "test_sow.pdf"
    assert extracted.file_type == "pdf"
    assert extracted.metadata["total_pages"] == 2
    assert len(extracted.sections) == 2
    assert "Project Apollo" in extracted.text_content
    assert "Milestone M1" in extracted.text_content


def test_docx_extractor(temp_test_dir):
    docx_file = temp_test_dir / "test_contract.docx"
    doc_docx = docx.Document()
    doc_docx.add_heading("Section 1: Scope", level=1)
    doc_docx.add_paragraph("This is the project scope description.")
    
    table = doc_docx.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Role"
    table.cell(0, 1).text = "Resource"
    table.cell(1, 0).text = "Talent PM"
    table.cell(1, 1).text = "Alice"
    
    doc_docx.save(str(docx_file))

    extractor = DocxExtractor()
    assert extractor.supports(docx_file) is True

    extracted = extractor.extract(docx_file)
    assert extracted.file_name == "test_contract.docx"
    assert extracted.file_type == "docx"
    assert "Section 1: Scope" in extracted.text_content
    assert "This is the project scope description." in extracted.text_content
    assert "Talent PM | Alice" in extracted.text_content


def test_pptx_extractor(temp_test_dir):
    pptx_file = temp_test_dir / "test_deck.pptx"
    prs = Presentation()
    slide_layout = prs.slide_layouts[0]  # Title slide
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    title.text = "PMO Governance Overview"
    subtitle.text = "Partnered Governance Model"

    # Add speaker notes
    notes_slide = slide.notes_slide
    text_frame = notes_slide.notes_text_frame
    text_frame.text = "Ensure PM and DM are briefed on the G-01 checklist."

    prs.save(str(pptx_file))

    extractor = PPTXExtractor()
    assert extractor.supports(pptx_file) is True

    extracted = extractor.extract(pptx_file)
    assert extracted.file_name == "test_deck.pptx"
    assert extracted.file_type == "pptx"
    assert "PMO Governance Overview" in extracted.text_content
    assert "Ensure PM and DM are briefed on the G-01 checklist." in extracted.text_content
    assert len(extracted.sections) == 1
    assert extracted.sections[0].metadata["speaker_notes"] == "Ensure PM and DM are briefed on the G-01 checklist."


def test_ingestion_service(temp_test_dir):
    # Create multiple files
    (temp_test_dir / "note.txt").write_text("Context notes", encoding="utf-8")
    
    doc_docx = docx.Document()
    doc_docx.add_paragraph("Docx notes")
    doc_docx.save(str(temp_test_dir / "spec.docx"))

    service = IngestionService()
    docs = service.ingest_directory(temp_test_dir)
    assert len(docs) == 2
    names = {d.file_name for d in docs}
    assert names == {"note.txt", "spec.docx"}


def test_ingestion_service_empty_and_missing_dir(tmp_path):
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()

    service = IngestionService()
    docs = service.ingest_directory(empty_dir)
    assert docs == []

    with pytest.raises(FileNotFoundError):
        service.ingest_directory(tmp_path / "non_existent_folder")


def test_ingestion_service_ocp_custom_extractor(temp_test_dir):
    class CustomLogExtractor(BaseDocumentExtractor):
        supported_extensions = {".log"}
        def extract(self, file_path: Path) -> ExtractedDocument:
            return ExtractedDocument(
                file_name=file_path.name,
                file_type="log",
                file_path=file_path,
                text_content=file_path.read_text(encoding="utf-8"),
                sections=[]
            )

    log_file = temp_test_dir / "app.log"
    log_file.write_text("System startup log", encoding="utf-8")

    service = IngestionService()
    service.register_extractor(CustomLogExtractor())
    doc = service.ingest_file(log_file)
    assert doc is not None
    assert doc.file_type == "log"
    assert "System startup log" in doc.text_content
