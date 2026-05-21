from typing import Any
import numpy as np


def is_bharatanatyam_valid(
    beat_times: np.ndarray,
    movement_times: np.ndarray,
    pose_metadata: dict[str, Any],
) -> tuple[bool, str]:
    """
    Lightweight gate to reject clearly non-dance / invalid videos.
    Uses already extracted features to avoid adding runtime-heavy steps.
    """
    pose_ratio = float(pose_metadata.get("pose_detection_ratio", 0.0))
    foot_hand_ratio = float(pose_metadata.get("foot_hand_ratio", 0.0))
    mean_foot_velocity = float(pose_metadata.get("mean_foot_velocity", 0.0))

    # 1) Person/full-body must be visible enough.
    if pose_ratio < 0.35:
        return False, "Low pose visibility; full-body Bharatanatyam posture not detected."

    # 2) Need clear rhythmic structure in both audio and movement.
    if len(beat_times) < 4 or len(movement_times) < 4:
        return False, "Insufficient rhythmic cues for Bharatanatyam validation."

    # Require enough rhythmic evidence before accepting as valid dance.
    matched_events = min(len(beat_times), len(movement_times))
    if matched_events < 10:
        return False, "Not enough consistent rhythmic events for Bharatanatyam."

    movement_beat_ratio = len(movement_times) / max(1, len(beat_times))
    if movement_beat_ratio < 0.35 or movement_beat_ratio > 2.5:
        return False, "Movement-beat structure is inconsistent with Bharatanatyam."

    # 3) Bharatanatyam typically has strong footwork with coordinated hand motion.
    if mean_foot_velocity < 0.002:
        return False, "Footwork signal is too weak for Bharatanatyam."
    if foot_hand_ratio < 0.35 or foot_hand_ratio > 5.5:
        return False, "Movement pattern does not match Bharatanatyam foot-hand dynamics."

    # 4) Movement cadence should be reasonably dense for dance.
    duration = float(movement_times[-1] - movement_times[0]) if len(movement_times) > 1 else 0.0
    if duration <= 0:
        return False, "Invalid movement duration."
    movement_rate = float(len(movement_times) / duration)
    if movement_rate < 0.3:
        return False, "Movement cadence is too sparse for Bharatanatyam."

    return True, "Valid Bharatanatyam-like video."
