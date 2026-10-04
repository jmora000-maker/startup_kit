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

# HTL-16/HTL-18 (C-11): an "upload" source is a (file_name, content) pair, where content is
# either raw bytes or a file-like object supporting .read(). This is how the future Streamlit
# app's st.file_uploader output is represented without changing any path-based extractor.
UploadSource = Tuple[str, Union[bytes, BinaryIO]]
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

    def ingest_sources(self, sources: Sequence[IngestSource]) -> List[ExtractedDocument]:
        """HTL-16/HTL-18 (C-11): ingest a mix of on-disk paths and in-memory uploads.

        Each item in ``sources`` is either a path (``str``/``Path``) or an upload pair
        ``(file_name, content)`` where ``content`` is ``bytes`` or a file-like object. Uploads
        have no disk path until something chooses to save them, so this is the "thin adapter"
        the HTL-18 audit notes as an acceptable alternative to rewriting every extractor to
        accept a stream directly: each upload is written to a per-call temporary file
        (preserving its given name/extension so the right extractor is still selected via the
        existing, unchanged path-based ``extract``/``supports`` API), ingested, then removed.
        Plain paths are ingested exactly as ``ingest_file`` already does, with no adapter.
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
                        extracted_docs.append(doc)
                    continue

                # Upload-style source: (file_name, bytes-or-file-like)
                file_name, content = source
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
                    extracted_docs.append(doc)

            if not extracted_docs:
                logger.warning("No valid supported documents were extracted from the provided sources")

            return extracted_docs
        finally:
            if tmp_dir is not None:
                shutil.rmtree(tmp_dir, ignore_errors=True)
