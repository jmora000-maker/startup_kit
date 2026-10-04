"""HTL-17: Streamlit front end widening the app from "list and review runs" into a complete
second front end matching the CLI's surface -- upload a SOW (or an existing Kit for
re-ingestion), set every CLI option, trigger a run, and download the generated files.

All real logic (ingestion, extraction, validation, document generation, re-ingestion) is called
through src/orchestrator.py's shared service layer (HTL-16); nothing here duplicates it. This
step does not build the review_queue/state-machine plumbing (HTL-01 through HTL-05, HTL-13): a
submitted run always goes straight through to generated output, the same as a normal
(non---review) CLI invocation does today.

HTL-27: every user sees the upload, dates, governance tier, contract type, the three named
roles, and output selection. LLM provider/model, the mock toggle, and the llm-cache mode sit
behind a collapsed, passphrase-locked "Advanced (admin)" section, closed by default. Until it is
unlocked with the correct passphrase, a run always uses fixed, safe defaults: the server's
configured real provider/model, mock off, cache off -- never whatever an invisible/inert widget
might otherwise hold.

This module is deliberately split into plain, pure functions (validation, role resolution,
admin-gate checking, download-target collection, client construction) and a thin `render()` that
only calls Streamlit widgets -- the pure functions are covered by tests/test_streamlit_app.py;
the widget code itself is only smoke-tested (per HTL-17's own Test column).
"""

import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.config import config
from src.core.outputs import OutputSelection, RunResult
from src.orchestrator import (
    StartupKitController,
    build_llm_client,
    parse_start_date,
    resolve_role_for_reingest,
)
from src.review_ui import state_persistence
from src.review_ui.constants import (
    CONTRACT_TYPES,
    GOVERNANCE_TIERS,
    MODEL_OPTIONS_BY_PROVIDER,
    PROVIDER_DEFAULT_MODEL_LABEL,
    resolve_select_index,
)

LLM_PROVIDERS = ["anthropic", "openai"]
# HTL-22: the app exposes only "off" and "replay" -- "record" writes into the curated
# test-fixture corpus and stays CLI/developer-only.
LLM_CACHE_MODES_IN_APP = ["off", "replay"]
ROLE_PLACEHOLDER = "[UNASSIGNED - TO BE CONFIRMED]"


def validate_start_date_text(start_date_text: str) -> Optional[str]:
    """HTL-17 Group 1 (C-2 reuse): validates a form field's raw start-date text using the same
    shared parse_start_date helper the CLI uses. Returns an error message, or None if valid."""
    if not start_date_text:
        return None
    try:
        parse_start_date(start_date_text)
    except ValueError:
        return f"Invalid start date '{start_date_text}'. Please use YYYY-MM-DD format."
    return None


def validate_generate_inputs(uploaded_file_names: Sequence[str], start_date_text: str) -> Optional[str]:
    """Pure validation for the "Generate" form. Returns an error message, or None if valid."""
    if not uploaded_file_names:
        return "Please upload at least one SOW or supporting document (PDF, DOCX, PPTX, or TXT)."
    return validate_start_date_text(start_date_text)


def validate_reingest_inputs(uploaded_file_name: Optional[str], start_date_text: str) -> Optional[str]:
    """Pure validation for the "Re-ingest" form. Returns an error message, or None if valid."""
    if not uploaded_file_name:
        return "Please upload an existing *_Startup_Kit.docx file to re-ingest."
    return validate_start_date_text(start_date_text)


def resolve_app_role(field_value: str) -> Optional[str]:
    """HTL-25: a blank text field on re-ingestion means "no override supplied for this run" --
    the existing baseline value is left untouched. The app has no interactive/non-interactive
    distinction to model (HTL-25/U-7), so this always calls the shared
    resolve_role_for_reingest with interactive=False: a filled field is applied, a blank one is
    not, and nothing ever carries a name over from a different run.
    """
    cleaned = field_value.strip() if field_value else ""
    flag_value = cleaned if cleaned else None
    return resolve_role_for_reingest(flag_value, cleaned, interactive=False)


