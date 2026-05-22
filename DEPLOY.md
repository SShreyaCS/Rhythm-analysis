# Backend deployment on Render (`rhythm-analysis.onrender.com`)

## Why Swagger `/analyze` spins forever

Render cuts HTTP requests at **~30 seconds**. Video analysis (MediaPipe + audio) often exceeded that, so Swagger shows **LOADING** then **502** with no JSON body.

## Render backend settings (required)

| Setting | Value |
|---------|--------|
| **Build command** | `pip install -r requirements.txt && python scripts/download_pose_model.py` |
| **Start command** | `uvicorn app:app --host 0.0.0.0 --port $PORT` |
| **apt packages** | Use repo `apt.txt` with `ffmpeg` (Render Python native runtime) |

### Environment variables (optional — Render auto-detects `RENDER=true`)

| Variable | Recommended |
|----------|-------------|
| `MAX_VIDEO_DURATION_SEC` | `20` |
| `ANALYZE_TIMEOUT_SEC` | `26` |
| `POSE_SAMPLE_FPS` | `6` |
| `MAX_POSE_SAMPLES` | `90` |

## Test in Swagger **before** the frontend

1. **GET `/health`** → must show:
   - `"status": "healthy"`
   - `"model_ready": true`
   - `"ffmpeg": "/usr/bin/ffmpeg"` (or similar)

   If `model_ready` is false → fix build command (download model script).  
   If `ffmpeg` is null → ensure `apt.txt` exists and redeploy.

2. **POST `/analyze`** with a clip **≤ 20 seconds** (short test video).

3. Response should return in **under ~30s** with JSON including `valid_video`, `rhythm_score`, `analysis_seconds`.

## Frontend (after backend works)

Set `VITE_API_URL=https://rhythm-analysis.onrender.com` on the static site and **rebuild** the frontend.
