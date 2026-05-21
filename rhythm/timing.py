import numpy as np

def compute_timing_accuracy(beat_times: np.ndarray, movement_times: np.ndarray) -> tuple[float, dict]:
    """Computes timing deviation (early/late/correct) for movements relative to beats."""
    if len(beat_times) == 0 or len(movement_times) == 0:
        return 0.0, {"early": 0, "late": 0, "correct": 0}
        
    early_count = 0
    late_count = 0
    correct_count = 0
    
    for m_time in movement_times:
        # Find closest beat
        closest_beat_idx = np.argmin(np.abs(beat_times - m_time))
        closest_beat = beat_times[closest_beat_idx]
        
        diff = m_time - closest_beat
        
        if abs(diff) < 0.2:
            correct_count += 1
        elif diff < 0:
            early_count += 1
        else:
            late_count += 1
            
    total_movements = len(movement_times)
    # Avoid zero division
    timing_accuracy = correct_count / (total_movements + 1e-6)
    
    timing_breakdown = {
        "early": early_count,
        "late": late_count,
        "correct": correct_count
    }
    
    return float(timing_accuracy), timing_breakdown
