import os
import tempfile
import numpy as np

import librosa
from moviepy import VideoFileClip

def get_beat_times(video_path: str) -> np.ndarray:
    """Extracts audio from video and returns beat timestamps."""
    try:
        clip = VideoFileClip(video_path)
        audio = clip.audio
        if audio is None:
            clip.close()
            return np.array([])

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
            tmp_audio_path = tmp_audio.name

        try:
            # Lower sample rate/mono is enough for beat tracking and faster to process.
            audio.write_audiofile(
                tmp_audio_path,
                fps=16000,
                nbytes=2,
                codec="pcm_s16le",
                ffmpeg_params=["-ac", "1"],
                logger=None,
            )
            y, sr = librosa.load(tmp_audio_path, sr=16000, mono=True, res_type="kaiser_fast")

            # Check if the audio is silent or contains only faint noise
            if len(y) == 0 or np.max(np.abs(y)) < 0.01:
                return np.array([])

            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        finally:
            if os.path.exists(tmp_audio_path):
                try:
                    os.remove(tmp_audio_path)
                except Exception:
                    pass

        clip.close()
        return np.array(beat_times)
    except Exception as e:
        print(f"Error in audio processing: {e}")
        return np.array([])
