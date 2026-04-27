# ocr.py — extract ONLY enriched cells with full course info

import cv2
import re
import numpy as np
from paddleocr import PaddleOCR
from typing import Dict, List, Optional, Tuple
from app.services.preprocess import preprocess_for_ocr
from app.services.table_detector import detect_table_cells, get_grid_dimensions

VALID_SLOT_PREFIXES = {
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'L',
    'TA', 'TB', 'TC', 'TD', 'TE', 'TF', 'TG', 'T',
    'SA', 'SB', 'SC', 'SD', 'SE', 'SF', 'SG',
    'STA', 'STB', 'STC', 'STD',
    'TAA', 'TBB', 'TCC', 'TDD', 'TEE', 'TFF', 'TGG',
}

# Valid type tags
VALID_TYPE_TAGS = {'ETH', 'ELA', 'TH', 'EL', 'PJ', 'LO'}

COURSE_CODE_RE = re.compile(r'^[A-Z]{2,4}\d{4}$')

DAY_NAMES = {
    'MON': 'Monday',   'TUE': 'Tuesday',  'WED': 'Wednesday',
    'THU': 'Thursday', 'FRI': 'Friday',   'SAT': 'Saturday', 'SUN': 'Sunday',
    'MONDAY': 'Monday', 'TUESDAY': 'Tuesday', 'WEDNESDAY': 'Wednesday',
    'THURSDAY': 'Thursday', 'FRIDAY': 'Friday', 'SATURDAY': 'Saturday',
}

TIME_SLOTS = [
    '08:00-08:50', '09:00-09:50', '10:00-10:50', '11:00-11:50',
    '12:00-12:50', '13:00-13:50', '14:00-14:50', '15:00-15:50',
    '16:00-16:50', '17:00-17:50', '18:00-18:50', '19:00-19:50',
]
HOUR_TO_SLOT = {int(ts.split(':')[0]): ts for ts in TIME_SLOTS}

_OCR_DIGIT_FROM_LETTER = str.maketrans('OIZSB', '01258')


def _clean_venue(venue: str) -> str:
    """Clean and format venue string"""
    if not venue:
        return 'TBD'
    
    venue = venue.upper().strip()
    
    # Remove ALL suffix
    venue = re.sub(r'[-_]?ALL$', '', venue, flags=re.IGNORECASE)
    venue = re.sub(r'\s+ALL$', '', venue, flags=re.IGNORECASE)
    
    # Fix common OCR errors
    venue = venue.replace('C8', 'CB').replace('C6', 'CB').replace('CE', 'CB')
    venue = venue.replace('A8', 'AB')
    venue = venue.replace('G1S', 'G15').replace('GIS', 'G15')
    
    # Fix digit OCR errors
    venue = venue.translate(_OCR_DIGIT_FROM_LETTER)
    
    # Format: Room-Building (e.g., 101-CB, G15-CB, 414-CB)
    match = re.match(r'^([A-Z]?\d{2,3})[-_\s]?([A-Z]{2,})$', venue)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    
    # Just room number
    match = re.match(r'^(\d{2,3})$', venue)
    if match:
        return match.group(1)
    
    # Handle G## format
    match = re.match(r'^(G\d{1,2})$', venue)
    if match:
        return f"{match.group(1)}-CB"
    
    # Remove any remaining type tags that might have been captured
    for type_tag in VALID_TYPE_TAGS:
        venue = venue.replace(type_tag, '')
    
    venue = venue.strip('-').strip()
    
    return venue if len(venue) >= 3 else 'TBD'


