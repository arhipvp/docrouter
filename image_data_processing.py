import os
import re
import time
from PIL import Image
import pytesseract
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn
from data_processing_common import sanitize_filename, extract_file_metadata
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
        foldername, filename, description = generate_image_metadata(image_path, progress, task_id)

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
        data_list.append(data)
    return data_list


def generate_image_metadata(image_path, progress, task_id):
    """Generate description, folder name, and filename for an image file."""

    # Total steps in processing an image
    total_steps = 3

    # Step 1: Generate description using file name
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    description = base_name.replace('_', ' ')
    progress.update(task_id, advance=1 / total_steps)

    # Remove any unwanted words and stopwords
    unwanted_words = set([
        'the', 'and', 'based', 'generated', 'this', 'is', 'filename', 'file', 'image', 'picture', 'photo',
        'folder', 'category', 'output', 'only', 'below', 'text', 'jpg', 'png', 'jpeg', 'gif', 'bmp', 'svg',
        'logo', 'in', 'on', 'of', 'with', 'by', 'for', 'to', 'from', 'a', 'an', 'as', 'at', 'red', 'blue',
        'green', 'color', 'colors', 'colored', 'text', 'graphic', 'graphics', 'main', 'subject', 'important',
        'details', 'description', 'depicts', 'show', 'shows', 'display', 'illustrates', 'presents', 'features',
        'provides', 'covers', 'includes', 'demonstrates', 'describes'
    ])
    stop_words = set(stopwords.words('english'))
    all_unwanted_words = unwanted_words.union(stop_words)
    lemmatizer = WordNetLemmatizer()

    # Function to clean and process text
    def clean_text(text, max_words):
        # Remove file extensions and special characters
        text = re.sub(r'\.\w{1,4}$', '', text)  # Remove file extensions like .jpg, .png
        text = re.sub(r'[^\w\s]', ' ', text)  # Remove special characters
        text = re.sub(r'\d+', '', text)  # Remove digits
        text = text.strip()
        # Split concatenated words (e.g., 'GoogleChrome' -> 'Google Chrome')
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        # Tokenize and lemmatize words
        words = word_tokenize(text)
        words = [word.lower() for word in words if word.isalpha()]
        words = [lemmatizer.lemmatize(word) for word in words]
        # Remove unwanted words and duplicates
        filtered_words = []
        seen = set()
        for word in words:
            if word not in all_unwanted_words and word not in seen:
                filtered_words.append(word)
                seen.add(word)
        # Limit to max words
        filtered_words = filtered_words[:max_words]
        return '_'.join(filtered_words)

    # Step 2: Generate filename
    filename = clean_text(base_name, max_words=3)
    if not filename:
        filename = 'image_' + base_name
    sanitized_filename = sanitize_filename(filename, max_words=3)
    progress.update(task_id, advance=1 / total_steps)

    # Step 3: Generate folder name
    foldername = clean_text(base_name, max_words=2)
    if not foldername:
        foldername = 'images'
    sanitized_foldername = sanitize_filename(foldername, max_words=2)
    progress.update(task_id, advance=1 / total_steps)

    return sanitized_foldername, sanitized_filename, description
