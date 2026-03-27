import os
import uuid
from supabase import create_client, Client
from dotenv import load_dotenv

# Explicitly load .env.local (dotenv defaults to .env)
load_dotenv(dotenv_path=".env.local")

_supabase: Client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"],
)


def insert_timetable(user_id: str, raw_data: list, parsed_data: dict) -> str:
    """Insert a timetable record and return its UUID."""
    timetable_id = str(uuid.uuid4())
    _supabase.table("timetables").insert({
        "id": timetable_id,
        "user_id": user_id,
        "data": parsed_data,
        "raw_data": raw_data,
    }).execute()
    return timetable_id


def get_timetable(timetable_id: str) -> dict | None:
    """Fetch a timetable by ID. Returns None if not found."""
    result = (
        _supabase.table("timetables")
        .select("*")
        .eq("id", timetable_id)
        .maybe_single()
        .execute()
    )
    return result.data if result else None


def insert_reminder(timetable_id: str, day: str, time: str, subject: str, faculty: str = "") -> str:
    """Insert a reminder and return its UUID."""
    reminder_id = str(uuid.uuid4())
    _supabase.table("reminders").insert({
        "id": reminder_id,
        "timetable_id": timetable_id,
        "day": day,
        "time": time,
        "subject": subject,
        "faculty": faculty,
    }).execute()
    return reminder_id


def get_reminders() -> list[dict]:
    """Fetch all reminders."""
    result = _supabase.table("reminders").select("*").execute()
    return result.data or []