def _parse_enriched_cell(text: str) -> Optional[dict]:
    """Parse enriched cell text using a simple split-based approach"""
    
    # Clean the text first
    text = text.strip()
    
    # Replace various separators with a standard one
    for sep in [' ', '_', '.', ',']:
        text = text.replace(sep, '-')
    
    # Remove extra dashes
    text = re.sub(r'-+', '-', text)
    
    # Remove ALL suffix
    text = re.sub(r'-ALL$', '', text, flags=re.IGNORECASE)
    
    # Split by dash
    parts = text.split('-')
    
    if len(parts) < 4:
        return None
    
    # First part should be the slot
    slot = parts[0]
    
    # Find the course code (should be like CSE1005, MAT2003, etc.)
    course_code = None
    course_index = -1
    
    for i, part in enumerate(parts[1:], 1):
        if COURSE_CODE_RE.match(part):
            course_code = part
            course_index = i
            break
    
    if not course_code:
        return None
    
    # After course code, look for type tag
    type_tag = None
    type_index = -1
    
    if course_index + 1 < len(parts):
        potential_type = parts[course_index + 1]
        if potential_type in VALID_TYPE_TAGS:
            type_tag = potential_type
            type_index = course_index + 1
    
    if not type_tag:
        return None
    
    # After type tag, everything else is venue
    venue_parts = parts[type_index + 1:] if type_index + 1 < len(parts) else []
    
    # Special handling: if the type tag and venue were merged (e.g., "ELA102")
    if not venue_parts and type_index + 1 < len(parts):
        # Check if the next part contains the venue merged with type
        next_part = parts[type_index + 1] if type_index + 1 < len(parts) else ''
        if next_part and any(tag in next_part for tag in VALID_TYPE_TAGS):
            # Extract venue by removing the type tag
            for tag in VALID_TYPE_TAGS:
                if next_part.startswith(tag):
                    venue_part = next_part[len(tag):]
                    if venue_part:
                        venue_parts = [venue_part]
                    break
    
    venue = '-'.join(venue_parts) if venue_parts else ''
    
    # Clean the venue
    venue = _clean_venue(venue)
    
    # Determine type name
    if type_tag in ['TH', 'ETH']:
        type_name = 'THEORY'
    elif type_tag in ['ELA', 'EL']:
        type_name = 'LAB'
    else:
        type_name = type_tag
    
    print(f'  [parsed] "{text}" -> slot={slot}, code={course_code}, type={type_tag}, venue={venue}')
    
    return {
        'slot': slot,
        'course_code': course_code,
        'type_tag': type_tag,
        'type_name': type_name,
        'venue': venue,
    }


def _parse_simple_cell(text: str) -> Optional[dict]:
    """Parse cells that don't have a slot prefix (just course-type-venue)"""
    
    text = text.strip()
    
    # Replace various separators
    for sep in [' ', '_', '.', ',']:
        text = text.replace(sep, '-')
    text = re.sub(r'-+', '-', text)
    text = re.sub(r'-ALL$', '', text, flags=re.IGNORECASE)
    
    parts = text.split('-')
    
    if len(parts) < 3:
        return None
    
    # Try to find course code
    course_code = None
    course_index = -1
    
    for i, part in enumerate(parts):
        if COURSE_CODE_RE.match(part):
            course_code = part
            course_index = i
            break
    
    if not course_code:
        return None
    
    # Look for type tag after course
    type_tag = None
    if course_index + 1 < len(parts):
        if parts[course_index + 1] in VALID_TYPE_TAGS:
            type_tag = parts[course_index + 1]
    
    if not type_tag:
        return None
    
    # Venue is everything after type
    venue_parts = parts[course_index + 2:] if course_index + 2 < len(parts) else []
    venue = '-'.join(venue_parts) if venue_parts else ''
    venue = _clean_venue(venue)
    
    # Determine type name
    if type_tag in ['TH', 'ETH']:
        type_name = 'THEORY'
    elif type_tag in ['ELA', 'EL']:
        type_name = 'LAB'
    else:
        type_name = type_tag
    
    print(f'  [simple] "{text}" -> code={course_code}, type={type_tag}, venue={venue}')
    
    return {
        'course_code': course_code,
        'type_tag': type_tag,
        'type_name': type_name,
        'venue': venue,
        'slot': 'N/A',
    }


def _is_valid_course_code(code: str) -> bool:
    """Validate course code format"""
    if not code:
        return False
    return bool(COURSE_CODE_RE.match(code))


