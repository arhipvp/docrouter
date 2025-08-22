import asyncio
import os
import sys
from io import BytesIO

from fastapi import UploadFile
from starlette.requests import Request

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from web_app.server import METADATA_STORE, get_metadata, list_files, upload_file  # noqa: E402


def test_upload_and_retrieve_metadata():
    METADATA_STORE.clear()
    file = UploadFile(filename="example.txt", file=BytesIO(b"content"))
    data = asyncio.run(upload_file(file, dry_run=True))
    assert set(["id", "metadata", "path", "status"]).issubset(data.keys())
    file_id = data["id"]
    assert data["status"] == "dry_run"
    assert data["metadata"]["extracted_text"].strip() == "content"
    assert data["metadata"]["path"] == data["path"]

    data2 = asyncio.run(get_metadata(file_id))
    assert data2 == data["metadata"]


def test_list_files_with_filter():
    METADATA_STORE.clear()
    file1 = UploadFile(filename="f1.txt", file=BytesIO(b"2023-10-12 amount 100"))
    file2 = UploadFile(filename="f2.txt", file=BytesIO(b"2023-10-13 amount 200"))

    data1 = asyncio.run(upload_file(file1, dry_run=True))
    data2 = asyncio.run(upload_file(file2, dry_run=True))

    request_all = Request({"type": "http", "query_string": b""})
    items = asyncio.run(list_files(request_all))
    ids = {item["id"] for item in items}
    assert {data1["id"], data2["id"]} <= ids

    request_filter = Request({"type": "http", "query_string": b"date=2023-10-12"})
    filtered = asyncio.run(list_files(request_filter))
    assert len(filtered) == 1
    assert filtered[0]["id"] == data1["id"]
