import json
import subprocess
import os
import math
from utils.s3 import upload_result_dir, fetch_video
from utils.main import  clear, consumer, producer
from src.run import id

thumbnailConsumer = consumer("videos.uploaded", group_id="thumbnail-service"+id)
doneProducer   = producer()

FRAME_W, FRAME_H   = 320, 180
FRAMES_PER_SHEET   = 100
FRAME_INTERVAL     = 2
COLS               = 10
OUTPUT_DIR         = "src/frames"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def format_vtt_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02}:{m:02}:{s:06.3f}"


def get_duration(video_path: str) -> float:
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path,
    ]).decode().strip())


def generate_sprites(video_path: str) -> dict:
    duration     = get_duration(video_path)
    total_frames = math.floor(duration / FRAME_INTERVAL)
    num_sheets   = math.ceil(total_frames / FRAMES_PER_SHEET)
    vtt_lines    = ["WEBVTT", ""]

    for i in range(num_sheets):
        start_frame_idx = i * FRAMES_PER_SHEET
        frames_in_sheet = min(FRAMES_PER_SHEET, total_frames - start_frame_idx)
        if frames_in_sheet <= 0:
            break

        actual_cols     = min(COLS, frames_in_sheet)
        actual_rows     = math.ceil(frames_in_sheet / actual_cols)
        output_filename = f"sprite_{i + 1}.webp"
        output_path     = os.path.join(OUTPUT_DIR, output_filename)
        start_time      = start_frame_idx * FRAME_INTERVAL

        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-ss", str(start_time), "-i", video_path,
            "-vf", (
                f"fps=1/{FRAME_INTERVAL},"
                f"scale={FRAME_W}:{FRAME_H},"
                f"tile={actual_cols}x{actual_rows}"
            ),
            "-frames:v", "1", "-y", output_path,
        ], check=True)
        print(f"[THUMBNAIL] Generated {output_filename}")

        for j in range(frames_in_sheet):
            t_start = (start_frame_idx + j) * FRAME_INTERVAL
            t_end   = t_start + FRAME_INTERVAL
            x = (j % actual_cols) * FRAME_W
            y = (j // actual_cols) * FRAME_H
            vtt_lines += [
                f"{format_vtt_time(t_start)} --> {format_vtt_time(t_end)}",
                f"{output_filename}#xywh={x},{y},{FRAME_W},{FRAME_H}",
                "",
            ]

    vtt_path = os.path.join(OUTPUT_DIR, "thumbnails.vtt")
    with open(vtt_path, "w") as f:
        f.write("\n".join(vtt_lines))

    return {
        "duration":     duration,
        "num_sheets":   num_sheets,
    }


print("[THUMBNAIL] Service started, waiting for events...")

try:
    while True:
        msg = thumbnailConsumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print("[THUMBNAIL] Kafka error:", msg.error())
            continue

        event    = json.loads(msg.value().decode())
        videoKey = msg.key().decode() if msg.key() else None

        videoId  = videoKey.split("/")[0]
        filename = videoKey.split("/")[-1]
        print(f"[THUMBNAIL] Processing: {filename}")

        try:
            local_video_path = fetch_video(videoKey,"thumbnail")
            sprite_data      = generate_sprites(local_video_path)

            upload_result_dir(OUTPUT_DIR, f"{videoId}/frames")
            print(f"[THUMBNAIL] Uploaded frames → s3:{videoId}/frames")

            payload = {
                "service": "thumbnail",
                "videoId": videoId,
                "status":  "success",
                "data":    sprite_data,
            }
            doneProducer.produce(
                topic="videos.pipeline.done",
                key=videoId,
                value=json.dumps(payload),
                callback=lambda err, m: (
                    print(f"[THUMBNAIL] Delivered → {m.topic()}") if not err
                    else print(f"[THUMBNAIL] Delivery failed: {err}")
                ),
            )
            doneProducer.flush()
            thumbnailConsumer.commit(msg)
            clear(["src/tmp","src/frames"], serviceId="thumbnail")
            print(f"[THUMBNAIL] Done: {filename}")

        except Exception as e:
            print(f"[THUMBNAIL] Failed: {filename}: {e}")
            doneProducer.produce(
                topic="videos.pipeline.done",
                key=videoId,
                value=json.dumps({"service": "thumbnail", "videoId": videoId, "status": "error", "error": str(e)}),
            )
            doneProducer.flush()
        finally:
            clear(["src/tmp","src/frames"], serviceId="thumbnail")
        


finally:
    clear(["src/tmp","src/frames"], serviceId="thumbnail")
    thumbnailConsumer.close()