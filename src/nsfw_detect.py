import cv2
import os
import subprocess
import json
import sys
from PIL import Image
from utils.main import should_convert

CONTAINER_NAME = os.getenv("NSFW_CONTAINER", "nsfw_detect_service")
TMP_DIR = "src/tmp"
os.makedirs(TMP_DIR, exist_ok=True)

def classify_frame(temp_filename: str) -> float:
    cmd = [
        "docker", "exec", CONTAINER_NAME,
        "python", "classify_nsfw.py",
        "--model_def", "nsfw_model/deploy.prototxt",
        "--pretrained_model", "nsfw_model/resnet_50_1by2_nsfw.caffemodel",
        f"/workspace/frames/{temp_filename}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip().strip("()").split(", ")[1])
    except Exception as e:
        print(f"Error parsing score: {e} | Raw output: {result.stdout}")
        return -1.0



def ensure_compatible_format(video_path):
    if should_convert(video_path):
        base_path = os.path.splitext(video_path)[0]
        converted_path = f"{base_path}_converted.mp4"
        
        print(f"Incompatible codec detected. Converting to H.264...")
        convert_cmd = [
            "ffmpeg", "-y", "-i", video_path, 
            "-c:v", "libx264", "-crf", "23", 
            "-preset", "veryfast", "-an", converted_path
        ]
        subprocess.run(convert_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        return converted_path, True
    return video_path, False

def score_frames_every_second(video_path):
    work_path, was_converted = ensure_compatible_format(video_path)
    
    cap = cv2.VideoCapture(work_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file {work_path}")
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    
    interval_frames = int(fps)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"Processing: {video_path} | FPS: {fps:.2f} | Total Frames: {total_frames}")

    results = []
    frame_idx = 0
    saved_idx = 0

    while frame_idx < total_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        
        if not ret:
            print(f"Warning: Could not read frame at index {frame_idx}. Skipping...")
            frame_idx += interval_frames
            continue

        temp_filename = f"frame_{saved_idx}.png"
        temp_path = os.path.join(TMP_DIR, temp_filename)
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb_frame)
        img.save(temp_path)
        
        score = classify_frame(temp_filename)
        timestamp = frame_idx / fps
        print(f"[@ {timestamp:.1f}s] Frame {frame_idx}: Score {score:.4f}")

        results.append({
            "time": round(timestamp),
            "score": score,
        })

        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        frame_idx += interval_frames
        saved_idx += 1

    cap.release()
    
    if was_converted and os.path.exists(work_path):
        os.remove(work_path)
        
    return results

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 -m src.run <path_to_video>")
        sys.exit(1)

    input_video = sys.argv[1]
    output_json = "src/detector/detections.json"
    
    detection_results = score_frames_every_second(input_video)
    
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w") as f:
        json.dump(detection_results, f, indent=2)
    
    print(f"Done. Processed {len(detection_results)} samples. Results saved to {output_json}")