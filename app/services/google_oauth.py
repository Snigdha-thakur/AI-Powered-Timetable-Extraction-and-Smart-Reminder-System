import os
from datetime import datetime, timedelta
from typing import Dict, List
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

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


def get_google_auth_url(timetable_id: str) -> str:
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id":     os.environ["GOOGLE_CLIENT_ID"],
                "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
                "redirect_uris": [os.environ["GOOGLE_REDIRECT_URI"]],
                "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
                "token_uri":     "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=timetable_id,   # pass timetable_id through OAuth state
    )
    return auth_url


def add_events_to_google_calendar(code: str, timetable_data: Dict[str, List[dict]]):
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id":     os.environ["GOOGLE_CLIENT_ID"],
                "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
                "redirect_uris": [os.environ["GOOGLE_REDIRECT_URI"]],
                "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
                "token_uri":     "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]
    flow.fetch_token(code=code)

    creds = flow.credentials
    service = build("calendar", "v3", credentials=creds)

    count = 0
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
            venue   = entry.get("venue", "")

            start_dt = datetime(event_date.year, event_date.month, event_date.day, hour, minute)
            end_dt   = start_dt + timedelta(minutes=50)

            event = {
                "summary": subject,
                "description": "\n".join(filter(None, [
                    f"Faculty: {faculty}" if faculty else "",
                    f"Venue: {venue}"     if venue   else "",
                ])),
                "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kolkata"},
                "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "Asia/Kolkata"},
                "recurrence": [f"RRULE:FREQ=WEEKLY;BYDAY={byday}"],
                "reminders": {
                    "useDefault": False,
                    "overrides": [{"method": "popup", "minutes": 15}],
                },
            }
            service.events().insert(calendarId="primary", body=event).execute()
            count += 1

    return count
