from confluent_kafka import Consumer
import json
import subprocess
import os
from utils.s3 import upload_result_dir, fetch_video
from utils.main import delete_tmp_content

consumer = Consumer({
    "bootstrap.servers": "172.24.207.98:9092",
    "group.id": "abc",
    "max.poll.interval.ms": 1200000,
    "enable.auto.commit": False,
})
consumer.subscribe(["videos.uploaded"])

CONTAINER_NAME = f"nsfw_detect_service"
NSFW_MODEL_DIR = os.path.abspath("open_nsfw")
TMP_FRAMES_DIR = os.path.abspath(os.path.join("src", "tmp"))
os.makedirs(TMP_FRAMES_DIR, exist_ok=True)

print("Starting persistent NSFW Docker container...")
subprocess.run([
    "docker", "run", "-d", "--rm",
    "--name", CONTAINER_NAME,
    "--volume", f"{NSFW_MODEL_DIR}:/workspace/open_nsfw",
    "--volume", f"{TMP_FRAMES_DIR}:/workspace/frames",
    "-w", "/workspace/open_nsfw",
    "bvlc/caffe:cpu", "tail", "-f", "/dev/null"
], check=True)

try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None: continue
        if msg.error():
            print("Kafka error:", msg.error())
            continue

        event = json.loads(msg.value().decode())
        file_key = event["fileKey"]
        filename = event.get("originalFilename", file_key)
        local_video_path = fetch_video(file_key)
        videoId = file_key.split("/")[0]

        print(f"--- Processing: {filename} ---")

        try:
            subprocess.run(["python3", "-m", "src.generateSprite", local_video_path], check=True)
            upload_result_dir("src/frames", f"{videoId}/frames")

            env = os.environ.copy()
            env["NSFW_CONTAINER"] = CONTAINER_NAME  
            subprocess.run(["python3", "-m", "open_nsfw.filter"], check=True, env=env)
            
            upload_result_dir("src/highscore", f"{videoId}")

            subprocess.run(["python3", "-m", "src.confident"], check=True)

            delete_tmp_content(TMP_FRAMES_DIR)

            consumer.commit(msg)
            print(f"Successfully processed {filename}")

        except Exception as e:
            print(f"Failed to process {filename}: {e}")
        finally:
            if os.path.exists(local_video_path):
                os.remove(local_video_path)

finally:
    print("Shutting down: Stopping Docker container...")
    subprocess.run(["docker", "stop", CONTAINER_NAME])
    consumer.close()