from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

from error_handling import handle_error
from file_sorter import place_file, get_folder_tree
from file_utils import extract_text
from models import Metadata
from web_app import db as database
import metadata_generation

logger = logging.getLogger(__name__)


async def process_input_directory(
    input_dir: str | Path, dest_root: str | Path, dry_run: bool = False
) -> None:
    """Асинхронно обработать все файлы из *input_dir* и разместить их под *dest_root*.

    Логика перенесена из прежнего CLI-модуля ``docrouter`` и предназначена
    для использования внутри бэкенда или сервисов.
    """

    input_path = Path(input_dir)
    logger.info("Processing directory %s", input_path)

    tree, index = get_folder_tree(dest_root)

    async def process_file(path: Path) -> None:
        logger.info("Processing file %s", path)
        try:
            text = extract_text(path)
            try:
                meta_result = await metadata_generation.generate_metadata(
                    text, folder_tree=tree, folder_index=index
                )
            except TypeError:
                meta_result = await metadata_generation.generate_metadata(text)  # type: ignore[arg-type]
            raw_meta = meta_result["metadata"]
            if isinstance(raw_meta, dict):
                meta_dict = raw_meta
            else:
                meta_dict = raw_meta.model_dump()
            rel_dir = path.parent.relative_to(input_path)
            rel_parts = list(rel_dir.parts)
            if rel_parts and not meta_dict.get("category"):
                meta_dict["category"] = rel_parts[0]
            if len(rel_parts) > 1 and not meta_dict.get("subcategory"):
                meta_dict["subcategory"] = rel_parts[1]
            dest_base = Path(dest_root)
            dest_base.mkdir(parents=True, exist_ok=True)
            file_id = str(uuid.uuid4())

            dest_path, missing, confirmed = place_file(
                path,
                meta_dict,
                dest_base,
                dry_run=dry_run,
                needs_new_folder=True,
                confirm_callback=lambda _paths: False,
            )
            metadata_obj = Metadata(**meta_dict)
            if missing:
                database.add_file(
                    file_id,
                    path.name,
                    metadata_obj,
                    str(path),
                    "pending",
                    meta_result.get("prompt"),
                    meta_result.get("raw_response"),
                    missing,
                    suggested_path=str(dest_path),
                    confirmed=confirmed,
                    created_path=str(dest_path) if confirmed else None,
                )
                logger.warning("Pending %s due to missing %s", path, missing)
                return

            status = "dry_run" if dry_run else "processed"
            database.add_file(
                file_id,
                path.name,
                metadata_obj,
                str(dest_path),
                status,
                meta_result.get("prompt"),
                meta_result.get("raw_response"),
                [],
                suggested_path=str(dest_path),
                confirmed=confirmed,
                created_path=str(dest_path) if confirmed else None,
            )
            logger.info("Finished processing %s", path)
        except Exception as exc:  # pragma: no cover - depending on runtime errors
            handle_error(path, exc)
            logger.error("Failed to process %s: %s", path, exc)

    tasks = [process_file(path) for path in input_path.rglob("*") if path.is_file()]
    await asyncio.gather(*tasks)
