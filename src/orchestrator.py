"""Workflow controller orchestrating Ingestion, LLM multi-pass extraction, Aggregation, and Word Generation."""

import shutil
import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path
from typing import BinaryIO, Callable, Optional, List, Tuple, Union

from src.config import config, normalize_person_name
from src.core.interfaces import (
    ILLMClient,
    IDocumentWriter,
    IStartupKitDocxParser,
)
from src.core.models import StartupKitBaseline, OutputSelection, RunResult, AWARD_DATE_SOURCE_STATED
from src.extractors.service import IngestionService, IngestSource
from src.extractors.startup_kit_docx_parser import StartupKitDocxParser
from src.extractors.date_extractor import extract_stated_award_date
from src.llm.client import LangChainLLMClient, MockLLMClient, CachingLLMClient
from src.llm.mock_responses import create_mock_llm_client
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
from src.generators.onboarding_deck import export_onboarding_deck, OnboardingDeckResult
from src.scoring.cli_reporter import (
    format_readiness_cli_summary,
    format_workbook_export_summary,
    format_deck_export_summary,
)

logger = logging.getLogger(__name__)

# HTL-28: on_progress(stage, detail="") reports real stage boundaries as they actually happen --
# "ingesting", "extracting", "validating", "generating" (once per document type actually being
# written). Defaults to a no-op everywhere so existing callers (the CLI today) are unaffected
# unless they choose to pass a real callback (e.g. the Streamlit app's live status display).
ProgressCallback = Callable[[str, str], None]


def _noop_progress(stage: str, detail: str = "") -> None:
    pass


def build_llm_client(
    provider: str = "anthropic",
    model: Optional[str] = None,
    anthropic_api_key: str = "",
    openai_api_key: str = "",
    cache_mode: str = "off",
    mock: bool = False,
    require_provider: bool = True,
) -> ILLMClient:
    """HTL-16 shared LLM client factory (consolidates the audit's C-5 and C-9 findings).

    Builds the right ``ILLMClient`` from explicit parameters only -- it never reads
    argparse or ``os.environ`` directly. The caller (``main.py``'s argument parsing today,
    the future Streamlit app tomorrow) is responsible for extracting these values from
    its own input source and passing them in.

    HTL-19: mock-mode fake data comes from the shared ``create_mock_llm_client`` factory.
    HTL-20: when no provider is configured and ``mock`` was not explicitly requested, this
    raises ``RuntimeError`` instead of silently falling back to mock data -- a deliberate
    behavior change from the CLI's previous silent fall-back. Pass ``require_provider=False``
    to keep the old non-raising behavior for call sites (such as a lazily-built, possibly
    unused default collaborator) that may never actually invoke the returned client.
    HTL-21: API keys are accepted as explicit parameters; this function adds nothing
    resembling a UI-facing key input.
    """
    if mock:
        logger.info("Using offline Mock LLM client for deterministic generation.")
        return create_mock_llm_client()

    provider_normalized = (
        "openai" if provider and provider.lower() in ("openai", "open-ai", "gpt", "chatgpt") else "anthropic"
    )

    if provider_normalized == "openai":
        if not openai_api_key and not anthropic_api_key:
            if require_provider:
                raise RuntimeError(
                    "No LLM provider is configured: OPENAI_API_KEY is not set and mock mode was not "
                    "requested. Set OPENAI_API_KEY, choose a different provider, or pass mock=True."
                )
            logger.warning("OPENAI_API_KEY is not set; building an inert LLM client with no active model.")
        openai_model = model if (model and model != config.anthropic_model) else config.openai_model
        anthropic_model = config.anthropic_model
        if openai_api_key and anthropic_api_key:
            logger.info("Using OpenAI client (%s) with Anthropic fallback (%s)", openai_model, anthropic_model)
        elif openai_api_key:
            logger.info("Using OpenAI LangChain client with model: %s", openai_model)
        inner = LangChainLLMClient(
            primary_provider="openai",
            api_key=anthropic_api_key,
            model_name=anthropic_model,
            openai_api_key=openai_api_key,
            openai_model_name=openai_model,
            temperature=config.temperature,
        )
        return CachingLLMClient(
            inner_client=inner,
            cache_dir=config.llm_cache_dir,
            mode=cache_mode,
            model_id=openai_model,
        )

    # anthropic (default)
    if not anthropic_api_key and not openai_api_key:
        if require_provider:
            raise RuntimeError(
                "No LLM provider is configured: neither ANTHROPIC_API_KEY nor OPENAI_API_KEY is set, "
                "and mock mode was not requested. Set an API key, choose a different provider, or pass mock=True."
            )
        logger.warning("No API key is configured; building an inert LLM client with no active model.")

    if not anthropic_api_key and openai_api_key:
        logger.info("ANTHROPIC_API_KEY is not set; using OpenAI LangChain client with model: %s", config.openai_model)
        inner = LangChainLLMClient(
            primary_provider="openai",
            api_key="",
            openai_api_key=openai_api_key,
            openai_model_name=config.openai_model,
            temperature=config.temperature,
        )
        return CachingLLMClient(
            inner_client=inner,
            cache_dir=config.llm_cache_dir,
            mode=cache_mode,
            model_id=config.openai_model,
        )

    anthropic_model = model or config.anthropic_model
    if anthropic_api_key and openai_api_key:
        logger.info("Using Anthropic Claude client (%s) with OpenAI fallback (%s)", anthropic_model, config.openai_model)
    elif anthropic_api_key:
        logger.info("Using Anthropic Claude LangChain client with model: %s", anthropic_model)
    inner = LangChainLLMClient(
        primary_provider="anthropic",
        api_key=anthropic_api_key,
        model_name=anthropic_model,
        temperature=config.temperature,
        openai_api_key=openai_api_key,
        openai_model_name=config.openai_model,
    )
    return CachingLLMClient(
        inner_client=inner,
        cache_dir=config.llm_cache_dir,
        mode=cache_mode,
        model_id=anthropic_model,
    )


