"""Workflow controller orchestrating Ingestion, LLM multi-pass extraction, Aggregation, and Word Generation."""

import shutil
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from src.config import config, normalize_person_name
from src.core.interfaces import (
    ILLMClient,
    IDocumentWriter,
    IStartupKitDocxParser,
)
from src.core.models import StartupKitBaseline, OutputSelection, RunResult
from src.extractors.service import IngestionService
from src.extractors.startup_kit_docx_parser import StartupKitDocxParser
from src.llm.client import LangChainLLMClient, MockLLMClient, CachingLLMClient
from src.llm.validation import validate_and_repair_baseline
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
from src.generators.pmo_workbook import export_pmo_workbook, PMOWorkbookResult
from src.scoring.cli_reporter import (
    print_readiness_cli_summary,
    print_workbook_export_summary,
)

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
        docx_parser: Optional[IStartupKitDocxParser] = None,
    ):
        self.ingestion_service = ingestion_service or IngestionService()
        if llm_client:
            self.llm_client = llm_client
        else:
            inner_client = LangChainLLMClient(
                api_key=config.anthropic_api_key,
                model_name=config.anthropic_model,
                openai_api_key=config.openai_api_key,
                openai_model_name=config.openai_model,
                temperature=config.temperature
            )
            self.llm_client = CachingLLMClient(
                inner_client=inner_client,
                cache_dir=config.llm_cache_dir,
                mode=config.llm_cache_mode,
                model_id=config.anthropic_model
            )
        self.aggregator = aggregator or BaselineAggregator()
        self.doc_writer = doc_writer or DocxGenerator()
        self.docx_parser = docx_parser or StartupKitDocxParser()

        # Domain Extractors
        self.charter_extractor = charter_extractor or CharterDomainExtractor()
        self.deliverables_extractor = deliverables_extractor or DeliverablesDomainExtractor()
        self.milestones_extractor = milestones_extractor or MilestonesDomainExtractor()
        self.raid_extractor = raid_extractor or RAIDDomainExtractor()
        self.questions_extractor = questions_extractor or QuestionsDomainExtractor()
        self.sow_interpretation_extractor = sow_interpretation_extractor or SOWInterpretationDomainExtractor()
        self.backlog_extractor = backlog_extractor or ScopeDecompositionDomainExtractor()
        self.acceptance_extractor = acceptance_extractor or AcceptanceProcessDomainExtractor()
        self.stakeholders_extractor = stakeholders_extractor or StakeholdersDomainExtractor()
        self.communications_extractor = communications_extractor or CommunicationsDomainExtractor()
        self.commercial_extractor = commercial_extractor or CommercialGuardrailsDomainExtractor()
        self.talent_extractor = talent_extractor or TalentOnboardingDomainExtractor()
        self.decisions_extractor = decisions_extractor or DecisionsDomainExtractor()
        self.conflicts_extractor = conflicts_extractor or ContractConflictsDomainExtractor()

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
        outputs: Optional[OutputSelection] = None,
        start_date: Optional[date] = None,
    ) -> RunResult:
        """Execute the end-to-end startup kit generation pipeline."""
        if outputs is None:
            outputs = OutputSelection()

        if inputs_dir is not None:
            in_path = inputs_dir
        elif isinstance(self.llm_client, MockLLMClient):
            in_path = config.mock_inputs_dir
        else:
            in_path = config.inputs_dir

        if output_dir is not None:
            out_path = output_dir
        elif isinstance(self.llm_client, MockLLMClient):
            out_path = config.mock_output_dir
        else:
            out_path = config.output_dir

        logger.info("Starting PMO Startup Kit generation from directory: %s", in_path)

        # 1. Ingest Documents
        documents = self.ingestion_service.ingest_directory(in_path)
        if not documents:
            raise FileNotFoundError(
                f"No supported documents found in inputs directory: {in_path}. "
                "Please place SOW PDF/DOCX or presentation PPTX files into the inputs folder."
            )

        logger.info("Ingested %d document(s): %s", len(documents), [d.file_name for d in documents])

        # 2. Multi-Pass LLM Extraction (Concurrent Execution)
        logger.info("Executing concurrent multi-pass LLM extractions (12 domain passes)...")
        with ThreadPoolExecutor(max_workers=14) as executor:
            future_charter = executor.submit(self.charter_extractor.extract, documents, self.llm_client)
            future_deliverables = executor.submit(self.deliverables_extractor.extract, documents, self.llm_client)
            future_milestones = executor.submit(self.milestones_extractor.extract, documents, self.llm_client)
            future_raid = executor.submit(self.raid_extractor.extract, documents, self.llm_client)
            future_questions = executor.submit(self.questions_extractor.extract, documents, self.llm_client)
            future_sow = (
                executor.submit(self.sow_interpretation_extractor.extract, documents, self.llm_client)
                if self.sow_interpretation_extractor else None
            )
            future_acceptance = (
                executor.submit(self.acceptance_extractor.extract, documents, self.llm_client)
                if self.acceptance_extractor else None
            )
            future_stakeholders = (
                executor.submit(self.stakeholders_extractor.extract, documents, self.llm_client)
                if self.stakeholders_extractor else None
            )
            future_comms = (
                executor.submit(self.communications_extractor.extract, documents, self.llm_client)
                if self.communications_extractor else None
            )
            future_commercial = (
                executor.submit(self.commercial_extractor.extract, documents, self.llm_client)
                if self.commercial_extractor else None
            )
            future_talent = (
                executor.submit(self.talent_extractor.extract, documents, self.llm_client)
                if self.talent_extractor else None
            )
            future_decisions = (
                executor.submit(self.decisions_extractor.extract, documents, self.llm_client)
                if self.decisions_extractor else None
            )
            future_conflicts = (
                executor.submit(self.conflicts_extractor.extract, documents, self.llm_client)
                if self.conflicts_extractor else None
            )

            charter = future_charter.result()
            deliverables = future_deliverables.result()
            milestones = future_milestones.result()
            raid = future_raid.result()
            questions = future_questions.result()
            sow_interpretation = future_sow.result() if future_sow else None
            acceptance = future_acceptance.result() if future_acceptance else None
            stakeholders = future_stakeholders.result() if future_stakeholders else None
            communications = future_comms.result() if future_comms else None
            commercial = future_commercial.result() if future_commercial else None
            talent = future_talent.result() if future_talent else None
            decisions = future_decisions.result() if future_decisions else None
            conflicts = future_conflicts.result() if future_conflicts else None

        # Backlog extraction passes deliverables
        backlog = (
            self.backlog_extractor.extract(documents, self.llm_client, deliverables=deliverables.deliverables)
            if self.backlog_extractor else None
        )

        # Apply leadership and governance overrides
        if tier_override and tier_override in ("Guided", "Partnered", "Elevated"):
            logger.info("Overriding Governance Tier with: %s", tier_override)
            charter.governance_tier = tier_override

        if contract_type_override:
            logger.info("Overriding Contract Type with: %s", contract_type_override)
            charter.contract_type = contract_type_override

        if pmo_lead is not None:
            norm_pmo = normalize_person_name(pmo_lead)
            logger.info("Setting PMO Lead: %s", norm_pmo)
            charter.pmo_lead = norm_pmo

        dm = delivery_lead if delivery_lead is not None else delivery_manager
        if dm is not None:
            norm_dm = normalize_person_name(dm)
            logger.info("Setting Delivery Lead / Manager: %s", norm_dm)
            charter.delivery_manager = norm_dm

        if talent_pm is not None:
            norm_tpm = normalize_person_name(talent_pm)
            logger.info("Setting Talent PM: %s", norm_tpm)
            charter.talent_pm = norm_tpm

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

        # 3b. Extraction Validation Layer (Section 4, VAL-01 to VAL-07)
        logger.info("Running extraction validation layer and reconciliation...")
        validation_report = validate_and_repair_baseline(baseline)

        # 4. Document & Workbook Generation according to outputs selection
        kit_path: Optional[Path] = None
        checklist_path: Optional[Path] = None
        wb_result: Optional[PMOWorkbookResult] = None
        written_paths: List[Path] = []

        if outputs.kit:
            logger.info("Generating Word Startup Kit document in %s...", out_path)
            if hasattr(self.doc_writer, "write_kit_docx"):
                kit_path = self.doc_writer.write_kit_docx(baseline, out_path)
            else:
                kit_path = self.doc_writer.write_docx(baseline, out_path)
            written_paths.append(kit_path)

        if outputs.checklist:
            logger.info("Generating Word Startup Readiness Checklist document in %s...", out_path)
            if hasattr(self.doc_writer, "write_checklist_docx"):
                checklist_path = self.doc_writer.write_checklist_docx(baseline, out_path)
                written_paths.append(checklist_path)

        if outputs.workbook:
            logger.info("Exporting Project Delivery Workbook to %s", out_path)
            wb_result = export_pmo_workbook(baseline, out_path, start_date=start_date)
            written_paths.append(wb_result.file_path)

        # 5. CLI Telemetry Summary
        print_readiness_cli_summary(baseline, written_paths if written_paths else [out_path])
        if wb_result is not None:
            print_workbook_export_summary(wb_result)

        logger.info("Startup Kit execution complete! Readiness score: %.1f%%", baseline.readiness_score)
        return RunResult(
            kit_path=kit_path,
            checklist_path=checklist_path,
            workbook=wb_result,
            readiness_score=baseline.readiness_score
        )

    def run_reingest(
        self,
        docx_path: Path,
        output_dir: Optional[Path] = None,
        output_file: Optional[Path] = None,
        pmo_lead: Optional[str] = None,
        delivery_lead: Optional[str] = None,
        delivery_manager: Optional[str] = None,
        talent_pm: Optional[str] = None,
        tier_override: Optional[str] = None,
        contract_type_override: Optional[str] = None,
        outputs: Optional[OutputSelection] = None,
        start_date: Optional[date] = None,
        create_backup: bool = True,
    ) -> RunResult:
        """Re-ingest an updated *_Startup_Kit.docx file, recalculate readiness, and regenerate report."""
        if outputs is None:
            outputs = OutputSelection()

        docx_file = Path(docx_path)
        if not docx_file.exists():
            raise FileNotFoundError(f"Target Startup Kit Word document not found at: {docx_file}")

        logger.info("Executing Single-Document Ingestion for: %s", docx_file)
        baseline = self.docx_parser.parse_startup_kit_docx(docx_file)

        # Apply leadership overrides if supplied
        dm = delivery_lead or delivery_manager
        if dm is not None:
            norm_dm = normalize_person_name(dm)
            logger.info("Applying Delivery Lead override: %s", norm_dm)
            if baseline.charter:
                baseline.charter.delivery_manager = norm_dm
            if baseline.talent_onboarding:
                baseline.talent_onboarding.delivery_manager = norm_dm
            if baseline.governance_context:
                baseline.governance_context.delivery_manager = norm_dm

        if talent_pm is not None:
            norm_tpm = normalize_person_name(talent_pm)
            logger.info("Applying Talent PM override: %s", norm_tpm)
            if baseline.charter:
                baseline.charter.talent_pm = norm_tpm
            if baseline.talent_onboarding:
                baseline.talent_onboarding.talent_pm = norm_tpm
            if baseline.governance_context:
                baseline.governance_context.talent_pm = norm_tpm

        if pmo_lead is not None:
            norm_pmo = normalize_person_name(pmo_lead)
            logger.info("Applying PMO Lead override: %s", norm_pmo)
            baseline.author_name = norm_pmo
            if baseline.charter:
                baseline.charter.pmo_lead = norm_pmo
            if baseline.talent_onboarding:
                baseline.talent_onboarding.pmo_lead = norm_pmo
            if baseline.governance_context:
                baseline.governance_context.pmo_lead = norm_pmo

        if tier_override is not None:
            logger.info("Applying Governance Tier override: %s", tier_override)
            baseline.governance_tier = tier_override
            if baseline.charter:
                baseline.charter.governance_tier = tier_override
            if baseline.governance_context:
                baseline.governance_context.governance_tier = tier_override

        if contract_type_override is not None:
            logger.info("Applying Contract Type override: %s", contract_type_override)
            baseline.contract_type = contract_type_override
            if baseline.charter:
                baseline.charter.contract_type = contract_type_override
            if baseline.governance_context:
                baseline.governance_context.contract_type = contract_type_override

        # Recalculate readiness and gate decision
        logger.info("Recalculating Startup Readiness Score and G-01 Gate Decision...")
        baseline = self.aggregator.recalculate_readiness(baseline)

        # Determine target output path
        if output_file is not None:
            target_path = Path(output_file)
        elif output_dir is not None:
            target_dir = Path(output_dir)
            target_path = target_dir / docx_file.name
        else:
            target_path = docx_file

        target_path.parent.mkdir(parents=True, exist_ok=True)

        kit_path: Optional[Path] = None
        checklist_path: Optional[Path] = None
        wb_result: Optional[PMOWorkbookResult] = None
        written_paths: List[Path] = []

        if outputs.kit:
            # Create backup if overwriting in place and backup is enabled
            if create_backup and target_path.resolve() == docx_file.resolve() and docx_file.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = docx_file.with_name(f"{docx_file.stem}_backup_{timestamp}.docx")
                try:
                    shutil.copy2(str(docx_file), str(backup_path))
                    logger.info("Created backup before overwrite at: %s", backup_path)
                except Exception as e:
                    logger.warning("Could not create backup of %s: %s", docx_file, e)

            logger.info("Regenerating updated Word Startup Kit document at: %s", target_path)
            if hasattr(self.doc_writer, "write_kit_docx"):
                kit_path = self.doc_writer.write_kit_docx(baseline, target_path)
            else:
                kit_path = self.doc_writer.write_docx(baseline, target_path)
            written_paths.append(kit_path)
        else:
            logger.info("Readiness recalculated; the Startup Kit .docx was not rewritten. Add --kit or --all to update it.")

        if outputs.checklist:
            logger.info("Regenerating updated Word Startup Readiness Checklist document at: %s", target_path)
            if hasattr(self.doc_writer, "write_checklist_docx"):
                checklist_path = self.doc_writer.write_checklist_docx(baseline, target_path)
                written_paths.append(checklist_path)

        export_dir = target_path.parent
        if outputs.workbook:
            logger.info("Exporting Project Delivery Workbook to %s", export_dir)
            wb_result = export_pmo_workbook(baseline, export_dir, start_date=start_date)
            written_paths.append(wb_result.file_path)

        if output_file is not None and not (outputs.kit or outputs.checklist):
            logger.warning("--output-file was provided but neither the Startup Kit nor the Readiness Checklist was selected; it only sets the destination folder for the workbook.")

        # Output CLI Telemetry Summary
        print_readiness_cli_summary(baseline, written_paths if written_paths else [target_path])
        if wb_result is not None:
            print_workbook_export_summary(wb_result)

        logger.info(
            "Startup Kit Re-evaluation complete! Readiness Score: %s%%, Status: %s",
            baseline.readiness_score,
            baseline.gate_decision.gate_decision_status if baseline.gate_decision else "N/A"
        )
        return RunResult(
            kit_path=kit_path,
            checklist_path=checklist_path,
            workbook=wb_result,
            readiness_score=baseline.readiness_score
        )
