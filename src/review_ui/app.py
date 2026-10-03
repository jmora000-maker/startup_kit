"""Standalone fact-review screen (HTL-06, HTL-07; section 17 step 1).

Run with: streamlit run src/review_ui/app.py

Reads one recorded fixture baseline directly (read-only) and writes corrected_baseline.json and
review_audit.json to review_ui_scratch/. All logic lives in src/review_ui/facts.py; this file only renders.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st  # noqa: E402

from src.review_ui import facts as review  # noqa: E402

GOVERNANCE_TIERS = ["Guided", "Partnered", "Elevated"]


@st.cache_resource
def _load():
    raw = review.load_baseline(review.FIXTURE_BASELINE_PATH)
    baseline = review.prepare_review_baseline(raw)
    return baseline, review.build_fact_categories(baseline)


def _render_field(field: review.FactField) -> str:
    st.markdown(f"**{field.label}**")
    if field.context:
        st.caption(field.context)
    st.text(f"Extracted value:  {field.value or '(empty)'}")
    if field.basis_label:
        st.text(f"Basis (tool-generated label, not a quote):  {field.basis_label}")
    if field.self_describing:
        st.caption(field.source_text)
    else:
        st.text(f"Source quote:  {field.source_text}")
    if field.source_location:
        st.caption(f"Source location (not a quote): {field.source_location}")

    if field.key == "project_identity.governance_tier" and field.value in GOVERNANCE_TIERS:
        return st.selectbox("Your value", GOVERNANCE_TIERS, index=GOVERNANCE_TIERS.index(field.value),
                            key=f"edit::{field.key}")
    if field.self_describing:
        return st.text_area("Your value", value=field.value, key=f"edit::{field.key}")
    return st.text_input("Your value", value=field.value, key=f"edit::{field.key}")


def main() -> None:
    st.set_page_config(page_title="Pre-Generation Fact Review", layout="wide")
    baseline, categories = _load()

    st.title("Pre-Generation Fact Review")
    st.caption(
        f"Standalone review of `{review.FIXTURE_BASELINE_PATH.relative_to(review.REPO_ROOT).as_posix()}` "
        f"(read-only). Saving writes to `{(review.SCRATCH_ROOT / review.FIXTURE_NAME).relative_to(review.REPO_ROOT).as_posix()}/`."
    )
    st.subheader(baseline.project_name)

    submitted: dict = {}
    notes: dict = {}
    with st.form("fact_review"):
        for cat in categories:
            with st.expander(cat.title, expanded=cat.key in ("award_date", "named_roles")):
                if cat.note:
                    st.info(cat.note)
                for field in cat.fields:
                    with st.container(border=True):
                        submitted[field.key] = _render_field(field)
                notes[cat.key] = st.text_input("Reviewer note for this category (optional)", key=f"note::{cat.key}")
        saved = st.form_submit_button("Save review")

    if saved:
        try:
            audit, baseline_path, audit_path = review.review_and_save(baseline, categories, submitted, notes)
        except ValueError as exc:
            st.error(str(exc))
            return
        st.success(f"Saved {baseline_path.name} and {audit_path.name} to {audit_path.parent}")
        st.json(audit)


main()
