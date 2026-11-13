"""HTL-75 / HTL-81 / HTL-82 / HTL-83: Administrative Manage Runs UI module for PMO Startup Kit.

Provides an admin-passphrase-gated dashboard to view, archive, unarchive,
and permanently purge review runs (via selection) and their associated files,
with state-persisted tab navigation.
"""

import logging

import streamlit as st

from src.config import config
from src.core.models import ReviewRunSummary
from src.review_storage import get_review_storage
from src.review_ui.generate import is_admin_unlocked

logger = logging.getLogger(__name__)

SESSION_KEY_UNLOCKED = "manage_runs_admin_unlocked"
SESSION_KEY_VIEW_TAB = "manage_runs_view_tab"
SESSION_KEY_BULK_PURGE_CONFIRMING = "manage_runs_bulk_purge_confirming"
SESSION_KEY_FLASH_SUCCESS = "manage_runs_flash_success"
SESSION_KEY_FLASH_ERROR = "manage_runs_flash_error"


def is_manage_runs_unlocked() -> bool:
    """Check if the Manage Runs page is currently unlocked in the user's session."""
    return bool(st.session_state.get(SESSION_KEY_UNLOCKED, False))


def unlock_manage_runs() -> None:
    """Unlock the Manage Runs page for the current session."""
    st.session_state[SESSION_KEY_UNLOCKED] = True


def lock_manage_runs() -> None:
    """Lock the Manage Runs page."""
    st.session_state[SESSION_KEY_UNLOCKED] = False


def _render_run_info(run: ReviewRunSummary, is_archived: bool = False) -> None:
    """Render run summary metadata card."""
    proj_title = run.project_name if run.project_name else "Untitled Project"
    st.markdown(f"**{proj_title}** (`{run.run_id}`)")
    state_label = f"`{run.state}` (Archived)" if is_archived else f"`{run.state}`"
    st.caption(f"State: {state_label}")
    created_str = (
        run.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        if run.created_at
        else "N/A"
    )
    st.text(f"Created: {created_str}")


