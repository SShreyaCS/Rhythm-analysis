import traceback
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor

from rhythm.audio import get_beat_times
from rhythm.pose import get_motion_signal
from rhythm.peaks import detect_movement_peaks
from rhythm.pattern import compute_pattern_score
from rhythm.timing import compute_timing_accuracy
from rhythm.evaluator import compute_final_score
from rhythm.validity import is_bharatanatyam_valid


def analyze_rhythm(video_path: str) -> Dict[str, Any]:
    """
    Main pipeline for Rhythm Analysis System.
    Given a Bharatanatyam dance video, it scores rhythm synchronization using 
    interval-based pattern comparison and timing deviation analysis.
    """
    default_result = {
        "valid_video": False,
        "rhythm_score": 0.0,
        "pattern_score": 0.0,
        "timing": {"early": 0, "late": 0, "correct": 0},
        "feedback": "Analysis failed or insufficient data detected."
    }

    try:
        # 1-4. Run audio and pose extraction concurrently.
        # They are independent and this preserves the same downstream logic.
        with ThreadPoolExecutor(max_workers=2) as executor:
            beat_future = executor.submit(get_beat_times, video_path)
            motion_future = executor.submit(get_motion_signal, video_path, True)
            beat_times = beat_future.result()
            times, motion_signal, pose_metadata = motion_future.result()
        
        # 5. Detect movement peaks
        movement_times = detect_movement_peaks(times, motion_signal)
        
        # Handle edge cases gracefully
        if len(movement_times) < 2 or len(beat_times) < 2:
            return default_result

        # Bharatanatyam validity gate (fast heuristic, no extra heavy processing).
        is_valid, validity_message = is_bharatanatyam_valid(beat_times, movement_times, pose_metadata)
        if not is_valid:
            invalid_result = default_result.copy()
            invalid_result["feedback"] = validity_message
            return invalid_result
            
        # 6, 7 & 8, 9. Interval extraction, Align lengths, Normalization, Pattern comparison
        pattern_score = compute_pattern_score(beat_times, movement_times)
        
        # 10. Timing Analysis (early / late / correct)
        timing_accuracy, timing_breakdown = compute_timing_accuracy(beat_times, movement_times)
        
        # 11 & 12. Final score and feedback matching
        final_score, feedback = compute_final_score(pattern_score, timing_accuracy)
        
        return {
            "valid_video": True,
            "rhythm_score": final_score,
            "pattern_score": pattern_score,
            "timing": timing_breakdown,
            "feedback": feedback
        }

    except Exception as e:
        print(f"Failed during analysis: {e}")
        traceback.print_exc()
        return default_result

if __name__ == "__main__":
    # Test stub
    pass
