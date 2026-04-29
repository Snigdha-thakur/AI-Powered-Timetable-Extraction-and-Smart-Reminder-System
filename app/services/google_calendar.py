import uuid
from datetime import datetime, timedelta, date
from typing import Dict, List

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
BYDAY_MAP = {
    "Monday": "MO", "Tuesday": "TU", "Wednesday": "WE",
    "Thursday": "TH", "Friday": "FR", "Saturday": "SA", "Sunday": "SU"
}


def _dates_for_weekday_in_range(day_name: str, start: date, end: date) -> List[date]:
    """Return all dates matching day_name between start and end inclusive."""
    target = DAY_ORDER.index(day_name)
    result = []
    delta = (target - start.weekday()) % 7
    current = start + timedelta(days=delta)
    while current <= end:
        result.append(current)
        current += timedelta(weeks=1)
    return result


def generate_ics(timetable_data: Dict[str, List[dict]], start_date: date = None, end_date: date = None) -> str:
    """Generate a .ics file. If start_date/end_date given, creates individual events per occurrence.
    Otherwise creates weekly recurring events."""
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
            description = "\\n".join(filter(None, [
                f"Faculty: {faculty}" if faculty else "",
                f"Venue: {venue}" if venue else "",
            ]))

            if start_date and end_date:
                # Generate one event per occurrence in the date range
                for event_date in _dates_for_weekday_in_range(day, start_date, end_date):
                    start_dt = datetime(event_date.year, event_date.month, event_date.day, hour, minute)
                    end_dt = start_dt + timedelta(minutes=50)
                    lines += [
                        "BEGIN:VEVENT",
                        f"UID:{uuid.uuid4()}@timetable",
                        f"DTSTART;TZID=Asia/Kolkata:{start_dt.strftime(fmt)}",
                        f"DTEND;TZID=Asia/Kolkata:{end_dt.strftime(fmt)}",
                        f"SUMMARY:{subject}",
                        f"DESCRIPTION:{description}",
                        "BEGIN:VALARM",
                        "TRIGGER:-PT15M",
                        "ACTION:DISPLAY",
                        f"DESCRIPTION:Reminder: {subject} starts in 15 minutes",
                        "END:VALARM",
                        "END:VEVENT",
                    ]
            else:
                # Recurring weekly (no date range)
                from datetime import date as date_type
                today = datetime.today()
                target = DAY_ORDER.index(day)
                days_ahead = (target - today.weekday()) % 7 or 7
                event_date = (today + timedelta(days=days_ahead)).date()
                start_dt = datetime(event_date.year, event_date.month, event_date.day, hour, minute)
                end_dt = start_dt + timedelta(minutes=50)
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
