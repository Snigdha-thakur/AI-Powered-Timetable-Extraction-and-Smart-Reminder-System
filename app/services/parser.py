from typing import Any

# Fixed time slots mapped by column index (index 0 = day, 1 = type, 2+ = subjects)
TIME_SLOTS = [
    "08:00-08:50", "09:00-09:50", "10:00-10:50", "11:00-11:50",
    "12:00-12:50", "13:00-13:50", "14:00-14:50", "15:00-15:50",
    "16:00-16:50", "17:00-17:50", "18:00-18:50", "19:00-19:50",
]

IGNORE_VALUES = {"-", "--", "lunch", ""}


def parse_timetable(raw_data: list[list[Any]]) -> dict:
    """
    Parse OCR-like raw rows into a structured timetable dict.

    Each row format:
      [Day, Type, subject1, faculty1, subject2, faculty2, ...]

    Subject and faculty are separate columns.
    Pairs: (col2, col3) → slot0, (col4, col5) → slot1, ...
    """
    timetable: dict[str, list[dict]] = {}

    for row in raw_data:
        if len(row) < 3:
            continue

        day = str(row[0]).strip()
        entry_type = str(row[1]).strip().upper()  # THEORY or LAB

        # Step through subject+faculty pairs starting at index 2
        slot_idx = 0
        col = 2
        while col < len(row):
            subject = str(row[col]).strip()
            faculty = str(row[col + 1]).strip() if col + 1 < len(row) else ""

            # Skip ignored subjects
            if subject.lower() not in IGNORE_VALUES:
                time_slot = TIME_SLOTS[slot_idx] if slot_idx < len(TIME_SLOTS) else f"slot-{slot_idx}"
                timetable.setdefault(day, []).append({
                    "type": entry_type,
                    "time": time_slot,
                    "subject": subject,
                    "faculty": faculty if faculty.lower() not in IGNORE_VALUES else "",
                })

            slot_idx += 1
            col += 2  # move to next subject+faculty pair

    return timetable
