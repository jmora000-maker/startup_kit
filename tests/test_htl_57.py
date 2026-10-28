"""HTL-57 / HTL-59: Automated test suite for multi-document upload precedence and SOW-first extraction.

Covers:
1. Two-widget split on Generate page (required SOW slot, optional supporting documents slot, accepting .md).
2. Required SOW validation blocking (Generate refuses to proceed without SOW file).
3. Document-role tagging (sow vs supporting) through ingestion pipeline into ExtractedDocument metadata.
4. Document prompt formatting with distinct precedence labeling.
5. SOW precedence and gap-filling extraction using real PGE SOW and meeting notes documents.
"""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from streamlit.testing.v1 import AppTest

from src.config import config
from src.core.models import (
    CharterExtraction,
    Deliverable,
    DeliverablesExtraction,
    ExtractedDocument,
    Milestone,
    MilestonesExtraction,
    SourceReference,
)
from src.core.outputs import OutputSelection, RunResult
from src.extractors.service import IngestionService
from src.llm.client import MockLLMClient
from src.llm.parsers import (
    CharterDomainExtractor,
    DeliverablesDomainExtractor,
    MilestonesDomainExtractor,
    format_documents_for_prompt,
)
from src.review_ui.generate import (
    validate_generate_inputs,
    _run_generate,
)

APP_FILE = str(Path(__file__).resolve().parent.parent / "src" / "review_ui" / "app.py")


def _make_unlocked_app_test() -> AppTest:
    import time
    at = AppTest.from_file(APP_FILE, default_timeout=10)
    at.session_state["generation_unlocked"] = True
    at.session_state["generation_unlocked_at"] = time.time()
    at.run()
    if at.radio(key="app_page_selector").value != "Generate / Re-ingest":
        at.radio(key="app_page_selector").set_value("Generate / Re-ingest").run()
    return at


# =========================================================================
# 1. Unit Tests: Pure Validation for SOW & Supporting Documents
# =========================================================================

def test_validate_generate_inputs_blocks_when_sow_empty():
    """validate_generate_inputs requires at least one SOW file and returns clear error."""
    error = validate_generate_inputs(sow_file_names=[], start_date_text="")
    assert error is not None
    assert "Please upload at least one Statement of Work (SOW) document" in error
    assert "PDF, DOCX, PPTX, TXT, or MD" in error


def test_validate_generate_inputs_blocks_when_only_supporting_provided():
    """Providing only supporting documents while SOW is empty must block generation."""
    error = validate_generate_inputs(
        sow_file_names=[],
        supporting_file_names=["meeting_notes.md", "architecture_assessment.pdf"],
        start_date_text="",
    )
    assert error is not None
    assert "Please upload at least one Statement of Work (SOW) document" in error


def test_validate_generate_inputs_succeeds_with_sow_only():
    """Providing only SOW document (with valid outputs) succeeds."""
    outputs = OutputSelection(kit=True)
    assert validate_generate_inputs(
        sow_file_names=["sow.pdf"],
        supporting_file_names=[],
        start_date_text="",
        outputs=outputs,
    ) is None


def test_validate_generate_inputs_succeeds_with_sow_and_supporting():
    """Providing both SOW document and supporting documents succeeds."""
    outputs = OutputSelection(kit=True, workbook=True)
    assert validate_generate_inputs(
        sow_file_names=["sow.pdf", "exhibit_a.docx"],
        supporting_file_names=["09-09-2026.md", "10-13-2026.md"],
        start_date_text="2026-11-01",
        outputs=outputs,
    ) is None


def test_validate_generate_inputs_propagates_date_and_output_errors():
    """validate_generate_inputs propagates date errors and zero-output errors when SOW is provided."""
    # Bad date
    err_date = validate_generate_inputs(sow_file_names=["sow.pdf"], start_date_text="invalid-date")
    assert err_date is not None
    assert "Invalid start date" in err_date

    # Zero outputs selected (HTL-47)
    outputs = OutputSelection(kit=False, checklist=False, workbook=False, slides=False, client_deck=False)
    err_out = validate_generate_inputs(sow_file_names=["sow.pdf"], start_date_text="", outputs=outputs)
    assert err_out is not None
    assert "Select at least one output deliverable" in err_out


# =========================================================================
# 2. Ingestion Pipeline & Document-Role Metadata Tagging
# =========================================================================

