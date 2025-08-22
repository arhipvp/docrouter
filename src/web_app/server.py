from __future__ import annotations

import uuid
from pathlib import Path

from typing import Dict, Any
import logging

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import load_config
from logging_config import setup_logging
from file_utils import extract_text
import metadata_generation
from file_sorter import place_file
from . import database

app = FastAPI()

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/")
async def serve_index() -> FileResponse:
    """Serve the upload form."""
    return FileResponse(Path(__file__).parent / "static" / "index.html")

# Load configuration and set up logging
config = load_config()


logging.basicConfig(level=getattr(logging, config.log_level.upper(), logging.INFO))


# Initialize database and uploads directory
database.init_db()
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
    database.add_file(file_id, metadata, str(dest_path), status)
    return {"id": file_id, "metadata": metadata, "path": str(dest_path), "status": status}


@app.get("/metadata/{file_id}")
async def get_metadata(file_id: str):
    """Retrieve stored metadata by file ID."""
    record = database.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="Metadata not found")
    return record["metadata"]
