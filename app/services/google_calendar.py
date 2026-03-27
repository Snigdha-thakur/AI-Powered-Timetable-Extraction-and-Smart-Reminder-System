import os
from datetime import datetime, timedelta
from typing import List, Dict
from urllib.parse import urlencode

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


def create_calendar_link(day: str, time: str, subject: str, faculty: str = "") -> str:
    """Generate a Google Calendar event link — no credentials needed."""
    event_date = _next_weekday(day)
    hour, minute = map(int, time.split(":"))
    start_dt = datetime(event_date.year, event_date.month, event_date.day, hour, minute)
    end_dt = start_dt + timedelta(minutes=50)

    fmt = "%Y%m%dT%H%M%S"
    params = {
        "action": "TEMPLATE",
        "text": subject,
        "dates": f"{start_dt.strftime(fmt)}/{end_dt.strftime(fmt)}",
        "details": f"Faculty: {faculty}" if faculty else "",
        "recur": f"RRULE:FREQ=WEEKLY;BYDAY={BYDAY_MAP[day]}",
    }
    return "https://calendar.google.com/calendar/render?" + urlencode(params)


def create_all_calendar_links(timetable_data: Dict[str, List[dict]]) -> List[str]:
    """Generate Google Calendar links for every class in the timetable."""
    urls = []
    for day, entries in timetable_data.items():
        for entry in entries:
            time_start = entry.get("time", "").split("-")[0]
            if not time_start:
                continue
            url = create_calendar_link(
                day=day,
                time=time_start,
                subject=entry.get("subject", ""),
                faculty=entry.get("faculty", ""),
            )
            urls.append(url)
    return urls
