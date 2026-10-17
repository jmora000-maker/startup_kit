"""Integration tests for standalone Google Cloud Storage client against local fake-gcs-server emulator."""

import os
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
import pytest

from src.storage.gcs_client import (
    get_storage_client,
    get_bucket_name,
    upload_file,
    download_file,
    list_run_files,
    delete_run_files,
)

GCS_EMULATOR_HOST = os.environ.get("STORAGE_EMULATOR_HOST", "http://localhost:4443")


@pytest.fixture(scope="session", autouse=True)
def ensure_gcs_emulator():
    """Verify Cloud Storage emulator (fake-gcs-server) is reachable before executing tests."""
    os.environ["STORAGE_EMULATOR_HOST"] = GCS_EMULATOR_HOST
    url = f"{GCS_EMULATOR_HOST.rstrip('/')}/storage/v1/b"
    try:
        with urllib.request.urlopen(url, timeout=2.0) as resp:
            if resp.status != 200:
                pytest.fail(
                    f"Cloud Storage emulator returned status {resp.status} at {url}. "
                    "Start it with: .\\fake-gcs-server.exe -scheme http -port 4443"
                )
    except Exception as exc:
        pytest.fail(
            f"Cloud Storage emulator (fake-gcs-server) is not reachable at {url} ({exc}). "
            "Start it with: .\\fake-gcs-server.exe -scheme http -port 4443"
        )


def test_upload_download_list_delete_lifecycle(tmp_path):
    """Verify complete lifecycle: upload, list, download, and delete for run files."""
    run_id = f"test_run_gcs_lifecycle_{int(datetime.now(timezone.utc).timestamp())}"
    
    # 1. Prepare sample files
    doc1 = tmp_path / "startup_kit.docx"
    doc1.write_bytes(b"Sample DOCX binary payload for Startup Kit")
    
    doc2 = tmp_path / "delivery_workbook.xlsx"
    doc2.write_bytes(b"Sample XLSX binary payload for PMO Workbook")

    doc3 = tmp_path / "onboarding_deck.pptx"
    doc3.write_bytes(b"Sample PPTX binary payload for Deck")

    # 2. Upload files
    p1 = upload_file(run_id, doc1, "startup_kit.docx")
    p2 = upload_file(run_id, doc2, "delivery_workbook.xlsx")
    p3 = upload_file(run_id, doc3, "onboarding_deck.pptx")

    assert p1 == f"runs/{run_id}/startup_kit.docx"
    assert p2 == f"runs/{run_id}/delivery_workbook.xlsx"
    assert p3 == f"runs/{run_id}/onboarding_deck.pptx"

    # 3. List files
    files = list_run_files(run_id)
    assert len(files) == 3
    assert f"runs/{run_id}/startup_kit.docx" in files
    assert f"runs/{run_id}/delivery_workbook.xlsx" in files
    assert f"runs/{run_id}/onboarding_deck.pptx" in files

    # 4. Download files
    download_dir = tmp_path / "downloads"
    dest1 = download_dir / "downloaded_kit.docx"
    dest2 = download_dir / "downloaded_workbook.xlsx"

    download_file(run_id, "startup_kit.docx", dest1)
    download_file(run_id, "delivery_workbook.xlsx", dest2)

    assert dest1.exists()
    assert dest1.read_bytes() == b"Sample DOCX binary payload for Startup Kit"
    assert dest2.exists()
    assert dest2.read_bytes() == b"Sample XLSX binary payload for PMO Workbook"

    # 5. Delete files
    deleted_count = delete_run_files(run_id)
    assert deleted_count == 3

    # 6. Verify list is now empty
    files_after = list_run_files(run_id)
    assert files_after == []


def test_upload_missing_local_file_raises_error():
    """Verify upload_file raises FileNotFoundError if source file does not exist."""
    with pytest.raises(FileNotFoundError):
        upload_file("run_dummy", Path("non_existent_file_abc.docx"), "doc.docx")


def test_download_missing_object_raises_error(tmp_path):
    """Verify download_file raises FileNotFoundError if blob does not exist in bucket."""
    dest = tmp_path / "out.docx"
    with pytest.raises(FileNotFoundError):
        download_file("run_dummy", "non_existent_doc_12345.docx", dest)


def test_bucket_name_configuration(monkeypatch):
    """Verify bucket name is read from environment variable or override parameter."""
    monkeypatch.setenv("GCS_BUCKET_NAME", "custom-bucket-env")
    assert get_bucket_name() == "custom-bucket-env"
    assert get_bucket_name("explicit-override") == "explicit-override"
