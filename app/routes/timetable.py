from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from fastapi.responses import Response, RedirectResponse
import uuid
import os
import tempfile
from datetime import date
from app.models.schemas import ReminderRequest, ReminderResponse
from app.services.supabase_client import insert_timetable, get_timetable, insert_reminder, get_latest_timetable_by_user
from app.services.ocr import OCRService
from app.services.google_calendar import generate_ics
from app.services.google_oauth import get_google_auth_url, add_events_to_google_calendar, delete_timetable_events_from_google_calendar, _pending_actions
from app.utils.dependencies import get_current_user

router = APIRouter()
ocr_service = OCRService()


@router.get("/timetable/my")
def fetch_my_timetable(user_id: str = Depends(get_current_user)):
    record = get_latest_timetable_by_user(user_id)
    if not record:
        raise HTTPException(status_code=404, detail="No timetable found.")
    return {"timetable_id": record["id"], "data": record["data"]}


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
def add_to_google_calendar(
    timetable_id: str,
    start_date: date = Query(..., description="Semester start date YYYY-MM-DD"),
    end_date: date = Query(..., description="Semester end date YYYY-MM-DD"),
):
    record = get_timetable(timetable_id)
    if not record:
        raise HTTPException(status_code=404, detail="Timetable not found.")
    state = f"{timetable_id}|{start_date}|{end_date}"
    auth_url = get_google_auth_url(timetable_id, state, action="add")
    return RedirectResponse(auth_url)


@router.delete("/timetable/{timetable_id}/remove-from-google-calendar")
def remove_from_google_calendar(
    timetable_id: str,
    start_date: date = Query(..., description="Semester start date YYYY-MM-DD"),
    end_date: date = Query(..., description="Semester end date YYYY-MM-DD"),
    _: str = Depends(get_current_user),
):
    state = f"{timetable_id}|{start_date}|{end_date}|delete"
    auth_url = get_google_auth_url(timetable_id, state, action="delete")
    return {"auth_url": auth_url}


@router.get("/auth/google/callback")
def google_callback(code: str, state: str):
    """Google redirects here after login. Adds or deletes timetable events in Google Calendar."""
    try:
        parts = state.split("|")
        timetable_id = parts[0]
        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")

        # delete state: "TT-XXX|start_date|end_date|delete"
        if len(parts) == 4 and parts[3] == "delete":
            start_date = date.fromisoformat(parts[1])
            end_date   = date.fromisoformat(parts[2])
            record = get_timetable(timetable_id)
            if not record:
                raise HTTPException(status_code=404, detail="Timetable not found.")
            count = delete_timetable_events_from_google_calendar(code, timetable_id, start_date, end_date)
            return RedirectResponse(f"{frontend_url}?calendar_sync=deleted&events={count}")

        # add state: "TT-XXX|start_date|end_date"
        start_date = date.fromisoformat(parts[1]) if len(parts) >= 3 else None
        end_date   = date.fromisoformat(parts[2]) if len(parts) >= 3 else None
        record = get_timetable(timetable_id)
        if not record:
            raise HTTPException(status_code=404, detail="Timetable not found.")
        count = add_events_to_google_calendar(code, timetable_id, record["data"], start_date, end_date)
        return RedirectResponse(f"{frontend_url}?calendar_sync=success&events={count}")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timetable/{timetable_id}/calendar-view")
def calendar_view(
    timetable_id: str,
    start_date: date = Query(..., description="Semester start date YYYY-MM-DD"),
    end_date: date = Query(..., description="Semester end date YYYY-MM-DD"),
):
    """Returns one event per actual date occurrence within the semester date range."""
    record = get_timetable(timetable_id)
    if not record:
        raise HTTPException(status_code=404, detail="Timetable not found.")

    from app.services.google_calendar import _dates_for_weekday_in_range
    DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    events = []

    for day, entries in record["data"].items():
        for entry in entries:
            base = {
                "day":         day,
                "day_index":   DAY_ORDER.index(day) if day in DAY_ORDER else 99,
                "time":        entry.get("time", ""),
                "time_start":  entry.get("time", "").split("-")[0].strip(),
                "time_end":    entry.get("time", "").split("-")[-1].strip(),
                "course_code": entry.get("course_code") or entry.get("subject", ""),
                "type":        entry.get("type", ""),
                "slot":        entry.get("slot", ""),
                "venue":       entry.get("venue", ""),
            }
            for d in _dates_for_weekday_in_range(day, start_date, end_date):
                events.append({**base, "date": str(d)})

    events.sort(key=lambda e: (e["date"], e["time_start"]))
    return {"timetable_id": timetable_id, "start_date": str(start_date), "end_date": str(end_date), "events": events}


@router.get("/timetable/{timetable_id}/calendar.ics")
def download_calendar_ics(
    timetable_id: str,
    start_date: date = Query(None, description="Start date YYYY-MM-DD"),
    end_date: date = Query(None, description="End date YYYY-MM-DD"),
):
    record = get_timetable(timetable_id)
    if not record:
        raise HTTPException(status_code=404, detail="Timetable not found.")
    ics_content = generate_ics(record["data"], start_date, end_date)
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=timetable.ics"},
    )


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

