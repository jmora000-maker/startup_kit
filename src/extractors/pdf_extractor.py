"""PDF document extractor using PyMuPDF (fitz)."""

from pathlib import Path
from typing import List, Set
import pymupdf as fitz
from src.extractors.base import BaseDocumentExtractor
from src.core.models import ExtractedDocument, DocumentSection


class PDFExtractor(BaseDocumentExtractor):
    """Extractor for Adobe PDF documents."""

    supported_extensions: Set[str] = {".pdf"}

    def extract(self, file_path: Path) -> ExtractedDocument:
        self._validate_file(file_path)

        doc = fitz.open(str(file_path))
        sections: List[DocumentSection] = []
        full_text_parts: List[str] = []

        try:
            total_pages = len(doc)
            for page_idx in range(total_pages):
                page = doc[page_idx]
                page_text = page.get_text("text") or ""
                page_text_clean = self._clean_text(page_text)

                if page_text_clean:
                    full_text_parts.append(f"--- Page {page_idx + 1} ---\n{page_text_clean}")

                sections.append(
                    DocumentSection(
                        title=f"Page {page_idx + 1}",
                        content=page_text_clean,
                        metadata={
                            "page_number": page_idx + 1,
                            "rect": [page.rect.x0, page.rect.y0, page.rect.x1, page.rect.y1],
                        }
                    )
                )

            metadata = {
                "total_pages": total_pages,
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
            }

            combined_text = "\n\n".join(full_text_parts)

            return ExtractedDocument(
                file_name=file_path.name,
                file_type="pdf",
                file_path=file_path,
                text_content=combined_text,
                sections=sections,
                metadata=metadata
            )
        finally:
            doc.close()
