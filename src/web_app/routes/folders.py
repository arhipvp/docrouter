from __future__ import annotations

import shutil
from pathlib import Path

import logging
from fastapi import APIRouter, HTTPException

from file_sorter import get_folder_tree
from .. import server

router = APIRouter()
logger = logging.getLogger(__name__)


def _resolve_in_output(relative: str) -> Path:
    """Преобразовать относительный путь в путь внутри output_dir."""
    base = Path(server.config.output_dir).resolve()
    target = (base / relative).resolve()
    if not target.is_relative_to(base):
        raise HTTPException(status_code=400, detail="Path outside output_dir")
    return target


@router.get("/folder-tree")
async def folder_tree():
    """Вернуть структуру папок в выходном каталоге."""
    return get_folder_tree(server.config.output_dir)


@router.post("/folders")
async def create_folder(path: str):
    """Создать каталог внутри output_dir."""
    target = _resolve_in_output(path)
    if target.exists():
        raise HTTPException(status_code=409, detail="Folder already exists")
    target.mkdir(parents=True, exist_ok=False)
    return get_folder_tree(server.config.output_dir)


@router.patch("/folders/{folder_path:path}")
async def rename_folder(folder_path: str, new_name: str):
    src = _resolve_in_output(folder_path)
    if not src.exists():
        raise HTTPException(status_code=404, detail="Folder not found")
    dest_relative = str(Path(folder_path).parent / new_name)
    dest = _resolve_in_output(dest_relative)
    if dest.exists():
        raise HTTPException(status_code=409, detail="Target already exists")
    src.rename(dest)
    return get_folder_tree(server.config.output_dir)


@router.delete("/folders/{folder_path:path}")
async def delete_folder(folder_path: str):
    target = _resolve_in_output(folder_path)
    base = Path(server.config.output_dir).resolve()
    if target == base:
        raise HTTPException(status_code=400, detail="Cannot delete root folder")
    if not target.exists():
        raise HTTPException(status_code=404, detail="Folder not found")
    shutil.rmtree(target)
    return get_folder_tree(server.config.output_dir)
