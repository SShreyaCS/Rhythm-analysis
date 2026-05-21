def generate_feedback(final_score: float) -> str:
    """Generates string feedback based on the final score."""
    if final_score > 0.85:
        return "Excellent synchronization"
    elif final_score > 0.7:
        return "Good rhythm, slightly off beat"
    else:
        return "Needs improvement in timing"

def compute_final_score(pattern_score: float, timing_accuracy: float) -> tuple[float, str]:
    """Computes final weighted score and provides text feedback."""
    final_score = 0.7 * pattern_score + 0.3 * timing_accuracy
    feedback = generate_feedback(final_score)
    return float(final_score), feedback
