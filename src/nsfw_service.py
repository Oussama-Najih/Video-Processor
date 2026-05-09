import json
import subprocess
import os
from utils.s3 import fetch_video
from utils.main import  consumer, producer, clear
from src.run import id


nsfwConsumer     = consumer("videos.uploaded", group_id="nsfw-service"+id)
doneProducer   = producer()

CONTAINER_NAME       = "nsfw_detect_service"
NSFW_MODEL_DIR       = os.path.abspath("open_nsfw")
TMP_FRAMES_DIR       = os.path.abspath(os.path.join("src", "tmp"))

os.makedirs(TMP_FRAMES_DIR, exist_ok=True)

print("[NSFW] Starting persistent Docker container...")
subprocess.run([
    "docker", "run", "-d", "--rm",
    "--name", CONTAINER_NAME,
    "--volume", f"{NSFW_MODEL_DIR}:/workspace/open_nsfw",
    "--volume", f"{TMP_FRAMES_DIR}:/workspace/frames",
    "-w", "/workspace/open_nsfw",
    "bvlc/caffe:cpu", "tail", "-f", "/dev/null",
], check=True)

print("[NSFW] Service started, waiting for events...")

try:
    while True:
        msg = nsfwConsumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print("[NSFW] Kafka error:", msg.error())
            continue

        event    = json.loads(msg.value().decode())

        videoKey = msg.key().decode() if msg.key() else None

        videoId  = videoKey.split("/")[0]
        filename = videoKey.split("/")[-1]
        print(f"[NSFW] Processing: {filename}")

        try:
            local_video_path = fetch_video(videoKey,"nsfw")

            env = os.environ.copy()
            env["NSFW_CONTAINER"] = CONTAINER_NAME
            env["VIDEO_ID"]       = videoId

            result = subprocess.run(
                ["python3", "-m", "src.nsfw_detect", local_video_path],
                env=env,
                capture_output=True,
                text=True
            )

            print("[NSFW DETECT STDOUT]")
            print(result.stdout)

            print("[NSFW DETECT STDERR]")
            print(result.stderr)

            if result.returncode != 0:
                raise RuntimeError(f"nsfw_detect failed: {result.stderr}")
            
            subprocess.run(["python3", "-m", "src.threshold"], check=True)

            with open("src/highscore/high_score_frames.json", "r") as f:
                high_scores = json.load(f)
                print(f"[NSFW] High-score frames: {len(high_scores)}")

            payload = {
                "service": "nsfw",
                "videoId": videoId,
                "status": "success",
                "data": {
                    "scores": high_scores,
                    "email": event.get("email"),
                    "userId": event.get("userId"),
                    "videoTitle": event.get("videoTitle")
                }
            }

            doneProducer.produce(
                topic="videos.pipeline.done",
                key=videoId,
                value=json.dumps(payload),
                callback=lambda err, m: (
                    print(f"[NSFW] Delivered → {m.topic()}") if not err
                    else print(f"[NSFW] Delivery failed: {err}")
                ),
            )
            doneProducer.flush()
            nsfwConsumer.commit(msg)
            clear(["src/tmp","src/highscore","src/detector"], serviceId="nsfw")
            print(f"[NSFW] Done: {filename}")

        except Exception as e:
            print(f"[NSFW] Failed: {filename}: {e}")
            doneProducer.produce(
                topic="videos.pipeline.done",
                key=videoId,
                value=json.dumps({"service": "nsfw", "videoId": videoId, "status": "error", "error": str(e)}),
            )
            doneProducer.flush()
        finally:
            clear(["src/tmp","src/highscore","src/detector"], serviceId="nsfw")


finally:
    clear(["src/tmp","src/highscore","src/detector"], serviceId="nsfw")
    print("[NSFW] Shutting down Docker container...")
    subprocess.run(["docker", "stop", CONTAINER_NAME])
    nsfwConsumer.close()