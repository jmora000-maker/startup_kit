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

    flash_success = st.session_state.pop("fact_review_flash_success", None)
    if flash_success:
        st.success(flash_success)

    storage = get_review_storage()
    all_runs = storage.list_runs()
    runs = [r for r in all_runs if r.state in ("pending_review", "approved", "generated")]
    runs.sort(key=lambda r: (r.state != "pending_review", r.state != "approved", -r.created_at.timestamp()))

    # Build run selection options: active runs first, followed by the demo fixture
    options = [r.run_id for r in runs] + [DEMO_FIXTURE_LABEL]
    label_map = {
        r.run_id: f"{r.project_name or r.run_id} ({r.run_id})"
        if r.state == "pending_review"
        else f"{r.project_name or r.run_id} ({r.run_id}) [{r.state}]"
        for r in runs
    }
    label_map[DEMO_FIXTURE_LABEL] = DEMO_FIXTURE_LABEL

    def _canonical_run_id(val: Any) -> str:
        if not val:
            return ""
        val_str = str(val).strip()
        if val_str in options:
            return val_str
        for r_id, lbl in label_map.items():
            if val_str == lbl:
                return r_id
        for opt in options:
            if f"({opt})" in val_str:
                return opt
        return val_str

    default_run_id = options[0] if options else DEMO_FIXTURE_LABEL
    current_selected = _canonical_run_id(
        state_persistence.persisted_value("fact_review_page", "selected_run_id", default_run_id)
    )
    select_index = resolve_select_index(current_selected, options, default_run_id)

    def _on_run_selector_change():
        widget_val = st.session_state.get("fact_review_run_selector")
        canonical_val = _canonical_run_id(widget_val)
        state_persistence.get_store("fact_review_page")["selected_run_id"] = canonical_val

    selected_run_id = st.selectbox(
        "Select run to review",
        options=options,
        index=select_index,
        format_func=lambda x: label_map.get(x, x),
        key="fact_review_run_selector",
        on_change=_on_run_selector_change,
    )
    selected_run_id = _canonical_run_id(selected_run_id)
    state_persistence.get_store("fact_review_page")["selected_run_id"] = selected_run_id

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

    saved = False
    approved = False
    generate_clicked = False
    blocking_errors = []

    if is_fixture:
        saved = st.button("Save review", key="fact_review_save_button")
    elif run.state == "approved":
        generate_clicked = st.button("Generate documents", key="fact_review_generate_button")
    elif run.state == "pending_review":
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
    elif run.state == "generated":
        st.info(f"Run {selected_run_id} has been generated.")

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
                st.session_state["fact_review_flash_success"] = f"Run {selected_run_id} approved successfully."
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    if generate_clicked:
        try:
            references, run_result = review.generate_approved_run(selected_run_id, storage=storage)
            st.session_state[f"fact_review::{selected_run_id}::generated_references"] = references
            st.session_state["fact_review_flash_success"] = f"Run {selected_run_id} documents generated successfully."
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    # Render download buttons if generation references exist
    generated_references = st.session_state.get(f"fact_review::{selected_run_id}::generated_references")
    if not is_fixture and not generated_references and run.state == "generated":
        run_dir = storage._run_dir(selected_run_id) if hasattr(storage, "_run_dir") else None
        if run_dir and run_dir.exists():
            existing_files = [
                p for p in run_dir.iterdir()
                if p.is_file() and p.name not in ("baseline.json", "status.json", "validation_report.json", "review_audit.json")
            ]
            if existing_files:
                generated_references = {p.name: str(p) for p in existing_files}

    if generated_references:
        st.caption("Download generated files (each button saves the named file via your browser's own download)")
        for filename, ref_path_str in generated_references.items():
            ref_path = Path(ref_path_str)
            if ref_path.exists():
                label = review.label_for_generated_file(filename)
                st.download_button(
                    label=f"Download {label}: {ref_path.name}",
                    data=ref_path.read_bytes(),
                    file_name=ref_path.name,
                    mime="application/octet-stream",
                    key=f"download::{selected_run_id}::{ref_path.name}",
                )


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
