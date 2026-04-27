from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
import uuid
import os
import tempfile
from app.models.schemas import UploadRequest, UploadResponse, ReminderRequest, ReminderResponse
from app.services.parser import parse_timetable
from app.services.supabase_client import insert_timetable, get_timetable, insert_reminder
from app.services.ocr import OCRService
from app.utils.dependencies import get_current_user

router = APIRouter()
ocr_service = OCRService()


@router.post("/upload", response_model=UploadResponse)
def upload_timetable(payload: UploadRequest, user_id: str = Depends(get_current_user)):
    parsed = parse_timetable(payload.raw_data)
    if not parsed:
        raise HTTPException(status_code=400, detail="No valid timetable data found in input.")
    result = insert_timetable(user_id=user_id, raw_data=payload.raw_data, parsed_data=parsed)
    return UploadResponse(message="Timetable stored", timetable_id=result["timetable_id"], user_id=result["user_id"])


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

