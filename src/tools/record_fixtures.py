"""Script to record LLM extractions and generate fixture sets for QA-02."""

import shutil
import json
import logging
from pathlib import Path
from src.config import config
from src.core.models import AWARD_DATE_SOURCE_STATED
from src.extractors.service import IngestionService
from src.extractors.date_extractor import extract_stated_award_date
from src.llm.client import LangChainLLMClient, CachingLLMClient, MockLLMClient
from src.llm.aggregator import BaselineAggregator
from main import create_mock_llm_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

FIXTURES_TO_RECORD = [
    {
        "name": "arc_genomics",
        "input_dir": Path("tests/fixtures/sow/arc_genomics/inputs"),
        "is_mock": False,
        "is_synthetic": False,
    },
    {
        "name": "mock_sow",
        "input_dir": Path("tests/fixtures/sow/mock_sow/inputs"),
        "is_mock": True,
        "is_synthetic": False,
    },
    {
        "name": "no_story_ids",
        "input_dir": Path("tests/fixtures/sow/no_story_ids/inputs"),
        "is_mock": False,
        "is_synthetic": True,
    },
    {
        "name": "numbered_deliverables",
        "input_dir": Path("tests/fixtures/sow/numbered_deliverables/inputs"),
        "is_mock": False,
        "is_synthetic": True,
    },
    {
        "name": "arc_application_implementation",
        "input_dir": Path("tests/fixtures/sow/arc_application_implementation/inputs"),
        "is_mock": False,
        "is_synthetic": False,
    },
]


