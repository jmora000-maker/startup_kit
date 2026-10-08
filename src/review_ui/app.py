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

from src.review_storage import get_review_storage  # noqa: E402
from src.review_ui import facts as review  # noqa: E402
from src.review_ui import generate as generate_page  # noqa: E402
from src.review_ui import state_persistence  # noqa: E402
from src.review_ui.constants import CONTRACT_TYPES, GOVERNANCE_TIERS, resolve_select_index  # noqa: E402

DEMO_FIXTURE_LABEL = review.DEMO_FIXTURE_OPTION


def _render_field(field: review.FactField, store_name: str, key_prefix: str) -> None:
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

    widget_key = f"{key_prefix}::edit::{field.key}"
    # Each field's current value is persisted (see state_persistence) the instant it changes, so an
    # edit survives switching away to the other page and back, even before "Save review" is clicked.
    current = state_persistence.persisted_value(store_name, field.key, field.value)
    on_change = lambda fk=field.key, wk=widget_key: state_persistence.sync_to_store(store_name, wk, fk)  # noqa: E731

    if field.key == "project_identity.governance_tier" and field.value in GOVERNANCE_TIERS:
        index = resolve_select_index(current, GOVERNANCE_TIERS, field.value)
        st.selectbox("Your value", GOVERNANCE_TIERS, index=index, key=widget_key, on_change=on_change)
    elif field.key == "project_identity.contract_type":
        # Item 4: contract type is now a shared, closed-set dropdown (see
        # src/review_ui/constants.py) instead of free text, identical to the Generate tab's own
        # contract-type field below. An extracted value outside the known set (e.g. blank, or a
        # SOW phrasing the extractor didn't normalize) falls back to displaying the field's own
        # original extracted value's index if recognized, else the first option.
        index = resolve_select_index(current, CONTRACT_TYPES, field.value)
        st.selectbox("Your value", CONTRACT_TYPES, index=index, key=widget_key, on_change=on_change)
    elif field.self_describing:
        st.text_area("Your value", value=current, key=widget_key, on_change=on_change)
    else:
        st.text_input("Your value", value=current, key=widget_key, on_change=on_change)


def _render_fact_review_page() -> None:
    st.title("Pre-Generation Fact Review")

    storage = get_review_storage()
    pending_runs = storage.list_pending_runs()

    # Build run selection options: pending runs first, followed by the demo fixture
    options = [r.run_id for r in pending_runs] + [DEMO_FIXTURE_LABEL]
    label_map = {r.run_id: f"{r.project_name or r.run_id} ({r.run_id})" for r in pending_runs}
    label_map[DEMO_FIXTURE_LABEL] = DEMO_FIXTURE_LABEL

    selected_run_id = st.selectbox(
        "Select run to review",
        options=options,
        format_func=lambda x: label_map.get(x, x),
        key="fact_review_run_selector",
    )

    if not selected_run_id:
        return

    is_fixture = selected_run_id == DEMO_FIXTURE_LABEL
    if is_fixture:
        baseline = review.load_run_baseline(DEMO_FIXTURE_LABEL)
        categories = review.build_fact_categories(baseline)
        st.caption(
            f"Standalone review of `{review.FIXTURE_BASELINE_PATH.relative_to(review.REPO_ROOT).as_posix()}` "
            f"(read-only). Saving writes to `{(review.SCRATCH_ROOT / review.FIXTURE_NAME).relative_to(review.REPO_ROOT).as_posix()}/`."
        )
    else:
        run = storage.get_run(selected_run_id)
        baseline = review.load_run_baseline(selected_run_id, storage=storage)
        categories = review.build_fact_categories(baseline)
        st.caption(
            f"Reviewing run `{selected_run_id}` (state: `{run.state}`). "
            "Saving updates this run in review storage."
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
    store_name = f"fact_review::{selected_run_id}"
    key_prefix = f"fact_review::{selected_run_id}"

    for cat in categories:
        with st.expander(cat.title, expanded=cat.key in ("award_date", "named_roles")):
            if cat.note:
                st.info(cat.note)
            for field in cat.fields:
                with st.container(border=True):
                    _render_field(field, store_name=store_name, key_prefix=key_prefix)
            note_field_key = f"note::{cat.key}"
            note_widget_key = f"{key_prefix}::note::{cat.key}"
            note_current = state_persistence.persisted_value(store_name, note_field_key, "")
            note_on_change = lambda nk=note_field_key, wk=note_widget_key: state_persistence.sync_to_store(  # noqa: E731
                store_name, wk, nk
            )
            st.text_input(
                "Reviewer note for this category (optional)",
                value=note_current,
                key=note_widget_key,
                on_change=note_on_change,
            )
    if is_fixture:
        saved = st.button("Save review", key="fact_review_save_button")
        approved = False
        blocking_errors = []
    else:
        blocking_errors = review.get_blocking_validation_errors(run.validation_report)
        if blocking_errors:
            st.error(
                "Approval blocked: this run has open error-severity validation finding(s) that must be resolved:\n"
                + "\n".join(f"- {err}" for err in blocking_errors)
            )
        col1, col2 = st.columns(2)
        with col1:
            saved = st.button("Save review", key="fact_review_save_button")
        with col2:
            approved = st.button(
                "Approve",
                key="fact_review_approve_button",
                disabled=bool(blocking_errors),
            )

    if saved:
        store = state_persistence.get_store(store_name)
        submitted = {f.key: store.get(f.key, f.value) for cat in categories for f in cat.fields}
        notes = {cat.key: store.get(f"note::{cat.key}", "") for cat in categories}
        try:
            if is_fixture:
                audit, baseline_path, audit_path = review.review_and_save(baseline, categories, submitted, notes)
                st.success(f"Saved {baseline_path.name} and {audit_path.name} to {audit_path.parent}")
            else:
                audit, corrected = review.save_run_review(
                    selected_run_id, baseline, categories, submitted, notes, storage=storage
                )
                st.success(f"Saved review for run {selected_run_id} to review storage.")
        except ValueError as exc:
            st.error(str(exc))
            return
        st.json(audit)

    if approved:
        if blocking_errors:
            st.error(
                f"Cannot approve run {selected_run_id}: open validation error(s):\n"
                + "\n".join(f"- {err}" for err in blocking_errors)
            )
        else:
            try:
                storage.update_status(selected_run_id, "approved", if_state="pending_review")
                st.success(f"Run {selected_run_id} approved successfully.")
            except ValueError as exc:
                st.error(str(exc))


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
