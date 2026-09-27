"""Abstract interfaces for the Startup Kit application."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Type, TypeVar, Optional, Any
from src.core.models import ExtractedDocument, StartupKitBaseline

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
