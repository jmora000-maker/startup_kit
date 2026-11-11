"""Unit and regression tests for HTL-104: Project Start Date Shifting Across All Artifacts and Fact Review."""

from datetime import date, timedelta
from pathlib import Path
import json
import openpyxl
import pptx
import pytest

from src.core.dates import shift_baseline_dates
from src.core.models import OutputSelection, StartupKitBaseline, Milestone, Deliverable, RiskAssumption
from src.generators.client_deck import export_client_deck
from src.generators.docx_generator import DocxGenerator
from src.generators.governance_deck import export_governance_deck
from src.generators.pmo_workbook import export_pmo_workbook
from src.orchestrator import StartupKitController
from src.review_storage import get_review_storage
from src.review_ui import facts as review
from tests.deck_bundle import load_baseline
from tests.test_htl_62 import _build_pge_baseline


def _build_test_pge_baseline():
    baseline = _build_pge_baseline()
    baseline.sow_awarded_date = date(2026, 10, 12)
    baseline.award_date_source = "stated"
    return baseline


def test_htl_104_shift_baseline_dates_model_transformation():
    """Verify shift_baseline_dates accurately shifts all entities and preserves original_sow_start_date."""
    pge = _build_test_pge_baseline()
    assert pge.sow_awarded_date == date(2026, 10, 12)
    assert pge.milestones[0].external_date == date(2026, 11, 18)
    assert pge.deliverables[0].submission_target_date == date(2026, 11, 18)

    # Shift forward by 14 days (2026-10-12 -> 2026-10-26)
    shifted = shift_baseline_dates(pge, date(2026, 10, 26))

    assert shifted.original_sow_start_date == date(2026, 10, 12)
    assert shifted.sow_awarded_date == date(2026, 10, 26)
    assert shifted.milestones[0].external_date == date(2026, 12, 2)
    assert shifted.deliverables[0].submission_target_date == date(2026, 12, 2)

    # Shift again by an additional 7 days (2026-10-26 -> 2026-11-02)
    shifted_again = shift_baseline_dates(shifted, date(2026, 11, 2))
    assert shifted_again.original_sow_start_date == date(2026, 10, 12)
    assert shifted_again.sow_awarded_date == date(2026, 11, 2)
    assert shifted_again.milestones[0].external_date == date(2026, 12, 9)
    assert shifted_again.deliverables[0].submission_target_date == date(2026, 12, 9)


def test_htl_104_pge_milestone_date_sow_shift_across_all_four_artifacts(tmp_path):
    """HTL-104: Milestone-date SOW (PGE) shifted by +14 days is verified across Workbook, Gov Deck, Client Deck, and Docx."""
    baseline = _build_test_pge_baseline()
    baseline.sow_interpretation.acceptance_process_narrative = None  # Use Tier 2 deterministic render-time date generation
    target_start = date(2026, 10, 26)
    shifted_baseline = shift_baseline_dates(baseline, target_start)

    # 1. PMO Delivery Workbook (.xlsx)
    wb_res = export_pmo_workbook(shifted_baseline, tmp_path, start_date=target_start)
    wb = openpyxl.load_workbook(str(wb_res.file_path), data_only=True)
    sched_sheet = wb["Project Schedule"]
    header_start_val = sched_sheet["A3"].value
    assert "2026-10-26" in str(header_start_val)

    # Find Milestone 1 row in schedule
    m1_found = False
    for row in sched_sheet.iter_rows(min_row=5, values_only=True):
        row_str = " ".join(str(c or "") for c in row)
        if "M1" in row_str or "Milestone 1" in row_str or "MS-01" in row_str:
            assert "2026-12-02" in row_str, f"Expected 2026-12-02 in M1 schedule row, got {row_str}"
            m1_found = True
            break
    assert m1_found, "Milestone 1 row not found in Project Schedule"

    # 2. PS Governance Kickoff Deck (.pptx)
    g_res = export_governance_deck(shifted_baseline, tmp_path)
    g_prs = pptx.Presentation(str(g_res.file_path))

    # Slide 17 (Submission step completion date, 17th slide / index 16, HTL-109)
    s17 = g_prs.slides[16]
    s17_text = " ".join(shp.text_frame.text for shp in s17.shapes if shp.has_text_frame)
    assert "2026-12-02" in s17_text, f"Shifted M1 date 2026-12-02 not found in Gov Deck Slide 17: {s17_text}"

    # 3. Client Kickoff Deck (.pptx)
    c_res = export_client_deck(shifted_baseline, tmp_path)
    assert c_res.file_path.exists()
    c_prs = pptx.Presentation(str(c_res.file_path))
    assert len(c_prs.slides) >= 5

    # 4. Startup Kit Document (.docx)
    writer = DocxGenerator()
    docx_path = tmp_path / "Startup_Kit_PGE_Shifted.docx"
    kit_path = writer.write_kit_docx(shifted_baseline, docx_path)
    assert kit_path.exists()

    import docx
    doc = docx.Document(str(kit_path))
    full_doc_text = " ".join(p.text for p in doc.paragraphs)
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                full_doc_text += " " + cell.text
    assert "2026-12-02" in full_doc_text, "Shifted M1 date 2026-12-02 missing from .docx"


