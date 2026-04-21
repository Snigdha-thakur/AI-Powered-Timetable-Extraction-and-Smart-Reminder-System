"""
CourseParser v10

Fixes over v9:
1. "Faculty Detalls" accepted as faculty name — reject text that contains
   any header keyword (Slot, Venue, Course, Faculty, Class, Category, etc.)
2. TFF2 false slot — tighten VALID_SLOT_PREFIXES: only T+single-letter
   (TA,TB,TC,TD,TE,TF,TG) are valid T-prefixed slots, not TFF/TBB/TCC etc.
   TFF2/TBB1/TCC1 are timetable grid codes, not course slots.
3. CSE3003 missing slots — slot-row classification: a row with ONLY a venue
   and no slots was being dropped. Fix: also buffer rows that have a venue
   AND are the first sub-row above an anchor (i.e. pending is empty).
4. MAT1011 venue wrong (NIL-ONL from ECS3001 bleeding) — venue collection
   now only uses the FIRST venue found per block (the one from the slot-row),
   not later continuation rows which may carry the next course's venue.
5. TEC3001 duplicate slot pairs — when a block accumulates slots from two
   sub-rows (theory + lab leaked together), we split on the declared type
   and only keep slots consistent with it, rather than returning all.
6. STS2007 missing — was likely dropped because its slot-row had no slots
   detected. Add looser anchor: if pending is None when anchor fires and
   the immediately preceding OCR row had slot_venue content, include it.
"""

import cv2
import re
import json
from paddleocr import PaddleOCR


# ── Header keywords (used for noise rejection too) ────────────────────────────
HEADER_KEYWORDS = [
    ("sl_no",       ["sl.no", "sl no", "slno", "sl.", "s.no"]),
    ("class_group", ["class group"]),
    ("course",      ["course"]),
    ("lt_pj",       ["lt pj", "l t p j", "credit"]),
    ("category",    ["category"]),
    ("option",      ["option"]),
    ("class_nbr",   ["class nbr", "class nb", "class no"]),
    ("slot_venue",  ["slot", "venue"]),
    ("faculty",     ["faculty", "faculty detail", "faculty name"]),
    ("reg_date",    ["registered", "updated"]),
    ("att_type",    ["attendance"]),
    ("status",      ["status", "ref no"]),
]

# All header keyword fragments — used to reject OCR noise that reads headers
ALL_HEADER_FRAGMENTS = {kw for _, kws in HEADER_KEYWORDS for kw in kws}

COURSE_CODE_RE = re.compile(r'\b([A-Z]{2,4}\d{4})\b')

TYPE_RE = re.compile(
    r'\(?\s*(Embedded\s+Theory|Embedded\s+Lab|Theory\s+Only|Lab\s+Only|Project|Non.Credit\s+Club)\s*\)?',
    re.IGNORECASE
)

SLOT_RE = re.compile(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?)\b')

VENUE_RE = re.compile(
    r'\b('
    r'\d{2,3}-[A-Z0-9][\w-]*'
    r'|[A-Z]\d{1,2}-[A-Z]{2,}[\w-]*'
    r'|ONL\w*-ONL'
    r'|NIL-ONL|NILL?-ONL'
    r')\b',
    re.IGNORECASE
)

# ── FIXED: only single-letter T-prefixes are valid course slots ───────────────
# TFF2, TBB1, TCC1 etc. are timetable GRID codes, not course slot names.
VALID_SLOT_PREFIXES = {
    'A','B','C','D','E','F','G','L',
    'TA','TB','TC','TD','TE','TF','TG','T',
}

NEVER_FACULTY = {
    'BIOMETRIC','MANUAL','SUBJECT','OFFERING','REGISTERED',
    'SEMESTER','REGULAR','PROJECT','CATEGORY','OPTION',
    'CLASS','FACULTY','DETAILS','UPDATED','DATE','TYPE',
    'STATUS','REF','NOTE','NOTES','GENERAL','VTOP','VIT',
    # Add header cell fragments explicitly
    'VENUE','SLOT','COURSE','GROUP','CATEGORY','OPTION',
    'ATTENDANCE','REGISTERED','UPDATED','TIME',
}

BUILDING_CODE_RE = re.compile(r'^[A-Z]{2,6}$')

FOOTER_RE  = re.compile(r'Total\s+Number\s+of\s+Credits', re.IGNORECASE)

