import numpy as np

def detect_movement_peaks(times: np.ndarray, motion_signal: np.ndarray) -> np.ndarray:
    """Detects peaks in the movement signal using a dynamic threshold (mean + std)."""
    if len(motion_signal) < 2:
        return np.array([])
        
    mean_val = np.mean(motion_signal)
    std_val = np.std(motion_signal)
    threshold = mean_val + std_val
    
    movement_times = []
    
    # Simple peak detection: greater than threshold and greater than neighbors
    for i in range(1, len(motion_signal) - 1):
        if motion_signal[i] > threshold:
            if motion_signal[i] > motion_signal[i-1] and motion_signal[i] > motion_signal[i+1]:
                movement_times.append(times[i])
                
    return np.array(movement_times)
