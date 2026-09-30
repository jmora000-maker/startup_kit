"""Tests for sequential-gate predecessors (spec v4 A15)."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model


def test_sequential_predecessors_m2(arc_run2):
    """Test M2 takes M1 as predecessor via ASM-01 and retains HS-4781 as client prerequisite."""
    model = build_workbook_model(arc_run2, start_date=date(2026, 10, 5))
    
    sched_map = {s.milestone_id: s for s in model.schedule_rows if s.row_type == "Milestone"}
    assert "M2" in sched_map
    m2 = sched_map["M2"]
    assert m2.predecessor == "M1"
    assert "Predecessor from sequential-gate assumption (ASM-01)" in m2.notes
    assert "HS-4781" in m2.client_prerequisites


def test_sequential_predecessors_chain(arc_run2):
    """Test entire milestone predecessor chain M2<-M1, M3<-M2, M4<-M3."""
    model = build_workbook_model(arc_run2, start_date=date(2026, 10, 5))
    
    sched_map = {s.milestone_id: s for s in model.schedule_rows if s.row_type == "Milestone"}
    assert sched_map["M1"].predecessor == ""
    assert sched_map["M2"].predecessor == "M1"
    assert sched_map["M3"].predecessor == "M2"
    assert sched_map["M4"].predecessor == "M3"