ROW_NOISE_RE = re.compile(
    r'(vtop\.vitap|VIT.AP\s+UNIVERSITY|Quick\s+Links'
    r'|Students\s+are\s+required'
    r'|Only\s+Registered'
    r'|Time\s+Table'
    r'|Winter\s+Semester|Summer\s+Semester'
    r'|Registered\s+and\s+Approved'
    r'|22[A-Z]{2}[A-Z0-9]+\s*\(STUDENT\)'
    r')',
    re.IGNORECASE
)

TOKEN_NOISE_RE = re.compile(
    r'^('
    r'AP\d{10,}'
    r'|\d{2}-[A-Z][a-z]{2}-\d{4}'
    r'|Subject\s+to'
    r'|Registered'
    r'|-\s*(Manual|Biometric)'
    r'|VIT.AP'
    r')\b',
    re.IGNORECASE
)


def clean(text):
    return re.sub(r'\s+', ' ', text).strip()

def fix_ocr_digits(text):
    return re.sub(r'\b([A-Z]{1,2}\d)[O]\b', lambda m: m.group(1) + '0', text)

def is_valid_slot(s):
    s = fix_ocr_digits(s).rstrip('- ').strip()
    m = re.match(r'^([A-Z]{1,3})(\d{1,2})[A-Z]?$', s)
    if not m:
        return False
    prefix = m.group(1)
    num    = int(m.group(2))
    # Reject multi-letter T-prefixes like TFF, TBB, TCC (timetable grid codes)
    if len(prefix) == 3:
        return False
    return prefix in VALID_SLOT_PREFIXES and 1 <= num <= 60

def extract_venue(text):
    m = VENUE_RE.search(text)
    return m.group(1).upper() if m else ""

def extract_slots(text):
    text = fix_ocr_digits(text)
    masked = VENUE_RE.sub(lambda m: ' ' * len(m.group(0)), text)
    return list(dict.fromkeys(
        s for s in SLOT_RE.findall(masked) if is_valid_slot(s)
    ))

def looks_like_building_code(word):
    return bool(BUILDING_CODE_RE.match(word)) and word == word.upper()

def contains_header_fragment(text):
    """True if text looks like it's an OCR reading of a table header cell."""
    t = text.lower()
    # Check for multi-word header phrases
    for kws in [kws for _, kws in HEADER_KEYWORDS]:
        for kw in kws:
            if kw in t and len(kw) > 4:  # only match phrases, not single letters
                return True
    # Check if it's a mashup of header words (e.g. "Class Group Course P Category")
    header_word_count = sum(
        1 for kw in ALL_HEADER_FRAGMENTS
        if len(kw) > 4 and kw in t
    )
    return header_word_count >= 2

def is_faculty_candidate(text):
    # ── Reject header cell OCR noise ──────────────────────────────────────
    if contains_header_fragment(text):
        return False

    t = re.sub(r'^(Prof|Dr|Ms|Mr|Mrs)\.?\s*', '', text.rstrip("-").strip(), flags=re.I)
    if not t or len(t) < 3:
        return False
    if re.match(r'^\d', t):
        return False
    if TOKEN_NOISE_RE.match(t):
        return False

    words = t.split()
    if not words:
        return False

    upper = {w.upper().rstrip('-') for w in words}
    if upper <= NEVER_FACULTY:
        return False

    if all(looks_like_building_code(w) for w in words):
        return False

    if all(re.match(r'^[\d.\-]+$', w) for w in words):
        return False

    alpha = [w for w in words if re.match(r'^[A-Za-z]{2,}$', w)]
    if not alpha:
        return False

    if len(words) == 1:
        return not looks_like_building_code(words[0])

    return True

def clean_course_name(raw, code):
    name = raw
    name = re.sub(r'\b' + re.escape(code) + r'\b', '', name)
    name = TYPE_RE.sub('', name)
    name = re.sub(r'\bAP\d+\b', '', name)
    name = re.sub(r'\d{2}-[A-Z][a-z]{2}-\d{4}', '', name)
    name = re.sub(r'\b\d+\.?\d*\b', '', name)
    name = re.sub(r'\b[A-Z]{2,6}\b', lambda m: '' if looks_like_building_code(m.group()) else m.group(), name)
    name = re.sub(r'\b(General|Semester|Regular|Subject|Offering|Non.Credit\s+Club)\b', '', name, flags=re.I)
    name = re.sub(r'\s*-\s*$', '', name)
    name = re.sub(r'^\s*-\s*', '', name)
    name = re.sub(r'\s*-\s*', ' ', name)
    name = re.sub(r"[^A-Za-z0-9 &,.']", ' ', name)
    return re.sub(r'\s+', ' ', name).strip()