@dataclass(frozen=True)
class DownloadTarget:
    label: str
    path: Path


def collect_download_targets(run_result: RunResult) -> List[DownloadTarget]:
    """HTL-24: builds the app's own download-button list straight from RunResult's structured
    path fields, instead of parsing the CLI's formatted summary text."""
    targets: List[DownloadTarget] = []
    if run_result.kit_path:
        targets.append(DownloadTarget("Startup Kit (.docx)", run_result.kit_path))
    if run_result.checklist_path:
        targets.append(DownloadTarget("Startup Readiness Checklist (.docx)", run_result.checklist_path))
    if run_result.workbook is not None:
        targets.append(DownloadTarget("Project Delivery Workbook (.xlsx)", run_result.workbook.file_path))
    if run_result.slides is not None:
        targets.append(DownloadTarget("Talent Onboarding Deck (.pptx)", run_result.slides.file_path))
        targets.append(DownloadTarget("Deck Trace Manifest (.json)", run_result.slides.manifest_path))
    return targets


def is_admin_unlocked(entered_passphrase: str, configured_passphrase: str) -> bool:
    """HTL-27: the Advanced (admin) section unlocks only on an exact, non-empty match against the
    configured passphrase (``config.admin_passphrase``: an env var locally, a Secret Manager value
    in production). An empty configured passphrase never unlocks, even against an empty entry --
    there is always a non-empty value configured in practice (the dev-only placeholder, at worst),
    so this is a defensive refusal, not a usable bypass.
    """
    if not configured_passphrase:
        return False
    return entered_passphrase == configured_passphrase


def resolve_llm_settings(
    admin_unlocked: bool,
    provider: str = "",
    model: str = "",
    mock: bool = False,
    cache_mode: str = "off",
):
    """HTL-27: when the admin section was never unlocked for this run, the provider, model, mock
    toggle, and cache mode are never read from the (in that case invisible and inert) admin
    widgets at all -- every run instead uses fixed, safe defaults: the server's configured real
    provider and its default model, mock off, and cache off. Only an unlocked admin's actual
    selections are ever passed through.
    """
    if not admin_unlocked:
        return config.default_provider, "", False, "off"
    return provider, model, mock, cache_mode


def build_app_llm_client(provider: str, model: str, mock: bool, cache_mode: str):
    """HTL-16/HTL-21: the app's only entry point for constructing an LLM client is the one
    shared factory. No API key field exists anywhere in this module, locked or unlocked; keys
    always come from the server-side config/secrets (HTL-15/HTL-21), never from a value typed
    into the page.
    """
    return build_llm_client(
        provider=provider,
        model=model or None,
        anthropic_api_key=config.anthropic_api_key,
        openai_api_key=config.openai_api_key,
        cache_mode=cache_mode,
        mock=mock,
    )


def _new_run_output_dir() -> Path:
    """Each submitted run gets its own disposable output folder so concurrent app sessions
    (Group 5's concurrency-readiness note) don't collide on file names."""
    return Path(tempfile.mkdtemp(prefix="startup_kit_app_run_"))


# HTL-28: real per-stage progress. orchestrator.run()/run_reingest() report real stage
# boundaries ('ingesting', 'extracting', 'validating', 'generating') through an on_progress
# callback as they actually happen; this maps each real stage to a user-facing label, replacing
# HTL-17's interim single generic spinner message with text reflecting the actual callback-
# reported stage, never a simulated or timed sequence.
STAGE_LABELS = {
    "ingesting": "Ingesting documents...",
    "extracting": "Running extraction...",
    "validating": "Validating...",
    "generating": "Generating documents...",
}


def progress_status_label(stage: str, detail: str = "") -> str:
    """Pure function: the live status text for a real on_progress(stage, detail) call. An
    unrecognized stage still shows something sensible (the raw stage name) rather than failing,
    since this must never be the reason a real run's progress display breaks.
    """
    base = STAGE_LABELS.get(stage, stage.capitalize() if stage else "Working")
    return f"{base} ({detail})" if detail else base


