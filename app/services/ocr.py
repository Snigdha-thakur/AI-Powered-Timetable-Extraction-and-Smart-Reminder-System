# ocr.py

import cv2
import re
import numpy as np
from paddleocr import PaddleOCR
from typing import Dict, List, Optional, Tuple
from app.services.course_parser import CourseParser
from app.services.preprocess import preprocess_for_ocr
from app.services.table_detector import detect_table_cells, get_grid_dimensions

# ── Slot validation ───────────────────────────────────────────────────────────

VALID_SLOT_PREFIXES = {
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'L',
    'TA', 'TB', 'TC', 'TD', 'TE', 'TF', 'TG', 'T',
    'SA', 'SB', 'SC', 'SD', 'SE', 'SF', 'SG',
    'STA', 'STB', 'STC', 'STD',
}
SLOT_RE = re.compile(r'\b([A-Z]{1,3}\d{1,2}[A-Z]?)\b')

# Venue pattern embedded in cell text
# Venues: 101-CB, 215-CB, G17-AB-2, ONL00003-ONL, NIL-ONL
# NOT slot-course prefixes: C2-MAT2003, L20-MAT2003
# Key: venue suffix after hyphen is a building code (2-3 letters, NOT 4-digit course code)
CELL_VENUE_RE = re.compile(
    r'\b('
    r'\d{3,}-[A-Z]{2,}[\w-]*'                          # 3+ digit room: 101-CB, 228-CB
    r'|[A-Z]\d{2,}-(?![A-Z]{2,4}\d{4})[A-Z]{2,}[\w-]*' # G17-CB but NOT L20-MAT2003
    r'|ONL\w*-ONL'                                      # ONL00003-ONL
    r'|NIL-ONL|NILL?-ONL'
    r')\b',
    re.IGNORECASE
)

# Fully-enriched cell: SLOT-COURSECODE-TYPE-VENUE[-ALL]
# e.g. "A1-CSE2005-ETH-225-CB-ALL", "L4-CSE1005-ELA-101-CB-ALL"
ENRICHED_CELL_RE = re.compile(
    r'^([A-Z]{1,3}\d{1,2}[A-Z]?)'      # slot
    r'-([A-Z]{2,4}\d{4})'               # course code
    r'-([A-Z]{2,3})'                    # type tag: ETH/ELA/TH/EL/PJ
    r'-([\w][\w\-\.]*?)(?:-ALL)?$',     # venue
    re.IGNORECASE
)

SKIP_TOKENS = {
    'THEORY', 'LAB', 'LUNCH', 'START', 'END',
    'CLUBS/ECS', 'ECS/CLUBS', '--', '-', '---', '----', '-----',
    'CLUBS', 'ECS',
}

DAY_NAMES = {
    'MON': 'Monday',   'TUE': 'Tuesday',  'WED': 'Wednesday',
    'THU': 'Thursday', 'FRI': 'Friday',   'SAT': 'Saturday', 'SUN': 'Sunday',
    'MONDAY': 'Monday', 'TUESDAY': 'Tuesday', 'WEDNESDAY': 'Wednesday',
    'THURSDAY': 'Thursday', 'FRIDAY': 'Friday', 'SATURDAY': 'Saturday',
}

_COURSE_WORDS = re.compile(
    r'\b(Networks?|Systems?|Statistics|Management|Engineering|Science|'
    r'Intelligence|Computing|Database|Programming|Architecture|Design|'
    r'Analysis|Theory|Mathematics|Physics|Chemistry|Electronics|'
    r'Communication|Security|Algorithm|Structure|Operating|Artificial|'
    r'Computation|Algebra|Clinics|Internship|Thinking|Coding|Forensics)\b',
    re.IGNORECASE
)


def _is_person_name(s: str) -> bool:
    s = s.strip()
    if not s or _COURSE_WORDS.search(s):
        return False
    if re.match(r'^(Prof|Dr|Ms|Mr|Mrs)\.?\s+\S', s, re.I):
        return True
    words = s.split()
    # Single short capitalized word with no digits = likely a name (e.g. "Shalini")
    if len(words) == 1 and words[0][0].isupper() and words[0].isalpha() and len(words[0]) >= 4:
        return True
    if len(words) >= 2 and all(w.isupper() and w.isalpha() for w in words):
        return True
    if (len(words) == 2
            and all(w[0].isupper() and w.isalpha() for w in words)
            and all(len(w) <= 12 for w in words)):
        return True
    return False


