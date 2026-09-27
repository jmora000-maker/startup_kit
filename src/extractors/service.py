"""Central document ingestion service coordinating file discovery and extraction."""

import logging
from pathlib import Path
from typing import List, Optional, Sequence
from src.core.interfaces import IDocumentExtractor
from src.core.models import ExtractedDocument
from src.extractors.pdf_extractor import PDFExtractor
from src.extractors.docx_extractor import DocxExtractor
from src.extractors.pptx_extractor import PPTXExtractor
from src.extractors.txt_extractor import TxtExtractor

logger = logging.getLogger(__name__)


class IngestionService:
    """Service that scans input folders and delegates parsing to appropriate extractors."""

    def __init__(self, extractors: Optional[Sequence[IDocumentExtractor]] = None):
        if extractors is None:
            self.extractors: List[IDocumentExtractor] = [
                PDFExtractor(),
                DocxExtractor(),
                PPTXExtractor(),
                TxtExtractor(),
            ]
        else:
            self.extractors = list(extractors)

    def register_extractor(self, extractor: IDocumentExtractor) -> None:
        """Register a new format extractor conforming to OCP."""
        self.extractors.insert(0, extractor)

    def get_extractor_for(self, file_path: Path) -> Optional[IDocumentExtractor]:
        """Find the first matching extractor for the given file."""
        for extractor in self.extractors:
            if extractor.supports(file_path):
                return extractor
        return None

    def ingest_file(self, file_path: Path) -> Optional[ExtractedDocument]:
        """Ingest a single file with appropriate error handling."""
        extractor = self.get_extractor_for(file_path)
        if not extractor:
            logger.warning("No supported extractor found for file: %s", file_path.name)
            return None

        try:
            logger.info("Extracting document: %s using %s", file_path.name, extractor.__class__.__name__)
            return extractor.extract(file_path)
        except Exception as exc:
            logger.error("Failed to extract file %s: %s", file_path, exc, exc_info=True)
            raise

    def ingest_directory(self, dir_path: Path) -> List[ExtractedDocument]:
        """Scan input directory and ingest all supported files."""
        if not dir_path.exists():
            raise FileNotFoundError(f"Input directory does not exist: {dir_path}")

        if not dir_path.is_dir():
            raise NotADirectoryError(f"Provided path is not a directory: {dir_path}")

        all_files = sorted(list(dir_path.iterdir()), key=lambda f: f.name)
        extracted_docs: List[ExtractedDocument] = []

        for file_path in all_files:
            if file_path.is_file() and not file_path.name.startswith("~") and not file_path.name.startswith("."):
                extractor = self.get_extractor_for(file_path)
                if extractor:
                    try:
                        doc = extractor.extract(file_path)
                        extracted_docs.append(doc)
                    except Exception as e:
                        logger.warning("Skipping corrupted or unreadable file %s: %s", file_path.name, e)

        if not extracted_docs:
            logger.warning("No valid supported documents were extracted from %s", dir_path)

        return extracted_docs
