import os
import time
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn

# --- imports из обеих веток
from data_processing_common import sanitize_filename, extract_file_metadata

# Ошибки модели: опционально (ветка move-error-files-to-unsorted)
try:
    from error_handling import handle_model_error  # (file_path, error_str, response, log_file=None) -> None
except Exception:
    handle_model_error = None  # graceful fallback

# --- Параллельные запросы к LLM (ветка limit-parallel-requests-to-llm)
try:
    from llm_client import LLMClient  # ожидается интерфейс .generate_sync(prompt: str) -> str
except Exception:
    LLMClient = None

API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
MAX_CONCURRENCY = int(os.getenv("LLM_MAX_CONCURRENCY", "2"))
llm_client = LLMClient(API_KEY, MODEL, max_concurrent_requests=MAX_CONCURRENCY) if (LLMClient and API_KEY) else None

# Пытаемся использовать клиент OpenRouter; если его нет — fallback на локальный анализатор
try:
    from openrouter_client import fetch_metadata_from_llm as _llm_fetch  # ожидается совместимый JSON
    _LLM_SOURCE = "openrouter"
except Exception:
    _LLM_SOURCE = "local"

    def _llm_fetch(text: str) -> dict:
        """
        Fallback: используем analysis_module.analyze_text_with_llm(text)
        и приводим результат к унифицированной схеме AI-метаданных.
        """
        try:
            from analysis_module import analyze_text_with_llm
        except Exception as e:  # нет даже локального анализатора
            # Минимальный безопасный ответ
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

        raw = analyze_text_with_llm(text) or {}
        # Нормализуем ключи под единую схему
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


def process_single_text_file(args, silent: bool = False, log_file: str | None = None):
    """
    Обработать один текстовый файл и сгенерировать метаданные.

    args: tuple[str, str] -> (file_path, extracted_text)
    """
    file_path, text = args
    start_time = time.time()

    # 1) Файловые метаданные (локально)
    file_meta = extract_file_metadata(file_path)

    # 2) AI-метаданные (через OpenRouter или локальный фолбэк)
    ai_meta = safe_fetch_ai_metadata(text)

    # 3) Прогресс-бар и построение итоговых полей
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn()
    ) as progress:
        task_id = progress.add_task(f"Processing {os.path.basename(file_path)}", total=1.0)

        try:
            foldername, filename, description, ai_meta = generate_text_metadata(
                text,
                file_path,
                progress,
                task_id,
                precomputed_meta=ai_meta
            )
        except Exception as e:
            response = getattr(e, "response", "")
            if handle_model_error:
                handle_model_error(file_path, str(e), response, log_file=log_file)
            else:
                msg = f"[docrouter] LLM/metadata error for {file_path}: {e} | response={response}"
                if log_file:
                    try:
                        with open(log_file, "a", encoding="utf-8") as f:
                            f.write(msg + "\n")
                    except Exception:
                        pass
                else:
                    print(msg)
            return None  # прерываем обработку текущего файла

    time_taken = time.time() - start_time

    message = (
        f"File: {file_path}\n"
        f"Time taken: {time_taken:.2f} seconds\n"
        f"Description: {description}\n"
        f"Folder name: {foldername}\n"
        f"Generated filename: {filename}\n"
        f"AI Source: {_LLM_SOURCE}\n"
        f"File metadata: {file_meta}\n"
        f"AI metadata: {ai_meta}\n"
    )

    if silent:
        if log_file:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(message + '\n')
    else:
        print(message)

    return {
        "file_path": file_path,
        "foldername": foldername,
        "filename": filename,
        "description": description,
        "metadata": {
            "file": file_meta,
            "ai": ai_meta,
        },
    }


def process_text_files(text_tuples, silent: bool = False, log_file: str | None = None):
    """Последовательная обработка набора файлов."""
    results = []
    for args in text_tuples:
        data = process_single_text_file(args, silent=silent, log_file=log_file)
        if data is not None:  # пропускаем сбойные файлы (их обработал handle_model_error)
            results.append(data)
    return results


def generate_text_metadata(
    input_text: str,
    file_path: str,
    progress: Progress,
    task_id: int,
    precomputed_meta: dict | None = None
):
    """Minimal wrapper that relies on LLM for metadata generation."""
    total_steps = 2

    metadata = precomputed_meta if precomputed_meta is not None else _llm_fetch(input_text)
    progress.update(task_id, advance=1 / total_steps)

    description = (metadata.get("notes") or "").strip()
    filename = sanitize_filename(
        metadata.get("suggested_filename") or os.path.splitext(os.path.basename(file_path))[0],
        max_words=3,
    )
    foldername = sanitize_filename(metadata.get("category", "Unsorted"), max_words=2)

    progress.update(task_id, advance=1 / total_steps)

    return foldername, filename, description, metadata


# --- утилиты

def safe_fetch_ai_metadata(text: str) -> dict:
    """Тонкая обертка над _llm_fetch с дефолтами."""
    try:
        meta = _llm_fetch(text) or {}
    except Exception:
        meta = {}
    # Заполняем обязательные поля безопасными значениями
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
    """Попытаться получить краткое описание через LLMClient (ограничение параллелизма)."""
    if not llm_client:
        return ""
    try:
        prompt = (
            "Summarize the following text in no more than three sentences:\n"
            f"{input_text}"
        )
        out = llm_client.generate_sync(prompt) or ""
        # небольшой санитайзинг: обрезка до ~150 слов
        words = out.split()
        if len(words) > 150:
            out = " ".join(words[:150])
        return out.strip()
    except Exception:
        return ""


def summarize_text_content(text: str) -> str:
    """
    Быстрая локальная эвристика: первые 2–3 «предложения» (делим по .!?), максимум ~150 слов.
    Без внешних зависимостей (nltk не нужен).
    """
    if not text:
        return ""
    # приблизительное разбиение на предложения
    spl = []
    buff = []
    for ch in text:
        buff.append(ch)
        if ch in ".!?":
            spl.append("".join(buff).strip())
            buff = []
    if buff:
        spl.append("".join(buff).strip())

    summary = " ".join(spl[:3]) if spl else text.strip().split("\n", 1)[0]
    words = summary.split()
    if len(words) > 150:
        summary = " ".join(words[:150])
    return summary.strip()
