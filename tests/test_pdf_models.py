"""Unit tests for PDF page and document metadata models."""

import pytest
from pydantic import ValidationError
from src.core.pdf_models import PDFPageMetadata, PDFDocumentMetadata


def test_pdf_page_metadata_valid():
    """Valid float coordinates and page number pass validation."""
    meta = PDFPageMetadata(page_number=1, rect=[0.0, 0.0, 612.0, 792.0])
    assert meta.page_number == 1
    assert meta.rect == [0.0, 0.0, 612.0, 792.0]


def test_pdf_page_metadata_rect_coercion():
    """Integer coordinates are properly coerced to floats."""
    meta = PDFPageMetadata(page_number=1, rect=[0, 0, 600, 800])
    assert meta.page_number == 1
    assert meta.rect == [0.0, 0.0, 600.0, 800.0]
    assert all(isinstance(c, float) for c in meta.rect)


def test_pdf_page_metadata_negative_coords():
    """Negative coordinates within valid bounds pass validation."""
    meta = PDFPageMetadata(page_number=1, rect=[-10.0, -20.0, 500.0, 700.0])
    assert meta.rect == [-10.0, -20.0, 500.0, 700.0]


def test_pdf_page_metadata_invalid_page_num():
    """Invalid page numbers (0, negative, string, float, bool) raise ValidationError."""
    for invalid_val in [0, -1, "1", 1.5, 1.0, True, False]:
        with pytest.raises(ValidationError):
            PDFPageMetadata(page_number=invalid_val, rect=[0.0, 0.0, 100.0, 100.0])


def test_pdf_page_metadata_invalid_rect_len():
    """Rectangles with fewer or more than 4 coordinates raise ValidationError."""
    with pytest.raises(ValidationError):
        PDFPageMetadata(page_number=1, rect=[0.0, 0.0, 100.0])
    with pytest.raises(ValidationError):
        PDFPageMetadata(page_number=1, rect=[0.0, 0.0, 100.0, 100.0, 100.0])
    with pytest.raises(ValidationError):
        PDFPageMetadata(page_number=1, rect="invalid")


def test_pdf_page_metadata_non_numeric_rect():
    """Non-numeric and boolean items in rect raise ValidationError."""
    with pytest.raises(ValidationError):
        PDFPageMetadata(page_number=1, rect=[0.0, 0.0, "100.0", 200.0])
    with pytest.raises(ValidationError):
        PDFPageMetadata(page_number=1, rect=[True, 0.0, 100.0, 200.0])
    with pytest.raises(ValidationError):
        PDFPageMetadata(page_number=1, rect=[0.0, False, 100.0, 200.0])


def test_pdf_page_metadata_non_finite_rect():
    """NaN and infinite coordinates raise ValidationError."""
    with pytest.raises(ValidationError):
        PDFPageMetadata(page_number=1, rect=[0.0, 0.0, float("nan"), 100.0])
    with pytest.raises(ValidationError):
        PDFPageMetadata(page_number=1, rect=[0.0, 0.0, float("inf"), 100.0])
    with pytest.raises(ValidationError):
        PDFPageMetadata(page_number=1, rect=[float("-inf"), 0.0, 100.0, 100.0])


def test_pdf_page_metadata_inverted_bounds():
    """Reversed bounding box coordinates (x1 < x0 or y1 < y0) raise ValidationError."""
    with pytest.raises(ValidationError, match="x1 .* must be greater than or equal to x0"):
        PDFPageMetadata(page_number=1, rect=[100.0, 0.0, 50.0, 200.0])
    with pytest.raises(ValidationError, match="y1 .* must be greater than or equal to y0"):
        PDFPageMetadata(page_number=1, rect=[0.0, 200.0, 100.0, 50.0])


def test_pdf_page_metadata_extra_preserved():
    """Extra metadata fields are preserved under ConfigDict(extra='allow')."""
    meta = PDFPageMetadata(page_number=1, rect=[0.0, 0.0, 100.0, 100.0], custom_tag="annot_1")
    dumped = meta.model_dump()
    assert dumped["custom_tag"] == "annot_1"


def test_pdf_doc_metadata_valid():
    """Valid document metadata passes validation."""
    doc_meta = PDFDocumentMetadata(total_pages=5, title="Doc Title", author="Author Name", subject="Topic")
    assert doc_meta.total_pages == 5
    assert doc_meta.title == "Doc Title"
    assert doc_meta.author == "Author Name"
    assert doc_meta.subject == "Topic"


def test_pdf_doc_metadata_none_normalization():
    """Explicit None values for title, author, and subject normalize to empty strings."""
    doc_meta = PDFDocumentMetadata(total_pages=3, title=None, author=None, subject=None)
    assert doc_meta.title == ""
    assert doc_meta.author == ""
    assert doc_meta.subject == ""


def test_pdf_doc_metadata_invalid_types():
    """Invalid types for total_pages, title, author, and subject raise ValidationError."""
    with pytest.raises(ValidationError):
        PDFDocumentMetadata(total_pages=-1)
    with pytest.raises(ValidationError):
        PDFDocumentMetadata(total_pages="5")
    with pytest.raises(ValidationError):
        PDFDocumentMetadata(total_pages=True)
    with pytest.raises(ValidationError):
        PDFDocumentMetadata(total_pages=1, title=123)
    with pytest.raises(ValidationError):
        PDFDocumentMetadata(total_pages=1, author=["Author"])


def test_pdf_doc_metadata_zero_pages():
    """total_pages=0 passes schema validation."""
    doc_meta = PDFDocumentMetadata(total_pages=0)
    assert doc_meta.total_pages == 0
    assert doc_meta.title == ""
