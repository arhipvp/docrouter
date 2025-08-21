import os
import re
import json
import logging

def sanitize_filename(name, max_length=50, max_words=5):
    """Sanitize the filename by removing unwanted words and characters."""
    # Remove file extension if present
    name = os.path.splitext(name)[0]
    # Remove unwanted words and data type words
    name = re.sub(
        r'\b(jpg|jpeg|png|gif|bmp|txt|md|pdf|docx|xls|xlsx|csv|ppt|pptx|image|picture|photo|this|that|these|those|here|there|'
        r'please|note|additional|notes|folder|name|sure|heres|a|an|the|and|of|in|'
        r'to|for|on|with|your|answer|should|be|only|summary|summarize|text|category)\b',
        '',
        name,
        flags=re.IGNORECASE
    )
    # Remove non-word characters except underscores
    sanitized = re.sub(r'[^\w\s]', '', name).strip()
    # Replace multiple underscores or spaces with a single underscore
    sanitized = re.sub(r'[\s_]+', '_', sanitized)
    # Convert to lowercase
    sanitized = sanitized.lower()
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    # Split into words and limit the number of words
    words = sanitized.split('_')
    limited_words = [word for word in words if word]  # Remove empty strings
    limited_words = limited_words[:max_words]
    limited_name = '_'.join(limited_words)
    # Limit length
    return limited_name[:max_length] if limited_name else 'untitled'

def build_storage_path(info, original_path, base_path="Archive", dry_run=False, logger=None):
    """Сформировать путь для сохранения файла по данным LLM."""
    category = info.get("category") or "Unsorted"
    subcategory = info.get("subcategory") or "General"
    org = info.get("person") or info.get("issuer") or "Unknown"
    filename = info.get("suggested_filename") or os.path.splitext(os.path.basename(original_path))[0]
    filename = sanitize_filename(filename)
    date_part = info.get("date")
    if date_part:
        filename = f"{date_part}__{filename}"
    ext = os.path.splitext(original_path)[1]
    dest_dir = os.path.join(base_path, category, subcategory, org)
    dest_file = os.path.join(dest_dir, f"{filename}{ext}")
    if logger:
        logger.info("Построен путь %s", dest_file)
    if dry_run:
        if logger:
            logger.info("Dry-run: каталог %s не создаётся", dest_dir)
    else:
        os.makedirs(dest_dir, exist_ok=True)
    return dest_file


def write_metadata(dest_file, info, file_meta=None, dry_run=False, logger=None):
    """Записать метаданные в JSON рядом с файлом."""
    meta_path = dest_file + ".json"
    data = {"llm": info}
    if file_meta is not None:
        data["file"] = file_meta
    if dry_run:
        if logger:
            logger.info("Dry-run: метаданные %s не записываются", meta_path)
        return meta_path
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    if logger:
        logger.info("Метаданные записаны в %s", meta_path)
    return meta_path