def _is_valid_slot(s: str) -> bool:
    s = s.strip().rstrip('- ')
    m = re.match(r'^([A-Z]{1,3})(\d{1,2})[A-Z]?$', s)
    if not m:
        return False
    prefix = m.group(1)
    # 3-letter prefixes are only valid if explicitly in VALID_SLOT_PREFIXES (STA, STB, STC, STD)
    # All other 3-letter prefixes (TFF, TBB, TCC etc.) are timetable grid codes, not slots
    return prefix in VALID_SLOT_PREFIXES and 1 <= int(m.group(2)) <= 60


def _parse_enriched_cell(text: str) -> Optional[dict]:
    """
    Parse enriched cell text. Handles both:
    - Single token: 'A1-CSE2005-ETH-225-CB-ALL'
    - OCR-split tokens: 'L20-MAT2003' + 'ELA-228-CB-ALL' joined as 'L20-MAT2003 ELA-228-CB-ALL'
    Returns dict with slot, course_code, type_tag, venue — or None.
    """
    # Try full match first (single token, most reliable)
    clean = text.strip()
    m = ENRICHED_CELL_RE.match(clean)
    if m:
        return {
            'slot':        m.group(1).upper(),
            'course_code': m.group(2).upper(),
            'type_tag':    m.group(3).upper(),
            'venue':       m.group(4).upper(),
        }

    # OCR sometimes splits 'L20-MAT2003-ELA-228-CB-ALL' into
    # 'L20-MAT2003' and 'ELA-228-CB-ALL' (two separate detections joined by space)
    # Rejoin by removing spaces around hyphens and retry
    rejoined = re.sub(r'\s*-\s*', '-', clean)
    rejoined = re.sub(r'\s+', '-', rejoined)  # spaces between parts → hyphens
    m = ENRICHED_CELL_RE.match(rejoined)
    if m:
        return {
            'slot':        m.group(1).upper(),
            'course_code': m.group(2).upper(),
            'type_tag':    m.group(3).upper(),
            'venue':       m.group(4).upper(),
        }

    # Also try: find SLOT-COURSECODE anywhere in text, then find venue separately
    slot_code_m = re.search(r'\b([A-Z]{1,3}\d{1,2}[A-Z]?)-([A-Z]{2,4}\d{4})-([A-Z]{2,3})', clean)
    if slot_code_m:
        venue = _extract_venue_from_cell(clean)
        return {
            'slot':        slot_code_m.group(1).upper(),
            'course_code': slot_code_m.group(2).upper(),
            'type_tag':    slot_code_m.group(3).upper(),
            'venue':       venue,
        }

    return None

def _clean_venue(v: str) -> str:
    if not v:
        return ''

    v = v.upper().replace('_', '-')

    # Fix OCR mistakes
    v = v.replace('CNL', 'ONL')
    v = v.replace('0N', 'ON')

    # 🔥 Remove trailing garbage like -A-L, -ALL, etc.
    v = re.sub(r'-[A-Z]-[A-Z]$', '', v)   # removes "-A-L"
    v = re.sub(r'-ALL$', '', v)

    # 🔥 Keep only valid patterns like 112-CB or ONL00003-ONL
    match = re.match(r'(ONL[\w-]*-ONL|\d{3,}-[A-Z]{2,}|[A-Z]\d{2,}-[A-Z]{2,})', v)
    if match:
        return match.group(1)

    return ''

def _clean_subject(name: str) -> str:
    if not name:
        return ""

    # remove dots and trailing junk
    name = re.sub(r'\.{2,}', '', name)

    # remove extra spaces
    name = re.sub(r'\s+', ' ', name).strip()

    return name

def _clean_faculty(fac: str) -> str:
    if not fac:
        return ""
    fac = fac.strip()
    # Never add a prefix — just return as-is (prefix already set by course_parser)
    return fac

def _extract_venue_from_cell(text: str) -> str:
    """
    Extract venue from enriched cell text.
    Enriched format: SLOT-COURSECODE-TYPE-VENUE[-ALL]
    e.g. 'A1-MAT2005-TH-230-CB-ALL' -> '230-CB'
         'L20-MAT2003-ELA-228-CB-ALL' -> '228-CB'
    """
    # Try structured parse on original and space-joined form
    for candidate in [text.strip(), re.sub(r'\s+', '-', text.strip())]:
        m = re.match(
            r'^[A-Z]{1,3}\d{1,2}[A-Z]?'    # slot
            r'-[A-Z]{2,4}\d{4}'             # course code
            r'-[A-Z]{2,3}'                  # type tag
            r'-([\w][\w\-\.]*?)(?:-ALL)?$', # venue
            candidate, re.IGNORECASE
        )
        if m:
            return m.group(1).upper()
    # Fallback: only use CELL_VENUE_RE if text doesn't start with a slot-course pattern
    # (prevents matching 'L20-MAT2003' as a venue)
    if not re.match(r'^[A-Z]{1,3}\d{1,2}[A-Z]?-[A-Z]{2,4}\d{4}', text.strip(), re.IGNORECASE):
        vm = CELL_VENUE_RE.search(text)
        return vm.group(1).upper() if vm else ''
    return ''