def render() -> None:
    """Render the Manage Runs page or whole-page passphrase gate."""
    st.title("Manage Runs")

    # 1. Whole-Page Passphrase Gate
    if not is_manage_runs_unlocked():
        st.markdown(
            "This administrative section is protected by an admin passphrase. "
            "Enter the passphrase to view, archive, unarchive, or permanently purge review runs."
        )
        with st.form("manage_runs_gate_form", border=False):
            entered_passphrase = st.text_input(
                "Admin Passphrase",
                type="password",
                key="manage_runs_passphrase_input",
            )
            submitted = st.form_submit_button(
                "Unlock Manage Runs",
                key="manage_runs_unlock_button",
                type="primary",
            )

        if submitted:
            if is_admin_unlocked(entered_passphrase or "", config.admin_passphrase):
                unlock_manage_runs()
                st.rerun()
            else:
                st.error("Incorrect passphrase. Access denied.")
        return

    # 2. Unlocked Dashboard
    header_col, lock_col = st.columns([5, 1])
    with header_col:
        st.caption("Administrative run lifecycle and storage management.")
    with lock_col:
        if st.button("Lock page", key="manage_runs_lock_button", type="primary"):
            lock_manage_runs()
            st.rerun()

    # Flash messages
    flash_success = st.session_state.pop(SESSION_KEY_FLASH_SUCCESS, None)
    if flash_success:
        st.success(flash_success)
    flash_error = st.session_state.pop(SESSION_KEY_FLASH_ERROR, None)
    if flash_error:
        st.error(flash_error)

    storage = get_review_storage()
    all_runs = storage.list_runs(include_archived=True)
    active_runs = [r for r in all_runs if not r.archived]
    archived_runs = [r for r in all_runs if r.archived]

    # Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Runs", len(all_runs))
    m2.metric("Active Runs", len(active_runs))
    m3.metric("Archived Runs", len(archived_runs))

    # HTL-81 / HTL-111: Stateful Tab Navigation via horizontal radio
    if SESSION_KEY_VIEW_TAB not in st.session_state:
        st.session_state[SESSION_KEY_VIEW_TAB] = "active"

    selected_view = st.radio(
        "View",
        options=["active", "archived"],
        format_func=lambda x: "Active Runs" if x == "active" else "Archived Runs",
        horizontal=True,
        key=SESSION_KEY_VIEW_TAB,
    )
    if selected_view not in ("active", "archived"):
        selected_view = "active"
        st.session_state[SESSION_KEY_VIEW_TAB] = "active"

    if selected_view == "active":
        if not active_runs:
            st.info("No active runs.")
        else:
            sorted_active = sorted(active_runs, key=lambda r: -r.created_at.timestamp())
            for run in sorted_active:
                with st.container(border=True):
                    c_info, c_action = st.columns([3, 1])
                    with c_info:
                        _render_run_info(run, is_archived=False)
                    with c_action:
                        if st.button("Archive", key=f"btn_archive_{run.run_id}", type="primary"):
                            try:
                                storage.archive_run(run.run_id)
                                st.session_state[SESSION_KEY_FLASH_SUCCESS] = (
                                    f"Run '{run.run_id}' has been archived."
                                )
                                st.rerun()
                            except Exception as exc:  # noqa: BLE001
                                st.session_state[SESSION_KEY_FLASH_ERROR] = (
                                    f"Failed to archive run '{run.run_id}': {exc}"
                                )
                                st.rerun()

    elif selected_view == "archived":
        if not archived_runs:
            st.info("No archived runs.")
        else:
            sorted_archived = sorted(archived_runs, key=lambda r: -r.created_at.timestamp())

            # HTL-82: Bulk selection controls and multi-run purge
            selected_runs = [
                r for r in sorted_archived
                if st.session_state.get(f"chk_select_{r.run_id}", False)
            ]

            # 2-Stage Confirmation Panel
            if st.session_state.get(SESSION_KEY_BULK_PURGE_CONFIRMING, False) and selected_runs:
                with st.container(border=True):
                    st.warning(
                        f"⚠️ **Confirm Bulk Purge**: You are about to permanently delete **{len(selected_runs)}** "
                        "archived run(s) and all associated files. This action cannot be undone."
                    )
                    st.markdown("**Selected Runs to Purge:**")
                    for r in selected_runs:
                        proj_title = r.project_name if r.project_name else "Untitled Project"
                        st.markdown(f"- **{proj_title}** (`{r.run_id}`)")

                    c_confirm, c_cancel = st.columns([2, 1])
                    with c_confirm:
                        if st.button(
                            f"⚠️ Confirm & Delete {len(selected_runs)} Runs",
                            key="btn_bulk_purge_confirm",
                            type="primary",
                        ):
                            success_count = 0
                            failed = []
                            for r in selected_runs:
                                try:
                                    storage.purge_run(r.run_id)
                                    success_count += 1
                                    st.session_state.pop(f"chk_select_{r.run_id}", None)
                                except Exception as exc:  # noqa: BLE001
                                    logger.exception("Failed to purge run %s", r.run_id)
                                    failed.append((r.run_id, str(exc)))

                            st.session_state[SESSION_KEY_BULK_PURGE_CONFIRMING] = False
                            if failed:
                                fail_summary = "; ".join(f"{rid}: {msg}" for rid, msg in failed)
                                if success_count > 0:
                                    st.session_state[SESSION_KEY_FLASH_ERROR] = (
                                        f"Purged {success_count} run(s). {len(failed)} failed: {fail_summary}"
                                    )
                                else:
                                    st.session_state[SESSION_KEY_FLASH_ERROR] = (
                                        f"Failed to purge {len(failed)} run(s): {fail_summary}"
                                    )
                            else:
                                st.session_state[SESSION_KEY_FLASH_SUCCESS] = (
                                    f"Successfully purged {success_count} run(s) and all associated files."
                                )
                            st.rerun()

                    with c_cancel:
                        if st.button("Cancel", key="btn_bulk_purge_cancel", type="primary"):
                            st.session_state[SESSION_KEY_BULK_PURGE_CONFIRMING] = False
                            st.rerun()

            # Bulk Action Toolbar
            col_sel_all, col_desel_all, col_bulk_purge, _ = st.columns([1, 1, 2, 2])
            with col_sel_all:
                if st.button("Select All", key="btn_select_all_archived", type="primary"):
                    for r in sorted_archived:
                        st.session_state[f"chk_select_{r.run_id}"] = True
                    st.rerun()
            with col_desel_all:
                if st.button("Deselect All", key="btn_deselect_all_archived", type="primary"):
                    for r in sorted_archived:
                        st.session_state[f"chk_select_{r.run_id}"] = False
                    st.rerun()
            with col_bulk_purge:
                selected_count = len(selected_runs)
                if st.button(
                    f"⚠️ Purge Selected ({selected_count})",
                    key="btn_bulk_purge_init",
                    disabled=(selected_count == 0),
                    type="primary",
                ):
                    st.session_state[SESSION_KEY_BULK_PURGE_CONFIRMING] = True
                    st.rerun()

            # Individual Run Cards
            for run in sorted_archived:
                with st.container(border=True):
                    c_chk, c_info, c_action = st.columns([0.5, 4.5, 1])
                    with c_chk:
                        st.checkbox(
                            "Select run",
                            key=f"chk_select_{run.run_id}",
                            label_visibility="collapsed",
                        )
                    with c_info:
                        _render_run_info(run, is_archived=True)
                    with c_action:
                        if st.button("Unarchive", key=f"btn_unarchive_{run.run_id}", type="primary"):
                            try:
                                storage.unarchive_run(run.run_id)
                                st.session_state.pop(f"chk_select_{run.run_id}", None)
                                st.session_state[SESSION_KEY_FLASH_SUCCESS] = (
                                    f"Run '{run.run_id}' restored to active."
                                )
                                st.rerun()
                            except Exception as exc:  # noqa: BLE001
                                st.session_state[SESSION_KEY_FLASH_ERROR] = (
                                    f"Failed to unarchive run '{run.run_id}': {exc}"
                                )
                                st.rerun()
