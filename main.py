"""Toptal PMO Startup Kit Generator CLI Entry Point."""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional, Union

from src.config import config, normalize_person_name
from src.extractors.service import IngestionService
from src.llm.client import LangChainLLMClient, MockLLMClient, CachingLLMClient
from src.llm.mock_responses import create_mock_llm_client
from src.llm.aggregator import BaselineAggregator
from src.generators.docx_generator import DocxGenerator
from src.orchestrator import (
    StartupKitController,
    build_llm_client,
    resolve_role_for_reingest,
    parse_start_date,
    resolve_execution_mode,
    resolve_mock_io_dirs,
)
from src.core.models import (
    SourceReference,
    Deliverable,
    Milestone,
    RiskAssumption,
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
    ContractAmbiguityItem,
    WorkPackageSeed,
    DecisionItem,
    CommunicationsPlanItem,
    Stakeholder,
    CommercialGuardrail,
    TalentOnboardingRecord,
    TalentMember,
    OutputSelection,
    RunResult,
)
from datetime import date


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )


# HTL-19: create_mock_llm_client now lives in src.llm.mock_responses (imported above)
# so both the CLI and the future Streamlit app share the same offline fake-data generator.
# It is re-exported here (as the `create_mock_llm_client` name imported above) for backward
# compatibility, since this module's own tests still do `from main import create_mock_llm_client`.


def parse_args():
    parser = argparse.ArgumentParser(
        description="Toptal PMO Startup Kit Generator - Automated Document Ingestion and Word Report Generation.",
        epilog="Output: by default only the PMO Startup Toolkit workbook is written. Add --kit, --checklist, or --all to also write Word documents."
    )
    parser.add_argument(
        "--inputs-dir",
        type=Path,
        default=None,
        help="Path to inputs directory containing SOWs and decks (default: inputs/, or tests/fixtures/sow/mock_sow/inputs when --mock is used)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Path to output directory for generated Word reports (default: output/, or output/Reports/Test when --mock is used)"
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=None,
        help="Explicit destination file path for regenerated Word report"
    )
    parser.add_argument(
        "--reingest-docx",
        "--docx-file",
        type=Path,
        dest="reingest_docx",
        default=None,
        help="Path to existing *_Startup_Kit.docx to re-ingest and recalculate readiness score"
    )
    parser.add_argument(
        "--provider",
        "--llm-provider",
        type=str,
        default=config.default_provider,
        choices=["anthropic", "openai", "claude", "gpt"],
        help="LLM provider to use: 'anthropic' (Claude, default) or 'openai' (GPT)"
    )
    parser.add_argument(
        "--openai",
        "--open-ai",
        action="store_true",
        help="Use OpenAI as the LLM provider"
    )
    parser.add_argument(
        "--anthropic",
        "--claude",
        action="store_true",
        help="Use Anthropic Claude as the LLM provider (default)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="LLM model name (defaults to 'claude-sonnet-5-5' for Anthropic or 'gpt-4o' for OpenAI)"
    )
    parser.add_argument(
        "--tier",
        type=str,
        choices=["Guided", "Partnered", "Elevated"],
        default=None,
        help="Override Governance Tier (Guided, Partnered, Elevated)"
    )
    parser.add_argument(
        "--contract-type",
        type=str,
        default=None,
        help="Override Contract Type (e.g., 'Time and Materials', 'Fixed Bid')"
    )
    parser.add_argument(
        "--pmo-lead",
        type=str,
        default=None,
        help="PMO Lead name (defaults to '[UNASSIGNED - TO BE CONFIRMED]' if not provided)"
    )
    parser.add_argument(
        "--delivery-lead",
        "--delivery-manager",
        type=str,
        dest="delivery_lead",
        default=None,
        help="Delivery Lead / Manager name (defaults to '[UNASSIGNED - TO BE CONFIRMED]' if not provided)"
    )
    parser.add_argument(
        "--talent-pm",
        type=str,
        default=None,
        help="Talent PM name (defaults to '[UNASSIGNED - TO BE CONFIRMED]' if not provided)"
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Disable interactive directory and role prompts (uses default paths and unassigned roles)"
    )
    parser.add_argument(
        "--api-key",
        "--anthropic-api-key",
        type=str,
        dest="api_key",
        default=None,
        help="Anthropic API Key (overrides ANTHROPIC_API_KEY environment variable and .env)"
    )
    parser.add_argument(
        "--openai-api-key",
        type=str,
        dest="openai_api_key",
        default=None,
        help="OpenAI API Key for fallback or direct execution (overrides OPENAI_API_KEY environment variable and .env)"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run using offline deterministic Mock LLM client (no API keys required)"
    )
    parser.add_argument(
        "--llm-cache",
        choices=["off", "record", "replay"],
        default=None,
        help="LLM cache mode (off, record, replay; default from LLM_CACHE_MODE or off)"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Project Start Date in ISO format (YYYY-MM-DD); planned dates are derived from this date"
    )
    parser.add_argument(
        "--export-tools",
        action="store_true",
        help="Write the Project Delivery Workbook Excel workbook (default when no output flag is given)"
    )
    parser.add_argument(
        "--kit",
        action="store_true",
        help="Write the Startup Kit Word document"
    )
    parser.add_argument(
        "--checklist",
        action="store_true",
        help="Write the Startup Readiness Checklist Word document"
    )
    parser.add_argument(
        "--slides",
        action="store_true",
        help="Write the Talent Team Onboarding Deck PowerPoint presentation"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="all_outputs",
        help="Write the Startup Kit, the Readiness Checklist, the Project Delivery Workbook, and the Talent Onboarding Deck"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose debug logging"
    )
    return parser.parse_args()


