import os
import random
import string
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

# Use absolute path so it works regardless of where uvicorn is launched from
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env.local")

_supabase: Client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"],
)


def insert_timetable(user_id: str, raw_data: list, parsed_data: dict) -> dict:
    chars = string.ascii_uppercase + string.digits
    timetable_id = "TT-" + "".join(random.choices(chars, k=6))
    _supabase.table("timetables").insert({
        "id": timetable_id,
        "user_id": user_id,
        "data": parsed_data,
        "raw_data": raw_data,
    }).execute()
    return {"timetable_id": timetable_id, "user_id": user_id}


def get_latest_timetable_by_user(user_id: str) -> dict | None:
    """Fetch the most recent timetable for a user."""
    result = (
        _supabase.table("timetables")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    return result.data if result else None


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


def insert_reminder(timetable_id: str, day: str, time: str, subject: str, faculty: str = "", venue: str = "") -> str:
    reminder_id = "RM-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    _supabase.table("reminders").insert({
        "id": reminder_id,
        "timetable_id": timetable_id,
        "day": day,
        "time": time,
        "subject": subject,
        "faculty": faculty,
        "venue": venue,
    }).execute()
    return reminder_id


def get_reminders() -> list[dict]:
    """Fetch all reminders."""
    result = _supabase.table("reminders").select("*").execute()
    return result.data or []


def get_user_email_by_timetable_id(timetable_id: str) -> str | None:
    """Fetch the owner's email for a given timetable."""
    result = (
        _supabase.table("timetables")
        .select("user_id")
        .eq("id", timetable_id)
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        return None
    user_id = result.data["user_id"]
    user = (
        _supabase.table("users")
        .select("email")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    return user.data["email"] if user and user.data else None
