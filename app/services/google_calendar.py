import uuid
from datetime import datetime, timedelta
from typing import Dict, List

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
BYDAY_MAP = {
    "Monday": "MO", "Tuesday": "TU", "Wednesday": "WE",
    "Thursday": "TH", "Friday": "FR", "Saturday": "SA", "Sunday": "SU"
}


def _next_weekday(day_name: str):
    today = datetime.today()
    target = DAY_ORDER.index(day_name)
    days_ahead = (target - today.weekday()) % 7 or 7
    return (today + timedelta(days=days_ahead)).date()


def generate_ics(timetable_data: Dict[str, List[dict]]) -> str:
    """Generate a single .ics file with all timetable events + 1-min popup reminders."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Timetable//EN",
        "CALSCALE:GREGORIAN",
        "X-WR-TIMEZONE:Asia/Kolkata",
    ]

    fmt = "%Y%m%dT%H%M%S"

    for day, entries in timetable_data.items():
        byday = BYDAY_MAP.get(day)
        if not byday:
            continue
        event_date = _next_weekday(day)

        for entry in entries:
            time_start = entry.get("time", "").split("-")[0].strip()
            if not time_start:
                continue
            try:
                hour, minute = map(int, time_start.split(":"))
            except ValueError:
                continue

            subject = entry.get("subject") or entry.get("course_code", "Class")
            faculty = entry.get("faculty", "")
            venue = entry.get("venue", "")

            start_dt = datetime(event_date.year, event_date.month, event_date.day, hour, minute)
            end_dt = start_dt + timedelta(minutes=50)

            description = "\\n".join(filter(None, [
                f"Faculty: {faculty}" if faculty else "",
                f"Venue: {venue}" if venue else "",
            ]))

            lines += [
                "BEGIN:VEVENT",
                f"UID:{uuid.uuid4()}@timetable",
                f"DTSTART;TZID=Asia/Kolkata:{start_dt.strftime(fmt)}",
                f"DTEND;TZID=Asia/Kolkata:{end_dt.strftime(fmt)}",
                f"RRULE:FREQ=WEEKLY;BYDAY={byday}",
                f"SUMMARY:{subject}",
                f"DESCRIPTION:{description}",
                "BEGIN:VALARM",
                "TRIGGER:-PT15M",
                "ACTION:DISPLAY",
                f"DESCRIPTION:Reminder: {subject} starts in 15 minutes",
                "END:VALARM",
                "END:VEVENT",
            ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
