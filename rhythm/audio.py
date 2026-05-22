import os
import shutil
import subprocess
import tempfile

import numpy as np
import librosa

from rhythm.config import MAX_AUDIO_SEC


def _ffmpeg_binary() -> str:
    return os.getenv("FFMPEG_BINARY") or shutil.which("ffmpeg") or "ffmpeg"


def _extract_audio_wav(video_path: str, wav_path: str, max_sec: float) -> None:
    """Fast audio extract via ffmpeg (much quicker than moviepy on small Render instances)."""
    ffmpeg = _ffmpeg_binary()
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        video_path,
        "-t",
        str(max_sec),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        wav_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=60)


def get_beat_times(video_path: str) -> np.ndarray:
    """Extract audio from video and return beat timestamps."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
            tmp_audio_path = tmp_audio.name

        try:
            _extract_audio_wav(video_path, tmp_audio_path, MAX_AUDIO_SEC)
            y, sr = librosa.load(tmp_audio_path, sr=16000, mono=True, res_type="kaiser_fast")

            if len(y) == 0 or np.max(np.abs(y)) < 0.01:
                return np.array([])

            _tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, trim=False)
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        finally:
            if os.path.exists(tmp_audio_path):
                try:
                    os.remove(tmp_audio_path)
                except OSError:
                    pass

        return np.array(beat_times)
    except FileNotFoundError:
        print("Error in audio processing: ffmpeg not found. Add ffmpeg via apt.txt on Render.")
        return np.array([])
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or b"").decode("utf-8", errors="replace")[:500]
        print(f"Error in audio processing (ffmpeg): {stderr}")
        return np.array([])
    except Exception as e:
        print(f"Error in audio processing: {e}")
        return np.array([])
