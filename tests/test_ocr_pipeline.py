import pytest

np = pytest.importorskip("numpy")

from ocr_pipeline import remove_noise, resize_to_dpi, run_ocr


def test_remove_noise_ksize_validation():
    image = np.zeros((5, 5), dtype=np.uint8)
    with pytest.raises(ValueError):
        remove_noise(image, ksize=2)
    with pytest.raises(ValueError):
        remove_noise(image, ksize=1)
    assert remove_noise(image, ksize=3).shape == image.shape


def test_resize_to_dpi_dpi_validation():
    image = np.zeros((5, 5), dtype=np.uint8)
    with pytest.raises(ValueError):
        resize_to_dpi(image, dpi=0)


def test_run_ocr_missing_file():
    with pytest.raises(FileNotFoundError):
        run_ocr("missing.png")


def test_run_ocr_unsupported_extension(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("test")
    with pytest.raises(ValueError):
        run_ocr(file_path)


def test_run_ocr_unreadable_image(tmp_path):
    file_path = tmp_path / "broken.png"
    file_path.write_text("not an image")
    with pytest.raises(ValueError):
        run_ocr(file_path)
