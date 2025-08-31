from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from error_handling import handle_error
from file_sorter import place_file
from file_utils import extract_text
import metadata_generation

logger = logging.getLogger(__name__)


async def process_directory(
    input_dir: str | Path, dest_root: str | Path, dry_run: bool = False
) -> None:
    """Асинхронно обработать все файлы из *input_dir* и разместить их под *dest_root*.

    Для каждого файла вызывается конвейер ``extract_text`` →
    ``metadata_generation.generate_metadata`` → ``place_file``. Любое исключение
    обрабатывается функцией :func:`handle_error`.
    """

    input_path = Path(input_dir)
    logger.info("Processing directory %s", input_path)

    async def process_file(path: Path) -> None:
        logger.info("Processing file %s", path)
        try:
            text = extract_text(path)
            meta_result = await metadata_generation.generate_metadata(text)
            raw_meta = meta_result["metadata"]
            if isinstance(raw_meta, dict):
                metadata = raw_meta
            else:
                metadata = raw_meta.model_dump()
            rel_dir = path.parent.relative_to(input_path)
            rel_parts = list(rel_dir.parts)
            if rel_parts and not metadata.get("category"):
                metadata["category"] = rel_parts[0]
            if len(rel_parts) > 1 and not metadata.get("subcategory"):
                metadata["subcategory"] = rel_parts[1]
            dest_base = Path(dest_root)
            dest_base.mkdir(parents=True, exist_ok=True)
            place_file(
                path,
                metadata,
                dest_base,
                dry_run=dry_run,
                needs_new_folder=True,
                confirm_callback=lambda _: True,
            )
            logger.info("Finished processing %s", path)
        except Exception as exc:  # pragma: no cover - depending on runtime errors
            handle_error(path, exc)
            logger.error("Failed to process %s: %s", path, exc)

    tasks = [process_file(path) for path in input_path.rglob("*") if path.is_file()]
    await asyncio.gather(*tasks)

