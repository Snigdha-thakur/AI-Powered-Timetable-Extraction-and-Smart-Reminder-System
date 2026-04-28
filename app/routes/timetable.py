from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import Response, RedirectResponse
import uuid
import os
import tempfile
from app.models.schemas import ReminderRequest, ReminderResponse
from app.services.supabase_client import insert_timetable, get_timetable, insert_reminder
from app.services.ocr import OCRService
from app.services.google_calendar import generate_ics
from app.services.google_oauth import get_google_auth_url, add_events_to_google_calendar
from app.utils.dependencies import get_current_user

router = APIRouter()
ocr_service = OCRService()


@router.get("/timetable/{timetable_id}")
def fetch_timetable(timetable_id: str):
    record = get_timetable(timetable_id)
    if not record:
        raise HTTPException(status_code=404, detail="Timetable not found.")
    return record["data"]


@router.post("/reminder", response_model=ReminderResponse)
def create_reminder(payload: ReminderRequest, user_id: str = Depends(get_current_user)):
    record = get_timetable(payload.timetable_id)
    if not record:
        raise HTTPException(status_code=404, detail="Timetable not found.")
    reminder_id = insert_reminder(
        timetable_id=payload.timetable_id,
        day=payload.day,
        time=payload.time,
        subject=payload.subject,
        faculty=payload.faculty,
        venue=payload.venue,
    )
    return ReminderResponse(message="Reminder created", reminder_id=reminder_id)


@router.get("/timetable/{timetable_id}/add-to-google-calendar")
def add_to_google_calendar(timetable_id: str):
    """Redirects user to Google login. After login, all events are added to their calendar."""
    record = get_timetable(timetable_id)
    if not record:
        raise HTTPException(status_code=404, detail="Timetable not found.")
    auth_url = get_google_auth_url(timetable_id)
    return RedirectResponse(auth_url)


@router.get("/auth/google/callback")
def google_callback(code: str, state: str):
    """Google redirects here after login. Adds all timetable events to Google Calendar."""
    try:
        record = get_timetable(state)  # state = timetable_id
        if not record:
            raise HTTPException(status_code=404, detail="Timetable not found.")
        count = add_events_to_google_calendar(code, state, record["data"])
        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
        return RedirectResponse(f"{frontend_url}?calendar_sync=success&events={count}")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



def download_calendar_ics(timetable_id: str):
    record = get_timetable(timetable_id)
    if not record:
        raise HTTPException(status_code=404, detail="Timetable not found.")
    ics_content = generate_ics(record["data"])
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=timetable.ics"},
    )


@router.get("/timetable/{timetable_id}/calendar-view")
def calendar_view(timetable_id: str):
    """Returns timetable as a list of events for displaying on a website calendar."""
    record = get_timetable(timetable_id)
    if not record:
        raise HTTPException(status_code=404, detail="Timetable not found.")

    DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    events = []
    for day, entries in record["data"].items():
        for entry in entries:
            events.append({
                "day":         day,
                "day_index":   DAY_ORDER.index(day) if day in DAY_ORDER else 99,
                "time":        entry.get("time", ""),
                "time_start":  entry.get("time", "").split("-")[0].strip(),
                "time_end":    entry.get("time", "").split("-")[-1].strip(),
                "course_code": entry.get("course_code") or entry.get("subject", ""),
                "type":        entry.get("type", ""),
                "slot":        entry.get("slot", ""),
                "venue":       entry.get("venue", ""),
            })

    events.sort(key=lambda e: (e["day_index"], e["time_start"]))
    return {"timetable_id": timetable_id, "events": events}


@router.post("/upload-schedule")
async def upload_schedule_image(
    schedule_image: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """
    Upload a single VTOP schedule grid screenshot.
    Extracts slot, course_code, venue, day, time directly from enriched cells.
    No course table image required.
    """
    schedule_path = None
    try:
        temp_dir = tempfile.gettempdir()
        schedule_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{schedule_image.filename}")
        with open(schedule_path, "wb") as f:
            f.write(await schedule_image.read())

        entries = ocr_service.extract_from_schedule_image(schedule_path)
        if not entries:
            raise HTTPException(status_code=400, detail="No timetable data found in image")

        # Group by day for the parsed_data (what GET /timetable/{id} returns)
        timetable: dict = {}
        for e in entries:
            day = e["day"]
            timetable.setdefault(day, []).append({
                "type":        e["type"],
                "time":        e["time"],
                "slot":        e["slot"],
                "course_code": e["course_code"],
                "venue":       e["venue"],
            })

        result = insert_timetable(user_id=user_id, raw_data=entries, parsed_data=timetable)
        return {"message": "Timetable stored", "timetable_id": result["timetable_id"]}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if schedule_path and os.path.exists(schedule_path):
            try:
                os.remove(schedule_path)
            except:
                pass

