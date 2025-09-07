from PIL import Image, ImageDraw, ImageFont
import shutil
import pytest

from file_utils import extract_text
from file_utils.image_ocr import extract_text_image


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_extract_text_from_image(tmp_path):
    image = Image.new('RGB', (100, 50), color='white')
    draw = ImageDraw.Draw(image)
    draw.text((10, 10), 'OCR', fill='black', font=ImageFont.load_default())
    image_path = tmp_path / 'sample.jpg'
    image.save(image_path)

    text = extract_text(image_path)
    assert 'OCR' in text


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_extract_text_from_image_fallback_language(tmp_path):
    image = Image.new('RGB', (100, 50), color='white')
    draw = ImageDraw.Draw(image)
    draw.text((10, 10), 'OCR', fill='black', font=ImageFont.load_default())
    image_path = tmp_path / 'sample.jpg'
    image.save(image_path)

    text = extract_text(image_path, language='xyz')
    assert 'OCR' in text


def test_extract_text_image_tesseract_not_found(monkeypatch, tmp_path):
    image = Image.new('RGB', (10, 10), color='white')
    image_path = tmp_path / 'sample.png'
    image.save(image_path)

    import pytesseract

    def fake_image_to_string(*_args, **_kwargs):
        raise pytesseract.TesseractNotFoundError()

    monkeypatch.setattr(pytesseract, 'image_to_string', fake_image_to_string)

    with pytest.raises(RuntimeError) as exc:
        extract_text_image(image_path)
    assert 'Tesseract OCR executable not found' in str(exc.value)
