import os
import fitz  # PyMuPDF
import docx


def read_text_file(file_path: str) -> str | None:
    """Прочитать содержимое текстового файла (ограничение по длине для скорости)."""
    max_chars = 3000
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read(max_chars)
    except Exception as e:
        print(f"Error reading text file {file_path}: {e}")
        return None


def read_docx_file(file_path: str) -> str | None:
    """Прочитать текст из .docx/.doc (через python-docx)."""
    try:
        doc = docx.Document(file_path)
        return '\n'.join(p.text for p in doc.paragraphs)
    except Exception as e:
        print(f"Error reading DOCX file {file_path}: {e}")
        return None


def read_pdf_file(file_path: str) -> str | None:
    """Прочитать текст из первых страниц PDF (через PyMuPDF)."""
    try:
        doc = fitz.open(file_path)
        num_pages_to_read = 3  # можно настроить
        pages = []
        for i in range(min(num_pages_to_read, len(doc))):
            page = doc.load_page(i)
            pages.append(page.get_text())
        return '\n'.join(pages)
    except Exception as e:
        print(f"Error reading PDF file {file_path}: {e}")
        return None


def read_file_data(file_path: str) -> str | None:
    """Выбрать способ чтения по расширению файла и вернуть текст."""
    ext = os.path.splitext(file_path.lower())[1]
    if ext in ('.txt', '.md', '.csv'):
        return read_text_file(file_path)
    if ext in ('.docx', '.doc'):
        return read_docx_file(file_path)
    if ext == '.pdf':
        return read_pdf_file(file_path)
    return None  # Неподдерживаемый тип


def collect_file_paths(base_path: str) -> list[str]:
    """Собрать все пути файлов из директории (или вернуть один путь), игнорируя скрытые файлы."""
    if os.path.isfile(base_path):
        return [base_path]
    file_paths: list[str] = []
    for root, _, files in os.walk(base_path):
        for name in files:
            if not name.startswith('.'):  # исключаем скрытые
                file_paths.append(os.path.join(root, name))
    return file_paths
