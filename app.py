from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
import shutil
import os
import uuid

# Import the main analysis function from the rhythm package
try:
    from rhythm.main import analyze_rhythm
except ImportError:
    analyze_rhythm = None

app = FastAPI(
    title="NrityaAI Rhythm API",
    description="API for analyzing rhythm synchronization built with FastAPI.",
    version="1.0.0"
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
        "endpoints": {
            "GET /": "API Information",
            "GET /health": "Health Check",
            "POST /analyze": "Upload a video file for rhythm analysis"
        }
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    status = "healthy" if analyze_rhythm is not None else "degraded (rhythm package missing)"
    return {"status": status}

@app.post("/analyze")
async def analyze_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    POST endpoint to upload a video and run the rhythm analysis.
    """
    if not analyze_rhythm:
        raise HTTPException(status_code=500, detail="The rhythm analysis module 'rhythm.main' could not be loaded.")

    if not file.filename.endswith(('.mp4', '.avi', '.mov', '.mkv')):
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a video file.")

    # Generate a unique path for the uploaded file
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    temp_file_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")

    try:
        # Save the uploaded file to disk
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Run the rhythm analysis
        # Note: This is synchronous and might block the event loop for long videos.
        # For a production app this should be pushed to a Celery worker, but it works for local testing.
        analysis_result = analyze_rhythm(temp_file_path)
        
        # Schedule cleanup task to delete the video after returning the response
        background_tasks.add_task(cleanup_file, temp_file_path)
        
        return JSONResponse(status_code=200, content=analysis_result)

    except Exception as e:
        # Ensure cleanup even if analysis fails
        background_tasks.add_task(cleanup_file, temp_file_path)
        raise HTTPException(status_code=500, detail=str(e))