def parse_start_date(value: Optional[str]) -> Optional[date]:
    """HTL-17 Group 1 (C-2): one shared start-date parse/validate helper.

    Accepts the raw string value (e.g. ``args.start_date`` from the CLI, or a form field's text
    from the app) and returns the parsed ``date``, or ``None`` when ``value`` is empty/``None``.
    Raises ``ValueError`` on an invalid ISO format -- it never logs, prints, or exits -- so each
    caller decides how to present the failure (the CLI logs the error and returns exit code 1;
    the app shows a ``st.error`` message), while the parsing/validation logic itself is identical
    for both.
    """
    if not value:
        return None
    return date.fromisoformat(value.strip())


def resolve_execution_mode(
    reingest_docx: Optional[Union[str, Path]],
    is_interactive: bool,
    prompted_mode: Optional[str] = None,
) -> str:
    """HTL-17 Group 1 (C-3): one shared rule choosing Initial Generation ("1") vs. DOCX
    Re-ingestion ("2").

    The decision is: an explicit ``--reingest-docx``/equivalent always means re-ingestion;
    otherwise, in an interactive CLI session, ``prompted_mode`` (already collected via
    ``input()``, which stays CLI-only) decides; otherwise it defaults to Initial Generation.
    A caller with no magic-string ambiguity at all (such as the app, which has two separate
    buttons/tabs rather than a prompt) can simply call ``run`` or ``run_reingest`` directly and
    never needs this function -- it exists so ``main.py``'s own mode selection is a plain,
    testable function instead of inline script logic.
    """
    if reingest_docx is not None:
        return "2"
    if is_interactive:
        return prompted_mode if prompted_mode is not None else "1"
    return "1"


