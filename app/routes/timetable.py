from fastapi import APIRouter, HTTPException, UploadFile, File, Form
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
    _supabase
)
from app.services.ocr import OCRService
from app.services.google_calendar import create_all_calendar_links

router = APIRouter()

# Initialize OCR service once
ocr_service = OCRService()


@router.post("/upload", response_model=UploadResponse)
def upload_timetable(payload: UploadRequest):
    """Parse raw OCR data, store both raw and parsed timetable in Supabase."""
    parsed = parse_timetable(payload.raw_data)

    if not parsed:
        raise HTTPException(status_code=400, detail="No valid timetable data found in input.")

    timetable_id = insert_timetable(
        user_id=payload.user_id,
        raw_data=payload.raw_data,
        parsed_data=parsed,
    )
    return UploadResponse(message="Timetable stored", timetable_id=timetable_id)


@router.get("/timetable/{timetable_id}")
def fetch_timetable(timetable_id: str):
    """Return structured timetable JSON for the given ID."""
    record = get_timetable(timetable_id)
    if not record:
        raise HTTPException(status_code=404, detail="Timetable not found.")
    return record["data"]


@router.post("/reminder", response_model=ReminderResponse)
def create_reminder(payload: ReminderRequest):
    """Store a reminder for a specific timetable entry."""
    record = get_timetable(payload.timetable_id)
    if not record:
        raise HTTPException(status_code=404, detail="Timetable not found.")

    reminder_id = insert_reminder(
        timetable_id=payload.timetable_id,
        day=payload.day,
        time=payload.time,
        subject=payload.subject,
        faculty=payload.faculty,
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
    user_id: str = Form(...),
    course_image: UploadFile = File(...),
    schedule_image: UploadFile = File(...)
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
        
        # Parse raw_data to structured format
        parsed_data = parse_raw_data_to_structured(raw_data)
        
        # Store in Supabase
        result = _supabase.table("timetables").insert({
            "user_id": user_id,
            "raw_data": raw_data,
            "data": parsed_data
        }).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to store timetable")
        
        timetable_id = result.data[0]["id"]
        
        return {
            "message": "Timetable stored",
            "timetable_id": timetable_id
        }
        
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


def parse_raw_data_to_structured(raw_data: List[List[str]]) -> dict:
    """
    Convert raw_data to structured timetable format
    """
    time_slots = [
        "08:00-08:50", "09:00-09:50", "10:00-10:50", "11:00-11:50",
        "12:00-12:50", "13:00-13:50", "14:00-14:50", "15:00-15:50",
        "16:00-16:50", "17:00-17:50", "18:00-18:50", "19:00-19:50"
    ]
    
    timetable = {}
    
    for row in raw_data:
        if len(row) < 2:
            continue
            
        day = row[0]
        entry_type = row[1]
        
        if day not in timetable:
            timetable[day] = []
        
        # Process each time slot
        slot_index = 0
        for i in range(2, len(row), 2):
            subject = row[i] if i < len(row) else "-"
            faculty = row[i+1] if i+1 < len(row) else ""
            
            if subject and subject != "-" and subject != "--":
                timetable[day].append({
                    "type": entry_type,
                    "time": time_slots[slot_index] if slot_index < len(time_slots) else "",
                    "subject": subject,
                    "faculty": faculty if faculty else ""
                })
            
            slot_index += 1
    
    return timetable