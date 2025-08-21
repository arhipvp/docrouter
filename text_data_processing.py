import os
import time
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn
from data_processing_common import sanitize_filename
from openrouter_client import fetch_metadata_from_llm

def process_single_text_file(args, silent=False, log_file=None):
    """Process a single text file to generate metadata."""
    file_path, text = args
    start_time = time.time()

    # Create a Progress instance for this file
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn()
    ) as progress:
        task_id = progress.add_task(f"Processing {os.path.basename(file_path)}", total=1.0)
        foldername, filename, description, metadata = generate_text_metadata(text, file_path, progress, task_id)

    end_time = time.time()
    time_taken = end_time - start_time

    message = (
        f"File: {file_path}\nTime taken: {time_taken:.2f} seconds\n"
        f"Description: {description}\nFolder name: {foldername}\nGenerated filename: {filename}\n"
    )
    if silent:
        if log_file:
            with open(log_file, 'a') as f:
                f.write(message + '\n')
    else:
        print(message)
    return {
        'file_path': file_path,
        'foldername': foldername,
        'filename': filename,
        'description': description,
        'metadata': metadata,
    }

def process_text_files(text_tuples, silent=False, log_file=None):
    """Process text files sequentially."""
    results = []
    for args in text_tuples:
        data = process_single_text_file(args, silent=silent, log_file=log_file)
        results.append(data)
    return results

def generate_text_metadata(input_text, file_path, progress, task_id):
    """Generate description, folder name, and filename for a text document using LLM."""

    # Total steps: 2 (LLM call and sanitization)
    total_steps = 2

    try:
        metadata = fetch_metadata_from_llm(input_text)
    except Exception:
        metadata = {field: '' for field in ['category', 'subcategory', 'issuer', 'person', 'suggested_filename', 'note']}
        metadata['category'] = 'Unsorted'
    progress.update(task_id, advance=1 / total_steps)

    # Build folder structure
    parts = [
        metadata.get('category', ''),
        metadata.get('subcategory', ''),
        metadata.get('person') or metadata.get('issuer', ''),
    ]
    parts = [sanitize_filename(p, max_words=2) for p in parts if p]
    foldername = os.path.join(*parts) if parts else 'Unsorted'

    # Build filename
    suggested = metadata.get('suggested_filename')
    if not suggested:
        suggested = os.path.splitext(os.path.basename(file_path))[0]
    filename = sanitize_filename(suggested, max_words=3)

    description = metadata.get('note', '')
    progress.update(task_id, advance=1 / total_steps)

    return foldername, filename, description, metadata
