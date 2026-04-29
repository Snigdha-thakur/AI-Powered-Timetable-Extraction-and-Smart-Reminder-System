import os
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
from datetime import datetime, timedelta  # noqa: F401
from typing import Dict, List
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

BYDAY_MAP = {
    "Monday": "MO", "Tuesday": "TU", "Wednesday": "WE",
    "Thursday": "TH", "Friday": "FR", "Saturday": "SA", "Sunday": "SU"
}

# Store code_verifier keyed by timetable_id between auth and callback
_code_verifiers: Dict[str, str] = {}


def _client_config():
    return {
        "web": {
            "client_id":     os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "redirect_uris": [os.environ["GOOGLE_REDIRECT_URI"]],
            "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
            "token_uri":     "https://oauth2.googleapis.com/token",
        }
    }


def get_google_auth_url(timetable_id: str, state: str = None) -> str:
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
    flow.redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=state or timetable_id,
    )
    if hasattr(flow, 'code_verifier') and flow.code_verifier:
        _code_verifiers[timetable_id] = flow.code_verifier
    elif hasattr(flow.oauth2session, '_code_verifier'):
        _code_verifiers[timetable_id] = flow.oauth2session._code_verifier
    return auth_url


def add_events_to_google_calendar(
    code: str,
    timetable_id: str,
    timetable_data: Dict[str, List[dict]],
    start_date,
    end_date,
):
    from app.services.google_calendar import _dates_for_weekday_in_range
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
    flow.redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]

    code_verifier = _code_verifiers.pop(timetable_id, None)
    if code_verifier:
        flow.fetch_token(code=code, code_verifier=code_verifier)
    else:
        flow.fetch_token(code=code)

    creds = flow.credentials
    service = build("calendar", "v3", credentials=creds)

    count = 0
    for day, entries in timetable_data.items():
        if day not in BYDAY_MAP:
            continue
        event_dates = _dates_for_weekday_in_range(day, start_date, end_date)

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

            for event_date in event_dates:
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
                    "reminders": {
                        "useDefault": False,
                        "overrides": [{"method": "popup", "minutes": 15}],
                    },
                }
                service.events().insert(calendarId="primary", body=event).execute()
                count += 1

    return count
