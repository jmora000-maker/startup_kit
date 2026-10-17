"""Storage abstraction for Pre-Generation Human Review paused runs (HTL-13).

The backend is chosen by one environment variable, REVIEW_STORAGE_BACKEND (values "local" or
"gcp"), mirroring LLM_PROVIDER and LLM_CACHE_MODE's existing pattern (src/config.py), defaulting
to "local". pytest and all local development always use the local backend regardless of what a
shell's environment happens to have set (tests/conftest.py), the same safety rule LLM_CACHE_MODE
already follows for live LLM calls.
"""

from src.config import config
from src.core.interfaces import ReviewStorage
from src.review_storage.firestore import FirestoreReviewStorage
from src.review_storage.local import LocalReviewStorage

__all__ = ["ReviewStorage", "LocalReviewStorage", "FirestoreReviewStorage", "get_review_storage"]


def get_review_storage() -> ReviewStorage:
    """Return the ReviewStorage backend selected by config.review_storage_backend."""
    backend = config.review_storage_backend
    if backend == "local":
        return LocalReviewStorage()
    if backend in ("gcp", "firestore"):
        return FirestoreReviewStorage()
    raise ValueError(f"Unknown REVIEW_STORAGE_BACKEND: {backend!r} (expected 'local' or 'gcp')")
