from contextlib import asynccontextmanager
import asyncio
import logging
import shutil
import time
import os
import uuid

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger("rhythm_api")

try:
    from rhythm.main import analyze_rhythm
    from rhythm.pose import POSE_MODEL_PATH, download_model_if_needed, warmup_pose_model
    from rhythm.config import (
        ANALYZE_TIMEOUT_SEC,
        MAX_UPLOAD_BYTES,
        MAX_VIDEO_DURATION_SEC,
    )
    from rhythm.video_limits import get_video_duration_seconds
except ImportError:
    analyze_rhythm = None
    warmup_pose_model = None
    download_model_if_needed = None
    POSE_MODEL_PATH = None
    MAX_UPLOAD_BYTES = 50 * 1024 * 1024
    MAX_VIDEO_DURATION_SEC = 20.0
    ANALYZE_TIMEOUT_SEC = 26.0
    get_video_duration_seconds = None

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


def _deployment_status() -> dict:
    model_ready = bool(POSE_MODEL_PATH and os.path.isfile(POSE_MODEL_PATH))
    ffmpeg_path = shutil.which("ffmpeg")
    return {
        "model_ready": model_ready,
        "model_path": POSE_MODEL_PATH,
        "ffmpeg": ffmpeg_path or None,
        "on_render": os.getenv("RENDER", "").lower() == "true",
        "max_video_seconds": MAX_VIDEO_DURATION_SEC,
        "analyze_timeout_seconds": ANALYZE_TIMEOUT_SEC,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure pose model exists and is loaded before accepting traffic."""
    if download_model_if_needed and POSE_MODEL_PATH:
        await asyncio.to_thread(download_model_if_needed, POSE_MODEL_PATH)
    if warmup_pose_model:
        ok = await asyncio.to_thread(warmup_pose_model)
        logger.info("Pose model warmup: %s", "ok" if ok else "failed")
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

UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def cleanup_file(filepath: str):
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except OSError as e:
            logger.warning("Error deleting %s: %s", filepath, e)


@app.get("/")
async def root():
    return {
        "message": "Welcome to the NrityaAI Rhythm API!",
        "limits": {
            "max_video_seconds": MAX_VIDEO_DURATION_SEC,
            "max_upload_mb": round(MAX_UPLOAD_BYTES / (1024 * 1024), 1),
            "analyze_timeout_seconds": ANALYZE_TIMEOUT_SEC,
        },
        "deployment": _deployment_status(),
        "endpoints": {
            "GET /health": "Health Check (use before /analyze)",
            "POST /analyze": "Upload a video file (max 20s on Render)",
        },
    }


@app.get("/health")
async def health_check():
    deploy = _deployment_status()
    module_ok = analyze_rhythm is not None
    ready = module_ok and deploy["model_ready"] and deploy["ffmpeg"]
    status = "healthy" if ready else "degraded"
    return {"status": status, **deploy}


@app.post("/analyze")
async def analyze_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Upload a video and run rhythm analysis.
    On Render, keep clips at or under 20 seconds.
    """
    if not analyze_rhythm:
        raise HTTPException(
            status_code=500,
            detail="The rhythm analysis module 'rhythm.main' could not be loaded.",
        )

    deploy = _deployment_status()
    if not deploy["model_ready"]:
        raise HTTPException(
            status_code=503,
            detail=(
                "Pose model is not on disk. Add to Render build command: "
                "python scripts/download_pose_model.py"
            ),
        )
    if not deploy["ffmpeg"]:
        raise HTTPException(
            status_code=503,
            detail="ffmpeg is not available. Ensure apt.txt lists ffmpeg and redeploy.",
        )

    if not file.filename or not file.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
        raise HTTPException(status_code=400, detail="Unsupported file format.")

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
                detail=f"Video too large. Max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
            )

        duration_sec = -1.0
        if get_video_duration_seconds:
            duration_sec = get_video_duration_seconds(temp_file_path)
            if duration_sec <= 0:
                raise HTTPException(status_code=400, detail="Could not read video duration.")
            if duration_sec > MAX_VIDEO_DURATION_SEC:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Video is {duration_sec:.1f}s. Maximum allowed is "
                        f"{MAX_VIDEO_DURATION_SEC:.0f}s on this server."
                    ),
                )

        started = time.perf_counter()
        logger.info("Analysis started for %s (%.1fs)", file.filename, duration_sec)

        try:
            analysis_result = await asyncio.wait_for(
                asyncio.to_thread(analyze_rhythm, temp_file_path),
                timeout=ANALYZE_TIMEOUT_SEC,
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail=(
                    f"Analysis exceeded {ANALYZE_TIMEOUT_SEC:.0f}s. "
                    f"Use a shorter clip (under {MAX_VIDEO_DURATION_SEC:.0f}s)."
                ),
            )

        elapsed = time.perf_counter() - started
        logger.info("Analysis finished in %.1fs", elapsed)

        background_tasks.add_task(cleanup_file, temp_file_path)
        return JSONResponse(
            status_code=200,
            content={**analysis_result, "analysis_seconds": round(elapsed, 2)},
        )

    except HTTPException:
        background_tasks.add_task(cleanup_file, temp_file_path)
        raise
    except Exception as e:
        background_tasks.add_task(cleanup_file, temp_file_path)
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail=str(e))
