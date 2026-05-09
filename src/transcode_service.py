import json
import os
import subprocess
from dataclasses import dataclass

from utils.s3 import upload_result_dir, fetch_video
from utils.main import consumer, producer, clear
from src.run import id as service_id

transcodeConsumer = consumer("videos.uploaded", group_id="transcode-service-" + str(service_id))
doneProducer = producer()

HLS_OUTPUT_DIR = os.path.abspath(os.path.join("src", "hls"))
os.makedirs(HLS_OUTPUT_DIR, exist_ok=True)

HLS_SEGMENT_TIME = 6
HLS_PLAYLIST_TYPE = "vod"

HLS_SEGMENT_EXT = "ts"

RENDITIONS = [
    ("360p", "640:360",  "800k",  "96k"),
    ("720p", "1280:720", "2800k", "128k"),
]

@dataclass(frozen=True)
class Rendition:
    name: str
    scale: str   
    vbr: str     
    abr: str     

RENDITIONS = [Rendition(*r) for r in RENDITIONS]


def run_cmd(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print("[FFMPEG] Command failed:\n", " ".join(cmd))
        print("[FFMPEG] stdout:\n", e.stdout)
        print("[FFMPEG] stderr:\n", e.stderr)
        raise


def bitrate_to_kbps(b: str) -> int:
    b = b.strip().lower()
    if b.endswith("k"):
        return int(b[:-1])
    if b.endswith("m"):
        return int(float(b[:-1]) * 1000)
    
    return int(b)


def write_master_playlist(out_dir: str) -> str:
    master_path = os.path.join(out_dir, "master.m3u8")

    with open(master_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("#EXTM3U\n")
        f.write("#EXT-X-VERSION:3\n\n")

        for r in RENDITIONS:
            w, h = r.scale.split(":")
            v_kbps = bitrate_to_kbps(r.vbr)
            a_kbps = bitrate_to_kbps(r.abr)
            
            bw_bits = int((v_kbps + a_kbps) * 1000 * 1.05)

            f.write(f"#EXT-X-STREAM-INF:BANDWIDTH={bw_bits},RESOLUTION={w}x{h}\n")
            f.write(f"{r.name}/index.m3u8\n\n")

    print(f"[TRANSCODE] Master playlist written → {master_path}")
    return master_path


def transcode_hls(local_video_path: str, video_id: str) -> str:
    out_dir = os.path.join(HLS_OUTPUT_DIR, video_id)
    os.makedirs(out_dir, exist_ok=True)
    
    force_key_frames_expr = f"expr:gte(t,n_forced*{HLS_SEGMENT_TIME})"

    for r in RENDITIONS:
        rdir = os.path.join(out_dir, r.name)
        os.makedirs(rdir, exist_ok=True)

        segment_pattern = os.path.join(rdir, "seg_%03d." + HLS_SEGMENT_EXT)
        playlist_path = os.path.join(rdir, "index.m3u8")

        cmd = [
            "ffmpeg", "-y",
            "-i", local_video_path,
            "-vf", f"scale={r.scale}",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-b:v", r.vbr,
            "-sc_threshold", "0",
            "-force_key_frames", force_key_frames_expr,
            "-c:a", "aac",
            "-b:a", r.abr,
            "-ac", "2",
            "-f", "hls",
            "-hls_time", str(HLS_SEGMENT_TIME),
            "-hls_playlist_type", HLS_PLAYLIST_TYPE,
            "-hls_flags", "independent_segments",
            "-hls_segment_filename", segment_pattern,
            playlist_path,
        ]

        print(f"[TRANSCODE] Encoding {r.name} → {video_id}")
        run_cmd(cmd)
        print(f"[TRANSCODE] Done {r.name}")

        
        with open(playlist_path, "r", encoding="utf-8") as vf:
            first = vf.readline().strip()
            if first != "#EXTM3U":
                raise RuntimeError(f"Variant playlist invalid for {r.name}: {playlist_path} (first line: {first})")

    
    write_master_playlist(out_dir)

    
    with open(os.path.join(out_dir, "master.m3u8"), "r", encoding="utf-8") as mf:
        first = mf.readline().strip()
        if first != "#EXTM3U":
            raise RuntimeError(f"Master playlist invalid: {os.path.join(out_dir, 'master.m3u8')} (first line: {first})")

    return out_dir


print("[TRANSCODE] Service started, waiting for events...")

try:
    while True:
        msg = transcodeConsumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print("[TRANSCODE] Kafka error:", msg.error())
            continue

        event = json.loads(msg.value().decode())
        videoKey = msg.key().decode() if msg.key() else None

        if not videoKey or "/" not in videoKey:
            print("[TRANSCODE] Invalid key:", videoKey)
            continue

        videoId = videoKey.split("/")[0]
        filename = videoKey.split("/")[-1]
        print(f"[TRANSCODE] Processing: {filename} (videoId={videoId})")

        try:
            local_video_path = fetch_video(videoKey, "transcode")
            hls_dir = transcode_hls(local_video_path, videoId)
            
            upload_result_dir(hls_dir, f"{videoId}/hls")
            print(f"[TRANSCODE] Uploaded → s3:{videoId}/hls")

            payload = {"service": "transcode", "videoId": videoId, "status": "success"}
            doneProducer.produce(
                topic="videos.pipeline.done",
                key=videoId,
                value=json.dumps(payload),
                callback=lambda err, m: (
                    print(f"[TRANSCODE] Delivered → {m.topic()}") if not err
                    else print(f"[TRANSCODE] Delivery failed: {err}")
                ),
            )
            doneProducer.flush()
            transcodeConsumer.commit(msg)

            clear(["src/tmp", "src/hls"], serviceId="transcode")
            print(f"[TRANSCODE] Done: {filename}")

        except Exception as e:
            print(f"[TRANSCODE] Failed: {filename}: {e}")
            doneProducer.produce(
                topic="videos.pipeline.done",
                key=videoId,
                value=json.dumps({
                    "service": "transcode",
                    "videoId": videoId,
                    "status": "error",
                    "error": str(e),
                }),
            )
            doneProducer.flush()
        finally:
            clear(["src/tmp", "src/hls"], serviceId="transcode")

finally:
    clear(["src/tmp", "src/hls"], serviceId="transcode")
    transcodeConsumer.close()