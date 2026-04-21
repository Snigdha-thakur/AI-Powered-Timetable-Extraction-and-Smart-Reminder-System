import cv2
import re
import sys
from paddleocr import PaddleOCR

path = sys.argv[1] if len(sys.argv) > 1 else "Screenshot (109).png"
ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
img = cv2.imread(path)
if img is None:
    print(f"ERROR: Cannot read {path}")
    exit()

h, w = img.shape[:2]
print(f"Image: {w}x{h}")
result = ocr.ocr(img, cls=True)

elements = []
for line in result[0]:
    bbox = line[0]
    text = re.sub(r'\s+', ' ', line[1][0]).strip()
    x_left   = min(p[0] for p in bbox)
    x_center = sum(p[0] for p in bbox) / 4
    y        = sum(p[1] for p in bbox) / 4
    elements.append((x_left, x_center, y, text))

rows_by_y = {}
for x_left, x_center, y, text in elements:
    key = round(y / 20) * 20
    rows_by_y.setdefault(key, []).append((x_left, x_center, y, text))

# Time header rows
print("\n--- Time header rows (HH:00 only) ---")
for y_key, row_items in sorted(rows_by_y.items()):
    times = []
    seen = set()
    for x_left, x_center, y, text in row_items:
        m = re.search(r'(\d{1,2}):?(\d{2})', text)
        if m:
            hour, minute = int(m.group(1)), int(m.group(2))
            if 8 <= hour <= 19 and minute == 0 and hour not in seen:
                seen.add(hour)
                times.append((x_left, f"{hour:02d}:00"))
    if len(times) >= 3:
        print(f"  Y={y_key}: {[t for _, t in sorted(times, key=lambda x: x[0])]}")

# All time header rows (any minute)
print("\n--- All time header rows (any minute, for reference) ---")
for y_key, row_items in sorted(rows_by_y.items()):
    times = []
    seen = set()
    for x_left, x_center, y, text in row_items:
        m = re.search(r'(\d{1,2}):(\d{2})', text)
        if m:
            hour, minute = int(m.group(1)), int(m.group(2))
            if 8 <= hour <= 19:
                key = f"{hour:02d}:{minute:02d}"
                if key not in seen:
                    seen.add(key)
                    times.append((x_left, key))
    if len(times) >= 5:
        print(f"  Y={y_key}: {[t for _, t in sorted(times, key=lambda x: x[0])]}")

# Day rows
print("\n--- Day rows ---")
DAY_NAMES = {
    'MON','TUE','WED','THU','FRI','SAT','SUN',
    'MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY'
}
day_ys = {}
for y_key, row_items in sorted(rows_by_y.items()):
    for x_left, x_center, y, text in row_items:
        t = text.upper().strip().rstrip('.')
        if t in DAY_NAMES:
            short = t[:3]
            if short not in day_ys:
                day_ys[short] = y_key
                print(f"  {short} at Y={y_key}, x={x_center:.0f}")
            break

# Tokens in each day row
print("\n--- Tokens per day row (Y+-40px) ---")
for day, day_y in day_ys.items():
    tokens = [(x_center, text) for x_left, x_center, y, text in elements if abs(y - day_y) < 40]
    tokens.sort()
    print(f"\n  {day} (Y={day_y}):")
    for x, t in tokens:
        print(f"    x={x:6.0f}  {t}")
