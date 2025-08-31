FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-rus \
    libmagic1 \
    libglib2.0-0 \
    libgl1 \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Ensure Tesseract can locate language data
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user ahead of time to avoid expensive chown operations
RUN useradd -m app

# Copy source code and assign ownership in one step
COPY --chown=app:app . .

EXPOSE 8000

USER app

CMD ["python", "main.py"]
