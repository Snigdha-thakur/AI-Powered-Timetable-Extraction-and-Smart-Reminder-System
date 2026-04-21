import cv2, re, sys
from paddleocr import PaddleOCR

DAY = {'TUE','WED','THU','FRI','SAT','MON','SUN',
       'TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY','MONDAY'}

for fname in sys.argv[1:]:
    img = cv2.imread(fname)
    if img is None:
        print(f'{fname}: cannot read'); continue
    h, w = img.shape[:2]
    ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
    result = ocr.ocr(img, cls=True)
    elements = []
    for line in result[0]:
        bbox = line[0]
        text = re.sub(r'\s+', ' ', line[1][0]).strip()
        xc = sum(p[0] for p in bbox) / 4
        y  = sum(p[1] for p in bbox) / 4
        elements.append((y, xc, text))
    elements.sort()
    print(f'\n=== {fname} ({w}x{h}) ===')
    print('DAY labels:')
    for y, x, t in elements:
        if t.upper().strip().rstrip('.') in DAY:
            print(f'  {t:12s}  y={y:6.0f}  x={x:6.0f}')
    print('Time header (HH:00):')
    for y, x, t in elements:
        m = re.search(r'(\d{1,2}):(\d{2})', t)
        if m and int(m.group(2)) == 0 and 8 <= int(m.group(1)) <= 19:
            print(f'  {t:10s}  y={y:6.0f}  x={x:6.0f}')
