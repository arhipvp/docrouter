from pathlib import Path
from typing import Any, List

from fastapi import APIRouter, HTTPException

from file_sorter import get_folder_tree
from .. import server

router = APIRouter()


def _resolve_in_output(relative: str) -> Path:
    """Преобразовать относительный путь в путь внутри ``output_dir``."""
    base = Path(server.config.output_dir).resolve()
    target = (base / relative).resolve()
    if not target.is_relative_to(base):
        raise HTTPException(status_code=400, detail="Path outside output_dir")
    return target


@router.get("/folder-tree")
async def folder_tree() -> List[dict[str, Any]]:
    """Вернуть дерево вида ``[{name, children}]`` в выходном каталоге."""
    tree, _ = get_folder_tree(server.config.output_dir)
    return tree

