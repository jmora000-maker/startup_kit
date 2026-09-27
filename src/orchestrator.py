"""Workflow controller orchestrating Ingestion, LLM multi-pass extraction, Aggregation, and Word Generation."""

import logging
from pathlib import Path
from typing import Optional, List

from src.config import config
from src.core.interfaces import (
    ILLMClient,
    IDocumentWriter,
)
from src.core.models import StartupKitBaseline
from src.extractors.service import IngestionService
from src.llm.client import LangChainLLMClient
from src.llm.parsers import (
    CharterDomainExtractor,
    DeliverablesDomainExtractor,
    MilestonesDomainExtractor,
    RAIDDomainExtractor,
    QuestionsDomainExtractor,
    SOWInterpretationDomainExtractor,
    ScopeDecompositionDomainExtractor,
    AcceptanceProcessDomainExtractor,
    StakeholdersDomainExtractor,
    CommunicationsDomainExtractor,
    CommercialGuardrailsDomainExtractor,
    TalentOnboardingDomainExtractor,
    DecisionsDomainExtractor,
    ContractConflictsDomainExtractor,
)
from src.llm.aggregator import BaselineAggregator
from src.generators.docx_generator import DocxGenerator
from src.generators.export_payloads import export_all_pmo_tools

logger = logging.getLogger(__name__)


