from PIL import Image, ImageDraw, ImageFont
import shutil
import pytest

from file_utils import extract_text


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_extract_text_from_image(tmp_path):
    image = Image.new('RGB', (100, 50), color='white')
    draw = ImageDraw.Draw(image)
    draw.text((10, 10), 'OCR', fill='black', font=ImageFont.load_default())
    image_path = tmp_path / 'sample.jpg'
    image.save(image_path)

    text = extract_text(image_path)
    assert 'OCR' in text
