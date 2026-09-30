"""Domain extraction runners for multi-pass LLM processing."""

from typing import List
from src.core.interfaces import IDomainExtractor, ILLMClient
from src.core.models import (
    ExtractedDocument,
    CharterExtraction,
    DeliverablesExtraction,
    MilestonesExtraction,
    RAIDExtraction,
    QuestionsExtraction,
    SOWInterpretationExtraction,
    ScopeDecompositionExtraction,
    AcceptanceProcessExtraction,
    StakeholdersExtraction,
    CommunicationsExtraction,
    CommercialGuardrailsExtraction,
    TalentOnboardingExtraction,
    DecisionsExtraction,
    ContractConflictsExtraction,
)
from src.llm.prompts import (
    SYSTEM_PROMPT,
    CHARTER_PROMPT,
    DELIVERABLES_PROMPT,
    MILESTONES_PROMPT,
    RAID_PROMPT,
    QUESTIONS_PROMPT,
    SOW_INTERPRETATION_PROMPT,
    SCOPE_DECOMPOSITION_PROMPT,
    ACCEPTANCE_PROCESS_PROMPT,
    STAKEHOLDERS_PROMPT,
    COMMUNICATIONS_PROMPT,
    COMMERCIAL_GUARDRAILS_PROMPT,
    TALENT_ONBOARDING_PROMPT,
    DECISIONS_PROMPT,
    CONTRACT_CONFLICTS_PROMPT,
)


def format_documents_for_prompt(documents: List[ExtractedDocument]) -> str:
    """Format a list of extracted documents into a structured string for LLM prompts."""
    if not documents:
        return "No documents provided."

    formatted_parts = []
    for doc in documents:
        formatted_parts.append(
            f"=== DOCUMENT: {doc.file_name} (Format: {doc.file_type.upper()}) ===\n"
            f"{doc.text_content}\n"
        )
    return "\n\n".join(formatted_parts)


class CharterDomainExtractor(IDomainExtractor):
    """Extracts high-level charter, leadership roles, and governance metadata."""

    def extract(self, documents: List[ExtractedDocument], llm_client: ILLMClient) -> CharterExtraction:
        docs_text = format_documents_for_prompt(documents)
        prompt = CHARTER_PROMPT.format(documents_text=docs_text)
        return llm_client.generate_structured(
            prompt=prompt,
            schema=CharterExtraction,
            system_prompt=SYSTEM_PROMPT
        )


class DeliverablesDomainExtractor(IDomainExtractor):
    """Extracts deliverables, ownership, and acceptance criteria."""

    def extract(self, documents: List[ExtractedDocument], llm_client: ILLMClient) -> DeliverablesExtraction:
        docs_text = format_documents_for_prompt(documents)
        prompt = DELIVERABLES_PROMPT.format(documents_text=docs_text)
        return llm_client.generate_structured(
            prompt=prompt,
            schema=DeliverablesExtraction,
            system_prompt=SYSTEM_PROMPT
        )


class MilestonesDomainExtractor(IDomainExtractor):
    """Extracts contractual milestones, external dates, and internal buffers."""

    def extract(self, documents: List[ExtractedDocument], llm_client: ILLMClient) -> MilestonesExtraction:
        docs_text = format_documents_for_prompt(documents)
        prompt = MILESTONES_PROMPT.format(documents_text=docs_text)
        return llm_client.generate_structured(
            prompt=prompt,
            schema=MilestonesExtraction,
            system_prompt=SYSTEM_PROMPT
        )


class RAIDDomainExtractor(IDomainExtractor):
    """Extracts RAID items (Risks, Assumptions, Issues, Dependencies)."""

    def extract(self, documents: List[ExtractedDocument], llm_client: ILLMClient) -> RAIDExtraction:
        docs_text = format_documents_for_prompt(documents)
        prompt = RAID_PROMPT.format(documents_text=docs_text)
        return llm_client.generate_structured(
            prompt=prompt,
            schema=RAIDExtraction,
            system_prompt=SYSTEM_PROMPT
        )


class QuestionsDomainExtractor(IDomainExtractor):
    """Extracts open questions and ambiguities requiring human clarification."""

    def extract(self, documents: List[ExtractedDocument], llm_client: ILLMClient) -> QuestionsExtraction:
        docs_text = format_documents_for_prompt(documents)
        prompt = QUESTIONS_PROMPT.format(documents_text=docs_text)
        return llm_client.generate_structured(
            prompt=prompt,
            schema=QuestionsExtraction,
            system_prompt=SYSTEM_PROMPT
        )


class SOWInterpretationDomainExtractor(IDomainExtractor):
    """Extracts SOW interpretation summary items and contract scope boundaries."""

    def extract(self, documents: List[ExtractedDocument], llm_client: ILLMClient) -> SOWInterpretationExtraction:
        docs_text = format_documents_for_prompt(documents)
        prompt = SOW_INTERPRETATION_PROMPT.format(documents_text=docs_text)
        return llm_client.generate_structured(
            prompt=prompt,
            schema=SOWInterpretationExtraction,
            system_prompt=SYSTEM_PROMPT
        )


