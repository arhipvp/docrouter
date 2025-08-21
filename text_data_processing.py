import re
import os
import time
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn
from data_processing_common import sanitize_filename, extract_file_metadata
from analysis_module import analyze_text_with_llm


def summarize_text_content(text):
    """Summarize the given text content using simple heuristics."""
    sentences = sent_tokenize(text)
    summary = " ".join(sentences[:3])
    words = summary.split()
    if len(words) > 150:
        summary = " ".join(words[:150])
    return summary

def process_single_text_file(args, silent=False, log_file=None):
    """Process a single text file to generate metadata."""
    file_path, text = args
    start_time = time.time()

    # Analyze text with LLM and gather metadata
    analysis = analyze_text_with_llm(text)
    metadata = extract_file_metadata(file_path)

    # Create a Progress instance for this file
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn()
    ) as progress:
        task_id = progress.add_task(f"Processing {os.path.basename(file_path)}", total=1.0)
        foldername, filename, description = generate_text_metadata(text, file_path, progress, task_id)

    end_time = time.time()
    time_taken = end_time - start_time

    message = (
        f"File: {file_path}\nTime taken: {time_taken:.2f} seconds\n"
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
        'file_path': file_path,
        'foldername': foldername,
        'filename': filename,
        'description': description,
        'analysis': analysis,
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
    """Generate description, folder name, and filename for a text document."""

    # Total steps in processing a text file
    total_steps = 3

    # Step 1: Generate description
    description = summarize_text_content(input_text)
    progress.update(task_id, advance=1 / total_steps)

    # Remove unwanted words and stopwords
    unwanted_words = set([
        'the', 'and', 'based', 'generated', 'this', 'is', 'filename', 'file', 'document', 'text', 'output', 'only', 'below', 'category',
        'summary', 'key', 'details', 'information', 'note', 'notes', 'main', 'ideas', 'concepts', 'in', 'on', 'of', 'with', 'by', 'for',
        'to', 'from', 'a', 'an', 'as', 'at', 'i', 'we', 'you', 'they', 'he', 'she', 'it', 'that', 'which', 'are', 'were', 'was', 'be',
        'have', 'has', 'had', 'do', 'does', 'did', 'but', 'if', 'or', 'because', 'about', 'into', 'through', 'during', 'before', 'after',
        'above', 'below', 'any', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
        'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now', 'new', 'depicts', 'show', 'shows', 'display',
        'illustrates', 'presents', 'features', 'provides', 'covers', 'includes', 'discusses', 'demonstrates', 'describes'
    ])
    stop_words = set(stopwords.words('english'))
    all_unwanted_words = unwanted_words.union(stop_words)
    lemmatizer = WordNetLemmatizer()

    # Function to clean and process text
    def clean_text(text, max_words):
        # Remove special characters and numbers
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\d+', '', text)
        text = text.strip()
        # Split concatenated words (e.g., 'mathOperations' -> 'math Operations')
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
    filename = clean_text(description, max_words=3)
    if not filename:
        filename = 'document_' + os.path.splitext(os.path.basename(file_path))[0]
    sanitized_filename = sanitize_filename(filename, max_words=3)
    progress.update(task_id, advance=1 / total_steps)

    # Step 3: Generate folder name from summary
    foldername = clean_text(description, max_words=2)
    if not foldername:
        foldername = 'documents'
    sanitized_foldername = sanitize_filename(foldername, max_words=2)
    progress.update(task_id, advance=1 / total_steps)

    return sanitized_foldername, sanitized_filename, description
