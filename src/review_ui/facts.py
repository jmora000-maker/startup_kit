"""Pure, Streamlit-free logic for the fact-review screen (HTL-06, HTL-07).

Builds the HTL-06 fact categories from a baseline, computes each category's provenance tag from the
reviewer's edits, applies corrections to a copy of the baseline, and serializes review_audit.json
in the Appendix Q.2 shape. app.py only calls these functions and renders their results.

Source-text discipline (DECK-05, applied here): the baseline model stores no literal SOW sentence for
any HTL-06 fact (SourceReference holds only a document name, a clause/slide location and a confidence
score), so every fact reports NO_QUOTE_LABEL. Clause locations and tool-generated basis labels are
returned separately and must never be presented as quotes.
"""

import copy
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.core.models import SourceReference, StartupKitBaseline
from src.generators.formatting import sanitize_filename
from src.generators.pmo_workbook.builder import build_workbook_model
from src.llm.validation import validate_and_repair_baseline

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_NAME = "arc_application_implementation"
FIXTURE_BASELINE_PATH = REPO_ROOT / "tests" / "fixtures" / "sow" / FIXTURE_NAME / "baseline.json"
SCRATCH_ROOT = REPO_ROOT / "review_ui_scratch"
PROTECTED_DIRS = (REPO_ROOT / "tests" / "fixtures", REPO_ROOT / "tests" / "oracles")

MACHINE_EXTRACTED_UNCONFIRMED = "machine_extracted_unconfirmed"
HUMAN_CORRECTED = "human_corrected"
PROVENANCE_TAGS = (MACHINE_EXTRACTED_UNCONFIRMED, HUMAN_CORRECTED)

NO_QUOTE_LABEL = "No source quote captured for this fact"
SELF_DESCRIBING_LABEL = "Self-describing validation finding (the message above is the finding itself, shown in full)"
CONTRACT_WIDE_WINDOW_SUFFIX = "business days from notice of milestone completion"

# Appendix Q.2: the facts map's seven keys are exactly HTL-06's seven categories, in this order
CATEGORY_KEYS = (
    "project_identity",
    "award_date",
    "named_roles",
    "milestones",
    "deliverable_phase_assignment",
    "contract_wide_review_window",
    "validation_findings",
)


@dataclass(frozen=True)
class FactField:
    """One reviewable value with its source text (or the explicit not-captured label)."""
    key: str
    label: str
    value: str
    source_quote: Optional[str] = None
    source_location: Optional[str] = None
    basis_label: Optional[str] = None
    context: Optional[str] = None
    self_describing: bool = False

    @property
    def source_text(self) -> str:
        if self.source_quote:
            return self.source_quote
        if self.self_describing:
            return SELF_DESCRIBING_LABEL
        return NO_QUOTE_LABEL


@dataclass(frozen=True)
class FactCategory:
    """One HTL-06 fact category and its reviewable fields."""
    key: str
    title: str
    fields: Tuple[FactField, ...]
    note: Optional[str] = None


def load_baseline(path: Path = FIXTURE_BASELINE_PATH) -> StartupKitBaseline:
    """Read a baseline.json (read-only)."""
    with open(path, encoding="utf-8") as fh:
        return StartupKitBaseline.model_validate(json.load(fh))


def prepare_review_baseline(baseline: StartupKitBaseline) -> StartupKitBaseline:
    """Return a validated copy: the screen reviews the baseline as it stands after VAL-01 to VAL-11 (HTL-02's split point).

    A recorded fixture baseline is stored before validation (validation_report is None), so the existing
    validation layer is run on an in-memory copy. The input baseline is never mutated.
    """
    reviewed = copy.deepcopy(baseline)
    if reviewed.validation_report is None:
        validate_and_repair_baseline(reviewed)
    return reviewed


def _date_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10]
    return str(value)


def _location(ref: Optional[SourceReference]) -> Optional[str]:
    if ref is None:
        return None
    if ref.clause_or_slide:
        return f"{ref.document_name}, {ref.clause_or_slide}"
    return ref.document_name


def _find_stakeholder(baseline: StartupKitBaseline, role_fragment: str, exclude_org: Optional[str] = None):
    for s in baseline.stakeholders:
        if role_fragment.lower() in (s.role or "").lower():
            if exclude_org and exclude_org.lower() in (s.organization or "").lower():
                continue
            return s
    return None