def infer_type(declared, slots):
    if not slots:
        return declared
    families = {s[0] for s in slots}
    has_L, has_non_L = 'L' in families, bool(families - {'L'})
    if declared:
        if 'Lab' in declared and has_non_L and not has_L:
            return "Theory Only" if "Only" in declared else "Embedded Theory"
        if 'Theory' in declared and has_L and not has_non_L:
            return "Lab Only" if "Only" in declared else "Embedded Lab"
        return declared
    return ("Embedded Lab" if has_L and not has_non_L
            else "Embedded Theory" if has_non_L and not has_L
            else "Embedded Lab")

def filter_slots_for_type(slots, declared):
    """
    If a block accidentally accumulated both theory and lab slots
    but has a single declared type, keep only the slots that match.
    """
    if not declared or not slots:
        return slots
    lab_slots    = [s for s in slots if s[0] == 'L']
    theory_slots = [s for s in slots if s[0] != 'L']
    if 'Lab' in declared and 'Theory' not in declared:
        return lab_slots if lab_slots else slots
    if 'Theory' in declared and 'Lab' not in declared:
        return theory_slots if theory_slots else slots
    return slots


# ── Column auto-detection ──────────────────────────────────────────────────────

def auto_detect_columns(ocr_lines, image_width):
    all_items = []
    for line in ocr_lines:
        bbox = line[0]
        text = clean(line[1][0])
        x    = sum(p[0] for p in bbox) / 4
        y    = sum(p[1] for p in bbox) / 4
        all_items.append((text, x, y, x / image_width * 100))

    footer_y = float('inf')
    for text, x, y, xp in all_items:
        if FOOTER_RE.search(text):
            footer_y = min(footer_y, y)
    items = [(t, x, y, xp) for t, x, y, xp in all_items if y < footer_y]

    # Anchor: combined slot tokens e.g. "A2+TA2 -"
    slot_xs, course_xs = [], []
    for text, x, y, xp in items:
        t = text.strip()
        if re.search(r'[A-Z]{1,2}\d{1,2}[A-Z]?\s*\+\s*[A-Z]{1,2}\d', t):
            slot_xs.append(xp)
        if COURSE_CODE_RE.match(t):
            course_xs.append(xp)

    if not slot_xs:
        for text, x, y, xp in items:
            t = text.strip()
            if re.match(r'^[A-Z]{1,2}\d{1,2}[A-Z]?$', t) and is_valid_slot(t):
                slot_xs.append(xp)

    if not slot_xs:
        return None

    def median(xs):
        s = sorted(xs)
        m = len(s) // 2
        return (s[m-1] + s[m]) / 2 if len(s) % 2 == 0 else s[m]

    sv_center  = median(slot_xs)
    crs_center = median(course_xs) if course_xs else sv_center * 0.4

    faculty_xs = [
        xp for text, x, y, xp in items
        if sv_center + 3 < xp < sv_center + 18
        and is_faculty_candidate(text.strip())
        and not TOKEN_NOISE_RE.match(text.strip())
        and not looks_like_building_code(text.strip())
    ]
    fac_center = median(faculty_xs) if len(faculty_xs) >= 2 else sv_center + 8

    course_right = (crs_center + sv_center) / 2
    sv_right     = (sv_center + fac_center) / 2
    fac_right    = min(fac_center + 15.0, 100.0)

    boundaries = {
        "course":     (0.0,          course_right),
        "slot_venue": (course_right, sv_right),
        "faculty":    (sv_right,     fac_right),
    }
    for col, _ in HEADER_KEYWORDS:
        if col not in boundaries:
            boundaries[col] = (0.0, 0.0)

    print(f"    [auto-detect] course={crs_center:.1f}%  slot_venue={sv_center:.1f}%  faculty={fac_center:.1f}%")
    return boundaries

def assign_column(x, image_width, boundaries):
    xp = x / image_width * 100
    for name, (x0, x1) in boundaries.items():
        if x0 <= xp < x1:
            return name
    return None


# ── Main parser ────────────────────────────────────────────────────────────────

