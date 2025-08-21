import os
import logging

from data_processing_common import extract_file_metadata, sanitize_filename
from file_utils import read_file_data

logger = logging.getLogger(__name__)

try:
    from error_handling import handle_model_error
except Exception:  # pragma: no cover - optional module
    handle_model_error = None

try:
    from openrouter_client import fetch_metadata_from_llm as _llm_fetch
    _LLM_SOURCE = "openrouter"
except Exception:
    _LLM_SOURCE = "local"


def extract_text(file_path: str) -> str:
    """Извлечь текст из файла, если возможно."""
    data = read_file_data(file_path)
    return data or ""


def process_text_file(file_path: str, log_file: str | None = None):
    """Извлечь текст, вызвать LLM и вернуть метаданные."""
    text = extract_text(file_path)
    file_meta = extract_file_metadata(file_path)

    try:
        ai_meta = _llm_fetch(text)
    except Exception as e:  # pragma: no cover - network errors
        response = getattr(e, "response", "")
        if handle_model_error:
            handle_model_error(file_path, str(e), response, log_file=log_file)
        else:
            msg = f"[docrouter] LLM error for {file_path}: {e} | response={response}"
            if log_file:
                try:
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(msg + "\n")
                except Exception:
                    pass
            logger.error(msg)
        return None

    return {
        "file_path": file_path,
        "text": text,
        "metadata": {"file": file_meta, "ai": ai_meta},
    }


def generate_text_metadata(input_text: str, file_path: str, precomputed_meta: dict | None = None):
    """Построить описание, папку и имя файла на основе AI-метаданных."""
    try:
        metadata = precomputed_meta if precomputed_meta is not None else _llm_fetch(input_text)
        for k in ["category", "subcategory", "issuer", "person", "doc_type", "date", "amount",
                  "tags", "suggested_filename", "notes"]:
            metadata.setdefault(k, "" if k != "tags" else [])
    except Exception:
        metadata = {
            "category": "Unsorted", "subcategory": "", "issuer": "", "person": "",
            "doc_type": "", "date": "", "amount": "", "tags": [],
            "suggested_filename": "", "notes": ""
        }

    description = (metadata.get("notes") or "").strip()
    if not description:
        description = summarize_text_content(input_text)

    parts = [metadata.get("category", ""), metadata.get("subcategory", ""),
             metadata.get("person") or metadata.get("issuer", "")]
    parts = [sanitize_filename(p, max_words=2) for p in parts if p]
    foldername = os.path.join(*parts) if parts else "Unsorted"

    suggested = metadata.get("suggested_filename") or os.path.splitext(os.path.basename(file_path))[0]
    filename = sanitize_filename(suggested, max_words=3)

    return foldername, filename, description, metadata


def safe_fetch_ai_metadata(text: str) -> dict:
    """Обёртка над _llm_fetch с дефолтами."""
    try:
        meta = _llm_fetch(text) or {}
    except Exception:
        meta = {}
    meta.setdefault("category", "Unsorted")
    meta.setdefault("subcategory", "")
    meta.setdefault("issuer", "")
    meta.setdefault("person", "")
    meta.setdefault("doc_type", "")
    meta.setdefault("date", "")
    meta.setdefault("amount", "")
    meta.setdefault("tags", [])
    meta.setdefault("suggested_filename", "")
    meta.setdefault("notes", "")
    return meta


def summarize_text_content(text: str) -> str:
    """Локальная эвристика: первые 2–3 «предложения», максимум ~150 слов."""
    if not text:
        return ""
    spl, buff = [], []
    for ch in text:
        buff.append(ch)
        if ch in ".!?":
            spl.append("".join(buff).strip())
            buff = []
    if buff:
        spl.append("".join(buff).strip())
    summary = " ".join(spl[:3]) if spl else text.strip().split("\n", 1)[0]
    words = summary.split()
    return " ".join(words[:150]) if len(words) > 150 else summary.strip()
