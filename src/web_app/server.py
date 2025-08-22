from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, File, HTTPException, Request, UploadFile

from config import load_config
from file_utils import extract_text
from file_sorter import place_file
import metadata_generation

app = FastAPI()

# Load configuration and set up logging
config = load_config()
logging.basicConfig(level=getattr(logging, config.log_level.upper(), logging.INFO))


# In-memory store for metadata
METADATA_STORE: Dict[str, Dict[str, Any]] = {}

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), dry_run: bool = False):
    """Upload a file and process it."""
    file_id = str(uuid.uuid4())
    temp_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
    try:
        contents = await file.read()
        with open(temp_path, "wb") as dest:
            dest.write(contents)

        text = extract_text(temp_path, language=config.tesseract_lang)
        metadata = metadata_generation.generate_metadata(text)
        metadata["extracted_text"] = text

        dest_path = place_file(str(temp_path), metadata, config.output_dir, dry_run=dry_run)
    except Exception as exc:  # pragma: no cover - error handling
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    status = "dry_run" if dry_run else "processed"
    stored_metadata = {**metadata, "path": str(dest_path)}
    METADATA_STORE[file_id] = stored_metadata
    return {
        "id": file_id,
        "metadata": stored_metadata,
        "path": str(dest_path),
        "status": status,
    }


@app.get("/metadata/{file_id}")
async def get_metadata(file_id: str):
    """Retrieve stored metadata by file ID."""
    data = METADATA_STORE.get(file_id)
    if not data:
        raise HTTPException(status_code=404, detail="Metadata not found")
    return data


@app.get("/files")
async def list_files(request: Request):
    """Return all files with optional metadata filtering."""
    filters = dict(request.query_params)
    items = []
    for file_id, metadata in METADATA_STORE.items():
        if all(str(metadata.get(k)) == v for k, v in filters.items()):
            filename = Path(metadata.get("path", "")).name
            items.append({"id": file_id, "filename": filename, "metadata": metadata})
    return items
