from __future__ import annotations
import uuid
from pathlib import Path
from typing import Tuple, Dict
from generate_metadata import generate_metadata
from file_sorter import sort_file

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def process_file(upload_file, dry_run: bool = False) -> Tuple[str, Dict[str, str], str, str]:
    """Save the uploaded file, generate metadata and sort it.

    Returns a tuple of ``(file_id, metadata, target_path, status)``.
    """
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}_{upload_file.filename}"
    with open(file_path, "wb") as dest:
        dest.write(upload_file.file.read())
    metadata = generate_metadata(str(file_path))
    target_path = sort_file(str(file_path), metadata, dry_run=dry_run)
    status = "dry_run" if dry_run else "processed"
    return file_id, metadata, target_path, status