def _extract_slots_from_cell(text: str) -> List[str]:
    found = []
    for part in re.split(r'\s+', text):
        for segment in part.split('+'):
            compact = segment.strip()
            if not compact or len(compact) < 2:
                continue
            m = re.match(r'^([A-Z]{1,3}\d{1,2}[A-Z]?)(?:-|$)', compact)
            if m:
                candidate = m.group(1)
                if _is_valid_slot(candidate):
                    found.append(candidate)
                    continue
            for candidate in SLOT_RE.findall(compact):
                if _is_valid_slot(candidate):
                    found.append(candidate)
                    break
    return found


# ── Time slot definitions ─────────────────────────────────────────────────────

TIME_SLOTS = [
    '08:00-08:50', '09:00-09:50', '10:00-10:50', '11:00-11:50',
    '12:00-12:50', '13:00-13:50', '14:00-14:50', '15:00-15:50',
    '16:00-16:50', '17:00-17:50', '18:00-18:50', '19:00-19:50',
]

# Map start-hour → time slot string
HOUR_TO_SLOT = {int(ts.split(':')[0]): ts for ts in TIME_SLOTS}


class OCRService:
    def __init__(self):
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
        self._course_parser = CourseParser()

    def clean_text(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

    def _ocr_image(self, img: np.ndarray) -> List[Tuple]:
        """Run PaddleOCR and return list of (x_left, x_center, y_center, text)."""
        result = self.ocr.ocr(img, cls=True)
        elements = []
        if not result or not result[0]:
            return elements
        for line in result[0]:
            bbox = line[0]
            text = self.clean_text(line[1][0])
            if not text:
                continue
            x_left   = min(p[0] for p in bbox)
            x_center = sum(p[0] for p in bbox) / 4
            y_center = sum(p[1] for p in bbox) / 4
            elements.append((x_left, x_center, y_center, text))
        return elements

    # ========== PHASE 1: Extract Course Data ==========

    def extract_courses(self, image_path: str):
        raw = self._course_parser.extract(image_path)
        by_slot: Dict[str, dict] = {}
        by_code: Dict[str, dict] = {}

        def _normalize_code(c: str) -> str:
            c = re.sub(r'^([A-Z]{2,3})5(\d{4})$', r'\g<1>S\2', c)
            return c

        for code, entries in raw.items():
            norm_code = _normalize_code(code)
            for entry in entries:
                name    = entry.get('name', '')
                faculty = entry.get('faculty', '')
                if name and _is_person_name(name) and faculty and not _is_person_name(faculty):
                    name, faculty = faculty, name
                elif name and _is_person_name(name) and not faculty:
                    faculty, name = name, ''
                info = {
                    'course_code': norm_code,
                    'course_name': name,
                    'type':        entry.get('type', ''),
                    'faculty':     faculty,
                    'venue':       entry.get('venue', ''),
                }
                by_code.setdefault(norm_code, info)
                for slot in entry.get('slots', []):
                    if slot:
                        by_slot[slot] = info
        return by_slot, by_code

    # ========== PHASE 2: Extract Timetable Grid ==========

    def _crop_to_schedule_grid(self, img: np.ndarray) -> Tuple[np.ndarray, int]:
        """
        Crop the image to only the schedule grid portion, discarding the course
        table above it. Uses OCR to find the first 'THEORY' label that appears
        alongside a 'Start' label — that row marks the top of the grid.

        Returns (cropped_img, y_offset) where y_offset is the pixel row where
        the crop starts (needed if we ever need to map back to original coords).
        """
        h, w = img.shape[:2]
        elements = self._ocr_image(img)

        # Find the topmost y where 'THEORY' and 'Start' appear in the same
        # horizontal band — that's the schedule header row
        bucket = max(int(h * 0.015), 8)
        rows_by_y: Dict[int, list] = {}
        for x_left, x_center, y, text in elements:
            key = round(y / bucket) * bucket
            rows_by_y.setdefault(key, []).append(text.upper().strip())

        grid_top_y = 0
        for y_key in sorted(rows_by_y.keys()):
            texts = rows_by_y[y_key]
            has_theory = any('THEORY' in t for t in texts)
            has_start  = any(t == 'START' for t in texts)
            has_times  = sum(1 for t in texts if re.match(r'^\d{1,2}:\d{2}$', t)) >= 3
            if (has_theory and has_start) or (has_theory and has_times):
                # Go up a little to include the full header row border
                grid_top_y = max(0, y_key - bucket * 2)
                break

        if grid_top_y == 0:
            # Could not find grid top — return full image
            return img, 0

        print(f'    [crop] Schedule grid starts at y={grid_top_y} (image height={h})')
        return img[grid_top_y:, :], grid_top_y

    def extract_timetable_grid(self, image_path: str) -> Dict[str, Dict[int, List[tuple]]]:
        img = preprocess_for_ocr(image_path)

        # Find crop offset for fallback path, but run cell detection on full image
        img_cropped, crop_y = self._crop_to_schedule_grid(img)

        # Try morphological detection on the CROPPED image first
        cells = detect_table_cells(img_cropped)

        if cells:
            print(f'    [grid] Detected {len(cells)} cells via morphological detection')
            result = self._extract_from_cell_grid(img_cropped, cells)
            # If we got a result but no time header found, retry on full image
            if not result:
                print('    [grid] Retrying on full image (crop may have removed header)')
                cells_full = detect_table_cells(img)
                if cells_full:
                    return self._extract_from_cell_grid(img, cells_full)
            return result
        else:
            print('    [grid] No table structure found, falling back to OCR clustering')
            return self._extract_from_ocr_fallback(img_cropped)

    def _preprocess_cell_for_ocr(self, cell_img: np.ndarray) -> np.ndarray:
        """
        Only neutralise genuinely colored backgrounds (lime-green, yellow highlights).
        Leave white/cream cells completely alone — preprocessing them causes
        PaddleOCR to hallucinate garbage on time values and slot codes.
        """
        if len(cell_img.shape) != 3:
            cell_img = cv2.cvtColor(cell_img, cv2.COLOR_GRAY2BGR)

        hsv = cv2.cvtColor(cell_img, cv2.COLOR_BGR2HSV)

        # Check if the cell is actually colored (highlighted)
        # Lime-green: hue 35-85, saturation > 80
        green_mask = cv2.inRange(hsv,
            np.array([35, 80, 100]),
            np.array([85, 255, 255])
        )
        # Yellow: hue 20-35, saturation > 60
        yellow_mask = cv2.inRange(hsv,
            np.array([20, 60, 100]),
            np.array([35, 255, 255])
        )
        color_mask = cv2.bitwise_or(green_mask, yellow_mask)

        # If less than 5% of pixels are colored, this is a white/plain cell
        # — return it as-is (no preprocessing, let PaddleOCR handle it)
        h, w = cell_img.shape[:2]
        colored_ratio = np.count_nonzero(color_mask) / (h * w)

        if colored_ratio < 0.05:
            # Plain cell — just upscale if tiny, no other processing
            if h < 40 or w < 80:
                scale = max(40 / h, 80 / w, 2.0)
                cell_img = cv2.resize(cell_img, None, fx=scale, fy=scale,
                                    interpolation=cv2.INTER_CUBIC)
            return cell_img

        # Colored cell — replace background with white, then return
        result = cell_img.copy()
        result[color_mask > 0] = [255, 255, 255]

        # Upscale if tiny
        h, w = result.shape[:2]
        if h < 40 or w < 80:
            scale = max(40 / h, 80 / w, 2.0)
            result = cv2.resize(result, None, fx=scale, fy=scale,
                                interpolation=cv2.INTER_CUBIC)

        return result

    def _extract_from_cell_grid(
        self, img: np.ndarray, cells: List[tuple]
    ) -> Dict[str, Dict[int, List[tuple]]]:
        """
        OCR each cell individually after neutralising its background colour.
        This avoids the 'Cemeater'/'Cene' hallucination caused by PaddleOCR
        misreading lime-green (#CCFF00) cell backgrounds.
        """
        num_rows, num_cols = get_grid_dimensions(cells)
        print(f'    [grid] Grid size: {num_rows} rows × {num_cols} cols')

        flat_grid: Dict[Tuple[int, int], str] = {}

        for row_idx, col_idx, x, y, w, h in sorted(cells, key=lambda c: (c[0], c[1])):
            # Smaller padding — just enough to avoid border bleed
            pad_x = max(1, int(w * 0.04))   # was 0.08
            pad_y = max(1, int(h * 0.06))   # was 0.12
            y1 = max(0, y + pad_y)
            y2 = min(img.shape[0], y + h - pad_y)
            x1 = max(0, x + pad_x)
            x2 = min(img.shape[1], x + w - pad_x)

            if y2 <= y1 or x2 <= x1:
                continue

            cell_img = img[y1:y2, x1:x2]
            # Neutralise background colour before OCR
            cell_proc = self._preprocess_cell_for_ocr(cell_img)

            result = self.ocr.ocr(cell_proc, cls=False)
            if result and result[0]:
                text = ' '.join(
                    self.clean_text(r[1][0]) for r in result[0]
                ).strip()
                if text:
                    flat_grid[(row_idx, col_idx)] = text

        return self._parse_grid_structure(flat_grid, num_rows, num_cols)

    def _parse_grid_structure(
        self,
        grid: Dict[Tuple[int, int], str],
        num_rows: int,
        num_cols: int,
    ) -> Dict[str, Dict[int, List[tuple]]]:

        # ── Step 1: Find time header row ─────────────────────────────────────
        time_col_map: Dict[int, int] = {}
        header_row = -1

        for row_idx in range(min(12, num_rows)):
            hours_in_row: Dict[int, int] = {}
            for col_idx in range(num_cols):
                text = grid.get((row_idx, col_idx), '').strip()

                # Try several patterns OCR might produce for time values:
                # "08:00", "8:00", "0800", "08 00", "08.00"
                found_hour = None
                for pattern in [
                    r'^(\d{1,2}):(\d{2})$',           # 08:00 or 8:00
                    r'^(\d{1,2})\s(\d{2})$',           # 08 00
                    r'^(\d{1,2})\.(\d{2})$',           # 08.00
                    r'^(\d{2})(\d{2})$',               # 0800
                ]:
                    m = re.match(pattern, text)
                    if m:
                        hour, minute = int(m.group(1)), int(m.group(2))
                        # Valid VTOP time slots start on the hour (minute==0)
                        # but allow OCR misread of 00 as 01 or 02
                        if 7 <= hour <= 20 and minute <= 5:
                            found_hour = hour
                            break

                # Also check if text CONTAINS a time (for cells with extra text)
                if found_hour is None:
                    m = re.search(r'\b(\d{1,2}):00\b', text)
                    if m:
                        hour = int(m.group(1))
                        if 7 <= hour <= 20:
                            found_hour = hour

                if found_hour is not None:
                    hours_in_row[col_idx] = found_hour

            print(f'    [grid] Row {row_idx}: found {len(hours_in_row)} time cols: {sorted(set(hours_in_row.values()))}')

            if len(hours_in_row) >= 4:
                header_row = row_idx
                time_col_map = hours_in_row
                break

        if not time_col_map:
            print('    [grid] WARNING: could not find time header row')
            # Debug: print what's in the first few rows
            for row_idx in range(min(6, num_rows)):
                row_content = {c: grid.get((row_idx, c), '') for c in range(min(10, num_cols))}
                print(f'    [grid] DEBUG row {row_idx}: {row_content}')
            return {}

        # Deduplicate — keep leftmost occurrence of each hour
        seen_hours: set = set()
        deduped_time_map: Dict[int, int] = {}
        for col_idx in sorted(time_col_map.keys()):
            hour = time_col_map[col_idx]
            if hour not in seen_hours:
                seen_hours.add(hour)
                deduped_time_map[col_idx] = hour

        print(f'    [grid] Header row {header_row}, hours: {sorted(deduped_time_map.values())}')

        # ── Step 2: Find Lunch column
        lunch_col = -1
        for col_idx in range(num_cols):
            if 'LUNCH' in grid.get((header_row, col_idx), '').upper():
                lunch_col = col_idx
                break

        # ── Step 3: Identify which rows are header rows to skip
        # Header block is all rows from 0 to first data row
        # A data row has: col0 = day name OR col1 = THEORY/LAB (not Start/End)
        header_block_end = header_row

        # Find where the actual data rows start
        for row_idx in range(header_row, min(header_row + 6, num_rows)):
            col0 = self.clean_text(grid.get((row_idx, 0), '')).upper().rstrip('.')
            col1 = self.clean_text(grid.get((row_idx, 1), '')).upper().rstrip('.')
            if col0 in DAY_NAMES or col1 in ('THEORY', 'LAB'):
                # Check it's actually a data row (not just "THEORY" in the header block)
                if col0 in DAY_NAMES:
                    header_block_end = row_idx
                    break

        # ── Step 4: Parse data rows
        timetable: Dict[str, Dict[int, List[tuple]]] = {}
        current_day = ''

        # Pre-scan: build a map of row_idx → day name, checking ALL columns
        # VTOP uses merged cells for day names — the day text may appear in
        # col0 OR col1 depending on how the morphological detector splits the merge.
        row_day_map: Dict[int, str] = {}
        for row_idx in range(header_row, num_rows):
            for col_idx in range(min(3, num_cols)):
                cell = self.clean_text(grid.get((row_idx, col_idx), '')).upper().rstrip('.')
                if cell in DAY_NAMES:
                    row_day_map[row_idx] = DAY_NAMES[cell]
                    break
                # Partial match (e.g. "TUE" inside "TUES")
                for abbr, full in DAY_NAMES.items():
                    if cell.startswith(abbr) and len(cell) <= len(abbr) + 3:
                        row_day_map[row_idx] = full
                        break

        print(f'    [grid] Day rows detected: {row_day_map}')

        # Debug: print first few data rows to diagnose column layout
        for row_idx in range(header_row, min(header_row + 10, num_rows)):
            row_content = {c: grid.get((row_idx, c), '') for c in range(min(6, num_cols))}
            print(f'    [grid] DEBUG row {row_idx}: {row_content}')

        for row_idx in range(header_row, num_rows):
            # Collect text from first 3 cols for type/day detection
            cells = [self.clean_text(grid.get((row_idx, c), '')).upper().rstrip('.')
                     for c in range(min(3, num_cols))]

            # Skip time header rows (Start / End)
            if any(c in ('START', 'END') for c in cells):
                continue

            # Update current day if this row has a day label
            if row_idx in row_day_map:
                current_day = row_day_map[row_idx]

            if not current_day:
                continue

            # Determine row type — search all first-3 cols
            row_type = None

            for c in cells:
                if 'THEORY' in c:
                    row_type = 'THEORY'
                    break
                if 'LAB' in c:
                    row_type = 'LAB'
                    break

            # 🔥 Fallback: infer from slot pattern
            if row_type is None:
                sample_text = ' '.join(cells)

                if re.search(r'\bL\d{1,2}\b', sample_text):
                    row_type = 'LAB'
                elif re.search(r'\b[A-GT]\d{1,2}\b', sample_text):
                    row_type = 'THEORY'
                else:
                    continue

            # Scan time columns
            for col_idx, hour in deduped_time_map.items():
                if col_idx == lunch_col:
                    continue
                text = self.clean_text(grid.get((row_idx, col_idx), ''))
                if not text or text.upper() in SKIP_TOKENS:
                    continue
                if re.match(r'^\d{1,2}:\d{2}$', text.strip()):
                    continue

                all_slots_in_cell = _extract_slots_from_cell(text)
                unique_slots = list(dict.fromkeys(all_slots_in_cell))
                if not unique_slots:
                    # No slot code found — check if it's an enriched cell with a course code
                    parsed = _parse_enriched_cell(text)
                    if parsed:
                        unique_slots = [parsed['slot']]
                    else:
                        continue

                # Use only the first slot from enriched cells to avoid false positives
                # from venue codes being parsed as slots (e.g. G12 in G12-CB)
                parsed_check = _parse_enriched_cell(text)
                if parsed_check:
                    unique_slots = [parsed_check['slot']]

                for slot_code in unique_slots[:2]:  # cap at 2 to avoid noise
                    timetable.setdefault(current_day, {}) \
                            .setdefault(hour, []) \
                            .append((slot_code, text, row_type))

        # Deduplicate
        for day in timetable:
            for hour in timetable[day]:
                seen: set = set()
                deduped = []
                for entry in timetable[day][hour]:
                    key = (entry[0], entry[2])
                    if key not in seen:
                        seen.add(key)
                        deduped.append(entry)
                timetable[day][hour] = deduped

        print(f'    [grid] Days found: {list(timetable.keys())}')
        return timetable

    def _extract_from_ocr_fallback(
        self, img: np.ndarray
    ) -> Dict[str, Dict[int, List[tuple]]]:
        """
        Fallback: run OCR on full image, cluster by Y, then parse.
        Uses adaptive Y-bucket size (1.5% of image height) instead of fixed 15px.
        """
        h, w = img.shape[:2]
        elements = self._ocr_image(img)

        # Adaptive bucket: 1.5% of image height
        bucket = max(int(h * 0.015), 8)

        rows_by_y: Dict[int, list] = {}
        for x_left, x_center, y, text in elements:
            key = round(y / bucket) * bucket
            rows_by_y.setdefault(key, []).append((x_left, x_center, y, text))

        # Find time header rows (may have duplicate hours — deduplicate)
        time_cols: List[Tuple[float, int]] = []  # (x_left, hour)
        time_row_y = None

        candidate_rows = []
        for y_key, row_items in sorted(rows_by_y.items()):
            times_in_row = []
            seen_hours: set = set()
            for x_left, x_center, y, text in row_items:
                m = re.search(r'\b(\d{1,2}):?(\d{2})\b', text)
                if m:
                    hour, minute = int(m.group(1)), int(m.group(2))
                    if 7 <= hour <= 20 and minute == 0 and hour not in seen_hours:
                        seen_hours.add(hour)
                        times_in_row.append((x_left, hour))
            if len(times_in_row) >= 4:
                candidate_rows.append((y_key, times_in_row))

        # Prefer row containing hour 8 (the Start row)
        for y_key, times_in_row in candidate_rows:
            if any(h == 8 for _, h in times_in_row):
                time_row_y = y_key
                time_cols = sorted(times_in_row, key=lambda t: t[0])
                break
        if not time_cols and candidate_rows:
            time_row_y, times_in_row = candidate_rows[0]
            time_cols = sorted(times_in_row, key=lambda t: t[0])

        if not time_cols:
            print('    [fallback] Could not find time header row')
            return {}

        # Deduplicate time columns
        seen_hours_set: set = set()
        deduped_cols = []
        for x_left, hour in time_cols:
            if hour not in seen_hours_set:
                seen_hours_set.add(hour)
                deduped_cols.append((x_left, hour))
        time_cols = deduped_cols

        print(f'    [fallback] Time columns: {[h for _, h in time_cols]}')

        # Build column x-boundaries
        col_bounds: List[Tuple[float, float, int]] = []
        for i, (x_left, hour) in enumerate(time_cols):
            x_end = time_cols[i + 1][0] if i + 1 < len(time_cols) else float('inf')
            col_bounds.append((x_left, x_end, hour))

        # Find THEORY/LAB label rows and DAY label rows
        theory_ys: List[int] = []
        lab_ys: List[int] = []
        day_labels: List[Tuple[int, str]] = []

        for y_key, row_items in sorted(rows_by_y.items()):
            if time_row_y is not None and y_key <= time_row_y:
                continue
            found_theory = found_lab = found_day = False
            for x_left, x_center, y, text in row_items:
                t = text.upper().strip().rstrip('.')
                if t == 'THEORY' and not found_theory:
                    theory_ys.append(y_key)
                    found_theory = True
                elif t == 'LAB' and not found_lab:
                    lab_ys.append(y_key)
                    found_lab = True
                elif t in DAY_NAMES and not found_day:
                    full = DAY_NAMES[t]
                    if not any(d == full for _, d in day_labels):
                        day_labels.append((y_key, full))
                    found_day = True

        # Map each day to its THEORY and LAB row Y
        # Window: adaptive — 5% of image height above/below day label
        window = max(int(h * 0.05), 30)
        day_row_map: Dict[str, Dict[str, int]] = {}

        for day_y, day_full in day_labels:
            t_cands = [y for y in theory_ys if day_y - window <= y <= day_y + window * 4]
            l_cands = [y for y in lab_ys    if day_y - window <= y <= day_y + window * 4]
            entry = {}
            if t_cands:
                entry['THEORY'] = min(t_cands, key=lambda y: abs(y - day_y))
            if l_cands:
                entry['LAB'] = min(l_cands, key=lambda y: abs(y - day_y))
            if entry:
                day_row_map[day_full] = entry

        # Row tolerance: adaptive — 2% of image height
        row_tol = max(int(h * 0.02), 12)

        timetable: Dict[str, Dict[int, List[tuple]]] = {}

        for day_full, row_types in day_row_map.items():
            timetable[day_full] = {}
            for row_type, row_y in row_types.items():
                row_tokens = [
                    (x_left, x_center, text)
                    for x_left, x_center, y, text in elements
                    if abs(y - row_y) < row_tol
                ]
                for x_left, x_center, text in row_tokens:
                    if text.upper().strip() in SKIP_TOKENS:
                        continue
                    if re.match(r'^[-–—\.\s]+$', text):
                        continue
                    slots = _extract_slots_from_cell(text)
                    for slot_code in slots:
                        assigned_hour = None
                        for x_start, x_end, hour in col_bounds:
                            if x_start <= x_center < x_end:
                                assigned_hour = hour
                                break
                        if assigned_hour is None:
                            assigned_hour = min(
                                time_cols, key=lambda tc: abs(tc[0] - x_center)
                            )[1]
                        timetable[day_full].setdefault(assigned_hour, []).append(
                            (slot_code, text, row_type)
                        )

            # Deduplicate
            seen_slots: set = set()
            deduped: Dict[int, List[tuple]] = {}
            for hour, entries in timetable[day_full].items():
                for s, txt, rt in entries:
                    key = (s, rt, hour)
                    if key not in seen_slots:
                        seen_slots.add(key)
                        deduped.setdefault(hour, []).append((s, txt, rt))
            timetable[day_full] = deduped

        print(f'    [fallback] Days: {list(timetable.keys())}')
        return timetable

    # ========== PHASE 3: Merge ==========

    def process_timetable(self, course_image_path: str, schedule_image_path: str) -> List[List[str]]:
        print('[Phase 1] Extracting course data...')
        courses, by_code = self.extract_courses(course_image_path)
        print(f'    {len(courses)} slot mappings, {len(by_code)} course codes')

        print('\n[Phase 2] Extracting timetable grid...')
        timetable_grid = self.extract_timetable_grid(schedule_image_path)

        print('\n[Phase 3] Merging...')
        output_rows = []

        for day_full, time_slot_map in timetable_grid.items():
            theory_slots: Dict[int, tuple] = {}
            lab_slots:    Dict[int, tuple] = {}

            for hour, slot_entries in time_slot_map.items():
                for slot_code, cell_text, row_type in slot_entries:

                    # ── Resolution priority ───────────────────────────────
                    # 1. Parse enriched cell directly → lookup by course code
                    # 2. Lookup slot code in by_slot
                    # 3. Discard
                    info: Optional[dict] = None
                    venue = ''

                    parsed = _parse_enriched_cell(cell_text)
                    if parsed:
                        info  = by_code.get(parsed['course_code'])
                        venue = parsed['venue']

                    if info is None and slot_code in courses:
                        info  = courses[slot_code]
                        venue = _extract_venue_from_cell(cell_text) or info.get('venue', '')

                    if info is None:
                        # Last resort: scan cell text for any course code
                        # Also try fixing common OCR misreads (5→S)
                        for cc_candidate in re.findall(r'[A-Z]{2,4}\d{4}', cell_text):
                            if cc_candidate in by_code:
                                info = by_code[cc_candidate]
                                venue = _extract_venue_from_cell(cell_text) or info.get('venue', '')
                                break
                            # Try S→5 fix: e.g. ST52007 → STS2007
                            fixed = re.sub(r'^([A-Z]{2,3})5([A-Z]{0,1}\d{3,4})$',
                                           lambda m: m.group(1) + 'S' + m.group(2), cc_candidate)
                            if fixed != cc_candidate and fixed in by_code:
                                info = by_code[fixed]
                                venue = _extract_venue_from_cell(cell_text) or info.get('venue', '')
                                break

                    if info is None:
                        continue

                    code = info.get('course_code', '')
                    name = _clean_subject(
                        info.get('course_name') or
                        by_code.get(code, {}).get('course_name') or
                        info.get('name') or ''
                    )
                    fac = info.get('faculty', '')
                    venue_from_info = info.get('venue', '')

                    # Guard: if name looks like a person, swap
                    if name and _is_person_name(name) and not fac:
                        fac, name = name, ''
                    elif name and _is_person_name(name) and fac and not _is_person_name(fac):
                        name, fac = fac, name

                    # Guard: if venue ended up in name field, rescue it
                    if name and CELL_VENUE_RE.match(name.strip()):
                        if not venue:
                            venue = name
                        name = ''

                    # If name is still empty or is a course code, use code as fallback
                    if not name or re.fullmatch(r'[A-Z]{2,4}\d{4}', name):
                        name = code or name

                    venue = _clean_venue(venue or venue_from_info)
                    if not venue:
                        venue = _clean_venue(_extract_venue_from_cell(cell_text))

                    is_lab = (
                        row_type == 'LAB'
                        or slot_code.startswith('L')
                        or 'Lab' in info.get('type', '')
                    )
                    target = lab_slots if is_lab else theory_slots

                    if hour not in target:
                        target[hour] = (slot_code, name, fac, venue)
                    else:
                        old = target[hour]
                        # Update if we now have better data
                        new_fac   = fac   if fac   else old[2]
                        new_venue = venue if venue else old[3]
                        target[hour] = (old[0], old[1], new_fac, new_venue)

            for row_type_label, slot_map in (('THEORY', theory_slots), ('LAB', lab_slots)):
                if not slot_map:
                    continue
                row = [day_full, row_type_label]
                for ts in TIME_SLOTS:
                    h = int(ts.split(':')[0])
                    if h in slot_map:
                        _, name, fac, venue = slot_map[h]
                        row += [name, fac, venue]
                    else:
                        row += ['-', '-', '-']
                output_rows.append(row)

        print(f'    Generated {len(output_rows)} rows')
        return output_rows
