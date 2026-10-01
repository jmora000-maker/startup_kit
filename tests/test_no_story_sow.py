"""Tests for SOWs without story IDs generating synthetic SOW work item references (v6 Section 1.1)."""

import re
import copy
from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model
from src.generators.pmo_workbook.writer import write_workbook
from src.llm.client import MockLLMClient
from src.orchestrator import StartupKitController


def test_synthetic_references_for_arc_without_stories(arc_run3, tmp_path):
    """Strip all HS-#### story IDs from ARC baseline and verify synthetic references are used."""
    baseline = copy.deepcopy(arc_run3)

    # Strip HS-#### from deliverables, backlog, raid items, and clear catalogue
    for d in baseline.deliverables:
        d.sow_reference = None
        if d.name:
            d.name = re.sub(r"\bHS-\d{3,5}\b", "", d.name).strip()
        if d.description:
            d.description = re.sub(r"\bHS-\d{3,5}\b", "", d.description).strip()

    for wp in baseline.backlog_seed:
        wp.sow_reference = None
        if wp.title:
            wp.title = re.sub(r"\bHS-\d{3,5}\b", "", wp.title).strip()
        if wp.description:
            wp.description = re.sub(r"\bHS-\d{3,5}\b", "", wp.description).strip()

    baseline.sow_stories_catalogue = []

    model = build_workbook_model(baseline, start_date=date(2026, 10, 5))

    # Verify synthetic references flag
    assert model.has_synthetic_sow_references is True

    # Verify traceability self check
    assert "SOW References" in model.traceability
    trace = model.traceability["SOW References"]
    assert trace["in_baseline"] > 0
    assert trace["in_workbook"] > 0
    assert trace["synthetic"] is True
    assert len(trace["missing_ids"]) == 0

    # Write workbook and verify Schedule row 4 note
    xlsx_path = tmp_path / "Test_Synthetic_Delivery_Workbook.xlsx"
    write_workbook(model, xlsx_path)

    import openpyxl
    wb = openpyxl.load_workbook(str(xlsx_path), data_only=True)
    ws_sched = wb["Project Schedule"]
    row4_val = str(ws_sched["A4"].value or "")
    assert "Synthetic reference - SOW has no item IDs" in row4_val


def test_mock_baseline_uses_section_sow_references(tmp_path):
    """Test that the mock baseline with Section references uses Section reference kind without error."""
    from main import create_mock_llm_client
    mock_client = create_mock_llm_client()

    controller = StartupKitController(llm_client=mock_client)
    res = controller.run(output_dir=tmp_path)

    assert res.workbook is not None and res.workbook.file_path.exists()
    trace = res.workbook.traceability["SOW References"]
    assert trace["in_baseline"] >= 1
    assert trace["in_workbook"] >= 1
    assert len(trace["missing_ids"]) == 0


def test_mock_baseline_without_references_generates_synthetic(tmp_path):
    """Test that when mock baseline has no SOW references or sections at all, synthetic references are generated."""
    from main import create_mock_llm_client
    mock_client = create_mock_llm_client()

    # Clear section references from mock responses
    for resp in mock_client.responses_by_schema.values():
        if hasattr(resp, "deliverables"):
            for d in resp.deliverables:
                d.sow_reference = None
        if hasattr(resp, "acceptance_matrix_items"):
            for a in resp.acceptance_matrix_items:
                a.sow_reference = None

    controller = StartupKitController(llm_client=mock_client)
    res = controller.run(output_dir=tmp_path)

    assert res.workbook is not None and res.workbook.file_path.exists()

    import openpyxl
    wb = openpyxl.load_workbook(str(res.workbook.file_path), data_only=True)
    ws_sched = wb["Project Schedule"]
    row4_val = str(ws_sched["A4"].value or "")
    assert "Synthetic reference - SOW has no item IDs" in row4_val
