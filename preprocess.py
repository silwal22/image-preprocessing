from __future__ import annotations

import logging
from typing import Iterable

import cv2
import numpy as np
from PIL import Image, ImageOps

try:
    import pytesseract
except Exception:  # pragma: no cover - optional dependency
    pytesseract = None

logger = logging.getLogger(__name__)


def _to_uint8_rgb(img: Image.Image) -> np.ndarray:
    if img.mode != "RGB":
        img = img.convert("RGB")
    return np.array(img, dtype=np.uint8)


def fix_exif_orientation(img: Image.Image) -> Image.Image:
    """Normalize orientation metadata stored in EXIF."""
    return ImageOps.exif_transpose(img)


def _estimate_rotation_angle(img: Image.Image) -> int:
    if pytesseract is None:
        return 0
    try:
        osd = pytesseract.image_to_osd(np.array(img.convert("RGB")))
    except Exception:
        return 0

    if not osd:
        return 0

    text = str(osd)
    for token in ("Rotate: 90", "Rotate: 270", "Rotate: 180"):
        if token in text:
            value = int(text.split(token)[-1].splitlines()[0].strip().split()[-1])
            if token.endswith("90"):
                return 90
            if token.endswith("270"):
                return 270
            if token.endswith("180"):
                return 180

    for token in ("Orientation in degrees: 90", "Orientation in degrees: 270", "Orientation in degrees: 180"):
        if token in text:
            value = int(text.split(token)[-1].split()[0])
            return value

    return 0


def deskew(img: Image.Image) -> Image.Image:
    """Correct small-angle skew based on detected text orientation."""
    gray = cv2.cvtColor(_to_uint8_rgb(img), cv2.COLOR_RGB2GRAY)
    if gray.size == 0:
        return img

    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(thresh > 0))
    if coords.size == 0:
        return img

    rect = cv2.minAreaRect(coords)
    angle = rect[-1]
    if angle < -45:
        angle = 90 + angle
    elif angle > 45:
        angle = angle - 90

    if abs(angle) >= 30:
        return img

    (h, w) = img.size
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    rotated = cv2.warpAffine(gray, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return Image.fromarray(rotated)


def auto_rotate(img: Image.Image) -> Image.Image:
    """Apply rotation with OCR-based detection and fallback skew correction."""
    rotated = img
    try:
        if pytesseract is not None:
            osd_angle = _estimate_rotation_angle(rotated)
            if osd_angle in (90, 180, 270):
                rotated = rotated.rotate(-osd_angle, expand=True)
    except Exception:
        logger.debug("OCR rotation detection failed; continuing with deskew fallback.", exc_info=True)

    deskewed = deskew(rotated)
    if deskewed.size != rotated.size:
        return deskewed
    if np.array_equal(np.asarray(deskewed), np.asarray(rotated)):
        return rotated
    return deskewed


def correct_brightness(img: Image.Image, threshold: int = 90) -> Image.Image:
    """Apply CLAHE-based brightness correction only when the image is dark."""
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    luminance = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
    mean_luminance = float(np.mean(luminance))
    if mean_luminance >= threshold / 255.0:
        return img

    lab = cv2.cvtColor(np.uint8(rgb * 255), cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    lab = cv2.merge((cl, a, b))
    rgb_corr = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    gamma = 1.15
    corrected = np.power(rgb_corr / 255.0, 1 / gamma)
    corrected = np.clip(corrected * 255, 0, 255).astype(np.uint8)
    return Image.fromarray(corrected, mode="RGB")


def preprocess(img: Image.Image, steps: set[str]) -> tuple[Image.Image, list[str]]:
    """Apply selected preprocessing steps and return the processed image plus changed-step log."""
    image = img
    changed_steps: list[str] = []

    if "exif" in steps:
        original = image
        image = fix_exif_orientation(image)
        if image.size != original.size or np.array_equal(np.asarray(image), np.asarray(original)) is False:
            changed_steps.append("exif")

    if "rotate" in steps:
        original = image
        image = auto_rotate(image)
        if not np.array_equal(np.asarray(image), np.asarray(original)):
            changed_steps.append("rotate")

    if "brightness" in steps:
        original = image
        image = correct_brightness(image)
        if not np.array_equal(np.asarray(image), np.asarray(original)):
            changed_steps.append("brightness")

    longest_side = max(image.size)
    if longest_side > 2000:
        scale = 2000 / longest_side
        new_size = (max(1, int(image.size[0] * scale)), max(1, int(image.size[1] * scale)))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
        changed_steps.append("downscale")

    return image, changed_steps
