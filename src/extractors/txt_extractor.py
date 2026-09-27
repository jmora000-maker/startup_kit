"""Plain text and markdown document extractor."""

from pathlib import Path
from typing import Set
from src.extractors.base import BaseDocumentExtractor
from src.core.models import ExtractedDocument, DocumentSection


class TxtExtractor(BaseDocumentExtractor):
    """Extractor for plain text (.txt) and markdown (.md) context files."""

    supported_extensions: Set[str] = {".txt", ".text", ".md"}

    def extract(self, file_path: Path) -> ExtractedDocument:
        self._validate_file(file_path)

        # Try UTF-8 first, fallback to latin-1
        try:
            raw_text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raw_text = file_path.read_text(encoding="latin-1")

        cleaned_text = self._clean_text(raw_text)

        sections = [
            DocumentSection(
                title=f"Content of {file_path.name}",
                content=cleaned_text,
                metadata={"file_name": file_path.name}
            )
        ]

        return ExtractedDocument(
            file_name=file_path.name,
            file_type="txt",
            file_path=file_path,
            text_content=cleaned_text,
            sections=sections,
            metadata={"char_count": len(cleaned_text), "lines_count": len(cleaned_text.splitlines())}
        )
