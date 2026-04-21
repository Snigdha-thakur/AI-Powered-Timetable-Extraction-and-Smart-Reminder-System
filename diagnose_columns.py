"""
Run this FIRST to see exactly what OCR detects and at what x positions.
This tells us the correct column boundaries for your image.

Usage:
    python diagnose_columns.py course.png
"""

import sys
import cv2
from paddleocr import PaddleOCR
import re

def clean(text):
    return re.sub(r'\s+', ' ', text).strip()

def diagnose(image_path):
    ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
    img = cv2.imread(image_path)

    if img is None:
        print(f"ERROR: Could not read image at {image_path}")
        return

    h, w = img.shape[:2]
    print(f"\nImage size: {w} x {h} px\n")
    print(f"{'TEXT':<45} {'X':>6}  {'Y':>6}  {'X%':>6}")
    print("-" * 70)

    result = ocr.ocr(img, cls=True)
    elements = []

    for line in result[0]:
        bbox = line[0]
        text = clean(line[1][0])
        x = sum(p[0] for p in bbox) / 4
        y = sum(p[1] for p in bbox) / 4
        x_pct = round(x / w * 100, 1)
        elements.append((y, x, text, x_pct))

    elements.sort(key=lambda e: (round(e[0] / 25) * 25, e[1]))

    prev_y = -999
    for y, x, text, x_pct in elements:
        if abs(y - prev_y) > 15:
            print()  # blank line between rows
        print(f"{text:<45} {x:>6.0f}  {y:>6.0f}  {x_pct:>5.1f}%")
        prev_y = y

    print("\n" + "=" * 70)
    print("COLUMN CALIBRATION GUIDE")
    print("=" * 70)
    print("Look at the X values above and identify where each column starts/ends.")
    print("Then update the COLUMNS list in course_parser.py accordingly.")
    print()
    print("Key columns to identify:")
    print("  - course      (contains 'CSE1005', 'Software Engineering', etc.)")
    print("  - slot_venue  (contains 'A2+TA2', 'L4+L5', '107-CB', etc.)")
    print("  - faculty     (contains faculty names)")

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "course.png"
    diagnose(path)