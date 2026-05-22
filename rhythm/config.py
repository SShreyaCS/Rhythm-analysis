"""Runtime limits — tighter defaults on Render to finish before the ~30s proxy timeout."""
import os

_ON_RENDER = os.getenv("RENDER", "").lower() == "true"


def _env_float(name: str, local_default: float, render_default: float) -> float:
    if name in os.environ:
        return float(os.environ[name])
    return render_default if _ON_RENDER else local_default


def _env_int(name: str, local_default: int, render_default: int) -> int:
    if name in os.environ:
        return int(os.environ[name])
    return render_default if _ON_RENDER else local_default


MAX_VIDEO_DURATION_SEC = _env_float("MAX_VIDEO_DURATION_SEC", 60.0, 20.0)
MAX_AUDIO_SEC = _env_float("MAX_AUDIO_SEC", MAX_VIDEO_DURATION_SEC, MAX_VIDEO_DURATION_SEC)
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
ANALYZE_TIMEOUT_SEC = _env_float("ANALYZE_TIMEOUT_SEC", 120.0, 26.0)

POSE_SAMPLE_FPS = _env_float("POSE_SAMPLE_FPS", 12.0, 6.0)
POSE_FRAME_SCALE = _env_float("POSE_FRAME_SCALE", 0.5, 0.4)
MAX_POSE_SAMPLES = _env_int("MAX_POSE_SAMPLES", 200, 90)
