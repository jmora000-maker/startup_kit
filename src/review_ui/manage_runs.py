"""HTL-75: Administrative Manage Runs UI module for PMO Startup Kit.

Provides an admin-passphrase-gated dashboard to view, archive, unarchive,
and permanently purge review runs and their associated files.
"""

import logging

import streamlit as st

from src.config import config
from src.core.models import ReviewRunSummary
from src.review_storage import get_review_storage
from src.review_ui.generate import is_admin_unlocked

logger = logging.getLogger(__name__)

SESSION_KEY_UNLOCKED = "manage_runs_admin_unlocked"
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
        entered_passphrase = st.text_input(
            "Admin Passphrase",
            type="password",
            key="manage_runs_passphrase_input",
        )
        submitted = st.button("Unlock Manage Runs", key="manage_runs_unlock_button")

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
        if st.button("Lock page", key="manage_runs_lock_button"):
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

    # Tabs
    tab_active, tab_archived = st.tabs([
        f"Active Runs ({len(active_runs)})",
        f"Archived Runs ({len(archived_runs)})",
    ])

    with tab_active:
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
                        if st.button("Archive", key=f"btn_archive_{run.run_id}"):
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

    with tab_archived:
        if not archived_runs:
            st.info("No archived runs.")
        else:
            sorted_archived = sorted(archived_runs, key=lambda r: -r.created_at.timestamp())
            for run in sorted_archived:
                with st.container(border=True):
                    c_info, c_action = st.columns([3, 2])
                    with c_info:
                        _render_run_info(run, is_archived=True)
                    with c_action:
                        act_col1, act_col2 = st.columns(2)
                        with act_col1:
                            if st.button("Unarchive", key=f"btn_unarchive_{run.run_id}"):
                                try:
                                    storage.unarchive_run(run.run_id)
                                    st.session_state[SESSION_KEY_FLASH_SUCCESS] = (
                                        f"Run '{run.run_id}' restored to active."
                                    )
                                    st.rerun()
                                except Exception as exc:  # noqa: BLE001
                                    st.session_state[SESSION_KEY_FLASH_ERROR] = (
                                        f"Failed to unarchive run '{run.run_id}': {exc}"
                                    )
                                    st.rerun()
                        with act_col2:
                            confirm_purge = st.checkbox(
                                "Confirm delete",
                                key=f"chk_purge_{run.run_id}",
                            )
                            if st.button(
                                "Purge",
                                key=f"btn_purge_{run.run_id}",
                                disabled=not confirm_purge,
                                type="primary",
                            ):
                                try:
                                    storage.purge_run(run.run_id)
                                    st.session_state[SESSION_KEY_FLASH_SUCCESS] = (
                                        f"Run '{run.run_id}' and all associated files permanently purged."
                                    )
                                    st.rerun()
                                except Exception as exc:  # noqa: BLE001
                                    st.session_state[SESSION_KEY_FLASH_ERROR] = (
                                        f"Failed to purge run '{run.run_id}': {exc}"
                                    )
                                    st.rerun()
