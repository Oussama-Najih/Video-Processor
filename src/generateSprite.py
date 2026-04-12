import json
import os
import subprocess
import math
import sys

if len(sys.argv) < 2:
    print("Usage: python generate_sprites.py <video_path_or_uri>")
    sys.exit(1)

video = sys.argv[1]

FRAME_W = 320
FRAME_H = 180
FRAMES_PER_SHEET = 100
FRAME_INTERVAL = 2
COLS = 10  
OUTPUT_DIR = "src/frames"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def format_vtt_time(seconds):
    """Converts seconds to WEBVTT timestamp format: HH:MM:SS.mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:06.3f}"

try:
    duration_output = subprocess.check_output(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video]
    ).decode().strip()
    duration = float(duration_output)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

total_frames = math.floor(duration / FRAME_INTERVAL)
num_sheets = math.ceil(total_frames / FRAMES_PER_SHEET)

vtt_content = ["WEBVTT", ""]

num_frames_per_sheet = {}

for i in range(num_sheets):
    start_frame_idx = i * FRAMES_PER_SHEET
    frames_in_this_sheet = min(FRAMES_PER_SHEET, total_frames - start_frame_idx)
    
    if frames_in_this_sheet <= 0:
        break

    actual_cols = min(COLS, frames_in_this_sheet)
    actual_rows = math.ceil(frames_in_this_sheet / actual_cols)

    output_filename = f"sprite_{i + 1}.webp"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    num_frames_per_sheet[output_path] = frames_in_this_sheet
    
    start_time = start_frame_idx * FRAME_INTERVAL

    ffmpeg_cmd = [
        'ffmpeg', '-hide_banner', '-loglevel', 'error',
        '-ss', str(start_time),
        '-i', video,
        '-vf', f"fps=1/{FRAME_INTERVAL},scale={FRAME_W}:{FRAME_H},tile={actual_cols}x{actual_rows}",
        '-frames:v', '1', '-y', output_path
    ]

    try:
        subprocess.run(ffmpeg_cmd, check=True)
        print(f"Generated sheet: {output_filename}")

        for j in range(frames_in_this_sheet):
            frame_global_idx = start_frame_idx + j
            
            t_start = frame_global_idx * FRAME_INTERVAL
            t_end = t_start + FRAME_INTERVAL
            
            col = j % actual_cols
            row = j // actual_cols
            x = col * FRAME_W
            y = row * FRAME_H

            vtt_content.append(f"{format_vtt_time(t_start)} --> {format_vtt_time(t_end)}")
            vtt_content.append(f"{output_filename}#xywh={x},{y},{FRAME_W},{FRAME_H}")
            vtt_content.append("")

    except subprocess.CalledProcessError as e:
        print(f"FFmpeg failed: {e}")
    

vtt_path = os.path.join(OUTPUT_DIR, "thumbnails.vtt")
with open(vtt_path, "w") as f:
    f.write("\n".join(vtt_content))

output_file = "src/detector/num_frames_per_sheet.json"
os.makedirs(os.path.dirname(output_file), exist_ok=True)

with open(output_file, "w") as f:
    json.dump(num_frames_per_sheet, f, indent=2)


print(f"\nDone! WebVTT with coordinates saved to: {vtt_path}")