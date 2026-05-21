import cv2
import numpy as np
import urllib.request
import os
import sys
import math
from typing import Any

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

# Speed controls (can be overridden via env vars).
# Lower SAMPLE_FPS / SCALE gives faster response with slightly coarser motion curves.
POSE_SAMPLE_FPS = float(os.getenv("POSE_SAMPLE_FPS", "12"))
POSE_FRAME_SCALE = float(os.getenv("POSE_FRAME_SCALE", "0.5"))

def download_model_if_needed(model_path: str):
    """Downloads the PoseLandmarker model task file if it doesn't exist locally."""
    if not os.path.exists(model_path):
        url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
        print(f"Downloading MediaPipe Pose model to {model_path}...")
        urllib.request.urlretrieve(url, model_path)

def get_motion_signal(video_path: str, return_metadata: bool = False):
    """Computes a combined motion signal (velocity) from the video."""
    try:
        model_path = os.path.join(os.path.dirname(__file__), "pose_landmarker_lite.task")
        download_model_if_needed(model_path)
        
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO
        )

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return np.array([]), np.array([])

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0 or np.isnan(fps):
            fps = 30.0
        frame_step = max(1, int(round(fps / max(1.0, POSE_SAMPLE_FPS))))

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

        # Landmark indices
        LEFT_WRIST = 15
        RIGHT_WRIST = 16
        LEFT_ANKLE = 27
        RIGHT_ANKLE = 28

        # Wrap MediaPipe operations in the suppressor
        with SuppressMediaPipeLogs():
            landmarker = vision.PoseLandmarker.create_from_options(options)

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Sample frames to reduce inference calls and improve throughput.
                if frame_idx % frame_step != 0:
                    frame_idx += 1
                    continue

                timestamp_sec = frame_idx / fps
                timestamp_ms = int(timestamp_sec * 1000)
                sampled_frames += 1
                
                # Downscale frame before pose detection for faster inference.
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

                if result.pose_landmarks and len(result.pose_landmarks) > 0:
                    pose_detected_frames += 1
                    landmarks = result.pose_landmarks[0]
                    la_lm = landmarks[LEFT_ANKLE]
                    ra_lm = landmarks[RIGHT_ANKLE]
                    lw_lm = landmarks[LEFT_WRIST]
                    rw_lm = landmarks[RIGHT_WRIST]

                    current_la_x, current_la_y = la_lm.x, la_lm.y
                    current_ra_x, current_ra_y = ra_lm.x, ra_lm.y
                    current_lw_x, current_lw_y = lw_lm.x, lw_lm.y
                    current_rw_x, current_rw_y = rw_lm.x, rw_lm.y

                    if prev_la is not None:
                        la_vel = math.hypot(current_la_x - prev_la[0], current_la_y - prev_la[1])
                        ra_vel = math.hypot(current_ra_x - prev_ra[0], current_ra_y - prev_ra[1])
                        lw_vel = math.hypot(current_lw_x - prev_lw[0], current_lw_y - prev_lw[1])
                        rw_vel = math.hypot(current_rw_x - prev_rw[0], current_rw_y - prev_rw[1])

                        foot_velocity = (la_vel + ra_vel) / 2.0
                        hand_velocity = (lw_vel + rw_vel) / 2.0
                        foot_velocities.append(foot_velocity)
                        hand_velocities.append(hand_velocity)
                        
                        motion_signal = 0.7 * foot_velocity + 0.3 * hand_velocity
                        times.append(timestamp_sec)
                        motion_signals.append(motion_signal)
                    
                    prev_la = (current_la_x, current_la_y)
                    prev_ra = (current_ra_x, current_ra_y)
                    prev_lw = (current_lw_x, current_lw_y)
                    prev_rw = (current_rw_x, current_rw_y)
                
                frame_idx += 1

            landmarker.close()

        cap.release()

        times_arr = np.array(times)
        motion_arr = np.array(motion_signals)

        if not return_metadata:
            return times_arr, motion_arr

        mean_foot_velocity = float(np.mean(foot_velocities)) if foot_velocities else 0.0
        mean_hand_velocity = float(np.mean(hand_velocities)) if hand_velocities else 0.0
        metadata: dict[str, Any] = {
            "sampled_frames": sampled_frames,
            "pose_detected_frames": pose_detected_frames,
            "pose_detection_ratio": (pose_detected_frames / sampled_frames) if sampled_frames else 0.0,
            "mean_foot_velocity": mean_foot_velocity,
            "mean_hand_velocity": mean_hand_velocity,
            "foot_hand_ratio": (mean_foot_velocity / mean_hand_velocity) if mean_hand_velocity > 1e-8 else 0.0,
        }
        return times_arr, motion_arr, metadata
    except Exception as e:
        print(f"Error in pose processing: {e}")
        import traceback
        traceback.print_exc()
        if return_metadata:
            return np.array([]), np.array([]), {
                "sampled_frames": 0,
                "pose_detected_frames": 0,
                "pose_detection_ratio": 0.0,
                "mean_foot_velocity": 0.0,
                "mean_hand_velocity": 0.0,
                "foot_hand_ratio": 0.0,
            }
        return np.array([]), np.array([])