def prompt_directories(
    inputs_dir: Optional[Union[str, Path]] = None,
    output_dir: Optional[Union[str, Path]] = None,
    interactive: bool = True,
    default_inputs_dir: Path = config.inputs_dir,
    default_output_dir: Path = config.output_dir
) -> tuple[Path, Path]:
    """Request input and output directory paths via CLI arguments or interactive prompts, falling back to defaults."""
    def _resolve(prompt_label: str, val: Optional[Union[str, Path]], default_path: Path) -> Path:
        if val is not None:
            if isinstance(val, str):
                cleaned = val.strip()
                return Path(cleaned) if cleaned else default_path
            return val
        if interactive:
            try:
                entered = input(f"Enter {prompt_label} [default: {default_path}]: ").strip()
                return Path(entered) if entered else default_path
            except (EOFError, OSError):
                return default_path
        return default_path

    resolved_inputs = _resolve("inputs directory", inputs_dir, default_inputs_dir)
    resolved_output = _resolve("output directory", output_dir, default_output_dir)
    return resolved_inputs, resolved_output


def prompt_reingest_file(
    docx_file: Optional[Union[str, Path]] = None,
    interactive: bool = True
) -> Optional[Path]:
    """Prompt for the path to the updated Startup Kit .docx file to re-ingest.

    A path/filename is required; there is no default. Typing 'exit' cancels and exits.
    """
    if docx_file is not None:
        if isinstance(docx_file, str):
            cleaned = docx_file.strip().strip("\"'")
            if cleaned:
                if cleaned.lower() in ("exit", "quit"):
                    return None
                return Path(cleaned)
            return None
        return docx_file

    if not interactive:
        return None

    while True:
        try:
            entered = input("Enter path to updated *_Startup_Kit.docx file (or type 'exit'): ").strip().strip("\"'")
            if not entered:
                print("Path/filename is required. Please enter a valid file path or type 'exit' to quit.")
                continue
            if entered.lower() in ("exit", "quit"):
                return None
            return Path(entered)
        except (EOFError, KeyboardInterrupt):
            return None


def prompt_execution_mode(interactive: bool = True) -> str:
    """Prompt user to select between Initial Generation (1) and DOCX Re-ingestion (2)."""
    if not interactive:
        return "1"
    try:
        print("Select Startup Kit execution mode:")
        print("  [1] Initial Generation (Ingest raw SOWs/decks from inputs directory)")
        print("  [2] Re-evaluate & Ingest updated *_Startup_Kit.docx")
        choice = input("Enter choice [1/2, default: 1]: ").strip()
        if choice in ("2", "re-evaluate", "reingest", "docx"):
            return "2"
        return "1"
    except (EOFError, OSError):
        return "1"


