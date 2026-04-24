from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import List
import uuid
import os
import tempfile
from app.models.schemas import UploadRequest, UploadResponse, ReminderRequest, ReminderResponse, GoogleCalendarReminderRequest, GoogleCalendarReminderResponse
from app.services.parser import parse_timetable
from app.services.supabase_client import (
    insert_timetable,
    get_timetable,
    insert_reminder,
)
from app.services.ocr import OCRService
from app.services.google_calendar import create_all_calendar_links
from app.utils.dependencies import get_current_user

router = APIRouter()

# Initialize OCR service once
ocr_service = OCRService()


@router.post("/upload", response_model=UploadResponse)
def upload_timetable(payload: UploadRequest, user_id: str = Depends(get_current_user)):
    parsed = parse_timetable(payload.raw_data)
    if not parsed:
        raise HTTPException(status_code=400, detail="No valid timetable data found in input.")
    result = insert_timetable(
        user_id=user_id,
        raw_data=payload.raw_data,
        parsed_data=parsed,
    )
    return UploadResponse(message="Timetable stored", timetable_id=result["timetable_id"], user_id=result["user_id"])


@router.get("/timetable/{timetable_id}")
def fetch_timetable(timetable_id: str):
    """Return structured timetable JSON for the given ID."""
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


@router.post("/reminder/google-calendar", response_model=GoogleCalendarReminderResponse)
def create_google_calendar_reminder(payload: GoogleCalendarReminderRequest):
    """Create recurring weekly Google Calendar events for all classes in the timetable."""
    record = get_timetable(payload.timetable_id)
    if not record:
        raise HTTPException(status_code=404, detail="Timetable not found.")

    event_urls = create_all_calendar_links(record["data"])
    return GoogleCalendarReminderResponse(
        message=f"Created {len(event_urls)} Google Calendar events",
        events_created=len(event_urls),
        event_urls=event_urls,
    )


@router.post("/upload-image")
async def upload_timetable_image(
    course_image: UploadFile = File(...),
    schedule_image: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """
    Upload timetable images, extract data using OCR, and store in database
    """
    course_path = None
    schedule_path = None
    
    try:
        # Create temp directory if it doesn't exist (Windows compatible)
        temp_dir = tempfile.gettempdir()
        
        # Save images temporarily
        course_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{course_image.filename}")
        schedule_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{schedule_image.filename}")
        
        # Save course image
        with open(course_path, "wb") as f:
            content = await course_image.read()
            f.write(content)
        
        # Save schedule image
        with open(schedule_path, "wb") as f:
            content = await schedule_image.read()
            f.write(content)
        
        # Process with OCR
        raw_data = ocr_service.process_timetable(course_path, schedule_path)

        if not raw_data:
            raise HTTPException(status_code=400, detail="No valid timetable data found")

        # Use the same parser as /upload endpoint
        parsed_data = parse_timetable(raw_data)

        # Store in Supabase
        result = insert_timetable(user_id=user_id, raw_data=raw_data, parsed_data=parsed_data)
        timetable_id = result["timetable_id"]

        return {
            "message": "Timetable stored",
            "timetable_id": timetable_id
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Clean up temp files
        if course_path and os.path.exists(course_path):
            try:
                os.remove(course_path)
            except:
                pass
        if schedule_path and os.path.exists(schedule_path):
            try:
                os.remove(schedule_path)
            except:
                pass


