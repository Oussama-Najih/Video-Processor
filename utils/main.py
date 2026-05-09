import os
import shutil
import subprocess
from confluent_kafka import Consumer
from confluent_kafka import Producer



COLS = 10
FRAME_W = 320
FRAME_H = 180

def createFrame(img,i):
    row = i // COLS
    col = i % COLS

    left = col * FRAME_W
    upper = row * FRAME_H
    right = left + FRAME_W
    lower = upper + FRAME_H

    sprite_w, sprite_h = img.size
    if right > sprite_w or lower > sprite_h:
        return False

    frame = img.crop((left, upper, right, lower))
    frame = frame.convert("RGB")
    return frame



def _clear_dir(path: str):
    if not os.path.isdir(path):
        return
    for name in os.listdir(path):
        p = os.path.join(path, name)
        try:
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)  
        except Exception as e:
            print(f"Failed to delete {p}. Reason: {e}")

def clear(folders: list | None = None, serviceId: str | None = None):
    folders = folders or ['src/tmp','src/video', 'src/hls', 'src/frames', 'src/detector', 'src/highscore']

    for folder in folders:
        if folder == "src/video":
            services = [serviceId] if serviceId else ["transcode", "thumbnail", "nsfw"]
            for service in services:
                _clear_dir(os.path.join(folder, service))
        else:
            _clear_dir(folder)



def consumer(topic: str,group_id: str):

    consumer = Consumer({
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        "group.id" : group_id,
        "max.poll.interval.ms": 1200000,
        "enable.auto.commit": False,
        "auto.offset.reset": "latest",
    })
    consumer.subscribe([topic])
    return consumer


def producer():
    producer = Producer({
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        "enable.idempotence": True,
    })
    return producer


def should_convert(video_path):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name", "-of", "csv=p=0", video_path
    ]
    try:
        codec = subprocess.check_output(cmd).decode().strip().lower()
        problematic_codecs = ['av1', 'vp9', 'hevc', 'h265']
        return codec in problematic_codecs
    except:
        return True 