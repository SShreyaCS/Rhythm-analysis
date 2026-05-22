from contextlib import asynccontextmanager
import asyncio
import shutil
import os
import uuid

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import the main analysis function from the rhythm package
try:
    from rhythm.main import analyze_rhythm
    from rhythm.pose import download_model_if_needed, POSE_MODEL_PATH
    from rhythm.video_limits import (
        MAX_UPLOAD_BYTES,
        MAX_VIDEO_DURATION_SEC,
        get_video_duration_seconds,
    )
except ImportError:
    analyze_rhythm = None
    download_model_if_needed = None
    POSE_MODEL_PATH = None
    MAX_UPLOAD_BYTES = 50 * 1024 * 1024
    MAX_VIDEO_DURATION_SEC = 25.0
    get_video_duration_seconds = None

# Comma-separated origins. Override with ALLOWED_ORIGINS on Render if needed.
_default_origins = ",".join([
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://rhythm-analysis-frontend.onrender.com",
])
_allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",")
    if origin.strip()
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Preload MediaPipe model at startup so /analyze does not download on first request."""
    if download_model_if_needed and POSE_MODEL_PATH:
        await asyncio.to_thread(download_model_if_needed, POSE_MODEL_PATH)
    yield


app = FastAPI(
    title="NrityaAI Rhythm API",
    description="API for analyzing rhythm synchronization built with FastAPI.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory to temporarily store uploaded videos
UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def cleanup_file(filepath: str):
    """Background task to delete the file after analysis."""
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception as e:
            print(f"Error deleting file {filepath}: {e}")


@app.get("/")
async def root():
    """
    Basic GET endpoint to verify the API is running.
    """
    return {
        "message": "Welcome to the NrityaAI Rhythm API!",
        "limits": {
            "max_video_seconds": MAX_VIDEO_DURATION_SEC,
            "max_upload_mb": round(MAX_UPLOAD_BYTES / (1024 * 1024), 1),
        },
        "endpoints": {
            "GET /": "API Information",
            "GET /health": "Health Check",
            "POST /analyze": "Upload a video file for rhythm analysis",
        },
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    status = "healthy" if analyze_rhythm is not None else "degraded (rhythm package missing)"
    return {
        "status": status,
        "max_video_seconds": MAX_VIDEO_DURATION_SEC,
    }


@app.post("/analyze")
async def analyze_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    POST endpoint to upload a video and run the rhythm analysis.
    """
    if not analyze_rhythm:
        raise HTTPException(
            status_code=500,
            detail="The rhythm analysis module 'rhythm.main' could not be loaded.",
        )

    if not file.filename or not file.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload a video file.",
        )

    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    temp_file_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")

    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(temp_file_path)
        if file_size > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"Video is too large ({file_size // (1024 * 1024)} MB). "
                    f"Maximum upload size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
                ),
            )

        if get_video_duration_seconds:
            duration = get_video_duration_seconds(temp_file_path)
            if duration <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Could not read video duration. The file may be corrupt.",
                )
            if duration > MAX_VIDEO_DURATION_SEC:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Video is {duration:.1f}s long. "
                        f"On this server, maximum length is {MAX_VIDEO_DURATION_SEC:.0f}s "
                        "(Render times out longer analyses with a 502). "
                        "Trim the clip or use a shorter performance."
                    ),
                )

        # Run CPU-heavy work off the event loop (still subject to Render's HTTP timeout).
        analysis_result = await asyncio.to_thread(analyze_rhythm, temp_file_path)

        background_tasks.add_task(cleanup_file, temp_file_path)
        return JSONResponse(status_code=200, content=analysis_result)

    except HTTPException:
        background_tasks.add_task(cleanup_file, temp_file_path)
        raise
    except Exception as e:
        background_tasks.add_task(cleanup_file, temp_file_path)
        raise HTTPException(status_code=500, detail=str(e))
