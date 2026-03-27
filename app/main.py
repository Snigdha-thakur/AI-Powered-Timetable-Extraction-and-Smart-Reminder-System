from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routes import timetable
from app.services.reminder import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()


app = FastAPI(
    title="Timetable Extraction API",
    description="API for extracting and managing timetables from images",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(timetable.router)


@app.get("/")
async def root():
    return {
        "message": "Timetable Extraction API is running",
        "endpoints": [
            "POST /upload - Upload raw timetable data",
            "POST /upload-image - Upload timetable images (OCR)",
            "GET /timetable/{id} - Get timetable by ID",
            "POST /reminder - Create a reminder"
        ]
    }