import os
import time
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
from datetime import datetime, timedelta  # noqa: F401
from typing import Dict, List
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

BYDAY_MAP = {
    "Monday": "MO", "Tuesday": "TU", "Wednesday": "WE",
    "Thursday": "TH", "Friday": "FR", "Saturday": "SA", "Sunday": "SU"
}

# Store code_verifier keyed by timetable_id between auth and callback
_code_verifiers: Dict[str, str] = {}

# Track which action to perform in callback: "add" or "delete"
_pending_actions: Dict[str, str] = {}


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


def get_google_auth_url(timetable_id: str, state: str = None, action: str = "add") -> str:
    _pending_actions[timetable_id] = action
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
    all_events = []
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
                all_events.append({
                    "summary": subject,
                    "location": venue,
                    "description": "\n".join(filter(None, [
                        f"Faculty: {faculty}" if faculty else "",
                        f"Venue: {venue}"     if venue   else "",
                    ])),
                    "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kolkata"},
                    "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "Asia/Kolkata"},
                    "reminders": {
                        "useDefault": False,
                        "overrides": [{"method": "popup", "minutes": 10}],
                    },
                    "extendedProperties": {
                        "private": {"timetable_id": timetable_id}
                    },
                })

    # Insert in batches of 50 with retry on rate limit
    BATCH_SIZE = 50
    for i in range(0, len(all_events), BATCH_SIZE):
        batch = service.new_batch_http_request()
        for event in all_events[i:i + BATCH_SIZE]:
            batch.add(service.events().insert(calendarId="primary", body=event))
        for attempt in range(5):
            try:
                batch.execute()
                count += len(all_events[i:i + BATCH_SIZE])
                break
            except HttpError as e:
                if e.resp.status == 403 and attempt < 4:
                    time.sleep(2 ** attempt)
                else:
                    raise
        time.sleep(0.5)  # small pause between batches

    return count


def delete_timetable_events_from_google_calendar(code: str, timetable_id: str, start_date, end_date) -> int:
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
    flow.redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]

    code_verifier = _code_verifiers.pop(timetable_id, None)
    if code_verifier:
        flow.fetch_token(code=code, code_verifier=code_verifier)
    else:
        flow.fetch_token(code=code)

    service = build("calendar", "v3", credentials=flow.credentials)

    time_min = f"{start_date}T00:00:00+05:30"
    time_max = f"{end_date}T23:59:59+05:30"
    to_delete = []
    page_token = None
    while True:
        results = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            maxResults=250,
            singleEvents=True,
            pageToken=page_token,
        ).execute()
        for event in results.get("items", []):
            desc = event.get("description") or ""
            extended_tid = event.get("extendedProperties", {}).get("private", {}).get("timetable_id", "")
            if "Venue:" in desc or extended_tid == timetable_id:
                to_delete.append(event["id"])
        page_token = results.get("nextPageToken")
        if not page_token:
            break

    # Batch delete
    deleted = 0
    BATCH_SIZE = 50
    for i in range(0, len(to_delete), BATCH_SIZE):
        batch = service.new_batch_http_request()
        for event_id in to_delete[i:i + BATCH_SIZE]:
            batch.add(service.events().delete(calendarId="primary", eventId=event_id))
        try:
            batch.execute()
            deleted += len(to_delete[i:i + BATCH_SIZE])
        except HttpError:
            pass
    return deleted
