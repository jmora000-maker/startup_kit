"""Base extractor classes and utilities."""

import os
from pathlib import Path
from typing import List, Set
from src.core.interfaces import IDocumentExtractor
from src.core.models import ExtractedDocument, DocumentSection


class BaseDocumentExtractor(IDocumentExtractor):
    """Base class for all concrete document format extractors."""

    supported_extensions: Set[str] = set()

    def supports(self, file_path: Path) -> bool:
        """Check if file extension is supported."""
        if not file_path:
            return False
        return file_path.suffix.lower() in self.supported_extensions

    def _validate_file(self, file_path: Path) -> None:
        """Validate file existence and readability."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if not file_path.is_file():
            raise ValueError(f"Target path is not a file: {file_path}")
        if file_path.stat().st_size == 0:
            raise ValueError(f"File is empty: {file_path}")

    @staticmethod
    def _clean_text(text: str) -> str:
        """Normalize whitespace and strip control characters."""
        if not text:
            return ""
        lines = [line.strip() for line in text.splitlines()]
        # Remove excessive empty lines while preserving paragraph boundaries
        cleaned_lines = []
        consecutive_empty = 0
        for line in lines:
            if not line:
                consecutive_empty += 1
                if consecutive_empty <= 1:
                    cleaned_lines.append("")
            else:
                consecutive_empty = 0
                cleaned_lines.append(line)
        return "\n".join(cleaned_lines).strip()