def contract_wide_review_window(baseline: StartupKitBaseline) -> Optional[str]:
    """KIT-03's computed window: the single normalized window every deliverable carries after validation, if any."""
    windows = {(d.review_window or "").strip() for d in baseline.deliverables}
    if len(windows) == 1:
        (only,) = windows
        if only.endswith(CONTRACT_WIDE_WINDOW_SUFFIX):
            return only
    return None


def _start_date_for_model(baseline: StartupKitBaseline) -> date:
    awarded = baseline.sow_awarded_date
    if isinstance(awarded, date):
        return awarded
    if awarded:
        try:
            return date.fromisoformat(str(awarded)[:10])
        except ValueError:
            pass
    return date.today()


def build_fact_categories(baseline: StartupKitBaseline) -> List[FactCategory]:
    """Build HTL-06's seven categories from an already-validated baseline (see prepare_review_baseline)."""
    workbook = build_workbook_model(copy.deepcopy(baseline), start_date=_start_date_for_model(baseline))
    schedule_by_ms = {
        r.milestone_id: r for r in workbook.schedule_rows if r.row_type in ("Milestone", "Checkpoint")
    }
    wbs_by_deliv = {r.deliverable_id: r for r in workbook.wbs_rows if r.element_type == "Deliverable"}

    charter = baseline.charter
    charter_loc = _location(charter.source_reference) if charter else None

    # 1. Project identity
    sponsor = _find_stakeholder(baseline, "sponsor", exclude_org="toptal")
    identity = (
        FactField("project_identity.project_name", "Project name", baseline.project_name or "",
                  source_location=charter_loc),
        FactField("project_identity.client_name", "Client", (charter.client_name if charter else None) or "",
                  source_location=charter_loc),
        FactField("project_identity.client_sponsor", "Client sponsor", sponsor.name if sponsor else "",
                  context=(f"Stakeholder role: {sponsor.role}" if sponsor else "No stakeholder with a Sponsor role")),
        FactField("project_identity.contract_type", "Contract type", baseline.contract_type or "",
                  source_location=charter_loc),
        FactField("project_identity.governance_tier", "Governance tier", baseline.governance_tier or "",
                  source_location=charter_loc),
    )

    # 2. Award / start date
    award = (
        FactField("award_date", "Award / start date", _date_str(baseline.sow_awarded_date),
                  context=f"Provenance (VAL-11): {baseline.award_date_source or 'not stated in SOW'}"),
    )

    # 3. Named roles
    dm_value = (charter.delivery_manager if charter else None) or ""
    if not dm_value:
        dm_sh = _find_stakeholder(baseline, "delivery manager")
        dm_value = dm_sh.name if dm_sh else ""
    contact = _find_stakeholder(baseline, "client contact") or _find_stakeholder(baseline, "approver", exclude_org="toptal")
    roles = (
        FactField("named_roles.delivery_manager", "Delivery Manager", dm_value),
        FactField("named_roles.client_contact", "Client Contact / Approver", contact.name if contact else "",
                  context=(f"Stakeholder role: {contact.role}" if contact else None)),
    )

    # 4. Milestones (gates and VAL-01 checkpoints)
    ms_fields: List[FactField] = []
    for kind, items in (("Gate", baseline.milestones), ("Checkpoint", baseline.interim_checkpoints)):
        for m in items:
            row = schedule_by_ms.get(m.id)
            loc = _location(m.source_reference)
            ctx = f"{kind} (VAL-01): {m.description}"
            basis = row.date_basis if row else None
            ms_fields.append(FactField(f"milestones.{m.id}.phase", f"{m.id} phase",
                                       (row.workstream if row else None) or (m.phase or ""),
                                       source_location=loc, context=ctx))
            ms_fields.append(FactField(f"milestones.{m.id}.external_date", f"{m.id} external date",
                                       _date_str(m.external_date), source_location=loc,
                                       basis_label=basis, context=ctx))

    # 5. Deliverable phase assignment
    del_fields: List[FactField] = []
    for d in baseline.deliverables:
        row = wbs_by_deliv.get(d.id)
        del_fields.append(FactField(
            f"deliverable_phase_assignment.{d.id}", f"{d.id} {d.name}", (row.workstream if row else "") or "",
            source_location=_location(d.source_reference),
            basis_label=(row.mapping_basis if row else None),
            context=(f"Gate: {row.milestone_id}" if row and row.milestone_id else None),
        ))

    # 6. Contract-wide review window (KIT-03)
    cw = contract_wide_review_window(baseline)
    sow_interp = baseline.sow_interpretation
    window = (
        FactField("contract_wide_review_window", "Contract-wide review window", cw or "",
                  source_location=_location(sow_interp.source_reference) if sow_interp else None,
                  context=None if cw else "No contract-wide review window detected"),
    )

    # 7. Validation findings, every entry in full
    report = baseline.validation_report
    findings = tuple(
        FactField(f"validation_findings.{i}", f"{f.severity} - {f.invariant_id}", f.message, self_describing=True)
        for i, f in enumerate(report.findings if report else [], start=1)
    )

    return [
        FactCategory("project_identity", "Project identity", identity,
                     note="The baseline model has no client-sponsor field; the value shown is the client stakeholder whose role names a Sponsor."),
        FactCategory("award_date", "Award / start date", award),
        FactCategory("named_roles", "Named roles", roles),
        FactCategory("milestones", "Milestones", tuple(ms_fields),
                     note="Date Basis is a label generated by the workbook builder (DT-03), not a source quote."),
        FactCategory("deliverable_phase_assignment", "Deliverable phase assignment", tuple(del_fields),
                     note="Mapping Basis is a label generated by the workbook builder (MAP-03), not a source quote."),
        FactCategory("contract_wide_review_window", "Contract-wide review window", window),
        FactCategory("validation_findings", "Validation findings", findings,
                     note=None if findings else "No validation findings."),
    ]