class StartupKitController:
    """Orchestrates end-to-end extraction from input files to generated Word report."""

    def __init__(
        self,
        ingestion_service: Optional[IngestionService] = None,
        llm_client: Optional[ILLMClient] = None,
        aggregator: Optional[BaselineAggregator] = None,
        doc_writer: Optional[IDocumentWriter] = None,
        charter_extractor: Optional[CharterDomainExtractor] = None,
        deliverables_extractor: Optional[DeliverablesDomainExtractor] = None,
        milestones_extractor: Optional[MilestonesDomainExtractor] = None,
        raid_extractor: Optional[RAIDDomainExtractor] = None,
        questions_extractor: Optional[QuestionsDomainExtractor] = None,
        sow_interpretation_extractor: Optional[SOWInterpretationDomainExtractor] = None,
        backlog_extractor: Optional[ScopeDecompositionDomainExtractor] = None,
        acceptance_extractor: Optional[AcceptanceProcessDomainExtractor] = None,
        stakeholders_extractor: Optional[StakeholdersDomainExtractor] = None,
        communications_extractor: Optional[CommunicationsDomainExtractor] = None,
        commercial_extractor: Optional[CommercialGuardrailsDomainExtractor] = None,
        talent_extractor: Optional[TalentOnboardingDomainExtractor] = None,
        decisions_extractor: Optional[DecisionsDomainExtractor] = None,
        conflicts_extractor: Optional[ContractConflictsDomainExtractor] = None,
    ):
        self.ingestion_service = ingestion_service or IngestionService()
        self.llm_client = llm_client or LangChainLLMClient(
            api_key=config.openai_api_key,
            model_name=config.openai_model,
            temperature=config.temperature
        )
        self.aggregator = aggregator or BaselineAggregator()
        self.doc_writer = doc_writer or DocxGenerator()

        # Domain Extractors
        self.charter_extractor = charter_extractor or CharterDomainExtractor()
        self.deliverables_extractor = deliverables_extractor or DeliverablesDomainExtractor()
        self.milestones_extractor = milestones_extractor or MilestonesDomainExtractor()
        self.raid_extractor = raid_extractor or RAIDDomainExtractor()
        self.questions_extractor = questions_extractor or QuestionsDomainExtractor()
        self.sow_interpretation_extractor = sow_interpretation_extractor
        self.backlog_extractor = backlog_extractor
        self.acceptance_extractor = acceptance_extractor
        self.stakeholders_extractor = stakeholders_extractor
        self.communications_extractor = communications_extractor
        self.commercial_extractor = commercial_extractor
        self.talent_extractor = talent_extractor
        self.decisions_extractor = decisions_extractor
        self.conflicts_extractor = conflicts_extractor

    def run(
        self,
        inputs_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        tier_override: Optional[str] = None,
        contract_type_override: Optional[str] = None,
        pmo_lead: Optional[str] = None,
        delivery_lead: Optional[str] = None,
        delivery_manager: Optional[str] = None,
        talent_pm: Optional[str] = None,
        export_tools: bool = False,
    ) -> Path:
        """Execute the end-to-end startup kit generation pipeline."""
        in_path = inputs_dir or config.inputs_dir
        out_path = output_dir or config.output_dir

        logger.info("Starting PMO Startup Kit generation from directory: %s", in_path)

        # 1. Ingest Documents
        documents = self.ingestion_service.ingest_directory(in_path)
        if not documents:
            raise FileNotFoundError(
                f"No supported documents found in inputs directory: {in_path}. "
                "Please place SOW PDF/DOCX or presentation PPTX files into the inputs folder."
            )

        logger.info("Ingested %d document(s): %s", len(documents), [d.file_name for d in documents])

        # 2. Multi-Pass LLM Extraction
        logger.info("Executing Pass 1: Charter & Governance Metadata...")
        charter = self.charter_extractor.extract(documents, self.llm_client)

        if tier_override and tier_override in ("Guided", "Partnered", "Elevated"):
            logger.info("Overriding Governance Tier with: %s", tier_override)
            charter.governance_tier = tier_override

        if contract_type_override:
            logger.info("Overriding Contract Type with: %s", contract_type_override)
            charter.contract_type = contract_type_override

        if pmo_lead is not None:
            logger.info("Setting PMO Lead: %s", pmo_lead)
            charter.pmo_lead = pmo_lead

        dm = delivery_lead if delivery_lead is not None else delivery_manager
        if dm is not None:
            logger.info("Setting Delivery Lead / Manager: %s", dm)
            charter.delivery_manager = dm

        if talent_pm is not None:
            logger.info("Setting Talent PM: %s", talent_pm)
            charter.talent_pm = talent_pm

        logger.info("Executing Pass 2: Deliverables & Acceptance Criteria...")
        deliverables = self.deliverables_extractor.extract(documents, self.llm_client)

        logger.info("Executing Pass 3: Milestones & Internal Buffers...")
        milestones = self.milestones_extractor.extract(documents, self.llm_client)

        logger.info("Executing Pass 4: RAID Log Items...")
        raid = self.raid_extractor.extract(documents, self.llm_client)

        logger.info("Executing Pass 5: Open Questions & Clarifications...")
        questions = self.questions_extractor.extract(documents, self.llm_client)

        sow_interpretation = self.sow_interpretation_extractor.extract(documents, self.llm_client) if self.sow_interpretation_extractor else None
        backlog = self.backlog_extractor.extract(documents, self.llm_client) if self.backlog_extractor else None
        acceptance = self.acceptance_extractor.extract(documents, self.llm_client) if self.acceptance_extractor else None
        stakeholders = self.stakeholders_extractor.extract(documents, self.llm_client) if self.stakeholders_extractor else None
        communications = self.communications_extractor.extract(documents, self.llm_client) if self.communications_extractor else None
        commercial = self.commercial_extractor.extract(documents, self.llm_client) if self.commercial_extractor else None
        talent = self.talent_extractor.extract(documents, self.llm_client) if self.talent_extractor else None
        decisions = self.decisions_extractor.extract(documents, self.llm_client) if self.decisions_extractor else None
        conflicts = self.conflicts_extractor.extract(documents, self.llm_client) if self.conflicts_extractor else None

        # 3. Aggregation & Business Rules
        logger.info("Synthesizing baseline model and enforcing business rules...")
        baseline: StartupKitBaseline = self.aggregator.aggregate(
            charter=charter,
            deliverables_ext=deliverables,
            milestones_ext=milestones,
            raid_ext=raid,
            questions_ext=questions,
            sow_interpretation_ext=sow_interpretation,
            backlog_ext=backlog,
            acceptance_ext=acceptance,
            stakeholders_ext=stakeholders,
            communications_ext=communications,
            commercial_ext=commercial,
            talent_ext=talent,
            decisions_ext=decisions,
            conflicts_ext=conflicts,
        )

        # 4. Word Document Generation
        logger.info("Generating Word Startup Kit document in %s...", out_path)
        generated_file = self.doc_writer.write_docx(baseline, out_path)

        # 5. Export downstream PMO workbook toolkits if requested
        if export_tools:
            logger.info("Exporting downstream PMO Operating System workbook toolkits to %s...", out_path)
            export_all_pmo_tools(baseline, out_path)

        logger.info("Startup Kit Generation complete! File created at: %s", generated_file)
        return generated_file
