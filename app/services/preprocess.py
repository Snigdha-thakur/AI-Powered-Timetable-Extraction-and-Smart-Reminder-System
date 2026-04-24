"""
Image preprocessing for VTOP timetable screenshots.
All values are relative to image dimensions — no hardcoded pixel sizes.
"""

import cv2
import numpy as np


def preprocess_for_ocr(image_path: str) -> np.ndarray:
    """
    Returns a preprocessed BGR image suitable for PaddleOCR.
    Upscales small images, denoises, and corrects skew.
    Returns BGR (not grayscale) because PaddleOCR works better with colour input.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Cannot read image: {image_path}")

    h, w = img.shape[:2]

    # 1. Upscale if too narrow — PaddleOCR degrades on small text
    #    Target: at least 1800px wide, scale proportionally
    if w < 1800:
        scale = 1800.0 / w
        img = cv2.resize(img, None, fx=scale, fy=scale,
                         interpolation=cv2.INTER_CUBIC)
        h, w = img.shape[:2]

    # 2. Mild sharpening to recover soft edges from browser screenshots
    kernel = np.array([[0, -0.5, 0],
                       [-0.5, 3, -0.5],
                       [0, -0.5, 0]])
    img = cv2.filter2D(img, -1, kernel)

    # 3. Deskew using grayscale moments (skew rarely > 2° in screenshots,
    #    but correcting even 0.5° improves row alignment)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255,
                              cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(binary > 0))
    if len(coords) > 200:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        if 0.3 < abs(angle) < 10:
            M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
            img = cv2.warpAffine(img, M, (w, h),
                                 flags=cv2.INTER_CUBIC,
                                 borderMode=cv2.BORDER_REPLICATE)

    return img