class CourseParser:
    def __init__(self):
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)

    def _run_ocr(self, image_path):
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Cannot read: {image_path}")
        h, w = img.shape[:2]
        result = self.ocr.ocr(img, cls=True)
        return result[0], w, h

    def _ocr_to_elements(self, ocr_lines, image_width, boundaries):
        footer_y = float('inf')
        for line in ocr_lines:
            text = clean(line[1][0])
            if FOOTER_RE.search(text):
                y = sum(p[1] for p in line[0]) / 4
                footer_y = min(footer_y, y)

        elements = []
        for line in ocr_lines:
            bbox = line[0]
            text = clean(line[1][0])
            if not text:
                continue
            x = sum(p[0] for p in bbox) / 4
            y = sum(p[1] for p in bbox) / 4
            if y >= footer_y:
                continue
            if TOKEN_NOISE_RE.match(text):
                continue
            col = assign_column(x, image_width, boundaries)
            if col:
                elements.append({"col": col, "text": text, "x": x, "y": y})
        return elements

    def _group_ocr_rows(self, elements, y_threshold=16):
        rows = {}
        for e in elements:
            placed = False
            for key in rows:
                if abs(e["y"] - key) < y_threshold:
                    rows[key].append(e)
                    placed = True
                    break
            if not placed:
                rows[e["y"]] = [e]
        return [(y, sorted(r, key=lambda e: e["x"])) for y, r in sorted(rows.items())]

    def _col_texts_of_row(self, row):
        ct = {}
        for e in row:
            ct.setdefault(e["col"], []).append(e["text"])
        return ct

    def _build_blocks(self, sorted_rows):
        def new_block():
            return {}

        def merge(block, ct):
            for col, texts in ct.items():
                block.setdefault(col, []).extend(texts)

        blocks  = []
        current = None
        pending = None
        prev_ct = None   # track the immediately preceding OCR row

        for y, row in sorted_rows:
            row_text = " ".join(e["text"] for e in row)
            if ROW_NOISE_RE.search(row_text):
                continue

            ct = self._col_texts_of_row(row)

            # ── ANCHOR ────────────────────────────────────────────────────
            is_anchor = any(
                COURSE_CODE_RE.search(t)
                for t in ct.get("course", [])
            )
            if is_anchor:
                if current is not None:
                    blocks.append(current)
                current = new_block()
                # If no pending but previous row had slot_venue content, use it
                if pending is None and prev_ct is not None:
                    sv_prev = " ".join(prev_ct.get("slot_venue", []))
                    if extract_slots(sv_prev) or extract_venue(sv_prev) or \
                       re.search(r'\bNILL?\b', sv_prev, re.I):
                        pending = prev_ct
                if pending is not None:
                    merge(current, pending)
                    pending = None
                merge(current, ct)
                prev_ct = ct
                continue

            # ── Row classification ─────────────────────────────────────────
            sv        = " ".join(ct.get("slot_venue", []))
            has_slots = bool(extract_slots(sv))
            has_venue = bool(extract_venue(sv))
            has_nil   = bool(re.search(r'\bNILL?\b', sv, re.I))
            has_fac   = any(
                is_faculty_candidate(t.rstrip("-").strip())
                for t in ct.get("faculty", [])
            )

            is_slot_row = has_slots or has_nil

            if is_slot_row:
                if pending is not None and current is not None:
                    merge(current, pending)
                pending = ct
                prev_ct = ct
                continue

            if has_fac and not has_slots and not has_venue:
                if pending is not None and current is not None:
                    merge(current, pending)
                pending = ct
                prev_ct = ct
                continue

            # Continuation (venue-only, type bracket, etc.)
            if current is not None:
                # ── FIX: only collect venue from continuation if block
                #    doesn't already have one ──────────────────────────────
                if has_venue:
                    existing_sv = " ".join(current.get("slot_venue", []))
                    if not extract_venue(existing_sv):
                        # Block has no venue yet — take this one
                        merge(current, {"slot_venue": ct.get("slot_venue", [])})
                    # else: block already has venue — don't overwrite it
                else:
                    merge(current, ct)

            prev_ct = ct

        if current is not None:
            if pending is not None:
                merge(current, pending)
            blocks.append(current)

        return blocks

    def _parse_block(self, block):
        course_raw = " ".join(block.get("course", []))
        code_m = COURSE_CODE_RE.search(course_raw)
        if not code_m:
            return []
        code = code_m.group(1)

        type_m   = TYPE_RE.search(course_raw)
        declared = re.sub(r'\s+', ' ', type_m.group(1).title()).strip() if type_m else ""
        if declared and 'Credit' in declared:
            declared = "Project"

        name = clean_course_name(course_raw, code)
        if not name:
            return []

        sv_raw    = " ".join(block.get("slot_venue", []))
        all_slots = extract_slots(sv_raw)
        venue     = extract_venue(sv_raw)
        is_nil    = bool(re.search(r'\bNILL?\b', sv_raw, re.IGNORECASE))

        faculty = ""
        for t in block.get("faculty", []):
            t_clean = t.rstrip("-").strip()
            if not t_clean:
                continue
            if is_faculty_candidate(t_clean):
                m_p = re.match(r'^(Prof|Dr|Ms|Mr|Mrs)\.?\s*', t_clean, re.I)
                if m_p:
                    prefix  = m_p.group(1).title()
                    rest    = t_clean[m_p.end():].strip()
                    faculty = f"{prefix}. {rest}"
                else:
                    faculty = t_clean
                break

        if is_nil and not declared:
            declared = "Project"

        # Split theory+lab if both present
        lab_slots    = [s for s in all_slots if s[0] == 'L']
        theory_slots = [s for s in all_slots if s[0] != 'L']

        if lab_slots and theory_slots:
            return [
                (code, {"name": name, "type": "Embedded Theory",
                        "slots": theory_slots,
                        "slot_families": sorted({s[0] for s in theory_slots}),
                        "venue": venue, "faculty": faculty}),
                (code, {"name": name, "type": "Embedded Lab",
                        "slots": lab_slots, "slot_families": ["L"],
                        "venue": venue, "faculty": faculty}),
            ]

        # ── FIX: if declared type contradicts slots, filter slots ──────────
        filtered_slots = filter_slots_for_type(all_slots, declared)

        final_type = infer_type(declared, filtered_slots)
        if not final_type:
            return []

        return [(code, {
            "name": name, "type": final_type,
            "slots": filtered_slots,
            "slot_families": sorted({s[0] for s in filtered_slots}),
            "venue": venue, "faculty": faculty,
        })]

    def _ensure_theory_companion(self, courses):
        for code, entries in courses.items():
            types = [e["type"] for e in entries]
            if "Embedded Lab" in types and "Embedded Theory" not in types:
                ref = next(e for e in entries if e["type"] == "Embedded Lab")
                courses[code].append({
                    "name": ref["name"], "type": "Embedded Theory",
                    "slots": [], "slot_families": [],
                    "venue": "", "faculty": ref["faculty"],
                })

    def extract(self, image_path):
        print("[1] Running OCR...")
        ocr_lines, img_w, img_h = self._run_ocr(image_path)
        print(f"    Image: {img_w}x{img_h}px, {len(ocr_lines)} OCR detections")

        print("[2] Auto-detecting column boundaries...")
        boundaries = auto_detect_columns(ocr_lines, img_w)
        if boundaries is None:
            raise RuntimeError(
                "Could not detect column positions. "
                "Ensure the VTOP course table is visible with slot codes."
            )

        print("[3] Assigning elements to columns...")
        elements = self._ocr_to_elements(ocr_lines, img_w, boundaries)
        print(f"    {len(elements)} elements assigned")

        print("[4] Grouping into OCR rows...")
        sorted_rows = self._group_ocr_rows(elements)
        print(f"    {len(sorted_rows)} OCR rows")

        print("[5] Building course blocks...")
        blocks = self._build_blocks(sorted_rows)
        print(f"    {len(blocks)} block(s)")

        print("[6] Parsing blocks...")
        courses = {}
        for block in blocks:
            for code, entry in self._parse_block(block):
                courses.setdefault(code, [])
                if entry["type"] in [e["type"] for e in courses[code]]:
                    continue
                courses[code].append(entry)
                print(
                    f"    [OK] {code} | {entry['type']:20s} | "
                    f"slots={entry['slots']} | venue={entry['venue']!r} | "
                    f"faculty={entry['faculty']!r}"
                )

        print("[7] Ensuring Embedded Theory companions...")
        self._ensure_theory_companion(courses)
        return courses


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "course.png"
    parser = CourseParser()
    data = parser.extract(path)
    print("\n" + "=" * 60)
    print("FINAL OUTPUT")
    print("=" * 60)
    print(json.dumps(data, indent=2))