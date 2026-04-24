import re
from typing import Any

# Fixed time slots mapped by column index
TIME_SLOTS = [
    "08:00-08:50", "09:00-09:50", "10:00-10:50", "11:00-11:50",
    "12:00-12:50", "13:00-13:50", "14:00-14:50", "15:00-15:50",
    "16:00-16:50", "17:00-17:50", "18:00-18:50", "19:00-19:50",
]

IGNORE_VALUES = {"-", "--", "---", "----", "-----", "lunch", ""}

MAX_SLOTS = len(TIME_SLOTS)

# Matches schedule grid slot/cell codes like "A2-MAT1011", "G12-CB", "L27-CSE3002", "TF2-STS3007-TH"
# Must start with letters followed by digits — rules out plain course names
_SLOT_CODE_RE = re.compile(
    r'^[A-Z]{1,3}\d{1,2}[A-Z]?'    # slot prefix with digits: A2, G12, L27, TF2
    r'(?:-[A-Z0-9][\w-]*)?$',        # optional suffix: -MAT1011, -CB, -TH
    re.IGNORECASE
)


def _is_slot_code(s: str) -> bool:
    """True if s looks like a timetable slot/cell code (has letters+digits prefix)."""
    s = s.strip()
    # Must contain at least one digit to be a slot code
    return bool(re.search(r'\d', s)) and bool(_SLOT_CODE_RE.match(s))


def parse_timetable(raw_data: list[list[Any]]) -> dict:
    """
    Parse raw rows into a structured timetable dict.

    Row format from OCR (triplets):
      [Day, Type, name1, fac1, venue1, name2, fac2, venue2, ...]  → step=3

    Row format from manual /upload (pairs):
      [Day, Type, name1, fac1, name2, fac2, ...]  → step=2

    Detection: if (len - 2) % 3 == 0 and (len - 2) % 2 != 0 → triplets.
    Always caps at MAX_SLOTS (12) slots per row.
    """
    timetable: dict[str, list[dict]] = {}

    for row in raw_data:
        if len(row) < 3:
            continue

        day        = str(row[0]).strip()
        entry_type = str(row[1]).strip().upper()
        data_cols  = row[2:]
        n          = len(data_cols)

        # Detect triplet vs pair
        # Triplets: [name, faculty, venue, name, faculty, venue, ...]
        # Pairs:    [name, faculty, name, faculty, ...]
        # Heuristic: if n%3==0 and n%2!=0 → definitely triplets
        # If n%6==0 (divisible by both): check if every 3rd element looks like a venue
        # (empty string, or a venue code like "101-CB") vs a subject/faculty name
        if (n % 3 == 0) and (n % 2 != 0):
            use_triplets = True
        elif (n % 2 == 0) and (n % 3 != 0):
            use_triplets = False
        elif n % 6 == 0:
            # Ambiguous — sample every 3rd element starting at index 2
            venue_candidates = [str(data_cols[i]).strip() for i in range(2, n, 3)]
            # Venues are empty strings or match venue-like patterns; names/faculty are not
            use_triplets = all(
                v == "" or v == "-" or bool(re.match(r'^[A-Z0-9]{2,}-[A-Z]{2,}', v, re.I))
                for v in venue_candidates
            )
        else:
            use_triplets = False
        step = 3 if use_triplets else 2

        slot_idx = 0
        col = 0
        while col < n and slot_idx < MAX_SLOTS:
            subject = str(data_cols[col]).strip()
            faculty = str(data_cols[col + 1]).strip() if col + 1 < n else ""
            venue   = str(data_cols[col + 2]).strip() if (use_triplets and col + 2 < n) else ""

            if subject.lower() not in IGNORE_VALUES and not _is_slot_code(subject):
                fac = faculty if faculty.lower() not in IGNORE_VALUES and not _is_slot_code(faculty) else ""
                timetable.setdefault(day, []).append({
                    "type":    entry_type,
                    "time":    TIME_SLOTS[slot_idx],
                    "subject": subject,
                    "faculty": fac,
                    "venue":   venue   if venue.lower()   not in IGNORE_VALUES else "",
                })

            slot_idx += 1
            col += step

    return timetable
