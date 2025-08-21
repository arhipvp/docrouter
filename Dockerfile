FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng tesseract-ocr-rus \
    ocrmypdf img2pdf poppler-utils imagemagick && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml /app/
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir -e .
COPY src /app/src
COPY prompts /app/prompts
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
CMD ["python","-m","docrouter.app"]
