"""
Table structure detector for VTOP schedule grid images.

Uses morphological line detection to find the actual cell grid,
then assigns (row_idx, col_idx) to each cell.

All kernel sizes are relative to image dimensions so the detector
works regardless of screenshot zoom level or resolution.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional


# (row_idx, col_idx, x, y, w, h)
Cell = Tuple[int, int, int, int, int, int]


def detect_table_cells(img: np.ndarray) -> List[Cell]:
    """
    Detect table cells in a bordered grid image.

    Returns list of (row_idx, col_idx, x, y, w, h).
    Returns empty list if no clear grid is found (caller should fall back).
    """
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()

    # Threshold: invert so lines are white on black
    _, binary = cv2.threshold(gray, 0, 255,
                              cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # ── Detect horizontal lines ──────────────────────────────────────────
    # Kernel width = 1/20 of image width (adaptive to zoom)
    h_len = max(w // 20, 40)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_len, 1))
    h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel, iterations=2)

    # ── Detect vertical lines ────────────────────────────────────────────
    v_len = max(h // 20, 20)
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_len))
    v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel, iterations=2)

    # ── Combine into grid mask ───────────────────────────────────────────
    grid = cv2.add(h_lines, v_lines)

    # Dilate slightly to close small gaps in lines
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    grid = cv2.dilate(grid, close_kernel, iterations=1)

    # ── Find cell contours ───────────────────────────────────────────────
    contours, hierarchy = cv2.findContours(
        grid, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        return []

    # Filter: cells must be reasonably sized
    # Min area: 0.01% of image; max area: 20% of image (skip full-image contour)
    min_area = (w * h) * 0.0001
    max_area = (w * h) * 0.20
    min_w, min_h = w // 80, h // 80

    rects = []
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        area = cw * ch
        if min_area < area < max_area and cw > min_w and ch > min_h:
            rects.append((x, y, cw, ch))

    if len(rects) < 10:
        # Not enough cells detected — grid lines probably not visible
        return []

    # ── Cluster into rows and columns ────────────────────────────────────
    # Use adaptive gap: 2% of image dimension
    row_gap = max(h // 50, 8)
    col_gap = max(w // 100, 8)

    ys = [r[1] for r in rects]
    xs = [r[0] for r in rects]

    row_centers = _cluster_1d(ys, gap=row_gap)
    col_centers = _cluster_1d(xs, gap=col_gap)

    if len(row_centers) < 3 or len(col_centers) < 3:
        return []

    cells: List[Cell] = []
    for (x, y, cw, ch) in rects:
        row_idx = min(range(len(row_centers)),
                      key=lambda i: abs(row_centers[i] - y))
        col_idx = min(range(len(col_centers)),
                      key=lambda i: abs(col_centers[i] - x))
        cells.append((row_idx, col_idx, x, y, cw, ch))

    return cells


def get_grid_dimensions(cells: List[Cell]) -> Tuple[int, int]:
    """Return (num_rows, num_cols) from detected cells."""
    if not cells:
        return 0, 0
    return max(c[0] for c in cells) + 1, max(c[1] for c in cells) + 1


def _cluster_1d(values: List[int], gap: int) -> List[int]:
    """Cluster 1D positions into groups separated by at least `gap` pixels."""
    if not values:
        return []
    sorted_vals = sorted(set(values))
    clusters: List[List[int]] = [[sorted_vals[0]]]
    for v in sorted_vals[1:]:
        if v - clusters[-1][-1] <= gap:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    return [int(sum(c) / len(c)) for c in clusters]
