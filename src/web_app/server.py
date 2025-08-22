from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os
import secrets

from config import load_config
from file_utils import extract_text
import metadata_generation
from file_sorter import place_file

app = FastAPI()

security = HTTPBasic()


def check_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Проверить учетные данные из HTTP Basic auth."""
    user = os.getenv("DOCROUTER_USER", "")
    password = os.getenv("DOCROUTER_PASS", "")
    valid_user = secrets.compare_digest(credentials.username, user)
    valid_pass = secrets.compare_digest(credentials.password, password)
    if not (valid_user and valid_pass):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Load configuration
config = load_config()
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))

# In-memory store for metadata and file paths
METADATA_STORE: Dict[str, Dict[str, Any]] = {}

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    dry_run: bool = False,
    _: str = Depends(check_credentials),
):
    """Upload a file and process it."""
    file_id = str(uuid.uuid4())
    temp_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
    try:
        contents = await file.read()
        with open(temp_path, "wb") as dest:
            dest.write(contents)

        text = extract_text(temp_path, language=config.TESSERACT_LANG)
        metadata = metadata_generation.generate_metadata(text)
        metadata["extracted_text"] = text

        dest_path = place_file(str(temp_path), metadata, config.OUTPUT_DIR, dry_run=dry_run)
    except Exception as exc:  # pragma: no cover - error handling
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    status = "dry_run" if dry_run else "processed"
    METADATA_STORE[file_id] = {"metadata": metadata, "path": str(dest_path)}
    return {
        "id": file_id,
        "metadata": metadata,
        "path": str(dest_path),
        "status": status,
    }


@app.get("/metadata/{file_id}")
async def get_metadata(file_id: str, _: str = Depends(check_credentials)):
    """Retrieve stored metadata by file ID."""
    data = METADATA_STORE.get(file_id)
    if not data:
        raise HTTPException(status_code=404, detail="Metadata not found")
    return data["metadata"]


@app.get("/files")
async def list_files(_: str = Depends(check_credentials)):
    """List all stored files with their metadata."""
    return [{"id": fid, "metadata": d["metadata"]} for fid, d in METADATA_STORE.items()]


@app.get("/download/{file_id}")
async def download_file(file_id: str, _: str = Depends(check_credentials)):
    """Download processed file by ID."""
    data = METADATA_STORE.get(file_id)
    if not data:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(data.get("path", ""))
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=path.name)