def prompt_role_names(
    pmo_lead: Optional[str] = None,
    delivery_lead: Optional[str] = None,
    talent_pm: Optional[str] = None,
    interactive: bool = True,
    default: str = "[UNASSIGNED - TO BE CONFIRMED]"
) -> tuple[str, str, str]:
    """Request leadership role names via CLI arguments or interactive prompts, defaulting to '[UNASSIGNED - TO BE CONFIRMED]'."""
    def _resolve(role_name: str, val: Optional[str]) -> str:
        if val is not None:
            cleaned = val.strip()
            return normalize_person_name(cleaned, default=default) if cleaned else default
        if interactive:
            try:
                entered = input(f"Enter {role_name} name [default: {default}]: ").strip()
                return normalize_person_name(entered, default=default) if entered else default
            except (EOFError, OSError):
                return default
        return default

    resolved_pmo_lead = _resolve("PMO Lead", pmo_lead)
    resolved_delivery_lead = _resolve("Delivery Lead", delivery_lead)
    resolved_talent_pm = _resolve("Talent PM", talent_pm)
    return resolved_pmo_lead, resolved_delivery_lead, resolved_talent_pm


def prompt_api_keys(
    api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    interactive: bool = False,
    default_anthropic_key: str = "",
    default_openai_key: str = "",
) -> tuple[str, str]:
    """Resolve Anthropic and OpenAI API keys via CLI arguments, environment variables, or configuration."""
    resolved_anthropic = api_key if api_key is not None else (default_anthropic_key or config.anthropic_api_key)
    resolved_openai = openai_api_key if openai_api_key is not None else (default_openai_key or config.openai_api_key)
    return resolved_anthropic, resolved_openai