def test_htl_104_arc_week_based_sow_shift_across_all_four_artifacts(tmp_path):
    """HTL-104: Week-based SOW (ARC) shifted by +14 days anchors schedule calculations from the new baseline date."""
    baseline = load_baseline("arc_application_implementation")
    assert baseline.sow_awarded_date == date(2026, 10, 12), f"Expected real SOW start date 2026-10-12, got {baseline.sow_awarded_date}"

    # Shift forward by 14 days (2026-10-12 -> 2026-10-26)
    target_start = date(2026, 10, 26)
    shifted_baseline = shift_baseline_dates(baseline, target_start)

    assert shifted_baseline.original_sow_start_date == date(2026, 10, 12)
    assert shifted_baseline.sow_awarded_date == target_start

    # 1. PMO Delivery Workbook (.xlsx)
    wb_res = export_pmo_workbook(shifted_baseline, tmp_path, start_date=target_start)
    wb = openpyxl.load_workbook(str(wb_res.file_path), data_only=True)
    sched_sheet = wb["Project Schedule"]
    header_start_val = sched_sheet["A3"].value
    assert "2026-10-26" in str(header_start_val)

    # Verify dynamically calculated planned_start for M1 (Phase 1, Weeks 1-5) starts on 2026-10-26
    m1_found = False
    for row in sched_sheet.iter_rows(min_row=5, values_only=True):
        if len(row) > 7 and row[1] == "Milestone" and row[3] == "M1":
            assert str(row[7]).startswith("2026-10-26"), f"Expected 2026-10-26 in M1 planned_start, got {row[7]}"
            m1_found = True
            break
    assert m1_found, "Milestone 1 row not found in Project Schedule"

    # 2. PS Governance Kickoff Deck (.pptx)
    g_res = export_governance_deck(shifted_baseline, tmp_path)
    assert g_res.file_path.exists()

    # 3. Client Kickoff Deck (.pptx)
    c_res = export_client_deck(shifted_baseline, tmp_path)
    assert c_res.file_path.exists()

    # 4. Startup Kit Document (.docx)
    writer = DocxGenerator()
    docx_path = tmp_path / "Startup_Kit_ARC_Shifted.docx"
    kit_path = writer.write_kit_docx(shifted_baseline, docx_path)
    assert kit_path.exists()