def resolve_mock_io_dirs(
    mock: bool,
    inputs_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> Tuple[Path, Path]:
    """HTL-17 Group 1 (C-4/C-10): the one place that chooses mock-fixture folders.

    When ``inputs_dir``/``output_dir`` is explicitly supplied, it is used as-is. Otherwise the
    mock fixture folders (``config.mock_inputs_dir``/``config.mock_output_dir``) are used when
    ``mock`` is True, and the normal ``config.inputs_dir``/``config.output_dir`` otherwise. This
    replaces the two separate, previously-duplicated decisions: ``main.py``'s own
    ``args.mock``-based default selection, and ``StartupKitController.run()``'s
    ``isinstance(self.llm_client, MockLLMClient)`` branch -- both now call this single function.
    """
    resolved_inputs = inputs_dir if inputs_dir is not None else (config.mock_inputs_dir if mock else config.inputs_dir)
    resolved_output = output_dir if output_dir is not None else (config.mock_output_dir if mock else config.output_dir)
    return resolved_inputs, resolved_output


def resolve_role_for_reingest(
    flag_value: Optional[str],
    prompted_value: str,
    interactive: bool,
    placeholder: str = "[UNASSIGNED - TO BE CONFIRMED]",
) -> Optional[str]:
    """HTL-25: decide whether a role override should be applied on re-ingestion.

    Re-ingestion recalculates readiness against an *existing* baseline that may already carry a
    previously-confirmed name; unlike a fresh run (where a blank role always becomes the
    placeholder, with no carry-over from any earlier run -- KIT-10), a role here is applied only
    when a person actually supplied a value for THIS re-ingestion: the CLI flag was given
    explicitly, or the interactive prompt was shown and the user did not simply accept the
    unassigned placeholder. Otherwise ``None`` is returned, meaning "leave the existing value in
    the re-ingested baseline untouched."

    This is the one place the "what happens when a role is blank" decision lives: ``main.py``'s
    interactive terminal prompting (``input()``) stays CLI-only, but the decision of whether a
    prompted value counts as "the user actually provided it" is this shared, importable
    function -- the same one a future app's call (always with ``interactive=False``, since a web
    form has no interactive/non-interactive distinction, HTL-25/U-7) goes through as well.
    """
    if flag_value is not None:
        return prompted_value
    if interactive and prompted_value != placeholder:
        return prompted_value
    return None


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
            # C-9: same shared factory as the CLI's build_llm_client, with require_provider=False
            # since this default is only a placeholder collaborator -- callers that only need
            # run_reingest() (which never touches self.llm_client) must not be forced to configure
            # an LLM provider just to construct the controller.
            self.llm_client = build_llm_client(
                provider="anthropic",
                model=config.anthropic_model,
                anthropic_api_key=config.anthropic_api_key,
                openai_api_key=config.openai_api_key,
                cache_mode=config.llm_cache_mode,
                mock=False,
                require_provider=False,
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
        input_documents: Optional[List[IngestSource]] = None,
        output_dir: Optional[Path] = None,
        tier_override: Optional[str] = None,
        contract_type_override: Optional[str] = None,
        pmo_lead: Optional[str] = None,
        delivery_lead: Optional[str] = None,
        delivery_manager: Optional[str] = None,
        talent_pm: Optional[str] = None,
        outputs: Optional[OutputSelection] = None,
        start_date: Optional[date] = None,
        on_progress: Optional[ProgressCallback] = None,
        pause_for_review: bool = False,
    ) -> RunResult:
        """Execute the end-to-end startup kit generation pipeline.

        HTL-16 Group 2 (C-11): ``input_documents`` is an alternative to ``inputs_dir`` that
        accepts a mix of disk paths and in-memory uploads (``(file_name, bytes_or_file_like)``
        pairs), for a caller (such as a future Streamlit upload) that has no inputs directory
        at all. Passing ``inputs_dir`` keeps the CLI's existing directory-based behavior
        completely unchanged.

        HTL-28: ``on_progress(stage, detail="")`` is called at real stage boundaries
        (``"ingesting"``, ``"extracting"``, ``"validating"``, ``"generating"`` once per document
        type actually written) as they actually happen. Defaults to a no-op, so this is a pure
        addition with no effect on any existing caller that doesn't pass one.

        HTL-29 / HTL-02: ``pause_for_review`` splits the pipeline after extraction and validation,
        storing the run in review storage (state ``pending_review``) and returning without
        generating any document files. Defaults to False, so existing callers are completely
        unaffected.
        """
        if outputs is None:
            outputs = OutputSelection()
        progress = on_progress or _noop_progress

        if input_documents is not None:
            progress("ingesting", f"{len(input_documents)} provided source(s)")
            logger.info("Starting PMO Startup Kit generation from %d provided source(s)", len(input_documents))
            documents = self.ingestion_service.ingest_sources(input_documents)
            if not documents:
                raise FileNotFoundError(
                    "No supported documents found in the provided inputs. "
                    "Please provide SOW PDF/DOCX or presentation PPTX files."
                )
            out_path = output_dir if output_dir is not None else config.output_dir
        else:
            # HTL-17 Group 1 (C-4/C-10): one shared rule (resolve_mock_io_dirs), the same
            # function main.py uses for its own default-folder selection, replaces this
            # method's previously-separate isinstance(self.llm_client, MockLLMClient) check.
            in_path, out_path = resolve_mock_io_dirs(
                mock=isinstance(self.llm_client, MockLLMClient),
                inputs_dir=inputs_dir,
                output_dir=output_dir,
            )

            progress("ingesting", str(in_path))
            logger.info("Starting PMO Startup Kit generation from directory: %s", in_path)

            # 1. Ingest Documents
            documents = self.ingestion_service.ingest_directory(in_path)
            if not documents:
                raise FileNotFoundError(
                    f"No supported documents found in inputs directory: {in_path}. "
                    "Please place SOW PDF/DOCX or presentation PPTX files into the inputs folder."
                )

        logger.info("Ingested %d document(s): %s", len(documents), [d.file_name for d in documents])

        # VAL-11: Extract explicit award/start date statements from ingested documents
        stated_award_date, date_warning = extract_stated_award_date(documents)
        if stated_award_date:
            logger.info("Extracted stated SOW award/start date: %s", stated_award_date)

        # 2. Multi-Pass LLM Extraction (Concurrent Execution)
        progress("extracting")
        logger.info("Executing concurrent multi-pass LLM extractions (12 domain passes)...")
        try:
            with ThreadPoolExecutor(max_workers=14) as executor:
                futures_map = {
                    executor.submit(self.charter_extractor.extract, documents, self.llm_client): "charter",
                    executor.submit(self.deliverables_extractor.extract, documents, self.llm_client): "deliverables",
                    executor.submit(self.milestones_extractor.extract, documents, self.llm_client): "milestones",
                    executor.submit(self.raid_extractor.extract, documents, self.llm_client): "raid",
                    executor.submit(self.questions_extractor.extract, documents, self.llm_client): "questions",
                }
                if self.sow_interpretation_extractor:
                    futures_map[executor.submit(self.sow_interpretation_extractor.extract, documents, self.llm_client)] = "sow"
                if self.acceptance_extractor:
                    futures_map[executor.submit(self.acceptance_extractor.extract, documents, self.llm_client)] = "acceptance"
                if self.stakeholders_extractor:
                    futures_map[executor.submit(self.stakeholders_extractor.extract, documents, self.llm_client)] = "stakeholders"
                if self.communications_extractor:
                    futures_map[executor.submit(self.communications_extractor.extract, documents, self.llm_client)] = "communications"
                if self.commercial_extractor:
                    futures_map[executor.submit(self.commercial_extractor.extract, documents, self.llm_client)] = "commercial"
                if self.talent_extractor:
                    futures_map[executor.submit(self.talent_extractor.extract, documents, self.llm_client)] = "talent"
                if self.decisions_extractor:
                    futures_map[executor.submit(self.decisions_extractor.extract, documents, self.llm_client)] = "decisions"
                if self.conflicts_extractor:
                    futures_map[executor.submit(self.conflicts_extractor.extract, documents, self.llm_client)] = "conflicts"

                total_extractors = len(futures_map) + (1 if self.backlog_extractor else 0)
                results = {}
                completed_count = 0
                for future in as_completed(futures_map):
                    key = futures_map[future]
                    results[key] = future.result()
                    completed_count += 1
                    progress("extracting", f"{completed_count}/{total_extractors} complete")

                charter = results["charter"]
                deliverables = results["deliverables"]
                milestones = results["milestones"]
                raid = results["raid"]
                questions = results["questions"]
                sow_interpretation = results.get("sow")
                acceptance = results.get("acceptance")
                stakeholders = results.get("stakeholders")
                communications = results.get("communications")
                commercial = results.get("commercial")
                talent = results.get("talent")
                decisions = results.get("decisions")
                conflicts = results.get("conflicts")

            # Backlog extraction passes deliverables
            if self.backlog_extractor:
                backlog = self.backlog_extractor.extract(
                    documents, self.llm_client, deliverables=deliverables.deliverables
                )
                completed_count += 1
                progress("extracting", f"{completed_count}/{total_extractors} complete")
            else:
                backlog = None
        except Exception as exc:
            reason = str(exc).strip() or exc.__class__.__name__
            if any(reason.startswith(f"{lbl} failed:") for lbl in ("ingestion", "extraction", "validation", "document generation", "run")):
                raise
            raise RuntimeError(f"extraction failed: {reason}") from exc

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
            sow_awarded_date=stated_award_date,
            award_date_source=AWARD_DATE_SOURCE_STATED if stated_award_date else None,
        )

        # 3b. Extraction Validation Layer (Section 4, VAL-01 to VAL-07)
        progress("validating")
        logger.info("Running extraction validation layer and reconciliation...")
        validation_report = validate_and_repair_baseline(baseline, date_conflict_warning=date_warning)

        # HTL-02 / HTL-29: Pipeline split point for Pre-Generation Human Review
        if pause_for_review:
            from src.review_storage import get_review_storage

            storage = get_review_storage()
            baseline_dict = baseline.model_dump(mode="json")
            validation_report_dict = validation_report.model_dump(mode="json")
            project_name = baseline.project_name or "Project Baseline"
            run_id = storage.create_run(
                project_name=project_name,
                baseline=baseline_dict,
                validation_report=validation_report_dict,
            )
            logger.info("Paused run created in review queue: %s", run_id)
            fallback_domains = list(getattr(self.llm_client, "fallback_domains", []) or [])
            primary_provider = getattr(self.llm_client, "primary_provider", None)
            return RunResult(
                readiness_score=baseline.readiness_score,
                baseline=baseline,
                validation_report=validation_report,
                fallback_domains=fallback_domains,
                primary_provider=primary_provider,
                paused=True,
                run_id=run_id,
            )

        # 4. Document & Workbook & Deck Generation according to outputs selection
        return self.generate_from_baseline(
            baseline=baseline,
            output_dir=out_path,
            outputs=outputs,
            start_date=start_date,
            on_progress=on_progress,
        )

    def generate_from_baseline(
        self,
        baseline: StartupKitBaseline,
        output_dir: Path,
        outputs: Optional[OutputSelection] = None,
        start_date: Optional[date] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> RunResult:
        """HTL-10: Produce the Kit, Checklist, Workbook, and deck from a validated/corrected baseline."""
        progress = on_progress or _noop_progress
        if outputs is None:
            outputs = OutputSelection(kit=True, checklist=True, workbook=True, slides=True)

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        kit_path: Optional[Path] = None
        checklist_path: Optional[Path] = None
        wb_result: Optional[PMOWorkbookResult] = None
        deck_result: Optional[OnboardingDeckResult] = None
        written_paths: List[Path] = []

        if outputs.slides and not outputs.checklist:
            logger.info("Deck sources: Startup Kit and Project Delivery Workbook also written")

        if outputs.kit:
            progress("generating", "Startup Kit")
            logger.info("Generating Word Startup Kit document in %s...", out_path)
            if hasattr(self.doc_writer, "write_kit_docx"):
                kit_path = self.doc_writer.write_kit_docx(baseline, out_path)
            else:
                kit_path = self.doc_writer.write_docx(baseline, out_path)
            written_paths.append(kit_path)

        if outputs.checklist:
            progress("generating", "Readiness Checklist")
            logger.info("Generating Word Startup Readiness Checklist document in %s...", out_path)
            if hasattr(self.doc_writer, "write_checklist_docx"):
                checklist_path = self.doc_writer.write_checklist_docx(baseline, out_path)
                written_paths.append(checklist_path)

        if outputs.workbook:
            progress("generating", "Delivery Workbook")
            logger.info("Exporting Project Delivery Workbook to %s", out_path)
            wb_result = export_pmo_workbook(baseline, out_path, start_date=start_date)
            written_paths.append(wb_result.file_path)

        if outputs.slides:
            progress("generating", "Onboarding Deck")
            logger.info("Exporting Talent Onboarding Deck to %s", out_path)
            deck_result = export_onboarding_deck(baseline, out_path, start_date=start_date)
            written_paths.append(deck_result.file_path)
            written_paths.append(deck_result.manifest_path)

        # 5. Build (but do not print) the CLI telemetry summary (HTL-16 Group 3: the
        # orchestrator itself prints nothing; main.py takes this returned text and prints it).
        summary_parts = [format_readiness_cli_summary(baseline, written_paths if written_paths else [out_path])]
        if wb_result is not None:
            summary_parts.append(format_workbook_export_summary(wb_result))
        if deck_result is not None:
            summary_parts.append(format_deck_export_summary(deck_result))
        summary_text = "\n".join(summary_parts)

        logger.info("Startup Kit execution complete! Readiness score: %.1f%%", baseline.readiness_score)
        # HTL-24: structured result fields -- the validated baseline (which already carries the
        # VAL-11/INV-38 award-date conflict warning in its open_questions/findings), the
        # validation report, and any OpenAI fallback-model notice -- so a UI can render its own
        # presentation from the same data the CLI prints, instead of only reading stdout/logs.
        fallback_domains = list(getattr(self.llm_client, "fallback_domains", []) or [])
        primary_provider = getattr(self.llm_client, "primary_provider", None)
        return RunResult(
            kit_path=kit_path,
            checklist_path=checklist_path,
            workbook=wb_result,
            slides=deck_result,
            slides_path=deck_result.file_path if deck_result else None,
            readiness_score=baseline.readiness_score,
            baseline=baseline,
            validation_report=getattr(baseline, "validation_report", None),
            summary_text=summary_text,
            fallback_domains=fallback_domains,
            primary_provider=primary_provider,
        )

    def run_reingest(
        self,
        docx_path: Optional[Path] = None,
        docx_source: Optional[Tuple[str, Union[bytes, BinaryIO]]] = None,
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
        always_write_new_file: bool = False,
        on_progress: Optional[ProgressCallback] = None,
    ) -> RunResult:
        """Re-ingest an updated *_Startup_Kit.docx file, recalculate readiness, and regenerate report.

        HTL-16 Group 2 (C-12): ``docx_source`` is an alternative to ``docx_path`` for an
        uploaded Kit that has no disk path (``(file_name, bytes_or_file_like)``). Since an
        upload has nothing to overwrite in place, ``output_dir`` or ``output_file`` is required
        when using ``docx_source``. Passing ``docx_path`` keeps the CLI's existing
        in-place-with-backup default completely unchanged.

        HTL-23: ``always_write_new_file`` is the ALTERNATIVE to the CLI's default
        in-place-overwrite-with-timestamped-backup behavior. When True, the Kit document is
        never written back over ``docx_path`` -- if no ``output_file``/``output_dir`` is given
        either, a new, timestamped file name is generated next to the input instead of
        overwriting it, and no backup is created (there is nothing to back up). The CLI's
        default (``always_write_new_file=False``) is unchanged; a future app always passes
        ``always_write_new_file=True`` for its uploads (HTL-23), which already pairs naturally
        with ``docx_source`` always requiring an explicit output destination above.

        HTL-28: ``on_progress(stage, detail="")`` reports real stage boundaries -- re-ingestion
        has no LLM extraction pass of its own (it parses an existing Kit document rather than
        re-running extraction), so only ``"ingesting"``, ``"validating"`` (the readiness
        recalculation), and ``"generating"`` (once per document type actually written) fire here.
        Defaults to a no-op, so this is a pure addition with no effect on any existing caller.
        """
        if outputs is None:
            outputs = OutputSelection()
        progress = on_progress or _noop_progress
        if always_write_new_file:
            create_backup = False

        _upload_temp_dir: Optional[str] = None
        if docx_source is not None:
            if output_dir is None and output_file is None:
                raise ValueError(
                    "output_dir or output_file is required when re-ingesting from docx_source: "
                    "an uploaded document has no disk location to overwrite in place."
                )
            file_name, content = docx_source
            _upload_temp_dir = tempfile.mkdtemp(prefix="startup_kit_reingest_")
            docx_file = Path(_upload_temp_dir) / Path(file_name).name
            data = content.read() if hasattr(content, "read") else content
            if isinstance(data, str):
                data = data.encode("utf-8")
            docx_file.write_bytes(data)
            create_backup = False  # nothing to back up; this is a disposable temp copy
        elif docx_path is not None:
            docx_file = Path(docx_path)
            if not docx_file.exists():
                raise FileNotFoundError(f"Target Startup Kit Word document not found at: {docx_file}")
        else:
            raise ValueError("Either docx_path or docx_source must be provided.")

        progress("ingesting", str(docx_file))
        logger.info("Executing Single-Document Ingestion for: %s", docx_file)
        baseline = self.docx_parser.parse_startup_kit_docx(docx_file)

        if _upload_temp_dir is not None:
            # The parser has already read everything it needs; nothing later in this method
            # re-reads the uploaded file's bytes (create_backup is forced False above, and
            # docx_file.name below is a pure Path operation that needs no existing file).
            shutil.rmtree(_upload_temp_dir, ignore_errors=True)

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
        progress("validating")
        logger.info("Recalculating Startup Readiness Score and G-01 Gate Decision...")
        baseline = self.aggregator.recalculate_readiness(baseline)

        # Determine target output path
        if output_file is not None:
            target_path = Path(output_file)
        elif output_dir is not None:
            target_dir = Path(output_dir)
            target_path = target_dir / docx_file.name
        elif always_write_new_file:
            # HTL-23: never overwrite the input Kit in place; synthesize a new file name.
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_path = docx_file.with_name(f"{docx_file.stem}_{timestamp}{docx_file.suffix}")
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

            progress("generating", "Startup Kit")
            logger.info("Regenerating updated Word Startup Kit document at: %s", target_path)
            if hasattr(self.doc_writer, "write_kit_docx"):
                kit_path = self.doc_writer.write_kit_docx(baseline, target_path)
            else:
                kit_path = self.doc_writer.write_docx(baseline, target_path)
            written_paths.append(kit_path)
        else:
            logger.info("Readiness recalculated; the Startup Kit .docx was not rewritten. Add --kit or --all to update it.")

        if outputs.checklist:
            progress("generating", "Readiness Checklist")
            logger.info("Regenerating updated Word Startup Readiness Checklist document at: %s", target_path)
            if hasattr(self.doc_writer, "write_checklist_docx"):
                checklist_path = self.doc_writer.write_checklist_docx(baseline, target_path)
                written_paths.append(checklist_path)

        export_dir = target_path.parent
        if outputs.workbook:
            progress("generating", "Delivery Workbook")
            logger.info("Exporting Project Delivery Workbook to %s", export_dir)
            wb_result = export_pmo_workbook(baseline, export_dir, start_date=start_date)
            written_paths.append(wb_result.file_path)

        deck_result: Optional[OnboardingDeckResult] = None
        if outputs.slides:
            progress("generating", "Onboarding Deck")
            logger.info("Exporting Talent Onboarding Deck to %s", export_dir)
            deck_result = export_onboarding_deck(baseline, export_dir, start_date=start_date)
            written_paths.append(deck_result.file_path)
            written_paths.append(deck_result.manifest_path)

        if output_file is not None and not (outputs.kit or outputs.checklist):
            logger.warning("--output-file was provided but neither the Startup Kit nor the Readiness Checklist was selected; it only sets the destination folder for the workbook and deck.")

        # Build (but do not print) the CLI telemetry summary (HTL-16 Group 3: the orchestrator
        # itself prints nothing; main.py takes this returned text and prints it).
        summary_parts = [format_readiness_cli_summary(baseline, written_paths if written_paths else [target_path])]
        if wb_result is not None:
            summary_parts.append(format_workbook_export_summary(wb_result))
        if deck_result is not None:
            summary_parts.append(format_deck_export_summary(deck_result))
        summary_text = "\n".join(summary_parts)

        logger.info(
            "Startup Kit Re-evaluation complete! Readiness Score: %s%%, Status: %s",
            baseline.readiness_score,
            baseline.gate_decision.gate_decision_status if baseline.gate_decision else "N/A"
        )
        fallback_domains = list(getattr(self.llm_client, "fallback_domains", []) or [])
        primary_provider = getattr(self.llm_client, "primary_provider", None)
        return RunResult(
            kit_path=kit_path,
            checklist_path=checklist_path,
            workbook=wb_result,
            slides=deck_result,
            slides_path=deck_result.file_path if deck_result else None,
            readiness_score=baseline.readiness_score,
            baseline=baseline,
            validation_report=getattr(baseline, "validation_report", None),
            summary_text=summary_text,
            fallback_domains=fallback_domains,
            primary_provider=primary_provider,
        )