def _run_generate(
    uploaded_files,
    start_date_text: str,
    governance_tier: str,
    contract_type: str,
    pmo_lead: str,
    delivery_lead: str,
    talent_pm: str,
    provider: str,
    model: str,
    mock: bool,
    cache_mode: str,
    outputs: OutputSelection,
    on_progress=None,
) -> RunResult:
    llm_client = build_app_llm_client(provider=provider, model=model, mock=mock, cache_mode=cache_mode)
    controller = StartupKitController(llm_client=llm_client)
    input_documents = [(f.name, f.getvalue()) for f in uploaded_files]
    output_dir = _new_run_output_dir()
    start_date = parse_start_date(start_date_text)
    return controller.run(
        input_documents=input_documents,
        output_dir=output_dir,
        tier_override=governance_tier,
        contract_type_override=contract_type or None,
        pmo_lead=pmo_lead,
        delivery_lead=delivery_lead,
        talent_pm=talent_pm,
        outputs=outputs,
        start_date=start_date,
        on_progress=on_progress,
    )


def _run_reingest(
    uploaded_kit_file,
    start_date_text: str,
    governance_tier: str,
    contract_type: str,
    pmo_lead_field: str,
    delivery_lead_field: str,
    talent_pm_field: str,
    provider: str,
    model: str,
    mock: bool,
    cache_mode: str,
    outputs: OutputSelection,
    on_progress=None,
) -> RunResult:
    llm_client = build_app_llm_client(provider=provider, model=model, mock=mock, cache_mode=cache_mode)
    controller = StartupKitController(llm_client=llm_client)
    output_dir = _new_run_output_dir()
    start_date = parse_start_date(start_date_text)
    return controller.run_reingest(
        docx_source=(uploaded_kit_file.name, uploaded_kit_file.getvalue()),
        output_dir=output_dir,
        # HTL-23: the app always writes a new file; there is no in-place-overwrite option here.
        always_write_new_file=True,
        pmo_lead=resolve_app_role(pmo_lead_field),
        delivery_lead=resolve_app_role(delivery_lead_field),
        talent_pm=resolve_app_role(talent_pm_field),
        tier_override=governance_tier or None,
        contract_type_override=contract_type or None,
        outputs=outputs,
        start_date=start_date,
        on_progress=on_progress,
    )


def _render_results(run_result: RunResult) -> None:
    import streamlit as st

    st.success("Run complete.")
    st.metric("Readiness score", f"{run_result.readiness_score:.1f}%")

    baseline = run_result.baseline
    if baseline is not None:
        if baseline.readiness_breakdown:
            st.caption("Readiness breakdown")
            st.table(
                [{"Category": k, "Score": v} for k, v in baseline.readiness_breakdown.items()]
            )
        if baseline.gate_decision is not None:
            st.write(f"Gate decision status: **{baseline.gate_decision.gate_decision_status}**")
        if baseline.open_questions:
            with st.expander(f"Open questions / clarifications ({len(baseline.open_questions)})"):
                for q in baseline.open_questions:
                    st.write(f"- {q}")

    if run_result.fallback_domains:
        st.warning(
            "The following extraction domain(s) used a secondary OpenAI fallback model: "
            + ", ".join(run_result.fallback_domains)
        )

    if run_result.validation_report is not None and run_result.validation_report.findings:
        with st.expander(f"Validation findings ({len(run_result.validation_report.findings)})"):
            for finding in run_result.validation_report.findings:
                st.write(f"**[{finding.severity}] {finding.invariant_id}** -- {finding.message}")

    targets = collect_download_targets(run_result)
    if targets:
        # INVESTIGATE 2: st.download_button genuinely pushes bytes straight to the browser's own
        # save dialog (data is bytes here, so Streamlit uses the "application/octet-stream" MIME
        # type, which every major browser downloads rather than displays inline) -- there is no
        # separate server-side save the user needs to go find. The actual gap was that the label
        # never showed the real generated file name, so after a silent, successful download a user
        # had no way to know what file to look for. The label now always includes it.
        st.caption("Download generated files (each button saves the named file via your browser's own download)")
        for target in targets:
            if target.path.exists():
                st.download_button(
                    label=f"Download {target.label}: {target.path.name}",
                    data=target.path.read_bytes(),
                    file_name=target.path.name,
                    mime="application/octet-stream",
                    key=f"download::{target.path}",
                )


