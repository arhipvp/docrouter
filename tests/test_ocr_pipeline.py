import pytest

np = pytest.importorskip("numpy")

from ocr_pipeline import remove_noise


def test_remove_noise_ksize_validation():
    image = np.zeros((5, 5), dtype=np.uint8)
    with pytest.raises(ValueError):
        remove_noise(image, ksize=2)
    with pytest.raises(ValueError):
        remove_noise(image, ksize=1)
    assert remove_noise(image, ksize=3).shape == image.shape
