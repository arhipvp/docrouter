from pathlib import Path

from fastapi import APIRouter, HTTPException

from file_sorter import get_folder_tree
from .. import server, db as database

router = APIRouter()


def _resolve_in_output(relative: str) -> Path:
    """Преобразовать относительный путь в путь внутри ``output_dir``."""
    base = Path(server.config.output_dir).resolve()
    target = (base / relative).resolve()
    if not target.is_relative_to(base):
        raise HTTPException(status_code=400, detail="Path outside output_dir")
    return target


@router.get("/folder-tree")
async def folder_tree():
    """Вернуть структуру папок и файлов в выходном каталоге."""
    tree, _ = get_folder_tree(server.config.output_dir)

    # Сопоставим пути файлов с их идентификаторами из БД, чтобы на фронте
    # можно было обращаться к существующим маршрутам просмотра/скачивания.
    id_map = {Path(rec.path).resolve(): rec.id for rec in database.list_files()}

    def attach_ids(nodes):
        for node in nodes:
            for f in node.get("files", []):
                fid = id_map.get(Path(server.config.output_dir) / f["path"])
                if fid:
                    f["id"] = fid
            attach_ids(node.get("children", []))

    attach_ids(tree)
    return tree