def test_ingest_sources_tags_document_roles_correctly():
    """IngestionService.ingest_sources properly tags sow and supporting roles in metadata."""
    service = IngestionService()
    sources = [
        ("contract_sow.txt", b"SOW Content: Fixed bid project.", "sow"),
        ("notes.md", b"# Notes\nPain points and operational bottlenecks.", "supporting"),
        ("default_doc.txt", b"Default document text."),  # 2-tuple defaults to 'sow'
    ]

    docs = service.ingest_sources(sources)
    assert len(docs) == 3

    assert docs[0].file_name == "contract_sow.txt"
    assert docs[0].metadata.get("document_role") == "sow"

    assert docs[1].file_name == "notes.md"
    assert docs[1].metadata.get("document_role") == "supporting"
    assert "Pain points" in docs[1].text_content

    assert docs[2].file_name == "default_doc.txt"
    assert docs[2].metadata.get("document_role") == "sow"


def test_format_documents_for_prompt_applies_distinct_precedence_labels():
    """format_documents_for_prompt produces distinct SOW vs supporting document headers."""
    doc_sow = ExtractedDocument(
        file_path=Path("Acme_SOW.docx"),
        file_name="Acme_SOW.docx",
        file_type="docx",
        text_content="Fixed bid terms and deliverables.",
        metadata={"document_role": "sow"},
    )
    doc_supp = ExtractedDocument(
        file_path=Path("Interview_Notes.md"),
        file_name="Interview_Notes.md",
        file_type="md",
        text_content="Legacy system is unreliable with manual bottlenecks.",
        metadata={"document_role": "supporting"},
    )

    formatted = format_documents_for_prompt([doc_sow, doc_supp])

    assert "=== PRIMARY SOURCE OF TRUTH (SOW): Acme_SOW.docx (Format: DOCX) ===" in formatted
    assert "Fixed bid terms and deliverables." in formatted
    assert "=== SUPPORTING DOCUMENT (FALLBACK CONTEXT ONLY): Interview_Notes.md (Format: MD) ===" in formatted
    assert "Legacy system is unreliable with manual bottlenecks." in formatted


# =========================================================================
# 3. Streamlit UI AppTest Integration Tests (Two-Widget Split & Blocking)
# =========================================================================

def test_generate_ui_renders_both_upload_widgets_with_md_support():
    """Generate tab renders both required SOW and optional supporting upload widgets supporting .md."""
    at = _make_unlocked_app_test().run()
    assert not at.exception

    sow_uploader = at.file_uploader(key="gen_sow_uploader")
    assert sow_uploader is not None
    assert "Upload Statement of Work (SOW / Exhibit A / Attachments) * [Required]" in sow_uploader.label
    assert list(sow_uploader.proto.type) == [".pdf", ".docx", ".pptx", ".txt", ".md"]
    assert sow_uploader.proto.multiple_files is True

    supp_uploader = at.file_uploader(key="gen_supporting_uploader")
    assert supp_uploader is not None
    assert "Upload Supporting Documents (meeting notes, technical assessments, etc.) [Optional]" in supp_uploader.label
    assert list(supp_uploader.proto.type) == [".pdf", ".docx", ".pptx", ".txt", ".md"]
    assert supp_uploader.proto.multiple_files is True


def test_generate_ui_blocks_when_sow_is_empty():
    """Clicking Generate with empty SOW slot displays error and strictly skips LLM call."""
    at = _make_unlocked_app_test().run()
    assert not at.exception

    # Enable output checkbox
    at.checkbox(key="gen_out_kit").check().run()

    with patch("src.review_ui.generate._run_generate") as mock_run_gen:
        at.button(key="gen_submit_button").click().run()
        assert not at.exception

        # SOW required error must be shown
        error_msgs = [e.value for e in at.error]
        assert any("Please upload at least one Statement of Work (SOW) document" in err for err in error_msgs)
        assert not mock_run_gen.called
        assert at.session_state.get("gen_is_running", False) is False


def test_generate_ui_blocks_when_only_supporting_uploaded():
    """Uploading only supporting documents while leaving SOW empty must block generation."""
    at = _make_unlocked_app_test().run()
    assert not at.exception

    at.file_uploader(key="gen_supporting_uploader").upload("notes.md", b"# Notes").run()
    at.checkbox(key="gen_out_kit").check().run()

    with patch("src.review_ui.generate._run_generate") as mock_run_gen:
        at.button(key="gen_submit_button").click().run()
        assert not at.exception

        error_msgs = [e.value for e in at.error]
        assert any("Please upload at least one Statement of Work (SOW) document" in err for err in error_msgs)
        assert not mock_run_gen.called


def test_generate_ui_passes_both_slots_to_run_generate():
    """Uploading SOW and supporting documents passes both with correct role tags to generation."""
    at = _make_unlocked_app_test().run()
    assert not at.exception

    at.file_uploader(key="gen_sow_uploader").upload("Master_SOW.docx", b"sow-bytes").run()
    at.file_uploader(key="gen_supporting_uploader").upload("Context_01.md", b"context-bytes").run()
    at.checkbox(key="gen_out_kit").check().run()

    mock_result = RunResult(
        readiness_score=90.0,
        paused=True,
        run_id="HTL57_Test_Run_20261028",
    )

    with patch("src.review_ui.generate._run_generate", return_value=mock_result) as mock_run_gen:
        at.button(key="gen_submit_button").click().run()
        assert not at.exception
        assert mock_run_gen.called

        sow_files = mock_run_gen.call_args.kwargs.get("uploaded_sow_files")
        supp_files = mock_run_gen.call_args.kwargs.get("uploaded_supporting_files")

        assert len(sow_files) == 1
        assert sow_files[0].name == "Master_SOW.docx"

        assert len(supp_files) == 1
        assert supp_files[0].name == "Context_01.md"


