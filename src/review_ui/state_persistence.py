"""Shared helper for persisting in-progress widget values across Streamlit page/tab switches.

Root cause this exists to fix (see reports\\htl_fact_review_regression_report.md, INVESTIGATE 1):
a widget's st.session_state entry is cleared by Streamlit the moment that widget isn't rendered in
a given script run. Since this app's pages (app.py's "Generate / Re-ingest" vs "Fact Review
(fixture)") and generate.py's "Generate" vs "Re-ingest" tabs each only render a subset of widgets
per run, switching away and back silently drops any not-yet-submitted edit -- including edits made
inside an st.form, whose widgets only commit to st.session_state on their own submit button anyway.

The fix: copy each widget's value into a separate, plain (non-widget) st.session_state dict the
moment it changes (via on_change), and use that persisted dict -- not the widget's own key -- as
both the widget's initial value on (re)render and the source of truth read at save/submit time.
"""

from typing import Any, Dict

import streamlit as st


def get_store(store_key: str) -> Dict[str, Any]:
    """Return the persistent value store for `store_key`, creating it if needed."""
    return st.session_state.setdefault(store_key, {})


def persisted_value(store_key: str, field_key: str, default: Any) -> Any:
    """The last persisted value for `field_key`, or `default` if never set."""
    return get_store(store_key).get(field_key, default)


def sync_to_store(store_key: str, widget_key: str, field_key: str) -> None:
    """on_change callback body: copy a widget's current session_state value into the persistent store.

    Must be called with the widget's own key already present in st.session_state (i.e. from within
    an on_change callback, where Streamlit guarantees this).
    """
    get_store(store_key)[field_key] = st.session_state[widget_key]
