# ocr.py

import cv2
import re
from paddleocr import PaddleOCR
from typing import Dict, List
from app.services.course_parser import CourseParser

VALID_SLOT_PREFIXES = {'A','B','C','D','E','F','G','L','T','TA','TB','TC','TD','TE','TF','TG','TAA','TBB','TCC','TDD','TEE','TFF','TGG'}
SLOT_RE = re.compile(r'\b([A-Z]{1,3}\d{1,2}[A-Z]?)\b')


def _is_valid_slot(s: str) -> bool:
    s = s.strip().rstrip('- ')
    m = re.match(r'^([A-Z]{1,3})(\d{1,2})[A-Z]?$', s)
    if not m:
        return False
    return m.group(1) in VALID_SLOT_PREFIXES and 1 <= int(m.group(2)) <= 60


class OCRService:
    def __init__(self):
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
        self._course_parser = CourseParser()

    def clean_text(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

    # ========== PHASE 1: Extract Course Data (via CourseParser) ==========

    def extract_courses(self, image_path: str):
        """
        Delegates to CourseParser.
        Returns (by_slot, by_code):
          by_slot: {slot_code: course_info}
          by_code: {course_code: course_info}
        """
        raw = self._course_parser.extract(image_path)
        by_slot: Dict[str, dict] = {}
        by_code: Dict[str, dict] = {}
        for code, entries in raw.items():
            for entry in entries:
                info = {
                    "course_code": code,
                    "course_name": entry.get("name", ""),
                    "type":        entry.get("type", ""),
                    "faculty":     entry.get("faculty", ""),
                    "venue":       entry.get("venue", ""),
                }
                by_code.setdefault(code, info)
                for slot in entry.get("slots", []):
                    if slot:
                        by_slot[slot] = info
        return by_slot, by_code

    # ========== PHASE 2: Extract Timetable Grid ==========

    def extract_timetable_grid(self, image_path: str) -> Dict[str, Dict[str, List[tuple]]]:
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")
        result = self.ocr.ocr(img, cls=True)

        elements = []
        for line in result[0]:
            bbox = line[0]
            text = self.clean_text(line[1][0])
            x_left   = min(p[0] for p in bbox)
            x_center = sum(p[0] for p in bbox) / 4
            y        = sum(p[1] for p in bbox) / 4
            elements.append((x_left, x_center, y, text))

        rows_by_y: Dict[int, list] = {}
        for x_left, x_center, y, text in elements:
            key = round(y / 20) * 20
            rows_by_y.setdefault(key, []).append((x_left, x_center, y, text))

        # ── Step 1: Find time header row ──────────────────────────────────
        time_row_y = None
        time_cols: List[tuple] = []
        for y_key, row_items in sorted(rows_by_y.items()):
            times_in_row = []
            seen_hours = set()
            for x_left, x_center, y, text in row_items:
                m = re.search(r'(\d{1,2}):?(\d{2})', text)
                if m:
                    hour, minute = int(m.group(1)), int(m.group(2))
                    if 8 <= hour <= 19 and minute == 0 and hour not in seen_hours:
                        seen_hours.add(hour)
                        times_in_row.append((x_left, f"{hour:02d}:00"))
            if len(times_in_row) >= 3:
                time_row_y = y_key
                time_cols = sorted(times_in_row, key=lambda t: t[0])
                break

        if not time_cols:
            raise RuntimeError("Could not find time header row in timetable image")

        print(f"    Time columns: {[t for _, t in time_cols]}")

        # ── Step 2: Find THEORY/LAB label rows and DAY label rows ─────────
        # Only look BELOW the time header — handles full-page screenshots
        THEORY_LAB = {'THEORY', 'LAB'}
        DAY_NAMES = {
            "MON": "MON", "TUE": "TUE", "WED": "WED",
            "THU": "THU", "FRI": "FRI", "SAT": "SAT", "SUN": "SUN",
            "MONDAY": "MON", "TUESDAY": "TUE", "WEDNESDAY": "WED",
            "THURSDAY": "THU", "FRIDAY": "FRI", "SATURDAY": "SAT",
        }

        theory_ys = []
        lab_ys    = []
        day_labels = []  # [(y, short_name)]

        for y_key, row_items in sorted(rows_by_y.items()):
            if y_key <= time_row_y:
                continue
            for x_left, x_center, y, text in row_items:
                t = text.upper().strip().rstrip('.')
                if t == 'THEORY':
                    theory_ys.append(y_key)
                    break
                if t == 'LAB':
                    lab_ys.append(y_key)
                    break
                if t in DAY_NAMES:
                    short = DAY_NAMES[t]
                    if not any(d == short for _, d in day_labels):
                        day_labels.append((y_key, short))
                    break

        print(f"    THEORY label ys: {theory_ys}")
        print(f"    LAB label ys:    {lab_ys}")
        print(f"    DAY labels: {day_labels}")

        # ── Step 3: Map each day to its THEORY and LAB row Y ─────────────
        # For each day label Y, find the nearest THEORY row above/at it
        # and nearest LAB row above/at it
        day_row_map: Dict[str, Dict[str, int]] = {}

        for day_y, day_short in day_labels:
            # THEORY row: closest theory_y that is <= day_y + 80
            t_candidates = [y for y in theory_ys if day_y - 20 <= y <= day_y + 80]
            l_candidates = [y for y in lab_ys    if day_y - 20 <= y <= day_y + 80]
            entry = {}
            if t_candidates:
                entry['THEORY'] = min(t_candidates, key=lambda y: abs(y - day_y))
            if l_candidates:
                entry['LAB'] = min(l_candidates, key=lambda y: abs(y - day_y))
            if entry:
                day_row_map[day_short] = entry

        print(f"    Day→row mapping: {day_row_map}")

        # ── Step 4: Build column x-boundaries ────────────────────────────
        col_bounds: List[tuple] = []
        for i, (x_left, time_str) in enumerate(time_cols):
            x_end = time_cols[i + 1][0] if i + 1 < len(time_cols) else float('inf')
            col_bounds.append((x_left, x_end, time_str))

        # ── Step 5: Extract slot codes per day per time column ────────────
        timetable: Dict[str, Dict[str, List[tuple]]] = {}

        for day_short, row_types in day_row_map.items():
            timetable[day_short] = {}

            for row_type, row_y in row_types.items():
                row_tokens = [
                    (x_left, x_center, text)
                    for x_left, x_center, y, text in elements
                    if abs(y - row_y) < 30
                ]
                for x_left, x_center, text in row_tokens:
                    if text.upper().strip() in ('THEORY', 'LAB', 'LUNCH', 'START', 'END'):
                        continue
                    for part in re.split(r'[\s]+', text):
                        compact = part.replace(' ', '')
                        if not compact or len(compact) < 2:
                            continue
                        slot_code = None
                        m = re.match(r'^([A-Z]{1,3}\d{1,2}[A-Z]?)(?:-|$|\+)', compact)
                        if m:
                            candidate = m.group(1)
                            if _is_valid_slot(candidate) and not re.match(r'^[A-Z]\d{2,}$', candidate):
                                slot_code = candidate
                        if not slot_code:
                            for candidate in SLOT_RE.findall(compact):
                                if _is_valid_slot(candidate) and not re.match(r'^[A-Z]\d{2,}$', candidate):
                                    slot_code = candidate
                                    break
                        if not slot_code:
                            continue
                        entry = (slot_code, compact, row_type)
                        for x_start, x_end, time_str in col_bounds:
                            if x_start <= x_center < x_end:
                                timetable[day_short].setdefault(time_str, []).append(entry)
                                break
                        else:
                            closest = min(time_cols, key=lambda tc: abs(tc[0] - x_center))
                            timetable[day_short].setdefault(closest[1], []).append(entry)

            # Deduplicate by (slot_code, row_type)
            timetable[day_short] = {
                t: list({(s, rt): (s, txt, rt) for s, txt, rt in entries}.values())
                for t, entries in timetable[day_short].items()
            }

        days_found = list(timetable.keys())
        print(f"    Days: {days_found}")
        for day, slots in list(timetable.items())[:2]:
            print(f"      {day}: {slots}")

        return timetable

    # ========== PHASE 3: Merge ==========

    def process_timetable(self, course_image_path: str, schedule_image_path: str) -> List[List[str]]:
        print("[Phase 1] Extracting course data...")
        courses, by_code = self.extract_courses(course_image_path)
        print(f"    {len(courses)} slot mappings, {len(by_code)} course codes")
        if courses:
            for slot, info in list(courses.items())[:5]:
                print(f"      {slot} -> {info.get('course_code')} ({info.get('type')})")

        print("\n[Phase 2] Extracting timetable grid...")
        timetable_grid = self.extract_timetable_grid(schedule_image_path)

        print("\n[Phase 3] Merging...")

        day_map = {
            "MON": "Monday", "TUE": "Tuesday", "WED": "Wednesday",
            "THU": "Thursday", "FRI": "Friday", "SAT": "Saturday", "SUN": "Sunday"
        }
        time_slots = [
            "08:00-08:50", "09:00-09:50", "10:00-10:50", "11:00-11:50",
            "12:00-12:50", "13:00-13:50", "14:00-14:50", "15:00-15:50",
            "16:00-16:50", "17:00-17:50", "18:00-18:50", "19:00-19:50"
        ]

        output_rows = []

        for day_short, time_slot_map in timetable_grid.items():
            day_full = day_map.get(day_short, day_short)

            theory_slots = {}
            lab_slots    = {}

            for time_str, slot_entries in time_slot_map.items():
                for slot_code, cell_text, row_type in slot_entries:
                    is_lab = (row_type == 'LAB') or slot_code.startswith('L')
                    if slot_code in courses:
                        info = courses[slot_code]
                        is_lab = is_lab or 'Lab' in info.get('type', '')
                        name = re.sub(r'\s*-\s*$', '', info.get('course_name', slot_code))
                        fac  = info.get('faculty', '')
                    else:
                        course_code_m = re.search(r'[A-Z]{2,4}\d{4}', cell_text)
                        if course_code_m and course_code_m.group(0) in by_code:
                            info = by_code[course_code_m.group(0)]
                            is_lab = is_lab or 'Lab' in info.get('type', '')
                            name = re.sub(r'\s*-\s*$', '', info.get('course_name', slot_code))
                            fac  = info.get('faculty', '')
                        else:
                            continue
                    target = lab_slots if is_lab else theory_slots
                    if time_str not in target:
                        target[time_str] = (slot_code, name, fac)

            if theory_slots:
                row = [day_full, "THEORY"]
                for ts in time_slots:
                    tk = ts.split("-")[0]
                    if tk in theory_slots:
                        _, name, fac = theory_slots[tk]
                        row += [name, fac]
                    else:
                        row += ["-", "-"]
                output_rows.append(row)

            if lab_slots:
                row = [day_full, "LAB"]
                for ts in time_slots:
                    tk = ts.split("-")[0]
                    if tk in lab_slots:
                        _, name, fac = lab_slots[tk]
                        row += [name, fac]
                    else:
                        row += ["-", "-"]
                output_rows.append(row)

        print(f"    Generated {len(output_rows)} rows")
        return output_rows