def _output_selection_from_checkboxes(kit: bool, checklist: bool, workbook: bool, slides: bool) -> OutputSelection:
    return OutputSelection(kit=kit, checklist=checklist, workbook=workbook, slides=slides)


# Item 3: both the Generate and Re-ingest tabs used to wrap all their fields in st.form, which
# only commits a widget's value to st.session_state on that form's own submit button -- and since
# app.py's page router only renders the currently-selected page's widgets, navigating to the Fact
# Review page and back unmounts every one of these widgets, silently dropping an in-progress edit
# (the exact same root cause as the Fact Review regression, see state_persistence.py). The fix
# reuses that same module rather than a second mechanism: st.form is removed below, each field's
# current value is persisted into its own store the instant it changes, and that store (not the
# widget's own, page-switch-fragile session_state key) supplies the widget's value on every
# render. File uploaders are the one exception: Streamlit has no API to set a file uploader's
# value, so a re-upload after switching away and back is an unavoidable, accepted limitation.
GENERATE_STORE = "generate_form_values"
REINGEST_STORE = "reingest_form_values"


def _persisted_text(store_key: str, field_key: str, label: str, default: str = "", widget_fn=None, **kwargs) -> str:
    import streamlit as st

    widget_fn = widget_fn or st.text_input
    current = state_persistence.persisted_value(store_key, field_key, default)
    on_change = lambda fk=field_key: state_persistence.sync_to_store(store_key, fk, fk)  # noqa: E731
    return widget_fn(label, value=current, key=field_key, on_change=on_change, **kwargs)


def _persisted_checkbox(
    store_key: str, field_key: str, label: str, default: bool = False, widget_fn=None, **kwargs
) -> bool:
    import streamlit as st

    widget_fn = widget_fn or st.checkbox
    current = state_persistence.persisted_value(store_key, field_key, default)
    on_change = lambda fk=field_key: state_persistence.sync_to_store(store_key, fk, fk)  # noqa: E731
    return widget_fn(label, value=bool(current), key=field_key, on_change=on_change, **kwargs)


def _persisted_selectbox(
    store_key: str, field_key: str, label: str, options: List[str], default: str, widget_fn=None, **kwargs
) -> str:
    import streamlit as st

    widget_fn = widget_fn or st.selectbox
    current = state_persistence.persisted_value(store_key, field_key, default)
    index = resolve_select_index(current, options, default)
    on_change = lambda fk=field_key: state_persistence.sync_to_store(store_key, fk, fk)  # noqa: E731
    return widget_fn(label, options, index=index, key=field_key, on_change=on_change, **kwargs)


def _render_admin_gate(key_prefix: str) -> bool:
    """HTL-27: a collapsed, closed-by-default "Advanced (admin)" expander. An ordinary user never
    sees provider/model/mock/cache-mode controls at all -- they render only after this gate
    reports unlocked. Rendered outside any st.form, since a passphrase check needs to take effect
    immediately (a form only reacts on its own submit button)."""
    import streamlit as st

    unlocked_key = f"{key_prefix}_admin_unlocked"
    if unlocked_key not in st.session_state:
        st.session_state[unlocked_key] = False

    with st.expander("Advanced (admin)", expanded=False):
        if st.session_state[unlocked_key]:
            st.caption("Unlocked: LLM provider/model, mock mode, and cache mode are set below.")
        else:
            st.caption(
                "Locked. Ordinary users do not need this section -- a run uses the server's "
                "configured real provider with mock off and caching off until an admin unlocks it."
            )
            entered = st.text_input(
                "Admin passphrase", type="password", key=f"{key_prefix}_admin_passphrase_input"
            )
            if st.button("Unlock", key=f"{key_prefix}_admin_unlock_button"):
                if is_admin_unlocked(entered, config.admin_passphrase):
                    st.session_state[unlocked_key] = True
                    st.rerun()
                else:
                    st.error("Incorrect passphrase.")
    return st.session_state[unlocked_key]


