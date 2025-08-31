from __future__ import annotations

import json
from typing import Any, Dict, Optional


def build_metadata_prompt(
    text: str,
    *,
    folder_tree: Optional[Dict[str, Any]] = None,
    folder_index: Optional[Dict[str, Any]] = None,
    file_info: Optional[Dict[str, Any]] = None,
) -> str:
    """Сформировать промт для извлечения метаданных."""
    tree_json = json.dumps(folder_tree or {}, ensure_ascii=False)
    index_json = json.dumps(folder_index or {}, ensure_ascii=False)
    info = file_info or {}
    filename = info.get("name")
    extension = info.get("extension")
    size = info.get("size")
    file_type = info.get("type")

    return (
        "You are an assistant that extracts structured metadata from documents.\n"
        f"Original file name: {filename}\n"
        f"Extension: {extension}\n"
        f"Size: {size}\n"
        f"File type: {file_type}\n"
        "Possible document types include: contracts, receipts, notifications, advertisement.\n"
        "Existing folder tree (JSON):\n"
        f"{tree_json}\n"
        "Existing folders index (JSON):\n"
        f"{index_json}\n"
        "Если ни одна папка не подходит, предложи новую category/subcategory. \n"
        "Выбирай person/category строго из Existing folders index, если совпадение найдено; needs_new_folder=true только при полном отсутствии.\n"
        "Return a JSON object with the fields: category, subcategory, needs_new_folder (boolean), issuer, person, doc_type, "
        "date, amount, counterparty, document_number, due_date, currency, tags_ru (list of strings), tags_en (list of strings),"
        "suggested_filename, description.\n"
        "Field 'person' must be in the format 'Фамилия Имя Отчество'; do not use the person's name in category or subcategory.\n"
        f"Document text:\n{text}"
    )


__all__ = ["build_metadata_prompt"]

