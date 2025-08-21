from __future__ import annotations
from pathlib import Path
from typing import Dict


def generate_metadata(file_path: str) -> Dict[str, str]:
    """Generate basic metadata for a file.

    Currently returns a minimal metadata dictionary with the file name.
    """
    path = Path(file_path)
    return {
        "file_name": path.name,
        "status": "processed",
    }