def render() -> None:
    import streamlit as st

    st.title("Generate / Re-ingest a Startup Kit")
    st.caption(
        "Upload documents, set the same options the CLI (main.py) exposes, trigger a run, and "
        "download the generated files -- a complete second front end to the shared orchestrator "
        "(HTL-16/HTL-17)."
    )

    tab_generate, tab_reingest = st.tabs(["Generate from SOW upload", "Re-ingest an existing Kit"])

    with tab_generate:
        admin_unlocked_gen = _render_admin_gate("gen")
        uploaded_files = st.file_uploader(
            "Upload SOW and/or supporting documents (PDF, DOCX, PPTX, TXT)",
            type=["pdf", "docx", "pptx", "txt"],
            accept_multiple_files=True,
            key="gen_uploader",
        )
        start_date_text = _persisted_text(
            GENERATE_STORE, "gen_start_date", "Project start date (YYYY-MM-DD, optional)"
        )
        # Item 8: the default governance tier now matches the server's configured default
        # (config.default_governance_tier) instead of a hardcoded index, consistent with how the
        # Fact Review screen shows whatever the baseline itself carries -- no more silently
        # diverging defaults between the two screens.
        governance_tier = _persisted_selectbox(
            GENERATE_STORE, "gen_tier", "Governance tier", GOVERNANCE_TIERS, config.default_governance_tier
        )
        # Item 4: contract type is a shared, closed-set dropdown (src/review_ui/constants.py),
        # identical to the Fact Review screen's own contract-type field.
        contract_type = _persisted_selectbox(
            GENERATE_STORE, "gen_contract_type", "Contract type", CONTRACT_TYPES, config.default_contract_type
        )
        pmo_lead = _persisted_text(GENERATE_STORE, "gen_pmo_lead", "PMO Lead")
        delivery_lead = _persisted_text(GENERATE_STORE, "gen_delivery_lead", "Delivery Lead / Manager")
        talent_pm = _persisted_text(GENERATE_STORE, "gen_talent_pm", "Talent PM")
        if admin_unlocked_gen:
            provider = _persisted_selectbox(
                GENERATE_STORE, "gen_provider", "LLM provider (admin)", LLM_PROVIDERS, config.default_provider
            )
            # Item 5: the model field is a dropdown of known-valid model names, not free text.
            model_options = [PROVIDER_DEFAULT_MODEL_LABEL] + MODEL_OPTIONS_BY_PROVIDER.get(provider, [])
            model_choice = _persisted_selectbox(
                GENERATE_STORE, "gen_model", "Model (admin, optional -- uses provider default if left as-is)",
                model_options, PROVIDER_DEFAULT_MODEL_LABEL,
            )
            model = "" if model_choice == PROVIDER_DEFAULT_MODEL_LABEL else model_choice
            mock = _persisted_checkbox(
                GENERATE_STORE, "gen_mock",
                "Mock mode (admin; run the offline client against my own upload, no API keys required)",
            )
            cache_mode = _persisted_selectbox(
                GENERATE_STORE, "gen_cache_mode", "LLM cache mode (admin)", LLM_CACHE_MODES_IN_APP, "off"
            )
        else:
            provider, model, mock, cache_mode = "", "", False, "off"
        st.caption("Outputs to produce")
        col1, col2, col3, col4 = st.columns(4)
        kit = _persisted_checkbox(GENERATE_STORE, "gen_out_kit", "Startup Kit", True, widget_fn=col1.checkbox)
        checklist = _persisted_checkbox(
            GENERATE_STORE, "gen_out_checklist", "Readiness Checklist", True, widget_fn=col2.checkbox
        )
        workbook = _persisted_checkbox(
            GENERATE_STORE, "gen_out_workbook", "Delivery Workbook", True, widget_fn=col3.checkbox
        )
        slides = _persisted_checkbox(
            GENERATE_STORE, "gen_out_slides", "Onboarding Deck", False, widget_fn=col4.checkbox
        )
        submitted = st.button("Generate", key="gen_submit_button")

        if submitted:
            file_names = [f.name for f in (uploaded_files or [])]
            error = validate_generate_inputs(file_names, start_date_text)
            if error:
                st.error(error)
            else:
                try:
                    outputs = _output_selection_from_checkboxes(kit, checklist, workbook, slides)
                    resolved_provider, resolved_model, resolved_mock, resolved_cache_mode = resolve_llm_settings(
                        admin_unlocked_gen, provider=provider, model=model, mock=mock, cache_mode=cache_mode
                    )
                    # Item 6/HTL-28: a visible, live progress indicator that reflects the real
                    # callback-reported stage (not a simulated or timed sequence) so the user
                    # isn't left wondering whether anything is happening during a run that can
                    # take a while.
                    with st.status("Starting...", expanded=True) as status_box:
                        def _update_status(stage: str, detail: str = "") -> None:
                            label = progress_status_label(stage, detail)
                            status_box.update(label=label)
                            status_box.write(label)

                        result = _run_generate(
                            uploaded_files=uploaded_files,
                            start_date_text=start_date_text,
                            governance_tier=governance_tier,
                            contract_type=contract_type,
                            pmo_lead=pmo_lead,
                            delivery_lead=delivery_lead,
                            talent_pm=talent_pm,
                            provider=resolved_provider,
                            model=resolved_model,
                            mock=resolved_mock,
                            cache_mode=resolved_cache_mode,
                            outputs=outputs,
                            on_progress=_update_status,
                        )
                        status_box.update(label="Run complete.", state="complete")
                    st.session_state["generate_run_result"] = result
                except RuntimeError as exc:
                    # HTL-20/HTL-26: no silent mock fall-back; the exact build_llm_client error is
                    # surfaced as a clear message, never a stack trace.
                    st.error(str(exc))
                except Exception as exc:  # noqa: BLE001 -- HTL-26: a clear message, not a traceback
                    st.error(f"Run failed: {exc}")

        if st.session_state.get("generate_run_result") is not None:
            _render_results(st.session_state["generate_run_result"])

    with tab_reingest:
        admin_unlocked_r = _render_admin_gate("reingest")
        uploaded_kit_file = st.file_uploader(
            "Upload an existing *_Startup_Kit.docx file to re-ingest", type=["docx"], key="reingest_file"
        )
        start_date_text_r = _persisted_text(
            REINGEST_STORE, "reingest_start_date", "Project start date (YYYY-MM-DD, optional)"
        )
        governance_tier_r = _persisted_selectbox(
            REINGEST_STORE, "reingest_tier", "Governance tier override (optional)",
            [""] + GOVERNANCE_TIERS, "",
        )
        # Item 4: contract type override is the same shared, closed-set dropdown as the Generate
        # tab and the Fact Review screen (blank = "no override", same as before).
        contract_type_r = _persisted_selectbox(
            REINGEST_STORE, "reingest_contract_type", "Contract type override (optional)",
            [""] + CONTRACT_TYPES, "",
        )
        pmo_lead_r = _persisted_text(
            REINGEST_STORE, "reingest_pmo_lead", "PMO Lead override (blank = keep existing value)"
        )
        delivery_lead_r = _persisted_text(
            REINGEST_STORE, "reingest_delivery_lead", "Delivery Lead override (blank = keep existing value)"
        )
        talent_pm_r = _persisted_text(
            REINGEST_STORE, "reingest_talent_pm", "Talent PM override (blank = keep existing value)"
        )
        if admin_unlocked_r:
            provider_r = _persisted_selectbox(
                REINGEST_STORE, "reingest_provider", "LLM provider (admin)", LLM_PROVIDERS, config.default_provider
            )
            model_options_r = [PROVIDER_DEFAULT_MODEL_LABEL] + MODEL_OPTIONS_BY_PROVIDER.get(provider_r, [])
            model_choice_r = _persisted_selectbox(
                REINGEST_STORE, "reingest_model", "Model (admin, optional)",
                model_options_r, PROVIDER_DEFAULT_MODEL_LABEL,
            )
            model_r = "" if model_choice_r == PROVIDER_DEFAULT_MODEL_LABEL else model_choice_r
            mock_r = _persisted_checkbox(REINGEST_STORE, "reingest_mock", "Mock mode (admin)")
            cache_mode_r = _persisted_selectbox(
                REINGEST_STORE, "reingest_cache_mode", "LLM cache mode (admin)", LLM_CACHE_MODES_IN_APP, "off"
            )
        else:
            provider_r, model_r, mock_r, cache_mode_r = "", "", False, "off"
        st.caption("Outputs to regenerate")
        rcol1, rcol2, rcol3, rcol4 = st.columns(4)
        kit_r = _persisted_checkbox(REINGEST_STORE, "reingest_out_kit", "Startup Kit", True, widget_fn=rcol1.checkbox)
        checklist_r = _persisted_checkbox(
            REINGEST_STORE, "reingest_out_checklist", "Readiness Checklist", True, widget_fn=rcol2.checkbox
        )
        workbook_r = _persisted_checkbox(
            REINGEST_STORE, "reingest_out_workbook", "Delivery Workbook", True, widget_fn=rcol3.checkbox
        )
        slides_r = _persisted_checkbox(
            REINGEST_STORE, "reingest_out_slides", "Onboarding Deck", False, widget_fn=rcol4.checkbox
        )
        submitted_r = st.button("Re-ingest and recalculate", key="reingest_submit_button")

        if submitted_r:
            error = validate_reingest_inputs(
                uploaded_kit_file.name if uploaded_kit_file else None, start_date_text_r
            )
            if error:
                st.error(error)
            else:
                try:
                    outputs_r = _output_selection_from_checkboxes(kit_r, checklist_r, workbook_r, slides_r)
                    resolved_provider_r, resolved_model_r, resolved_mock_r, resolved_cache_mode_r = resolve_llm_settings(
                        admin_unlocked_r, provider=provider_r, model=model_r, mock=mock_r, cache_mode=cache_mode_r
                    )
                    with st.status("Starting...", expanded=True) as status_box_r:
                        def _update_status_r(stage: str, detail: str = "") -> None:
                            label = progress_status_label(stage, detail)
                            status_box_r.update(label=label)
                            status_box_r.write(label)

                        result_r = _run_reingest(
                            uploaded_kit_file=uploaded_kit_file,
                            start_date_text=start_date_text_r,
                            governance_tier=governance_tier_r,
                            contract_type=contract_type_r,
                            pmo_lead_field=pmo_lead_r,
                            delivery_lead_field=delivery_lead_r,
                            talent_pm_field=talent_pm_r,
                            provider=resolved_provider_r,
                            model=resolved_model_r,
                            mock=resolved_mock_r,
                            cache_mode=resolved_cache_mode_r,
                            outputs=outputs_r,
                            on_progress=_update_status_r,
                        )
                        status_box_r.update(label="Run complete.", state="complete")
                    st.session_state["reingest_run_result"] = result_r
                except RuntimeError as exc:
                    st.error(str(exc))
                except Exception as exc:  # noqa: BLE001 -- HTL-26: a clear message, not a traceback
                    st.error(f"Run failed: {exc}")

        if st.session_state.get("reingest_run_result") is not None:
            _render_results(st.session_state["reingest_run_result"])
