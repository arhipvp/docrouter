import os
import time
from PIL import Image
import pytesseract
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn

from data_processing_common import sanitize_filename, extract_file_metadata
from error_handling import handle_model_error
from analysis_module import analyze_text_with_llm



def process_single_image(image_path, silent=False, log_file=None):
    """Process a single image file to generate metadata."""
    start_time = time.time()

    # Extract text using OCR
    with Image.open(image_path) as img:
        extracted_text = pytesseract.image_to_string(img)

    # Analyze text with LLM
    analysis = analyze_text_with_llm(extracted_text)

    # Get file metadata
    metadata = extract_file_metadata(image_path)

    # Create a Progress instance for this file
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn()
    ) as progress:
        task_id = progress.add_task(f"Processing {os.path.basename(image_path)}", total=1.0)
        try:
            foldername, filename, description = generate_image_metadata(image_path, progress, task_id)
        except Exception as e:
            response = getattr(e, 'response', '')
            handle_model_error(image_path, str(e), response, log_file=log_file)
            return None

    end_time = time.time()
    time_taken = end_time - start_time

    message = (
        f"File: {image_path}\nTime taken: {time_taken:.2f} seconds\n"
        f"Description: {description}\nFolder name: {foldername}\n"
        f"Generated filename: {filename}\n"
        f"Metadata: {metadata}\n"
        f"Analysis: {analysis}\n"
    )
    if silent:
        if log_file:
            with open(log_file, 'a') as f:
                f.write(message + '\n')
    else:
        print(message)
    return {
        'file_path': image_path,
        'foldername': foldername,
        'filename': filename,
        'description': description,
        'text': extracted_text,
        'analysis': analysis,
        'metadata': metadata,
    }


def process_image_files(image_paths, silent=False, log_file=None):
    """Process image files sequentially."""
    data_list = []
    for image_path in image_paths:
        data = process_single_image(image_path, silent=silent, log_file=log_file)
        if data is not None:
            data_list.append(data)
    return data_list


def generate_image_metadata(image_path, progress, task_id):
    """Placeholder wrapper for OCR/LLM-based metadata generation."""

    # Future implementation: use OCR text and an LLM to derive these values.
    progress.update(task_id, advance=1)

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    filename = sanitize_filename(base_name, max_words=3)
    foldername = "images"
    description = ""

    return foldername, filename, description
