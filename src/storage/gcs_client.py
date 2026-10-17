"""Standalone Google Cloud Storage client module for the Startup Kit app.

Per schema design in docs/GCP_Firestore_CloudStorage_Setup.md Section 7 & 8.
Connects via google-cloud-storage, respecting STORAGE_EMULATOR_HOST when set.
"""

import os
from pathlib import Path
from typing import List, Optional, Union

from google.cloud import storage

DEFAULT_BUCKET_NAME = "toptal-startup-kit-outputs"


def get_bucket_name(override: Optional[str] = None) -> str:
    """Resolve bucket name from argument or GCS_BUCKET_NAME env var."""
    return override or os.environ.get("GCS_BUCKET_NAME") or DEFAULT_BUCKET_NAME


def get_storage_client(project: Optional[str] = None) -> storage.Client:
    """Initialize and return a Cloud Storage client.
    
    If STORAGE_EMULATOR_HOST is set in environment, the client connects to the
    emulator without requiring real cloud credentials.
    """
    proj = (
        project
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCP_PROJECT")
        or "toptal-delivery-apps"
    )
    return storage.Client(project=proj)


def _get_or_create_bucket(
    client: storage.Client,
    bucket_name: str,
) -> storage.Bucket:
    """Retrieve bucket or create it if missing (e.g. under emulator testing)."""
    bucket = client.bucket(bucket_name)
    if not bucket.exists():
        try:
            bucket = client.create_bucket(bucket_name)
        except Exception:
            # In case of concurrent creation or permissions
            bucket = client.bucket(bucket_name)
    return bucket


def upload_file(
    run_id: str,
    local_file_path: Union[str, Path],
    document_name: str,
    client: Optional[storage.Client] = None,
    bucket_name: Optional[str] = None,
) -> str:
    """Upload a local file to the bucket at path runs/{run_id}/{document_name}.
    
    Returns the storage object path (blob name).
    """
    local_path = Path(local_file_path)
    if not local_path.is_file():
        raise FileNotFoundError(f"Local file not found: {local_path}")

    cl = client or get_storage_client()
    b_name = get_bucket_name(bucket_name)
    bucket = _get_or_create_bucket(cl, b_name)

    blob_name = f"runs/{run_id}/{document_name}"
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(str(local_path))
    return blob_name


def download_file(
    run_id: str,
    document_name: str,
    destination_path: Union[str, Path],
    client: Optional[storage.Client] = None,
    bucket_name: Optional[str] = None,
) -> Path:
    """Download a file from runs/{run_id}/{document_name} to local destination_path.
    
    Returns the resolved destination Path.
    """
    dest = Path(destination_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    cl = client or get_storage_client()
    b_name = get_bucket_name(bucket_name)
    bucket = _get_or_create_bucket(cl, b_name)

    blob_name = f"runs/{run_id}/{document_name}"
    blob = bucket.blob(blob_name)
    if not blob.exists():
        raise FileNotFoundError(f"Object not found in bucket {b_name}: {blob_name}")

    blob.download_to_filename(str(dest))
    return dest


def list_run_files(
    run_id: str,
    client: Optional[storage.Client] = None,
    bucket_name: Optional[str] = None,
) -> List[str]:
    """List all files currently stored under runs/{run_id}/ in the bucket."""
    cl = client or get_storage_client()
    b_name = get_bucket_name(bucket_name)
    bucket = _get_or_create_bucket(cl, b_name)

    prefix = f"runs/{run_id}/"
    blobs = list(cl.list_blobs(bucket, prefix=prefix))

    # Emulator compatibility fallback: fake-gcs-server on Windows can fail prefix queries
    # containing forward slashes due to path separator handling.
    if not blobs:
        all_blobs = list(cl.list_blobs(bucket))
        blobs = [b for b in all_blobs if b.name.startswith(prefix)]

    return [b.name for b in blobs]


def delete_run_files(
    run_id: str,
    client: Optional[storage.Client] = None,
    bucket_name: Optional[str] = None,
) -> int:
    """Delete all files under runs/{run_id}/ in the bucket.
    
    Returns the number of deleted files.
    """
    cl = client or get_storage_client()
    b_name = get_bucket_name(bucket_name)
    bucket = _get_or_create_bucket(cl, b_name)

    file_names = list_run_files(run_id, client=cl, bucket_name=b_name)
    count = 0
    for name in file_names:
        blob = bucket.blob(name)
        if blob.exists():
            blob.delete()
            count += 1
    return count
