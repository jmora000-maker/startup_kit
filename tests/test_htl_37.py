"""HTL-37: Fact Review's milestone correction field must be labeled clearly when it is
editing a workstream category, not a phase code.
"""

from datetime import date
from src.core.models import (
    Milestone,
    ProjectStartupCharter,
    StartupKitBaseline,
)
from src.review_ui import facts as review


def test_milestone_field_label_with_native_phase_code():
    """A milestone with a native phase code (P1, Phase 2, etc.) shows '{m.id} phase'."""
    baseline = StartupKitBaseline(
        project_name="Phase Label Project",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 11, 1),
        charter=ProjectStartupCharter(client_name="Acme Corp"),
        milestones=[
            Milestone(id="M1", description="P1 Foundation: architecture and kickoff", external_date=date(2026, 12, 1)),
            Milestone(id="M2", description="Phase 2 Services: build services", external_date=date(2027, 1, 15)),
        ],
        interim_checkpoints=[
            Milestone(id="CP-01", description="(P1 Foundation): Inception review", external_date=date(2026, 11, 15)),
        ],
    )
    categories = {c.key: c for c in review.build_fact_categories(baseline)}
    ms_fields = {f.key: f for f in categories["milestones"].fields}

    # Verify keys remain milestones.{id}.phase
    assert "milestones.M1.phase" in ms_fields
    assert "milestones.M2.phase" in ms_fields
    assert "milestones.CP-01.phase" in ms_fields

    # Verify labels indicate phase
    assert ms_fields["milestones.M1.phase"].label == "M1 phase"
    assert ms_fields["milestones.M2.phase"].label == "M2 phase"
    assert ms_fields["milestones.CP-01.phase"].label == "CP-01 phase"


def test_milestone_field_label_with_workstream_classification():
    """A milestone with only a workstream classification (keyword-inferred or Unclassified)
    shows '{m.id} workstream' instead of '{m.id} phase'.
    """
    baseline = StartupKitBaseline(
        project_name="Workstream Label Project",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 11, 1),
        charter=ProjectStartupCharter(client_name="Acme Corp"),
        milestones=[
            # Keyword inferred: 'Data & Integration'
            Milestone(id="M1", description="Data pipeline ingestion and schema migrations", external_date=date(2026, 12, 1)),
            # Unclassified fallback
            Milestone(id="M2", description="General deliverables accepted", external_date=date(2027, 1, 15)),
        ],
        interim_checkpoints=[
            Milestone(id="CP-01", description="Midpoint milestone status check", external_date=date(2026, 11, 15)),
        ],
    )
    categories = {c.key: c for c in review.build_fact_categories(baseline)}
    ms_fields = {f.key: f for f in categories["milestones"].fields}

    # Verify keys remain milestones.{id}.phase for form submission and correction compatibility
    assert "milestones.M1.phase" in ms_fields
    assert "milestones.M2.phase" in ms_fields
    assert "milestones.CP-01.phase" in ms_fields

    # Verify labels indicate workstream instead of phase
    assert ms_fields["milestones.M1.phase"].label == "M1 workstream"
    assert ms_fields["milestones.M2.phase"].label == "M2 workstream"
    assert ms_fields["milestones.CP-01.phase"].label == "CP-01 workstream"

    # Values reflect inferred workstream and Unclassified fallback
    assert ms_fields["milestones.M1.phase"].value == "Data & Integration"
    assert ms_fields["milestones.M2.phase"].value == "Unclassified"


def test_mixed_milestones_and_end_to_end_correction():
    """A baseline with mixed phase and workstream milestones correctly labels each field,
    and correcting an Unclassified workstream through the field clears Unclassified.
    """
    baseline = StartupKitBaseline(
        project_name="Mixed Project",
        contract_type="Fixed Bid",
        governance_tier="Elevated",
        sow_awarded_date=date(2026, 11, 1),
        charter=ProjectStartupCharter(client_name="Acme Corp"),
        milestones=[
            Milestone(id="M1", description="P1 Discovery: scoping and architecture", external_date=date(2026, 12, 1)),
            Milestone(id="M2", description="Execution milestone sign-off", external_date=date(2027, 1, 15)),
        ],
    )
    categories = {c.key: c for c in review.build_fact_categories(baseline)}
    ms_fields = {f.key: f for f in categories["milestones"].fields}

    assert ms_fields["milestones.M1.phase"].label == "M1 phase"
    assert ms_fields["milestones.M2.phase"].label == "M2 workstream"
    assert ms_fields["milestones.M2.phase"].value == "Unclassified"

    # Correct M2 workstream to "Data & Integration"
    submitted = review.extracted_values(list(categories.values()))
    submitted["milestones.M2.phase"] = "Data & Integration"
    facts, corrections = review.compute_review(list(categories.values()), submitted)

    assert facts["milestones"] == review.HUMAN_CORRECTED
    assert [c["field"] for c in corrections] == ["milestones.M2.phase"]
    assert corrections[0]["extracted"] == "Unclassified"
    assert corrections[0]["corrected_to"] == "Data & Integration"

    corrected_baseline = review.apply_corrections(baseline, corrections)
    corrected_categories = {c.key: c for c in review.build_fact_categories(corrected_baseline)}
    corrected_fields = {f.key: f for f in corrected_categories["milestones"].fields}

    assert corrected_fields["milestones.M2.phase"].value == "Data & Integration"
