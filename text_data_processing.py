import logging

from data_processing_common import extract_file_metadata
from file_utils import read_file_data

try:
    from error_handling import handle_model_error
except Exception:  # pragma: no cover - optional module
    handle_model_error = None

from openrouter_client import fetch_metadata_from_llm

logger = logging.getLogger(__name__)


def extract_text(file_path: str) -> str:
    """Извлечь текст из файла, если возможно."""
    data = read_file_data(file_path)
    return data or ""


def process_text_file(file_path: str, log_file: str | None = None):
    """Извлечь текст, вызвать LLM и вернуть метаданные."""
    text = extract_text(file_path)
    file_meta = extract_file_metadata(file_path)

    try:
        ai_meta = fetch_metadata_from_llm(text)
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