class OCRService:
    def __init__(self):
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)

    def clean_text(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

    def _preprocess_cell_for_ocr(self, cell_img: np.ndarray) -> np.ndarray:
        if len(cell_img.shape) != 3:
            cell_img = cv2.cvtColor(cell_img, cv2.COLOR_GRAY2BGR)
        
        h, w = cell_img.shape[:2]
        if h < 40 or w < 80:
            scale = max(40 / h, 80 / w, 2.0)
            cell_img = cv2.resize(cell_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
        return cell_img

    def extract_from_schedule_image(self, image_path: str) -> List[dict]:
        print('[Schedule] Extracting enriched cells only...')
        img = preprocess_for_ocr(image_path)
        crop_y = self._find_grid_top(img)
        img_crop = img[crop_y:, :] if crop_y > 0 else img

        cells = detect_table_cells(img_crop)
        if not cells:
            cells = detect_table_cells(img)
            img_crop = img
        if not cells:
            print('[Schedule] No grid detected')
            return []

        num_rows, num_cols = get_grid_dimensions(cells)
        print(f'[Schedule] Grid: {num_rows}r x {num_cols}c')

        flat_grid: Dict[Tuple[int, int], str] = {}

        for row_idx, col_idx, x, y, w, h in sorted(cells, key=lambda c: (c[0], c[1])):
            pad_x = max(1, int(w * 0.04))
            pad_y = max(1, int(h * 0.06))
            y1 = max(0, y + pad_y)
            y2 = min(img_crop.shape[0], y + h - pad_y)
            x1 = max(0, x + pad_x)
            x2 = min(img_crop.shape[1], x + w - pad_x)
            if y2 <= y1 or x2 <= x1:
                continue

            cell_proc = self._preprocess_cell_for_ocr(img_crop[y1:y2, x1:x2])
            ocr_result = self.ocr.ocr(cell_proc, cls=False)
            if ocr_result and ocr_result[0]:
                text = ' '.join(self.clean_text(r[1][0]) for r in ocr_result[0]).strip()
                if text:
                    flat_grid[(row_idx, col_idx)] = text

        return self._parse_grid_to_entries(flat_grid, num_rows, num_cols)

    def _find_grid_top(self, img: np.ndarray) -> int:
        h, w = img.shape[:2]
        result = self.ocr.ocr(img, cls=True)
        if not result or not result[0]:
            return 0
        bucket = max(int(h * 0.015), 8)
        rows_by_y: Dict[int, list] = {}
        for line in result[0]:
            text = self.clean_text(line[1][0]).upper()
            y = sum(p[1] for p in line[0]) / 4
            key = round(y / bucket) * bucket
            rows_by_y.setdefault(key, []).append(text)
        for y_key in sorted(rows_by_y.keys()):
            texts = rows_by_y[y_key]
            has_theory = any('THEORY' in t for t in texts)
            has_start = any(t == 'START' for t in texts)
            has_times = sum(1 for t in texts if re.match(r'^\d{1,2}:\d{2}$', t)) >= 3
            if (has_theory and has_start) or (has_theory and has_times):
                return max(0, y_key - bucket * 2)
        return 0

    def _parse_grid_to_entries(
        self,
        grid: Dict[Tuple[int, int], str],
        num_rows: int,
        num_cols: int,
    ) -> List[dict]:

        # Find time header
        time_col_map: Dict[int, int] = {}
        header_row = -1
        for row_idx in range(min(12, num_rows)):
            hours: Dict[int, int] = {}
            for col_idx in range(num_cols):
                text = grid.get((row_idx, col_idx), '').strip()
                for pat in [r'^(\d{1,2}):(\d{2})$', r'^(\d{1,2})\s(\d{2})$',
                            r'^(\d{1,2})\.(\d{2})$', r'^(\d{2})(\d{2})$']:
                    m = re.match(pat, text)
                    if m:
                        hh, mn = int(m.group(1)), int(m.group(2))
                        if 7 <= hh <= 20 and mn <= 5:
                            hours[col_idx] = hh
                            break
                if col_idx not in hours:
                    m = re.search(r'\b(\d{1,2}):00\b', text)
                    if m:
                        hh = int(m.group(1))
                        if 7 <= hh <= 20:
                            hours[col_idx] = hh
            if len(hours) >= 4:
                header_row = row_idx
                time_col_map = hours
                break

        if not time_col_map:
            print('[Schedule] Could not find time header')
            return []

        # Find lunch columns
        lunch_cols: set = set()
        for col_idx in range(num_cols):
            if 'LUNCH' in grid.get((header_row, col_idx), '').upper():
                lunch_cols.add(col_idx)

        # Build day mapping
        row_day_map: Dict[int, str] = {}
        
        for row_idx in range(header_row, num_rows):
            for col_idx in range(min(8, num_cols)):
                cell = self.clean_text(grid.get((row_idx, col_idx), '')).upper()
                if not cell:
                    continue
                
                for abbr, full in DAY_NAMES.items():
                    if cell == abbr or cell.startswith(abbr) or f" {abbr} " in f" {cell} ":
                        row_day_map[row_idx] = full
                        print(f'[Schedule] Found {full} at row {row_idx}, col {col_idx}: "{cell}"')
                        break
                if row_idx in row_day_map:
                    break
        
        # Fill day gaps
        last_day = None
        for row_idx in range(header_row, num_rows):
            if row_idx in row_day_map:
                last_day = row_day_map[row_idx]
            elif last_day:
                row_day_map[row_idx] = last_day

        # Build type mapping
        row_type_map: Dict[int, str] = {}
        for row_idx in range(header_row, num_rows):
            for col_idx in range(min(4, num_cols)):
                cell = self.clean_text(grid.get((row_idx, col_idx), '')).upper()
                if not cell:
                    continue
                
                if 'THEORY' in cell:
                    row_type_map[row_idx] = 'THEORY'
                    break
                elif 'LAB' in cell or re.search(r'\bLA[B8]\b', cell):
                    row_type_map[row_idx] = 'LAB'
                    break
            
            if row_idx not in row_type_map and row_idx - 1 in row_type_map:
                row_type_map[row_idx] = row_type_map[row_idx - 1]

        # Create time slot mapping for each column
        sorted_time_cols: List[int] = sorted(time_col_map.keys())
        col_to_time: Dict[int, str] = {}
        for col_idx in range(num_cols):
            hour = time_col_map.get(col_idx)
            if hour is None:
                left_cols = [c for c in sorted_time_cols if c <= col_idx]
                if left_cols:
                    hour = time_col_map[left_cols[-1]]
            if hour:
                col_to_time[col_idx] = HOUR_TO_SLOT.get(hour, f'{hour:02d}:00-{hour:02d}:50')

        # DEBUG: Print all cells in the grid to see what we're missing
        print("\n[DEBUG] === ALL CELLS IN GRID ===")
        for row_idx in sorted(grid.keys()):
            row_cells = []
            for col_idx in range(num_cols):
                text = grid.get((row_idx, col_idx), '')
                if text and len(text) > 2:
                    row_cells.append(f"[{col_idx}]\"{text[:40]}\"")
            if row_cells:
                day_info = f"DAY:{row_day_map.get(row_idx, '?')}" if row_idx in row_day_map else ""
                type_info = f"TYPE:{row_type_map.get(row_idx, '?')}" if row_idx in row_type_map else ""
                print(f"  Row {row_idx:2d} {day_info:15} {type_info:10} -> {', '.join(row_cells)}")
        print("[DEBUG] ====================\n")

        # Extract all entries
        entries: List[dict] = []
        
        for (row_idx, col_idx), text in grid.items():
            # Skip header rows and lunch columns
            if row_idx <= header_row + 1:
                continue
            if col_idx in lunch_cols:
                continue
            
            # Get day and type for this row
            current_day = row_day_map.get(row_idx)
            if not current_day:
                continue
            
            row_type = row_type_map.get(row_idx)
            if not row_type:
                continue
            
            # Skip cells that are too short or are labels
            if len(text) < 6 or text.upper() in ['THEORY', 'LAB', 'LUNCH', 'START', 'END', 'TUE', 'WED', 'THU', 'FRI', 'SAT']:
                continue
            
            # Get time for this column
            time_str = col_to_time.get(col_idx)
            if not time_str:
                continue
            
            # Try to parse as enriched cell first
            parsed = _parse_enriched_cell(text)
            
            # If that fails, try to parse as a simpler format
            if not parsed:
                parsed = _parse_simple_cell(text)
            
            if parsed:
                entries.append({
                    'day': current_day,
                    'time': time_str,
                    'type': parsed['type_name'],
                    'slot': parsed.get('slot', 'N/A'),
                    'course_code': parsed['course_code'],
                    'venue': parsed['venue'],
                })
                print(f'  [MATCHED] Row {row_idx}, Col {col_idx}: "{text}"')

        # Deduplicate
        seen_keys: set = set()
        result_entries: List[dict] = []
        for e in entries:
            key = (e['day'], e['time'], e['course_code'])
            if key not in seen_keys:
                seen_keys.add(key)
                result_entries.append(e)

        print(f'\n[Schedule] Extracted {len(result_entries)} total entries')
        
        # Group by day
        grouped = {}
        for entry in result_entries:
            day = entry['day']
            if day not in grouped:
                grouped[day] = []
            grouped[day].append(entry)
        
        for day, entries_list in grouped.items():
            print(f'  {day}: {len(entries_list)} entries')
        
        return result_entries

    def _debug_print_grid(self, grid: Dict[Tuple[int, int], str], num_rows: int, num_cols: int):
        """Debug: Print all non-empty cells in grid"""
        print("\n[DEBUG] All non-empty cells in grid:")
        for row_idx in range(num_rows):
            row_cells = []
            for col_idx in range(num_cols):
                text = grid.get((row_idx, col_idx), '')
                if text and len(text) > 2:
                    row_cells.append(f"({col_idx}){text[:30]}")
            if row_cells:
                print(f"  Row {row_idx}: {', '.join(row_cells)}")