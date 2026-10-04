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

GOVERNANCE_TIERS = ["Guided", "Partnered", "Elevated"]
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
        with st.form("generate_form"):
            uploaded_files = st.file_uploader(
                "Upload SOW and/or supporting documents (PDF, DOCX, PPTX, TXT)",
                type=["pdf", "docx", "pptx", "txt"],
                accept_multiple_files=True,
            )
            start_date_text = st.text_input("Project start date (YYYY-MM-DD, optional)", key="gen_start_date")
            governance_tier = st.selectbox("Governance tier", GOVERNANCE_TIERS, index=1, key="gen_tier")
            contract_type = st.text_input(
                "Contract type", value=config.default_contract_type, key="gen_contract_type"
            )
            pmo_lead = st.text_input("PMO Lead", value="", key="gen_pmo_lead")
            delivery_lead = st.text_input("Delivery Lead / Manager", value="", key="gen_delivery_lead")
            talent_pm = st.text_input("Talent PM", value="", key="gen_talent_pm")
            if admin_unlocked_gen:
                provider = st.selectbox("LLM provider (admin)", LLM_PROVIDERS, key="gen_provider")
                model = st.text_input(
                    "Model (admin, optional, uses provider default if blank)", value="", key="gen_model"
                )
                mock = st.checkbox(
                    "Mock mode (admin; run the offline client against my own upload, no API keys required)",
                    key="gen_mock",
                )
                cache_mode = st.selectbox("LLM cache mode (admin)", LLM_CACHE_MODES_IN_APP, key="gen_cache_mode")
            else:
                provider, model, mock, cache_mode = "", "", False, "off"
            st.caption("Outputs to produce")
            col1, col2, col3, col4 = st.columns(4)
            kit = col1.checkbox("Startup Kit", value=True, key="gen_out_kit")
            checklist = col2.checkbox("Readiness Checklist", value=True, key="gen_out_checklist")
            workbook = col3.checkbox("Delivery Workbook", value=True, key="gen_out_workbook")
            slides = col4.checkbox("Onboarding Deck", value=False, key="gen_out_slides")
            submitted = st.form_submit_button("Generate")

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
                    )
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
        with st.form("reingest_form"):
            uploaded_kit_file = st.file_uploader(
                "Upload an existing *_Startup_Kit.docx file to re-ingest", type=["docx"], key="reingest_file"
            )
            start_date_text_r = st.text_input("Project start date (YYYY-MM-DD, optional)", key="reingest_start_date")
            governance_tier_r = st.selectbox(
                "Governance tier override (optional)", [""] + GOVERNANCE_TIERS, key="reingest_tier"
            )
            contract_type_r = st.text_input("Contract type override (optional)", value="", key="reingest_contract_type")
            pmo_lead_r = st.text_input(
                "PMO Lead override (blank = keep existing value)", value="", key="reingest_pmo_lead"
            )
            delivery_lead_r = st.text_input(
                "Delivery Lead override (blank = keep existing value)", value="", key="reingest_delivery_lead"
            )
            talent_pm_r = st.text_input(
                "Talent PM override (blank = keep existing value)", value="", key="reingest_talent_pm"
            )
            if admin_unlocked_r:
                provider_r = st.selectbox("LLM provider (admin)", LLM_PROVIDERS, key="reingest_provider")
                model_r = st.text_input("Model (admin, optional)", value="", key="reingest_model")
                mock_r = st.checkbox("Mock mode (admin)", key="reingest_mock")
                cache_mode_r = st.selectbox("LLM cache mode (admin)", LLM_CACHE_MODES_IN_APP, key="reingest_cache_mode")
            else:
                provider_r, model_r, mock_r, cache_mode_r = "", "", False, "off"
            st.caption("Outputs to regenerate")
            rcol1, rcol2, rcol3, rcol4 = st.columns(4)
            kit_r = rcol1.checkbox("Startup Kit", value=True, key="reingest_out_kit")
            checklist_r = rcol2.checkbox("Readiness Checklist", value=True, key="reingest_out_checklist")
            workbook_r = rcol3.checkbox("Delivery Workbook", value=True, key="reingest_out_workbook")
            slides_r = rcol4.checkbox("Onboarding Deck", value=False, key="reingest_out_slides")
            submitted_r = st.form_submit_button("Re-ingest and recalculate")

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
                    )
                    st.session_state["reingest_run_result"] = result_r
                except RuntimeError as exc:
                    st.error(str(exc))
                except Exception as exc:  # noqa: BLE001 -- HTL-26: a clear message, not a traceback
                    st.error(f"Run failed: {exc}")

        if st.session_state.get("reingest_run_result") is not None:
            _render_results(st.session_state["reingest_run_result"])
