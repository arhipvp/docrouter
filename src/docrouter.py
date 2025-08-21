from __future__ import annotations

from pathlib import Path

from file_utils import extract_text
from generate_metadata import generate_metadata
from file_sorter import place_file

from error_handling import handle_error


def process_directory(input_dir: str | Path, dest_root: str | Path, dry_run: bool = False) -> None:
    """Process all files from *input_dir* and place them under *dest_root*.

    Each file is passed through the pipeline: ``extract_text`` →
    ``generate_metadata`` → ``place_file``.  Any exception during processing is
    delegated to :func:`handle_error`.
    """
    input_path = Path(input_dir)
    for path in input_path.iterdir():
        if not path.is_file():
            continue
        try:
            text = extract_text(path)
            metadata = generate_metadata(text)
            place_file(path, metadata, dest_root, dry_run=dry_run)
        except Exception as exc:  # pragma: no cover - depending on runtime errors
            handle_error(path, exc)
