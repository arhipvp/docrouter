import os
import shutil
from typing import Optional


def move_to_unsorted(file_path: str, unsorted_dir: Optional[str] = None) -> str:
    """Move the file to an "Unsorted" directory.

    Parameters
    ----------
    file_path: str
        Path of the file that caused an error.
    unsorted_dir: Optional[str]
        Directory to move the file into. If not provided, a folder named
        ``Unsorted`` will be created alongside the file.

    Returns
    -------
    str
        The destination path of the moved file.
    """
    base_dir = os.path.dirname(file_path)
    target_dir = unsorted_dir or os.path.join(base_dir, "Unsorted")
    os.makedirs(target_dir, exist_ok=True)
    destination = os.path.join(target_dir, os.path.basename(file_path))
    shutil.move(file_path, destination)
    return destination


def log_model_error(error_text: str, model_response: str, log_file: Optional[str] = None) -> None:
    """Log an error message and the model's original response.

    Parameters
    ----------
    error_text: str
        Description of the error encountered.
    model_response: str
        Raw response returned by the model.
    log_file: Optional[str]
        Path to the log file. If not provided, ``error_log.txt`` is used.
    """
    log_path = log_file or "error_log.txt"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"Error: {error_text}\n")
        f.write(f"Model response: {model_response}\n")
        f.write("-" * 40 + "\n")


def handle_model_error(file_path: str, error_text: str, model_response: str, *,
                        unsorted_dir: Optional[str] = None,
                        log_file: Optional[str] = None) -> str:
    """Move a problematic file to ``Unsorted`` and log the details.

    Parameters
    ----------
    file_path: str
        Path to the file being processed.
    error_text: str
        The text describing the encountered error.
    model_response: str
        The original response returned by the model.
    unsorted_dir: Optional[str]
        Directory where the file should be placed. By default, an
        ``Unsorted`` folder will be created next to the file.
    log_file: Optional[str]
        Log file path where the error should be recorded.

    Returns
    -------
    str
        The destination path of the moved file.
    """
    destination = move_to_unsorted(file_path, unsorted_dir)
    log_model_error(error_text, model_response, log_file)
    return destination