class ScopeDecompositionDomainExtractor(IDomainExtractor):
    """Extracts scope decomposition and backlog seed work packages."""

    def extract(
        self,
        documents: List[ExtractedDocument],
        llm_client: ILLMClient,
        deliverables: Optional[List[Any]] = None,
    ) -> ScopeDecompositionExtraction:
        docs_text = format_documents_for_prompt(documents)
        deliv_text = (
            "\n".join(f"- {getattr(d, 'id', '')}: {getattr(d, 'name', '') or getattr(d, 'description', '')}" for d in deliverables)
            if deliverables else "No extracted deliverables available."
        )
        prompt = SCOPE_DECOMPOSITION_PROMPT.format(documents_text=docs_text, deliverables_text=deliv_text)
        return llm_client.generate_structured(
            prompt=prompt,
            schema=ScopeDecompositionExtraction,
            system_prompt=SYSTEM_PROMPT
        )


class AcceptanceProcessDomainExtractor(IDomainExtractor):
    """Extracts acceptance process matrix entries and client review windows."""

    def extract(self, documents: List[ExtractedDocument], llm_client: ILLMClient) -> AcceptanceProcessExtraction:
        docs_text = format_documents_for_prompt(documents)
        prompt = ACCEPTANCE_PROCESS_PROMPT.format(documents_text=docs_text)
        return llm_client.generate_structured(
            prompt=prompt,
            schema=AcceptanceProcessExtraction,
            system_prompt=SYSTEM_PROMPT
        )


class StakeholdersDomainExtractor(IDomainExtractor):
    """Extracts stakeholders, roles, and responsibility models."""

    def extract(self, documents: List[ExtractedDocument], llm_client: ILLMClient) -> StakeholdersExtraction:
        docs_text = format_documents_for_prompt(documents)
        prompt = STAKEHOLDERS_PROMPT.format(documents_text=docs_text)
        return llm_client.generate_structured(
            prompt=prompt,
            schema=StakeholdersExtraction,
            system_prompt=SYSTEM_PROMPT
        )


class CommunicationsDomainExtractor(IDomainExtractor):
    """Extracts communications and reporting obligations."""

    def extract(self, documents: List[ExtractedDocument], llm_client: ILLMClient) -> CommunicationsExtraction:
        docs_text = format_documents_for_prompt(documents)
        prompt = COMMUNICATIONS_PROMPT.format(documents_text=docs_text)
        return llm_client.generate_structured(
            prompt=prompt,
            schema=CommunicationsExtraction,
            system_prompt=SYSTEM_PROMPT
        )


class CommercialGuardrailsDomainExtractor(IDomainExtractor):
    """Extracts commercial guardrails, work-at-risk rules, and margin protections."""

    def extract(self, documents: List[ExtractedDocument], llm_client: ILLMClient) -> CommercialGuardrailsExtraction:
        docs_text = format_documents_for_prompt(documents)
        prompt = COMMERCIAL_GUARDRAILS_PROMPT.format(documents_text=docs_text)
        return llm_client.generate_structured(
            prompt=prompt,
            schema=CommercialGuardrailsExtraction,
            system_prompt=SYSTEM_PROMPT
        )


class TalentOnboardingDomainExtractor(IDomainExtractor):
    """Extracts talent staffing, onboarding roster, and skill requirements."""

    def extract(self, documents: List[ExtractedDocument], llm_client: ILLMClient) -> TalentOnboardingExtraction:
        docs_text = format_documents_for_prompt(documents)
        prompt = TALENT_ONBOARDING_PROMPT.format(documents_text=docs_text)
        return llm_client.generate_structured(
            prompt=prompt,
            schema=TalentOnboardingExtraction,
            system_prompt=SYSTEM_PROMPT
        )


class DecisionsDomainExtractor(IDomainExtractor):
    """Extracts decision log seed items."""

    def extract(self, documents: List[ExtractedDocument], llm_client: ILLMClient) -> DecisionsExtraction:
        docs_text = format_documents_for_prompt(documents)
        prompt = DECISIONS_PROMPT.format(documents_text=docs_text)
        return llm_client.generate_structured(
            prompt=prompt,
            schema=DecisionsExtraction,
            system_prompt=SYSTEM_PROMPT
        )


class ContractConflictsDomainExtractor(IDomainExtractor):
    """Extracts contractual ambiguities, conflicts, and non-testable clauses (NFR-02)."""

    def extract(self, documents: List[ExtractedDocument], llm_client: ILLMClient) -> ContractConflictsExtraction:
        docs_text = format_documents_for_prompt(documents)
        prompt = CONTRACT_CONFLICTS_PROMPT.format(documents_text=docs_text)
        return llm_client.generate_structured(
            prompt=prompt,
            schema=ContractConflictsExtraction,
            system_prompt=SYSTEM_PROMPT
        )
