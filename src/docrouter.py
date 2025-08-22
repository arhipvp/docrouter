from __future__ import annotations

from pathlib import Path
import logging

from file_utils import extract_text
import metadata_generation
from file_sorter import place_file

from error_handling import handle_error

logger = logging.getLogger(__name__)


def process_directory(input_dir: str | Path, dest_root: str | Path, dry_run: bool = False) -> None:
    """Process all files from *input_dir* and place them under *dest_root*.

    Each file is passed through the pipeline: ``extract_text`` →
    ``metadata_generation.generate_metadata`` → ``place_file``.  Any exception during processing is
    delegated to :func:`handle_error`.
    """
    input_path = Path(input_dir)
    logger.info("Processing directory %s", input_path)
    for path in input_path.rglob("*"):
        if not path.is_file():
            continue
        logger.info("Processing file %s", path)
        try:
            text = extract_text(path)
            metadata = metadata_generation.generate_metadata(text)
            rel_dir = path.parent.relative_to(input_path)
            dest_base = Path(dest_root) / rel_dir
            dest_base.mkdir(parents=True, exist_ok=True)
            place_file(path, metadata, dest_base, dry_run=dry_run)
            logger.info("Finished processing %s", path)
        except Exception as exc:  # pragma: no cover - depending on runtime errors
            handle_error(path, exc)
            logger.error("Failed to process %s: %s", path, exc)
