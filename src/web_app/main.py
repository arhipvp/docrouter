from __future__ import annotations
from fastapi import FastAPI, UploadFile, File, HTTPException
from file_utils import process_file
from typing import Dict, Any

app = FastAPI()

FILE_STORE: Dict[str, Dict[str, Any]] = {}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), dry_run: bool = False):
    file_id, metadata, target_path, status = process_file(file, dry_run=dry_run)
    FILE_STORE[file_id] = {"metadata": metadata, "status": status, "path": target_path}
    return {"file_id": file_id, "metadata": metadata, "path": target_path, "status": status}


@app.get("/files/{file_id}")
async def get_file(file_id: str):
    data = FILE_STORE.get(file_id)
    if not data:
        raise HTTPException(status_code=404, detail="File not found")
    return data
