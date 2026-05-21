import numpy as np

def compute_pattern_score(beat_times: np.ndarray, movement_times: np.ndarray) -> float:
    """Computes interval-based pattern synchronization score."""
    if len(beat_times) < 2 or len(movement_times) < 2:
        return 0.0
        
    # Interval extraction
    beat_intervals = np.diff(beat_times)
    movement_intervals = np.diff(movement_times)
    
    # Align lengths
    min_len = min(len(beat_intervals), len(movement_intervals))
    if min_len == 0:
        return 0.0
        
    beat_intervals = beat_intervals[:min_len]
    movement_intervals = movement_intervals[:min_len]
    
    # Normalization
    sum_b = np.sum(beat_intervals)
    sum_m = np.sum(movement_intervals)
    
    if sum_b == 0 or sum_m == 0:
        return 0.0
        
    beat_pattern = beat_intervals / sum_b
    movement_pattern = movement_intervals / sum_m
    
    # Pattern Comparison
    error = np.mean(np.abs(beat_pattern - movement_pattern))
    pattern_score = max(0.0, 1.0 - error)
    
    return float(pattern_score)