def main():
    args = parse_args()
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger("main")

    logger.info("=========================================================")
    logger.info("    TOPTAL PMO STARTUP KIT GENERATOR (Readiness Phase)   ")
    logger.info("=========================================================")

    try:
        is_interactive = not args.non_interactive

        # HTL-17 Group 1 (C-2): shared parse/validate helper; the exit code/logging stays here.
        parsed_start_date: Optional[date] = None
        if getattr(args, "start_date", None):
            try:
                parsed_start_date = parse_start_date(args.start_date)
            except ValueError:
                logger.error("Invalid --start-date format '%s'. Must be YYYY-MM-DD.", args.start_date)
                return 1

        # HTL-17 Group 1 (C-3): shared mode-selection rule; the interactive input() prompt
        # itself (CLI-only UX) is collected here and handed to the shared resolver.
        prompted_mode = (
            prompt_execution_mode(interactive=True)
            if (args.reingest_docx is None and is_interactive)
            else None
        )
        mode = resolve_execution_mode(args.reingest_docx, is_interactive, prompted_mode)

        outputs = OutputSelection.from_flags(
            all_=args.all_outputs,
            kit=args.kit,
            checklist=args.checklist,
            export_tools=args.export_tools,
            slides=args.slides,
        )
        logger.info(
            "Outputs -> Kit: %s | Checklist: %s | Workbook: %s | Slides: %s",
            "yes" if outputs.kit else "no",
            "yes" if outputs.checklist else "no",
            "yes" if outputs.workbook else "no",
            "yes" if outputs.slides else "no",
        )

        if mode == "2":
            target_docx = prompt_reingest_file(
                docx_file=args.reingest_docx,
                interactive=is_interactive,
            )
            if target_docx is None:
                if is_interactive:
                    logger.info("Exiting Startup Kit re-ingestion.")
                    return 0
                else:
                    logger.error("No DOCX file provided for re-ingestion mode. Specify --reingest-docx <path>.")
                    return 1

            logger.info("Mode: DOCX Re-ingestion & Readiness Recalculation")
            logger.info("Target Document: %s", target_docx)

            pmo_lead, delivery_lead, talent_pm = prompt_role_names(
                pmo_lead=args.pmo_lead,
                delivery_lead=args.delivery_lead,
                talent_pm=args.talent_pm,
                interactive=is_interactive
            )

            controller = StartupKitController(
                doc_writer=DocxGenerator(),
                aggregator=BaselineAggregator()
            )

            # HTL-25: the "blank role on re-ingest" decision lives in the shared
            # resolve_role_for_reingest function now, not inline here.
            run_result = controller.run_reingest(
                docx_path=target_docx,
                output_dir=args.output_dir,
                output_file=args.output_file,
                pmo_lead=resolve_role_for_reingest(args.pmo_lead, pmo_lead, is_interactive),
                delivery_lead=resolve_role_for_reingest(args.delivery_lead, delivery_lead, is_interactive),
                talent_pm=resolve_role_for_reingest(args.talent_pm, talent_pm, is_interactive),
                tier_override=args.tier,
                contract_type_override=args.contract_type,
                outputs=outputs,
                start_date=parsed_start_date,
            )

            # HTL-16 Group 3: the orchestrator no longer prints; main.py prints the returned
            # summary text (cli_reporter.py's formatting functions, now fed by RunResult).
            if run_result.summary_text:
                print(run_result.summary_text)

            logger.info("SUCCESS: Project Startup Kit re-evaluated successfully!")
            if run_result.kit_path:
                logger.info("Startup Kit Word Document: %s", run_result.kit_path.resolve())
            if run_result.checklist_path:
                logger.info("Readiness Checklist Word Document: %s", run_result.checklist_path.resolve())
            if run_result.workbook:
                logger.info("Project Delivery Workbook: %s", run_result.workbook.file_path.resolve())
            if run_result.slides:
                logger.info("Talent Onboarding Deck: %s", run_result.slides.file_path.resolve())
            return 0

        # Mode 1: Initial Generation
        logger.info("Mode: Initial Generation (From SOWs and input artifacts)")
        # HTL-17 Group 1 (C-4/C-10): one shared rule, also used by orchestrator.run()'s own
        # fallback, replaces this module's previously-separate args.mock-based defaulting.
        default_inputs, default_outputs = resolve_mock_io_dirs(mock=args.mock)
        inputs_dir, output_dir = prompt_directories(
            inputs_dir=args.inputs_dir,
            output_dir=args.output_dir,
            interactive=is_interactive,
            default_inputs_dir=default_inputs,
            default_output_dir=default_outputs
        )
        logger.info("Directories -> Inputs: %s | Output: %s", inputs_dir, output_dir)

        pmo_lead, delivery_lead, talent_pm = prompt_role_names(
            pmo_lead=args.pmo_lead,
            delivery_lead=args.delivery_lead,
            talent_pm=args.talent_pm,
            interactive=is_interactive
        )
        logger.info("Leadership Roles -> PMO Lead: %s | Delivery Lead: %s | Talent PM: %s", pmo_lead, delivery_lead, talent_pm)

        # Determine selected LLM provider
        if args.openai or (args.provider and args.provider.lower() in ("openai", "open-ai", "gpt", "chatgpt")):
            selected_provider = "openai"
        else:
            selected_provider = "anthropic"

        active_api_key, active_openai_key = prompt_api_keys(
            api_key=args.api_key,
            openai_api_key=getattr(args, "openai_api_key", None),
            interactive=False,
            default_anthropic_key=config.anthropic_api_key,
            default_openai_key=config.openai_api_key,
        )

        cache_mode = args.llm_cache or config.llm_cache_mode

        # HTL-16/HTL-20: one shared factory builds the LLM client from explicit parameters
        # extracted from argparse here. It raises rather than silently falling back to mock
        # data when no provider is configured and --mock was not passed (intentional behavior
        # change from the CLI's previous silent fall-back; see reports/htl16_shared_layer_report.md).
        llm_client = build_llm_client(
            provider=selected_provider,
            model=args.model,
            anthropic_api_key=active_api_key,
            openai_api_key=active_openai_key,
            cache_mode=cache_mode,
            mock=args.mock,
        )

        controller = StartupKitController(
            ingestion_service=IngestionService(),
            llm_client=llm_client,
            aggregator=BaselineAggregator(),
            doc_writer=DocxGenerator()
        )

        run_result = controller.run(
            inputs_dir=inputs_dir,
            output_dir=output_dir,
            tier_override=args.tier,
            contract_type_override=args.contract_type,
            pmo_lead=pmo_lead,
            delivery_lead=delivery_lead,
            talent_pm=talent_pm,
            outputs=outputs,
            start_date=parsed_start_date,
        )

        # HTL-16 Group 3: the orchestrator no longer prints; main.py prints the returned
        # summary text (cli_reporter.py's formatting functions, now fed by RunResult).
        if run_result.summary_text:
            print(run_result.summary_text)

        if run_result.fallback_domains:
            logger.info("Notice: The following extraction domain(s) used secondary OpenAI fallback: %s", ", ".join(run_result.fallback_domains))

        logger.info("SUCCESS: Project Startup Kit generated successfully!")
        if run_result.kit_path:
            logger.info("Startup Kit Word Document: %s", run_result.kit_path.resolve())
        if run_result.checklist_path:
            logger.info("Readiness Checklist Word Document: %s", run_result.checklist_path.resolve())
        if run_result.workbook:
            logger.info("Project Delivery Workbook: %s", run_result.workbook.file_path.resolve())
        if run_result.slides:
            logger.info("Talent Onboarding Deck: %s", run_result.slides.file_path.resolve())
        return 0

    except Exception as exc:
        logger.error("Startup Kit generation failed: %s", exc, exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())
