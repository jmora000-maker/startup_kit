"""Startup Kit Streamlit app entry point.

Run with: streamlit run src/review_ui/app.py

This is the one app entry point with two pages, selected from the sidebar:

- "Generate / Re-ingest" (HTL-17): the full second front end to the CLI -- upload, every CLI
  option, trigger a run, download results. All logic lives in src/review_ui/generate.py, which
  calls src/orchestrator.py's shared service layer (HTL-16); this file only renders.
- "Fact Review (fixture)" (HTL-06, HTL-07; section 17 step 1): the standalone fact-review screen,
  unchanged, reading one recorded fixture baseline directly (read-only) and writing
  corrected_baseline.json and review_audit.json to review_ui_scratch/. All logic lives in
  src/review_ui/facts.py; this file only renders. This page does not yet route through the
  review_queue/state-machine plumbing (HTL-01 through HTL-05, HTL-13), which is later work.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st  # noqa: E402

from src.review_ui import facts as review  # noqa: E402
from src.review_ui import generate as generate_page  # noqa: E402
from src.review_ui import state_persistence  # noqa: E402

GOVERNANCE_TIERS = ["Guided", "Partnered", "Elevated"]
FACT_REVIEW_STORE = "fact_review_values"


@st.cache_resource
def _load():
    raw = review.load_baseline(review.FIXTURE_BASELINE_PATH)
    baseline = review.prepare_review_baseline(raw)
    return baseline, review.build_fact_categories(baseline)


def _render_field(field: review.FactField) -> None:
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

    widget_key = f"edit::{field.key}"
    # Each field's current value is persisted (see state_persistence) the instant it changes, so an
    # edit survives switching away to the other page and back, even before "Save review" is clicked.
    current = state_persistence.persisted_value(FACT_REVIEW_STORE, field.key, field.value)
    on_change = lambda fk=field.key: state_persistence.sync_to_store(FACT_REVIEW_STORE, f"edit::{fk}", fk)  # noqa: E731

    if field.key == "project_identity.governance_tier" and field.value in GOVERNANCE_TIERS:
        index = GOVERNANCE_TIERS.index(current) if current in GOVERNANCE_TIERS else GOVERNANCE_TIERS.index(field.value)
        st.selectbox("Your value", GOVERNANCE_TIERS, index=index, key=widget_key, on_change=on_change)
    elif field.self_describing:
        st.text_area("Your value", value=current, key=widget_key, on_change=on_change)
    else:
        st.text_input("Your value", value=current, key=widget_key, on_change=on_change)


def _render_fact_review_page() -> None:
    baseline, categories = _load()

    st.title("Pre-Generation Fact Review")
    st.caption(
        f"Standalone review of `{review.FIXTURE_BASELINE_PATH.relative_to(review.REPO_ROOT).as_posix()}` "
        f"(read-only). Saving writes to `{(review.SCRATCH_ROOT / review.FIXTURE_NAME).relative_to(review.REPO_ROOT).as_posix()}/`."
    )
    st.subheader(baseline.project_name)

    # NOTE (regression fix, see INVESTIGATE 1): this screen used to render every field inside a
    # single st.form, whose widgets only commit their edited value to st.session_state when the
    # form's own submit button is pressed. Since the HTL-17 two-page router conditionally mounts
    # only one page's widgets at a time, navigating to the other page and back unmounts this form
    # entirely -- and Streamlit clears a widget's own st.session_state entry the moment it isn't
    # rendered, so the not-yet-submitted edit is lost even for a plain (non-form) widget. Each
    # field's value is now mirrored into state_persistence's own store on every change (see
    # _render_field), and it's that persisted store -- not the widgets' own session_state keys --
    # that Save reads from, so an edit survives switching pages before "Save review" is clicked.
    for cat in categories:
        with st.expander(cat.title, expanded=cat.key in ("award_date", "named_roles")):
            if cat.note:
                st.info(cat.note)
            for field in cat.fields:
                with st.container(border=True):
                    _render_field(field)
            note_widget_key = f"note::{cat.key}"
            note_current = state_persistence.persisted_value(FACT_REVIEW_STORE, note_widget_key, "")
            note_on_change = lambda nk=note_widget_key: state_persistence.sync_to_store(  # noqa: E731
                FACT_REVIEW_STORE, nk, nk)
            st.text_input("Reviewer note for this category (optional)", value=note_current,
                         key=note_widget_key, on_change=note_on_change)
    saved = st.button("Save review")

    if saved:
        store = state_persistence.get_store(FACT_REVIEW_STORE)
        submitted = {f.key: store.get(f.key, f.value) for cat in categories for f in cat.fields}
        notes = {cat.key: store.get(f"note::{cat.key}", "") for cat in categories}
        try:
            audit, baseline_path, audit_path = review.review_and_save(baseline, categories, submitted, notes)
        except ValueError as exc:
            st.error(str(exc))
            return
        st.success(f"Saved {baseline_path.name} and {audit_path.name} to {audit_path.parent}")
        st.json(audit)


def main() -> None:
    st.set_page_config(page_title="PMO Startup Kit", layout="wide")
    page = st.sidebar.radio(
        "Page",
        ["Generate / Re-ingest", "Fact Review (fixture)"],
        key="app_page_selector",
    )
    if page == "Generate / Re-ingest":
        generate_page.render()
    else:
        _render_fact_review_page()


main()
