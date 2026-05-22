import cv2
import math
import os
import threading
import urllib.request
from typing import Any

import numpy as np

from rhythm.config import (
    MAX_POSE_SAMPLES,
    MAX_VIDEO_DURATION_SEC,
    POSE_FRAME_SCALE,
    POSE_SAMPLE_FPS,
)


class SuppressMediaPipeLogs:
    """Context manager to suppress C++ stderr output from MediaPipe."""

    def __enter__(self):
        self.null_fd = os.open(os.devnull, os.O_RDWR)
        self.save_fd = os.dup(2)
        os.dup2(self.null_fd, 2)

    def __exit__(self, *_):
        os.dup2(self.save_fd, 2)
        os.close(self.null_fd)
        os.close(self.save_fd)


import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

POSE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "pose_landmarker_lite.task")

_landmarker = None
_landmarker_lock = threading.Lock()


def download_model_if_needed(model_path: str = POSE_MODEL_PATH) -> None:
    if os.path.exists(model_path):
        return
    url = (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
    )
    print(f"Downloading MediaPipe Pose model to {model_path}...")
    urllib.request.urlretrieve(url, model_path)


def _get_landmarker() -> vision.PoseLandmarker:
    global _landmarker
    with _landmarker_lock:
        if _landmarker is not None:
            return _landmarker
        download_model_if_needed(POSE_MODEL_PATH)
        base_options = python.BaseOptions(model_asset_path=POSE_MODEL_PATH)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
        )
        with SuppressMediaPipeLogs():
            _landmarker = vision.PoseLandmarker.create_from_options(options)
        return _landmarker


def warmup_pose_model() -> bool:
    """Load pose model once at startup (avoids multi-second delay on first /analyze)."""
    try:
        _get_landmarker()
        return True
    except Exception as e:
        print(f"Pose model warmup failed: {e}")
        return False


def get_motion_signal(video_path: str, return_metadata: bool = False):
    """Compute combined motion signal (velocity) from the video."""
    empty_meta = {
        "sampled_frames": 0,
        "pose_detected_frames": 0,
        "pose_detection_ratio": 0.0,
        "mean_foot_velocity": 0.0,
        "mean_hand_velocity": 0.0,
        "foot_hand_ratio": 0.0,
    }

    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            if return_metadata:
                return np.array([]), np.array([]), empty_meta
            return np.array([]), np.array([])

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0 or np.isnan(fps):
            fps = 30.0
        frame_step = max(1, int(round(fps / max(1.0, POSE_SAMPLE_FPS))))
        max_frame_idx = int(MAX_VIDEO_DURATION_SEC * fps)

        frame_idx = 0
        prev_la = None
        prev_ra = None
        prev_lw = None
        prev_rw = None
        times = []
        motion_signals = []
        sampled_frames = 0
        pose_detected_frames = 0
        foot_velocities = []
        hand_velocities = []

        LEFT_WRIST = 15
        RIGHT_WRIST = 16
        LEFT_ANKLE = 27
        RIGHT_ANKLE = 28

        with SuppressMediaPipeLogs():
            landmarker = _get_landmarker()

            while frame_idx < max_frame_idx:
                if frame_idx % frame_step != 0:
                    if not cap.grab():
                        break
                    frame_idx += 1
                    continue

                ret, frame = cap.read()
                if not ret:
                    break

                timestamp_sec = frame_idx / fps
                timestamp_ms = int(timestamp_sec * 1000)
                sampled_frames += 1
                if sampled_frames >= MAX_POSE_SAMPLES:
                    break

                frame_small = cv2.resize(
                    frame,
                    None,
                    fx=POSE_FRAME_SCALE,
                    fy=POSE_FRAME_SCALE,
                    interpolation=cv2.INTER_AREA,
                )
                frame_rgb = cv2.cvtColor(frame_small, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
                result = landmarker.detect_for_video(mp_image, timestamp_ms)

                if result.pose_landmarks:
                    pose_detected_frames += 1
                    landmarks = result.pose_landmarks[0]
                    la_lm = landmarks[LEFT_ANKLE]
                    ra_lm = landmarks[RIGHT_ANKLE]
                    lw_lm = landmarks[LEFT_WRIST]
                    rw_lm = landmarks[RIGHT_WRIST]

                    current_la = (la_lm.x, la_lm.y)
                    current_ra = (ra_lm.x, ra_lm.y)
                    current_lw = (lw_lm.x, lw_lm.y)
                    current_rw = (rw_lm.x, rw_lm.y)

                    if prev_la is not None:
                        la_vel = math.hypot(current_la[0] - prev_la[0], current_la[1] - prev_la[1])
                        ra_vel = math.hypot(current_ra[0] - prev_ra[0], current_ra[1] - prev_ra[1])
                        lw_vel = math.hypot(current_lw[0] - prev_lw[0], current_lw[1] - prev_lw[1])
                        rw_vel = math.hypot(current_rw[0] - prev_rw[0], current_rw[1] - prev_rw[1])
                        foot_velocity = (la_vel + ra_vel) / 2.0
                        hand_velocity = (lw_vel + rw_vel) / 2.0
                        foot_velocities.append(foot_velocity)
                        hand_velocities.append(hand_velocity)
                        motion_signals.append(0.7 * foot_velocity + 0.3 * hand_velocity)
                        times.append(timestamp_sec)

                    prev_la = current_la
                    prev_ra = current_ra
                    prev_lw = current_lw
                    prev_rw = current_rw

                frame_idx += 1

        cap.release()

        times_arr = np.array(times)
        motion_arr = np.array(motion_signals)

        if not return_metadata:
            return times_arr, motion_arr

        mean_foot = float(np.mean(foot_velocities)) if foot_velocities else 0.0
        mean_hand = float(np.mean(hand_velocities)) if hand_velocities else 0.0
        metadata: dict[str, Any] = {
            "sampled_frames": sampled_frames,
            "pose_detected_frames": pose_detected_frames,
            "pose_detection_ratio": (pose_detected_frames / sampled_frames) if sampled_frames else 0.0,
            "mean_foot_velocity": mean_foot,
            "mean_hand_velocity": mean_hand,
            "foot_hand_ratio": (mean_foot / mean_hand) if mean_hand > 1e-8 else 0.0,
        }
        return times_arr, motion_arr, metadata
    except Exception as e:
        print(f"Error in pose processing: {e}")
        import traceback

        traceback.print_exc()
        if return_metadata:
            return np.array([]), np.array([]), empty_meta
        return np.array([]), np.array([])