def record_fixture(fixture_info: dict, global_cache_dir: Path, target_base_dir: Path):
    name = fixture_info["name"]
    input_dir = fixture_info["input_dir"]
    is_mock = fixture_info["is_mock"]
    
    logger.info(f"--- Recording fixture: {name} from {input_dir} (mock={is_mock}) ---")
    fixture_dir = target_base_dir / name
    fixture_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Copy inputs
    fixture_inputs = fixture_dir / "inputs"
    if input_dir.resolve() != fixture_inputs.resolve():
        if fixture_inputs.exists():
            shutil.rmtree(fixture_inputs)
        shutil.copytree(input_dir, fixture_inputs)
    
    # 2. Ingest
    ingestion = IngestionService()
    docs = ingestion.ingest_directory(fixture_inputs)
    logger.info(f"Ingested {len(docs)} documents for {name}")
    
    # 3. Setup client in record mode (writing to fixture_dir / 'llm_cache' AND global_cache_dir)
    local_cache_dir = fixture_dir / "llm_cache"
    local_cache_dir.mkdir(parents=True, exist_ok=True)
    
    if is_mock:
        raw_client = create_mock_llm_client()
    else:
        raw_client = LangChainLLMClient(
            api_key=config.anthropic_api_key,
            model_name=config.anthropic_model,
            openai_api_key=config.openai_api_key,
            openai_model_name=config.openai_model,
            temperature=0.0
        )
    
    # Wrap in caching client recording to local cache
    caching_client = CachingLLMClient(
        inner_client=raw_client,
        cache_dir=local_cache_dir,
        mode="record" if not is_mock else "record",
        model_id=config.anthropic_model if not is_mock else "mock-client"
    )
    
    # Run extractors concurrently
    from concurrent.futures import ThreadPoolExecutor
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
    
    charter_ext = CharterDomainExtractor()
    deliv_ext = DeliverablesDomainExtractor()
    milestones_ext = MilestonesDomainExtractor()
    raid_ext = RAIDDomainExtractor()
    questions_ext = QuestionsDomainExtractor()
    sow_interp_ext = SOWInterpretationDomainExtractor()
    backlog_ext = ScopeDecompositionDomainExtractor()
    acceptance_ext = AcceptanceProcessDomainExtractor()
    stakeholders_ext = StakeholdersDomainExtractor()
    comms_ext = CommunicationsDomainExtractor()
    commercial_ext = CommercialGuardrailsDomainExtractor()
    talent_ext = TalentOnboardingDomainExtractor()
    decisions_ext = DecisionsDomainExtractor()
    conflicts_ext = ContractConflictsDomainExtractor()

    logger.info("Extracting first batch of domains concurrently...")
    with ThreadPoolExecutor(max_workers=14) as executor:
        f_charter = executor.submit(charter_ext.extract, docs, caching_client)
        f_deliv = executor.submit(deliv_ext.extract, docs, caching_client)
        f_milestones = executor.submit(milestones_ext.extract, docs, caching_client)
        f_raid = executor.submit(raid_ext.extract, docs, caching_client)
        f_questions = executor.submit(questions_ext.extract, docs, caching_client)
        f_sow = executor.submit(sow_interp_ext.extract, docs, caching_client)
        f_acceptance = executor.submit(acceptance_ext.extract, docs, caching_client)
        f_stakeholders = executor.submit(stakeholders_ext.extract, docs, caching_client)
        f_comms = executor.submit(comms_ext.extract, docs, caching_client)
        f_commercial = executor.submit(commercial_ext.extract, docs, caching_client)
        f_talent = executor.submit(talent_ext.extract, docs, caching_client)
        f_decisions = executor.submit(decisions_ext.extract, docs, caching_client)
        f_conflicts = executor.submit(conflicts_ext.extract, docs, caching_client)

        charter = f_charter.result()
        deliverables = f_deliv.result()
        milestones = f_milestones.result()
        raid = f_raid.result()
        questions = f_questions.result()
        sow_interp = f_sow.result()
        acceptance = f_acceptance.result()
        stakeholders = f_stakeholders.result()
        comms = f_comms.result()
        commercial = f_commercial.result()
        talent = f_talent.result()
        decisions = f_decisions.result()
        conflicts = f_conflicts.result()

    # Backlog extraction passes deliverables
    logger.info("Extracting backlog domain...")
    backlog = backlog_ext.extract(docs, caching_client, deliverables=deliverables.deliverables)
    
    # Aggregate
    stated_award_date, _ = extract_stated_award_date(docs)
    aggregator = BaselineAggregator()
    baseline = aggregator.aggregate(
        charter=charter,
        deliverables_ext=deliverables,
        milestones_ext=milestones,
        raid_ext=raid,
        questions_ext=questions,
        sow_interpretation_ext=sow_interp,
        backlog_ext=backlog,
        acceptance_ext=acceptance,
        stakeholders_ext=stakeholders,
        communications_ext=comms,
        commercial_ext=commercial,
        talent_ext=talent,
        decisions_ext=decisions,
        conflicts_ext=conflicts,
        sow_awarded_date=stated_award_date,
        award_date_source=AWARD_DATE_SOURCE_STATED if stated_award_date else None,
    )
    
    # Save baseline JSON
    baseline_json_path = fixture_dir / "baseline.json"
    with open(baseline_json_path, "w", encoding="utf-8") as f:
        json.dump(baseline.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
    
    # Also copy all cached json files from local_cache_dir into global_cache_dir
    for f in local_cache_dir.glob("*.json"):
        shutil.copy(f, global_cache_dir / f.name)
        
    logger.info(f"Successfully recorded fixture {name} to {fixture_dir}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Record fixtures")
    parser.add_argument("--fixture", type=str, default=None, help="Name of specific fixture to record")
    args = parser.parse_args()

    global_cache_dir = Path("tests/fixtures/llm_cache")
    global_cache_dir.mkdir(parents=True, exist_ok=True)
    target_base_dir = Path("tests/fixtures/sow")
    
    fixtures = [f for f in FIXTURES_TO_RECORD if args.fixture is None or f["name"] == args.fixture]
    for fix in fixtures:
        record_fixture(fix, global_cache_dir, target_base_dir)


if __name__ == "__main__":
    main()
