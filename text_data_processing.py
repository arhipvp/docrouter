import os
import time
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn

# --- imports из обеих веток
from data_processing_common import sanitize_filename, extract_file_metadata

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
        foldername, filename, description, ai_meta = generate_text_metadata(
            text,
            file_path,
            progress,
            task_id,
            precomputed_meta=ai_meta
        )

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
        results.append(data)
    return results


def generate_text_metadata(
    input_text: str,
    file_path: str,
    progress: Progress,
    task_id: int,
    precomputed_meta: dict | None = None
):
    """
    Построить описание, папку и имя файла на основе AI-метаданных.
    Если precomputed_meta не передан — вызовет _llm_fetch(input_text).
    """
    total_steps = 2

    # 1) Получаем AI-метаданные
    try:
        metadata = precomputed_meta if precomputed_meta is not None else _llm_fetch(input_text)
        # Гарантируем наличие ключей
        for k in ["category", "subcategory", "issuer", "person", "doc_type", "date", "amount", "tags", "suggested_filename", "notes"]:
            metadata.setdefault(k, "" if k != "tags" else [])
    except Exception:
        metadata = {
            "category": "Unsorted",
            "subcategory": "",
            "issuer": "",
            "person": "",
            "doc_type": "",
            "date": "",
            "amount": "",
            "tags": [],
            "suggested_filename": "",
            "notes": ""
        }
    progress.update(task_id, advance=1 / total_steps)

    # 2) Папка
    parts = [
        metadata.get("category", ""),
        metadata.get("subcategory", ""),
        metadata.get("person") or metadata.get("issuer", ""),
    ]
    parts = [sanitize_filename(p, max_words=2) for p in parts if p]
    foldername = os.path.join(*parts) if parts else "Unsorted"

    # 3) Имя файла
    suggested = metadata.get("suggested_filename")
    if not suggested:
        # если ИИ не предложил имя — берем исходное без расширения
        suggested = os.path.splitext(os.path.basename(file_path))[0]
    filename = sanitize_filename(suggested, max_words=3)

    description = metadata.get("notes", "")
    progress.update(task_id, advance=1 / total_steps)

    return foldername, filename, description, metadata


# --- утилита
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
