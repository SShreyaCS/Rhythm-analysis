import os
import sys
import json
from rhythm.main import analyze_rhythm

def main():
    if len(sys.argv) < 2:
        print("Usage: python test.py <path_to_video.mp4>")
        print("Example: python test.py sample_dance.mp4")
        sys.exit(1)

    video_path = sys.argv[1]
    
    if not os.path.exists(video_path):
        print(f"Error: Video file '{video_path}' not found.")
        sys.exit(1)
        
    print(f"Analyzing rhythm for: {video_path}...")
    print("This may take a minute depending on the length of the video.")
    print("-" * 50)
    
    result = analyze_rhythm(video_path)
    
    print("-" * 50)
    print("ANALYSIS RESULTS:")
    print(json.dumps(result, indent=4))

if __name__ == "__main__":
    main()
