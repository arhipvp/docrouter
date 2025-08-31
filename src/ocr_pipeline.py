from __future__ import annotations

"""Utility functions for image preprocessing and OCR."""

from pathlib import Path
from typing import Union
import logging

import cv2
import numpy as np
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)


def increase_contrast(image: np.ndarray, alpha: float = 1.5, beta: int = 0) -> np.ndarray:
    """Increase image contrast using a linear transformation.

    :param image: Input image as NumPy array.
    :param alpha: Contrast control (1.0-3.0).
    :param beta: Brightness control (0-100).
    :return: Image with enhanced contrast.
    """
    return cv2.convertScaleAbs(image, alpha=alpha, beta=beta)


def remove_noise(image: np.ndarray, ksize: int = 3) -> np.ndarray:
    """Remove noise from the image using median blur.

    :param image: Input image.
    :param ksize: Size of the kernel; must be an odd integer.
    :return: Denoised image.
    """
    return cv2.medianBlur(image, ksize)


def deskew(image: np.ndarray) -> np.ndarray:
    """Correct skew in the image using its minimum area rectangle.

    :param image: Input image.
    :return: Deskewed image.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    if coords.size == 0:
        return image
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    h, w = image.shape[:2]
    m = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(image, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def binarize(image: np.ndarray) -> np.ndarray:
    """Convert the image to a binary form using Otsu's thresholding.

    :param image: Input image.
    :return: Binarized (grayscale) image.
    """
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def resize_to_dpi(image: np.ndarray, dpi: int = 300) -> np.ndarray:
    """Resize image to approximate the desired DPI.

    :param image: Input image.
    :param dpi: Target DPI value.
    :return: Resized image.
    """
    pil_img = Image.fromarray(image)
    orig_dpi = pil_img.info.get("dpi", (72, 72))[0] or 72
    scale = dpi / orig_dpi
    if scale == 1:
        return image
    new_size = (int(pil_img.width * scale), int(pil_img.height * scale))
    return cv2.resize(image, new_size, interpolation=cv2.INTER_CUBIC)


def crop_margins(image: np.ndarray, margin: float = 0.05) -> np.ndarray:
    """Crop margins around the image.

    :param image: Input image.
    :param margin: Fraction of width/height to remove from each side.
    :return: Cropped image.
    """
    h, w = image.shape[:2]
    top = int(h * margin)
    bottom = h - top
    left = int(w * margin)
    right = w - left
    return image[top:bottom, left:right]


def run_ocr(path: Union[str, Path], lang: str = "rus", dpi: int = 300) -> str:
    """Run the OCR pipeline on the given image and return recognized text.

    :param path: Path to the image file.
    :param lang: Tesseract language code (default ``"rus"``).
    :param dpi: Target DPI for preprocessing.
    :return: Recognized text as a string.
    """
    image = cv2.imread(str(path))
    if image is None:
        raise FileNotFoundError(f"Image not found: {path}")
    image = resize_to_dpi(image, dpi)
    image = increase_contrast(image)
    image = remove_noise(image)
    image = deskew(image)
    image = crop_margins(image)
    image = binarize(image)
    pil_img = Image.fromarray(image)
    try:
        return pytesseract.image_to_string(pil_img, lang=lang)
    except pytesseract.TesseractError as exc:
        if lang != "eng":
            logger.warning("Tesseract language '%s' unavailable, falling back to 'eng'", lang)
            return pytesseract.image_to_string(pil_img, lang="eng")
        raise exc