def test_htl_104_combinatorial_generate_and_fact_review_cases(tmp_path, monkeypatch):
    """HTL-104: Test all four Generate and Fact-Review combinatorial cases."""
    monkeypatch.setenv("STARTUP_KIT_REVIEW_STORAGE_BACKEND", "local")
    monkeypatch.setenv("STARTUP_KIT_LOCAL_STORAGE_DIR", str(tmp_path / "review_storage"))
    storage = get_review_storage()

    # Case 1: Neither entered -> zero shift against SOW date
    pge1 = _build_test_pge_baseline()
    run_id_1 = storage.create_run("PGE Case 1", pge1.model_dump(mode="json"), {})
    loaded_1 = review.load_run_baseline(run_id_1, storage=storage)
    assert loaded_1.sow_awarded_date == date(2026, 10, 12)
    assert loaded_1.milestones[0].external_date == date(2026, 11, 18)
    cats_1 = review.build_fact_categories(loaded_1)
    award_field_1 = next(f for cat in cats_1 if cat.key == "award_date" for f in cat.fields if f.key == "award_date")
    assert "Shift:" not in award_field_1.context

    # Case 2: Generate only -> shift applied on run creation and displayed in Fact Review
    pge2 = _build_test_pge_baseline()
    pge2_shifted = shift_baseline_dates(pge2, date(2026, 10, 26))
    run_id_2 = storage.create_run("PGE Case 2", pge2_shifted.model_dump(mode="json"), {})
    loaded_2 = review.load_run_baseline(run_id_2, storage=storage)
    assert loaded_2.sow_awarded_date == date(2026, 10, 26)
    assert loaded_2.milestones[0].external_date == date(2026, 12, 2)
    cats_2 = review.build_fact_categories(loaded_2)
    award_field_2 = next(f for cat in cats_2 if cat.key == "award_date" for f in cat.fields if f.key == "award_date")
    assert "Original SOW date: 2026-10-12" in award_field_2.context
    assert "Shift: +14 days" in award_field_2.context

    ms_field_2 = next(f for cat in cats_2 if cat.key == "milestones" for f in cat.fields if f.key.endswith(".external_date"))
    assert ms_field_2.value == "2026-12-02"
    assert "Original SOW date: 2026-11-18" in ms_field_2.context
    assert "Shifted by +14 days" in ms_field_2.context

    # Case 3: Fact Review only -> user edits start date on Fact Review
    pge3 = _build_test_pge_baseline()
    run_id_3 = storage.create_run("PGE Case 3", pge3.model_dump(mode="json"), {})
    loaded_3 = review.load_run_baseline(run_id_3, storage=storage)
    corrections_3 = [{"field": "award_date", "extracted": "2026-10-12", "corrected_to": "2026-10-26"}]
    corrected_3 = review.apply_corrections(loaded_3, corrections_3)
    assert corrected_3.original_sow_start_date == date(2026, 10, 12)
    assert corrected_3.sow_awarded_date == date(2026, 10, 26)
    assert corrected_3.milestones[0].external_date == date(2026, 12, 2)

    # Case 4: Both entered -> Fact Review edit takes final precedence recalculating delta from original_sow_start_date
    pge4 = _build_test_pge_baseline()
    pge4_shifted = shift_baseline_dates(pge4, date(2026, 10, 26))
    run_id_4 = storage.create_run("PGE Case 4", pge4_shifted.model_dump(mode="json"), {})
    loaded_4 = review.load_run_baseline(run_id_4, storage=storage)
    # User modifies start date on Fact Review to 2026-11-02 (+21 days from original 2026-10-12)
    corrections_4 = [{"field": "award_date", "extracted": "2026-10-26", "corrected_to": "2026-11-02"}]
    corrected_4 = review.apply_corrections(loaded_4, corrections_4)
    assert corrected_4.original_sow_start_date == date(2026, 10, 12)
    assert corrected_4.sow_awarded_date == date(2026, 11, 2)
    assert corrected_4.milestones[0].external_date == date(2026, 12, 9)  # 2026-11-18 + 21 days


def test_htl_104_persistence_surviving_run_reopen(tmp_path):
    """HTL-104: Saving and approving a shifted baseline persists shifted dates and original_sow_start_date to disk."""
    from src.review_storage.local import LocalReviewStorage
    storage = LocalReviewStorage(base_dir=tmp_path / "review_storage")

    pge = _build_test_pge_baseline()
    run_id = storage.create_run("PGE Persistence Test", pge.model_dump(mode="json"), {})

    # Fact review applies shift to 2026-10-26 (+14 days)
    loaded = review.load_run_baseline(run_id, storage=storage)
    categories = review.build_fact_categories(loaded)
    submitted = {f.key: f.value for cat in categories for f in cat.fields}
    submitted["award_date"] = "2026-10-26"

    audit, corrected = review.save_run_review(
        run_id=run_id,
        baseline=loaded,
        categories=categories,
        submitted=submitted,
        storage=storage,
    )

    # Verify on-disk baseline.json
    run_dir = storage._run_dir(run_id)
    saved_json = json.loads((run_dir / "baseline.json").read_text(encoding="utf-8"))
    assert saved_json["original_sow_start_date"] == "2026-10-12"
    assert saved_json["sow_awarded_date"] == "2026-10-26"
    assert saved_json["milestones"][0]["external_date"] == "2026-12-02"

    # Reopen run from storage
    storage.update_status(run_id, "approved")
    reopened = review.load_run_baseline(run_id, storage=storage)

    assert reopened.original_sow_start_date == date(2026, 10, 12)
    assert reopened.sow_awarded_date == date(2026, 10, 26)
    assert reopened.milestones[0].external_date == date(2026, 12, 2)

    # Fact categories show dual-date context after reload
    reopened_cats = review.build_fact_categories(reopened)
    award_field = next(f for cat in reopened_cats if cat.key == "award_date" for f in cat.fields if f.key == "award_date")
    assert "Original SOW date: 2026-10-12" in award_field.context
    assert "Shift: +14 days" in award_field.context
