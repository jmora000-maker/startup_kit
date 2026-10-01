"""Tests for SOW stories as core delivery tasks (spec v5 A21)."""

from datetime import date
from src.generators.pmo_workbook.builder import build_workbook_model


def test_story_tasks_under_degenerate_backlog(arc_run3):
    """Test that under a degenerate backlog, deliverable packages contain one story task per story ID."""
    model = build_workbook_model(arc_run3, start_date=date(2026, 10, 5))

    # Check total tasks = 165
    tasks = [w for w in model.wbs_rows if w.level == 4]
    assert len(tasks) == 165

    # Check no task name starts with 'Work Package:'
    for t in tasks:
        assert not t.name.lower().startswith("work package:"), f"Task name starts with 'Work Package:': {t.name}"

    # Story tasks are sourced from 'Baseline - SOW Work Items' (TXT-04)
    story_tasks = [t for t in tasks if t.source in ("Baseline - SOW Stories", "Baseline - SOW Work Items")]
    assert len(story_tasks) == 35

    # Story task naming verification: '{verb} {HS-ID}'
    for st in story_tasks:
        assert st.source_id.startswith("HS-")
        assert st.owner == "Toptal Delivery Team"
        assert st.sow_stories == st.source_id
        assert st.source_id in st.name

    # Check that degenerate work package IDs are retained on Level 3 Deliverable source_id
    deliv_rows = [w for w in model.wbs_rows if w.level == 3 and w.element_type == "Deliverable"]
    assert len(deliv_rows) == 19
    for idx, d_row in enumerate(deliv_rows, 1):
        assert d_row.source_id == f"WP-{idx:02d}"
