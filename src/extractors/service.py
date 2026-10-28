"""Central document ingestion service coordinating file discovery and extraction."""

import logging
import shutil
import tempfile
from pathlib import Path
from typing import BinaryIO, List, Optional, Sequence, Tuple, Union
from src.core.interfaces import IDocumentExtractor
from src.core.models import ExtractedDocument
from src.extractors.pdf_extractor import PDFExtractor
from src.extractors.docx_extractor import DocxExtractor
from src.extractors.pptx_extractor import PPTXExtractor
from src.extractors.txt_extractor import TxtExtractor

logger = logging.getLogger(__name__)

# HTL-16/HTL-18 (C-11) / HTL-57: an "upload" source is a (file_name, content) or (file_name, content, role) pair,
# where content is either raw bytes or a file-like object supporting .read(), and role is "sow" or "supporting".
UploadSource = Union[
    Tuple[str, Union[bytes, BinaryIO]],
    Tuple[str, Union[bytes, BinaryIO], str],
]
IngestSource = Union[str, Path, UploadSource]


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

    def ingest_directory(self, dir_path: Path, default_role: str = "sow") -> List[ExtractedDocument]:
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
                        if doc:
                            doc.metadata.setdefault("document_role", default_role)
                            extracted_docs.append(doc)
                    except Exception as e:
                        logger.warning("Skipping corrupted or unreadable file %s: %s", file_path.name, e)

        if not extracted_docs:
            logger.warning("No valid supported documents were extracted from %s", dir_path)

        return extracted_docs

    def ingest_sources(
        self,
        sources: Sequence[IngestSource],
        default_role: str = "sow",
    ) -> List[ExtractedDocument]:
        """HTL-16/HTL-18 (C-11) / HTL-57: ingest a mix of on-disk paths and in-memory uploads.

        Each item in ``sources`` is either a path (``str``/``Path``) or an upload tuple
        ``(file_name, content)`` or ``(file_name, content, role)`` where ``content`` is ``bytes``
        or a file-like object, and ``role`` is "sow" or "supporting".
        """
        extracted_docs: List[ExtractedDocument] = []
        tmp_dir: Optional[str] = None
        try:
            for source in sources:
                if isinstance(source, (str, Path)):
                    file_path = Path(source)
                    if not file_path.is_file():
                        logger.warning("Skipping non-existent input path: %s", file_path)
                        continue
                    try:
                        doc = self.ingest_file(file_path)
                    except Exception as e:
                        logger.warning("Skipping corrupted or unreadable file %s: %s", file_path.name, e)
                        continue
                    if doc:
                        doc.metadata.setdefault("document_role", default_role)
                        extracted_docs.append(doc)
                    continue

                # Upload-style source: (file_name, bytes-or-file-like) or (file_name, bytes, role)
                if len(source) == 3:
                    file_name, content, doc_role = source
                else:
                    file_name, content = source
                    doc_role = default_role

                if tmp_dir is None:
                    tmp_dir = tempfile.mkdtemp(prefix="startup_kit_upload_")
                temp_path = Path(tmp_dir) / Path(file_name).name
                data = content.read() if hasattr(content, "read") else content
                if isinstance(data, str):
                    data = data.encode("utf-8")
                temp_path.write_bytes(data)
                try:
                    doc = self.ingest_file(temp_path)
                except Exception as e:
                    logger.warning("Skipping corrupted or unreadable upload %s: %s", file_name, e)
                    continue
                if doc:
                    doc.metadata["document_role"] = doc_role
                    extracted_docs.append(doc)

            if not extracted_docs:
                logger.warning("No valid supported documents were extracted from the provided sources")

            return extracted_docs
        finally:
            if tmp_dir is not None:
                shutil.rmtree(tmp_dir, ignore_errors=True)
