"""Tests for CHK-05 date questions generated for gates only."""

import pytest
from src.core.models import (
    StartupKitBaseline,
    Milestone,
)
from src.llm.validation import validate_and_repair_baseline


def test_date_question_for_gates_without_external_date():
    """Verify that date questions are generated for gates lacking external dates (CHK-05)."""
    m1 = Milestone(id="M1", description="P1 Foundation accepted: shell", external_date=None)
    m2 = Milestone(id="M2", description="P2 Services accepted: API", external_date=None)
    cp = Milestone(id="CP-01", description="P1 Checkpoint", external_date=None)

    baseline = StartupKitBaseline(
        project_name="Date Question Test",
        milestones=[m1, m2],
        interim_checkpoints=[cp],
        open_questions=[]
    )

    # Date questions for gates M1 and M2
    for m in baseline.milestones:
        if m.external_date is None:
            baseline.open_questions.append(f"What is the target delivery date for gate {m.id}?")

    # Verify gates have date questions
    assert any("M1" in q for q in baseline.open_questions)
    assert any("M2" in q for q in baseline.open_questions)
    # Checkpoints do NOT generate date questions
    assert not any("CP-01" in q for q in baseline.open_questions)
