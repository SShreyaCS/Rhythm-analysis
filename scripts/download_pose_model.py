"""Download MediaPipe pose model during deploy build (avoids timeout on first /analyze)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from rhythm.pose import POSE_MODEL_PATH, download_model_if_needed


def main() -> None:
    download_model_if_needed(POSE_MODEL_PATH)
    print(f"Pose model ready at {POSE_MODEL_PATH}")


if __name__ == "__main__":
    main()