def extracted_values(categories: List[FactCategory]) -> Dict[str, str]:
    """Flatten every field to {field key: extracted value}."""
    return {f.key: f.value for c in categories for f in c.fields}


def compute_review(
    categories: List[FactCategory],
    submitted: Dict[str, str],
    notes: Optional[Dict[str, str]] = None,
) -> Tuple[Dict[str, str], List[Dict[str, str]]]:
    """HTL-07: tag each category and list a correction for every edited field.

    A category is human_corrected when any of its fields differs (ignoring surrounding whitespace) from
    the extracted value; otherwise machine_extracted_unconfirmed. Fields absent from `submitted` are unchanged.
    """
    notes = notes or {}
    facts: Dict[str, str] = {}
    corrections: List[Dict[str, str]] = []
    for cat in categories:
        edited = False
        for f in cat.fields:
            new_value = (submitted.get(f.key, f.value) or "").strip()
            if new_value != (f.value or "").strip():
                edited = True
                corrections.append({
                    "field": f.key,
                    "extracted": f.value,
                    "corrected_to": new_value,
                    "reviewer_note": (notes.get(cat.key) or "").strip(),
                })
        facts[cat.key] = HUMAN_CORRECTED if edited else MACHINE_EXTRACTED_UNCONFIRMED
    return {k: facts[k] for k in CATEGORY_KEYS}, corrections


def _parse_iso_date(value: str, field: str) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field}: '{value}' is not a YYYY-MM-DD date") from exc


def _phase_code(value: str) -> str:
    return value.split()[0] if value.split() else value


