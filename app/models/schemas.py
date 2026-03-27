from pydantic import BaseModel
from typing import Any
import uuid

from typing import List, Optional, Dict, Any


class UploadRequest(BaseModel):
    user_id: str
    raw_data: list[list[Any]]


class UploadResponse(BaseModel):
    message: str
    timetable_id: str


class ReminderRequest(BaseModel):
    timetable_id: str
    day: str
    time: str
    subject: str
    faculty: str = ""


class ReminderResponse(BaseModel):
    message: str
    reminder_id: str



class UploadRequest(BaseModel):
    user_id: str
    raw_data: List[List[str]]


class UploadResponse(BaseModel):
    message: str
    timetable_id: str


class ReminderRequest(BaseModel):
    timetable_id: str
    day: str
    time: str
    subject: str
    faculty: Optional[str] = ""


class ReminderResponse(BaseModel):
    message: str
    reminder_id: str


class TimetableEntry(BaseModel):
    type: str
    time: str
    subject: str
    faculty: str


class TimetableResponse(BaseModel):
    timetable: Dict[str, List[TimetableEntry]]


class GoogleCalendarReminderRequest(BaseModel):
    timetable_id: str


class GoogleCalendarReminderResponse(BaseModel):
    message: str
    events_created: int
    event_urls: list[str]