"""Утилиты для работы с файлами."""

import os


def read_text_file(file_path: str) -> str | None:
    """Прочитать содержимое текстового файла."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading text file {file_path}: {e}")
        return None


def read_file_data(file_path: str) -> str | None:
    """Вернуть текст для поддерживаемых форматов файлов."""
    ext = os.path.splitext(file_path.lower())[1]
    if ext in ('.txt', '.md'):
        return read_text_file(file_path)
    return None


def collect_file_paths(base_path: str) -> list[str]:
    """Собрать пути файлов из директории, игнорируя скрытые."""
    if os.path.isfile(base_path):
        return [base_path]
    file_paths: list[str] = []
    for root, _, files in os.walk(base_path):
        for name in files:
            if not name.startswith('.'):  # исключаем скрытые
                file_paths.append(os.path.join(root, name))
    return file_paths