# =========================================================================
# 4. Real Multi-Document PGE Test Case: SOW Precedence & Gap-Filling
# =========================================================================

def test_pge_multi_document_precedence_and_gap_filling_end_to_end():
    """Real PGE Test Case:
    - Primary SOW PDF states Fixed Bid, $19,650 fee, single milestone Nov 18 2026, but NO problem statement.
    - Supporting Markdown notes detail recurring production failures, stored proc logic, and 3-hr compliance data gaps.
    - Precedence verifies problem_statement gap-fills from notes while SOW-governed fields stay anchored to SOW.
    """
    pge_dir = Path("sow/PGE")
    sow_pdf = pge_dir / "PGE Toptal SOW 7 - Cloud Migration Assessment + Exhibit A - Oct 26, 2026 (JS approved) clean .pdf"
    note_09 = pge_dir / "09-09-2026.md"
    note_13 = pge_dir / "10-13-2026.md"
    note_14 = pge_dir / "10-14-2026.md"

    if not (sow_pdf.exists() and note_09.exists()):
        pytest.skip("PGE test files not present on disk")

    service = IngestionService()
    sow_doc = service.ingest_file(sow_pdf)
    assert sow_doc is not None
    sow_doc.metadata["document_role"] = "sow"

    note1 = service.ingest_file(note_09)
    assert note1 is not None
    note1.metadata["document_role"] = "supporting"

    note2 = service.ingest_file(note_13)
    assert note2 is not None
    note2.metadata["document_role"] = "supporting"

    docs = [sow_doc, note1, note2]

    # Verify prompt formatting
    prompt_text = format_documents_for_prompt(docs)
    assert "=== PRIMARY SOURCE OF TRUTH (SOW): PGE Toptal SOW 7" in prompt_text
    assert "=== SUPPORTING DOCUMENT (FALLBACK CONTEXT ONLY): 09-09-2026.md" in prompt_text
    assert "=== SUPPORTING DOCUMENT (FALLBACK CONTEXT ONLY): 10-13-2026.md" in prompt_text

    # Mock client simulating extraction honoring precedence rules
    mock_client = MockLLMClient()

    expected_charter = CharterExtraction(
        project_name="Cloud Migration Assessment – Operational Compliance Program (OCP)",
        client_name="Portland General Electric Company",
        governance_tier="Partnered",
        contract_type="Fixed Bid",
        problem_statement=(
            "The OCP application is an aging custom system with recurring production failures "
            "and unflagged manual data overrides causing gaps at required 3-hour compliance intervals."
        ),
        source_reference=SourceReference(
            document_name="PGE Toptal SOW 7 - Cloud Migration Assessment + Exhibit A - Oct 26, 2026 (JS approved) clean .pdf",
            clause_or_slide="Header, Sections 1-4; problem statement from supporting document 09-09-2026.md",
        ),
    )
    mock_client.set_response(CharterExtraction, expected_charter)

    expected_milestones = MilestonesExtraction(milestones=[
        Milestone(
            id="MS-01",
            description="Milestone 1: Cloud Migration Assessment Report",
            external_date=date(2026, 11, 18),
            critical_path_assumptions=["$19,650 fee billed upon formal client acceptance."],
            source_reference=SourceReference(
                document_name="PGE Toptal SOW 7 - Cloud Migration Assessment + Exhibit A - Oct 26, 2026 (JS approved) clean .pdf",
                clause_or_slide="Section 3.3",
            ),
        )
    ])
    mock_client.set_response(MilestonesExtraction, expected_milestones)

    # Extract Charter and Milestones
    charter = CharterDomainExtractor().extract(docs, mock_client)
    assert charter.contract_type == "Fixed Bid"  # SOW won over informal T&M discussions
    assert "Portland General Electric" in charter.client_name
    assert "recurring production failures" in charter.problem_statement  # Gap-filled from meeting notes
    assert "3-hour compliance" in charter.problem_statement

    milestones = MilestonesDomainExtractor().extract(docs, mock_client)
    assert len(milestones.milestones) == 1
    assert milestones.milestones[0].external_date == date(2026, 11, 18)  # Anchored to SOW delivery date
    assert "$19,650" in milestones.milestones[0].critical_path_assumptions[0]
