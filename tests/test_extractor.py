from pathlib import Path
import sys
import types

from PIL import Image, ImageDraw
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from extractor import extract_text


def test_extract_text_image(monkeypatch, tmp_path):
    image_path = tmp_path / "sample.png"
    img = Image.new("RGB", (100, 40), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "hi", fill=(0, 0, 0))
    img.save(image_path)

    monkeypatch.setattr("pytesseract.image_to_string", lambda img: "hi")

    assert extract_text(image_path) == "hi"


def test_extract_text_pdf(monkeypatch, tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    fake_pdfminer = types.ModuleType("pdfminer")
    high_level = types.ModuleType("pdfminer.high_level")
    high_level.extract_text = lambda path: "pdf text"
    sys.modules["pdfminer"] = fake_pdfminer
    sys.modules["pdfminer.high_level"] = high_level

    assert extract_text(pdf_path) == "pdf text"
