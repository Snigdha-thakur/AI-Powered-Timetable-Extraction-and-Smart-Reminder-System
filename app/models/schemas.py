from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class UploadRequest(BaseModel):
    raw_data: List[List[Any]]


class UploadResponse(BaseModel):
    message: str
    timetable_id: str
    user_id: str


class ReminderRequest(BaseModel):
    timetable_id: str
    day: str
    time: str
    subject: str
    faculty: Optional[str] = ""
    venue: Optional[str] = ""


class ReminderResponse(BaseModel):
    message: str
    reminder_id: str


class TimetableEntry(BaseModel):
    type: str
    time: str
    subject: str
    faculty: str
    venue: Optional[str] = ""


class TimetableResponse(BaseModel):
    timetable: Dict[str, List[TimetableEntry]]


class GoogleCalendarReminderRequest(BaseModel):
    timetable_id: str


class GoogleCalendarReminderResponse(BaseModel):
    message: str
    events_created: int
    event_urls: List[str]
