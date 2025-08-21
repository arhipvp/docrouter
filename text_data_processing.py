import os
import time
import logging

from data_processing_common import sanitize_filename, extract_file_metadata
from config_loader import load_config, load_openrouter_settings

# Логгер
logger = logging.getLogger(__name__)

# Опциональный обработчик ошибок
try:
    from error_handling import handle_model_error
except Exception:
    handle_model_error = None

# Опциональный клиент LLM
try:
    from llm_client import LLMClient
except Exception:
    LLMClient = None

CONFIG = load_config()
OR_SETTINGS = load_openrouter_settings()
API_KEY = OR_SETTINGS.get("api_key")
MODEL = OR_SETTINGS.get("model")
MAX_CONCURRENCY = OR_SETTINGS.get("max_concurrency", 2)
llm_client = (
    LLMClient(API_KEY, MODEL, max_concurrent_requests=MAX_CONCURRENCY)
    if (LLMClient and API_KEY)
    else None
)

# Источник AI-метаданных: OpenRouter или локальный анализатор
try:
    from openrouter_client import fetch_metadata_from_llm as _llm_fetch
    _LLM_SOURCE = "openrouter"
except Exception:
    _LLM_SOURCE = "local"

    def _llm_fetch(text: str) -> dict:
        try:
            from analysis_module import analyze_text_with_llm
            raw = analyze_text_with_llm(text) or {}
            return {
                "category": raw.get("category") or raw.get("cat") or "Unsorted",
                "subcategory": raw.get("subcategory", ""),
                "issuer": raw.get("issuer") or raw.get("vendor", ""),
                "person": raw.get("person", ""),
                "doc_type": raw.get("doc_type") or raw.get("type", ""),
                "date": raw.get("date", ""),
                "amount": raw.get("amount", ""),
                "tags": raw.get("tags", []) or [],
                "suggested_filename": raw.get("suggested_filename", ""),
                "notes": raw.get("notes") or raw.get("summary", "") or ""
            }
        except Exception as e:
            return {
                "category": "Unsorted",
                "subcategory": "",
                "issuer": "",
                "person": "",
                "doc_type": "",
                "date": "",
                "amount": "",
                "tags": [],
                "suggested_filename": "",
                "notes": f"no analyzer available: {e}"
            }


def process_single_text_file(args, silent: bool = False, log_file: str | None = None):
    """Обработать один текстовый файл и сгенерировать метаданные."""
    file_path, text = args
    start_time = time.time()

    file_meta = extract_file_metadata(file_path)
    ai_meta = safe_fetch_ai_metadata(text)

    try:
        foldername, filename, description, ai_meta = generate_text_metadata(
            text, file_path, precomputed_meta=ai_meta
        )
    except Exception as e:
        response = getattr(e, "response", "")
        msg = f"[docrouter] LLM/metadata error for {file_path}: {e} | response={response}"
        if handle_model_error:
            handle_model_error(file_path, str(e), response, log_file=log_file)
        else:
            if log_file:
                try:
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(msg + "\n")
                except Exception:
                    pass
            if not silent:
                logger.error(msg)
        return None

    time_taken = time.time() - start_time
    summary = f"{file_path} -> {foldername}/{filename} ({time_taken:.2f}s, source={_LLM_SOURCE})"

    if log_file:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(summary + '\n')
    if not silent:
        logger.info(summary)

    return {
        "file_path": file_path,
        "foldername": foldername,
        "filename": filename,
        "description": description,
        "metadata": {"file": file_meta, "ai": ai_meta},
    }


def process_text_files(text_tuples, silent: bool = False, log_file: str | None = None):
    """Последовательная обработка набора файлов."""
    results = []
    for args in text_tuples:
        data = process_single_text_file(args, silent=silent, log_file=log_file)
        if data is not None:
            results.append(data)
    return results


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
            "doc_type": "", "date": "", "amount": "", "tags": [], "suggested_filename": "", "notes": ""
        }

    description = (metadata.get("notes") or "").strip()
    if not description:
        description = try_summarize_with_client(input_text) or summarize_text_content(input_text)

    parts = [metadata.get("category", ""), metadata.get("subcategory", ""),
             metadata.get("person") or metadata.get("issuer", "")]
    parts = [sanitize_filename(p, max_words=2) for p in parts if p]
    foldername = os.path.join(*parts) if parts else "Unsorted"

    suggested = metadata.get("suggested_filename") or os.path.splitext(os.path.basename(file_path))[0]
    filename = sanitize_filename(suggested, max_words=3)

    return foldername, filename, description, metadata


# --- утилиты

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


def try_summarize_with_client(input_text: str) -> str:
    """Краткое описание через LLMClient (если доступен)."""
    if not llm_client:
        return ""
    try:
        prompt = "Summarize the following text in no more than three sentences:\n" + input_text
        out = (llm_client.generate_sync(prompt) or "").strip()
        words = out.split()
        return " ".join(words[:150]) if len(words) > 150 else out
    except Exception:
        return ""


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