def apply_corrections(baseline: StartupKitBaseline, corrections: List[Dict[str, str]]) -> StartupKitBaseline:
    """Return a copy of `baseline` with every correction applied. Raises ValueError for an unparseable date."""
    out = copy.deepcopy(baseline)
    charter, gc = out.charter, out.governance_context
    for c in corrections:
        key, new = c["field"], c["corrected_to"]
        parts = key.split(".")
        if key == "project_identity.project_name":
            out.project_name = new
            for obj in (charter, gc):
                if obj is not None:
                    obj.project_name = new
        elif key == "project_identity.client_name":
            for obj in (charter, gc):
                if obj is not None:
                    obj.client_name = new
        elif key == "project_identity.client_sponsor":
            s = _find_stakeholder(out, "sponsor", exclude_org="toptal")
            if s is not None:
                s.name = new
        elif key in ("project_identity.contract_type", "project_identity.governance_tier"):
            attr = parts[1]
            setattr(out, attr, new)
            for obj in (charter, gc):
                if obj is not None:
                    setattr(obj, attr, new)
        elif key == "award_date":
            out.sow_awarded_date = _parse_iso_date(new, key)
        elif key == "named_roles.delivery_manager":
            old = c["extracted"]
            for obj in (charter, gc, out.talent_onboarding):
                if obj is not None:
                    obj.delivery_manager = new
            for s in out.stakeholders:
                if s.name == old and "delivery manager" in (s.role or "").lower():
                    s.name = new
        elif key == "named_roles.client_contact":
            for s in out.stakeholders:
                if s.name == c["extracted"]:
                    s.name = new
        elif parts[0] == "milestones" and len(parts) == 3:
            ms = next((m for m in out.milestones + out.interim_checkpoints if m.id == parts[1]), None)
            if ms is not None:
                if parts[2] == "phase":
                    ms.phase = _phase_code(new)
                elif parts[2] == "external_date":
                    ms.external_date = _parse_iso_date(new, key)
        elif parts[0] == "deliverable_phase_assignment" and len(parts) == 2:
            for item in out.sow_stories_catalogue:
                if item.deliverable_id == parts[1]:
                    item.phase = _phase_code(new)
        elif key == "contract_wide_review_window":
            for d in out.deliverables:
                if not c["extracted"] or (d.review_window or "").strip() == c["extracted"]:
                    d.review_window = new
        elif parts[0] == "validation_findings" and len(parts) == 2 and out.validation_report:
            idx = int(parts[1]) - 1
            if 0 <= idx < len(out.validation_report.findings):
                out.validation_report.findings[idx].message = new
    return out


def make_run_id(project_name: str, when: datetime) -> str:
    """HTL-03's run id shape: {sanitize_filename(project_name)}_{YYYYMMDD_HHMMSS}."""
    return f"{sanitize_filename(project_name)}_{when.strftime('%Y%m%d_%H%M%S')}"


def build_review_audit(
    run_id: str,
    facts: Dict[str, str],
    corrections: List[Dict[str, str]],
    reviewed_at: datetime,
) -> Dict[str, Any]:
    """Serialize review_audit.json in Appendix Q.2's shape."""
    missing = [k for k in CATEGORY_KEYS if k not in facts]
    bad = {k: v for k, v in facts.items() if v not in PROVENANCE_TAGS}
    if missing or bad or set(facts) - set(CATEGORY_KEYS):
        raise ValueError(f"Invalid facts map (INV-37): missing={missing}, invalid={bad}")
    return {
        "run_id": run_id,
        "reviewed_by": "",
        "reviewed_at": reviewed_at.strftime("%Y-%m-%dT%H:%M:%S"),
        "facts": {k: facts[k] for k in CATEGORY_KEYS},
        "corrections": list(corrections),
    }


def _is_protected(path: Path) -> bool:
    resolved = path.resolve()
    return any(resolved == p.resolve() or p.resolve() in resolved.parents for p in PROTECTED_DIRS)


def save_review(
    corrected: StartupKitBaseline,
    audit: Dict[str, Any],
    out_dir: Path = SCRATCH_ROOT / FIXTURE_NAME,
) -> Tuple[Path, Path]:
    """Write corrected_baseline.json and review_audit.json to the scratch location (never under tests/fixtures or tests/oracles)."""
    out_dir = Path(out_dir)
    if _is_protected(out_dir):
        raise ValueError(f"Refusing to write review output under a protected test directory: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    baseline_path = out_dir / "corrected_baseline.json"
    audit_path = out_dir / "review_audit.json"
    baseline_path.write_text(json.dumps(corrected.model_dump(mode="json"), indent=2, ensure_ascii=False), encoding="utf-8")
    audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    return baseline_path, audit_path


def review_and_save(
    baseline: StartupKitBaseline,
    categories: List[FactCategory],
    submitted: Dict[str, str],
    notes: Optional[Dict[str, str]] = None,
    out_dir: Path = SCRATCH_ROOT / FIXTURE_NAME,
    when: Optional[datetime] = None,
) -> Tuple[Dict[str, Any], Path, Path]:
    """The screen's save action: compute provenance, apply corrections, write both files."""
    when = when or datetime.now()
    facts, corrections = compute_review(categories, submitted, notes)
    corrected = apply_corrections(baseline, corrections)
    audit = build_review_audit(make_run_id(baseline.project_name, when), facts, corrections, when)
    baseline_path, audit_path = save_review(corrected, audit, out_dir)
    return audit, baseline_path, audit_path
