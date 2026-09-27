"""PPTX presentation extractor using python-pptx."""

from pathlib import Path
from typing import List, Set, Dict, Any
from pptx import Presentation
from src.extractors.base import BaseDocumentExtractor
from src.core.models import ExtractedDocument, DocumentSection


class PPTXExtractor(BaseDocumentExtractor):
    """Extractor for Microsoft PowerPoint (.pptx) presentations."""

    supported_extensions: Set[str] = {".pptx", ".ppt"}

    def extract(self, file_path: Path) -> ExtractedDocument:
        self._validate_file(file_path)

        prs = Presentation(str(file_path))
        sections: List[DocumentSection] = []
        full_text_parts: List[str] = []

        for slide_idx, slide in enumerate(prs.slides, start=1):
            slide_title = ""
            slide_text_blocks: List[str] = []

            # 1. Extract slide shapes and tables
            for shape in slide.shapes:
                if shape.has_text_frame:
                    text = shape.text_frame.text.strip()
                    if text:
                        if shape == slide.shapes.title:
                            slide_title = text
                        else:
                            slide_text_blocks.append(text)
                elif shape.has_table:
                    table_rows = []
                    for row in shape.table.rows:
                        row_cells = [self._clean_text(cell.text).replace("\n", " ") for cell in row.cells]
                        table_rows.append(" | ".join(row_cells))
                    if table_rows:
                        slide_text_blocks.append("[Table]\n" + "\n".join(table_rows))

            # 2. Extract speaker notes
            speaker_notes = ""
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                speaker_notes = slide.notes_slide.notes_text_frame.text.strip()

            title_display = f"Slide {slide_idx}: {slide_title}" if slide_title else f"Slide {slide_idx}"
            body_content = "\n".join(slide_text_blocks).strip()

            full_slide_desc = [f"=== {title_display} ==="]
            if body_content:
                full_slide_desc.append(body_content)
            if speaker_notes:
                full_slide_desc.append(f"[Speaker Notes]: {speaker_notes}")

            slide_full_str = "\n".join(full_slide_desc)
            full_text_parts.append(slide_full_str)

            sections.append(
                DocumentSection(
                    title=title_display,
                    content=body_content,
                    metadata={
                        "slide_number": slide_idx,
                        "slide_title": slide_title,
                        "speaker_notes": speaker_notes
                    }
                )
            )

        metadata: Dict[str, Any] = {
            "total_slides": len(prs.slides),
        }

        combined_text = "\n\n".join(full_text_parts)

        return ExtractedDocument(
            file_name=file_path.name,
            file_type="pptx",
            file_path=file_path,
            text_content=combined_text,
            sections=sections,
            metadata=metadata
        )
