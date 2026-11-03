"""Date manipulation and baseline shifting utilities for PMO Startup Kit (HTL-104)."""

from datetime import date, timedelta
from typing import Optional, Any
from src.core.models import StartupKitBaseline, parse_flexible_date


def shift_baseline_dates(
    baseline: StartupKitBaseline,
    target_start_date: date,
) -> StartupKitBaseline:
    """Shift all SOW-derived dates in a baseline by the delta to target_start_date (HTL-104).

    Calculates delta = target_start_date - current_start_date and shifts:
    - baseline.sow_awarded_date
    - baseline.milestones[*].external_date and internal_buffer_date
    - baseline.interim_checkpoints[*].external_date, internal_buffer_date, target_date
    - baseline.deliverables[*].submission_target_date
    - baseline.raid_items[*].due_date and baseline.risks[*].due_date
    - baseline.dependencies_assumptions[*].required_validation_date / target_date
    - baseline.readiness_checklist[*].due_date

    Preserves baseline.original_sow_start_date as the initial unshifted contractual anchor.
    """
    if target_start_date is None:
        return baseline

    parsed_target = parse_flexible_date(target_start_date)
    if parsed_target is None:
        return baseline

    # Establish immutable original_sow_start_date if not already set
    if baseline.original_sow_start_date is None:
        if baseline.sow_awarded_date is not None:
            baseline.original_sow_start_date = baseline.sow_awarded_date
        else:
            baseline.original_sow_start_date = parsed_target

    current_start = baseline.sow_awarded_date or baseline.original_sow_start_date
    if current_start is None:
        baseline.sow_awarded_date = parsed_target
        return baseline

    delta_days = (parsed_target - current_start).days
    baseline.sow_awarded_date = parsed_target

    if delta_days == 0:
        return baseline

    delta = timedelta(days=delta_days)

    # 1. Milestones
    for m in baseline.milestones:
        if m.external_date:
            m.external_date = m.external_date + delta
        if m.internal_buffer_date:
            m.internal_buffer_date = m.internal_buffer_date + delta

    # 2. Interim Checkpoints
    for m in baseline.interim_checkpoints:
        if m.external_date:
            m.external_date = m.external_date + delta
        if m.internal_buffer_date:
            m.internal_buffer_date = m.internal_buffer_date + delta
        if hasattr(m, "target_date") and getattr(m, "target_date", None):
            m.target_date = m.target_date + delta

    # 3. Deliverables
    for d in baseline.deliverables:
        if d.submission_target_date:
            d.submission_target_date = d.submission_target_date + delta

    # 4. RAID items / Risks
    for r in baseline.raid_items:
        if getattr(r, "due_date", None):
            r.due_date = r.due_date + delta

    if hasattr(baseline, "risks") and isinstance(baseline.risks, list):
        for r in baseline.risks:
            if getattr(r, "due_date", None):
                r.due_date = r.due_date + delta

    # 5. Dependencies & Assumptions
    for dep in baseline.dependencies_assumptions:
        if getattr(dep, "required_validation_date", None):
            dep.required_validation_date = dep.required_validation_date + delta
        if hasattr(dep, "target_date") and getattr(dep, "target_date", None):
            dep.target_date = dep.target_date + delta

    if hasattr(baseline, "dependencies") and isinstance(baseline.dependencies, list):
        for dep in baseline.dependencies:
            if getattr(dep, "required_validation_date", None):
                dep.required_validation_date = dep.required_validation_date + delta
            if hasattr(dep, "target_date") and getattr(dep, "target_date", None):
                dep.target_date = dep.target_date + delta

    # 6. Readiness Checklist
    for item in baseline.readiness_checklist:
        if getattr(item, "due_date", None):
            item.due_date = item.due_date + delta

    return baseline
