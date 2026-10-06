"""Abstract interfaces for the Startup Kit application."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Type, TypeVar, Optional, Any
from src.core.models import ExtractedDocument, ReviewRun, ReviewRunSummary, StartupKitBaseline

T = TypeVar("T")


class IDocumentExtractor(ABC):
    """Abstract base extractor for individual document formats."""

    @abstractmethod
    def extract(self, file_path: Path) -> ExtractedDocument:
        """Extract text, sections, and metadata from a document file."""
        pass

    @abstractmethod
    def supports(self, file_path: Path) -> bool:
        """Check if this extractor supports the given file format."""
        pass


class ILLMClient(ABC):
    """Abstract interface for LLM client integration."""

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None
    ) -> T:
        """Generate a structured response adhering to a given Pydantic schema."""
        pass

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate free-form text response."""
        pass


class IDomainExtractor(ABC):
    """Abstract interface for domain-specific LLM extraction passes."""

    @abstractmethod
    def extract(
        self,
        documents: List[ExtractedDocument],
        llm_client: ILLMClient
    ) -> Any:
        """Execute a domain-specific extraction pass."""
        pass


class IDocumentWriter(ABC):
    """Abstract interface for document report generation."""

    @abstractmethod
    def write_docx(
        self,
        baseline: StartupKitBaseline,
        output_path: Path
    ) -> Path:
        """Generate and save the Microsoft Word Startup Kit document."""
        pass


class IStartupKitDocxParser(ABC):
    """Interface for extracting a structured StartupKitBaseline from an existing Startup Kit DOCX."""

    @abstractmethod
    def parse_startup_kit_docx(self, file_path: Path) -> StartupKitBaseline:
        """Parse an existing *_Startup_Kit.docx file into a StartupKitBaseline model."""
        pass


class ReviewStorage(ABC):
    """Abstract interface for where a paused HTL-02 run lives (HTL-13). Every other Pre-Generation
    Human Review requirement is written against this interface, never against a filesystem or a
    cloud API directly, so the local backend (HTL-03) and the cloud backend (HTL-14) are
    interchangeable, the same way ILLMClient lets LangChainLLMClient, MockLLMClient, and
    CachingLLMClient stand in for each other.
    """

    @abstractmethod
    def create_run(self, project_name: str, baseline: dict, validation_report: dict) -> str:
        """Create a new paused run from a validated baseline and its validation report, and
        return the newly assigned run_id (HTL-03's {sanitize_filename(project_name)}_{YYYYMMDD_HHMMSS}
        shape for the local backend). The run starts in the pending_review state."""
        pass

    @abstractmethod
    def get_run(self, run_id: str) -> ReviewRun:
        """Return the full stored run (its state plus the exact baseline/validation_report it was
        created or last corrected with)."""
        pass

    @abstractmethod
    def list_runs(self, state: Optional[str] = None) -> List[ReviewRunSummary]:
        """List every stored run, optionally filtered to one state; with no filter, list all."""
        pass

    @abstractmethod
    def update_status(self, run_id: str, new_state: str, if_state: Optional[str] = None) -> None:
        """Move a run to new_state. Raises if if_state is given and does not match the run's
        current state -- this is what makes a single Approve click uncontested (HTL-09); the
        check and the write must be atomic, with no update applied when the guard fails."""
        pass

    @abstractmethod
    def save_corrected_baseline(self, run_id: str, baseline: dict, audit: dict) -> None:
        """Replace a run's stored baseline with a reviewer-corrected one, alongside its review
        audit (HTL-07)."""
        pass

    @abstractmethod
    def put_generated_files(self, run_id: str, file_paths: List[Path]) -> Dict[str, str]:
        """Store a run's generated output files and return {filename: download_reference}; a
        local path for the local backend, a signed URL for the cloud backend."""
        pass
