from __future__ import annotations
import os
from pathlib import Path
from typing import Dict


def sort_file(file_path: str, metadata: Dict[str, str], dry_run: bool = False) -> str:
    """Return the target path where the file would be moved.

    When ``dry_run`` is False, the file is actually moved to the new location.
    """
    base_dir = Path("sorted")
    base_dir.mkdir(parents=True, exist_ok=True)
    target_path = base_dir / metadata["file_name"]
    if not dry_run:
        os.replace(file_path, target_path)
    return str(target_path)
