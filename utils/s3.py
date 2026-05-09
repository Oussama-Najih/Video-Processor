import os
from utils.minio_client import get_s3_client

BUCKET = os.getenv("BUCKET", "videos")

import os

def upload_result_dir(local_dir: str, dest_prefix: str):
    if not os.path.isdir(local_dir):
        raise NotADirectoryError(f"Directory not found: {local_dir}")

    s3 = get_s3_client()

    for root, _, files in os.walk(local_dir):
        for filename in files:
            local_path = os.path.join(root, filename)

            rel_path = os.path.relpath(local_path, local_dir)

            rel_key = rel_path.replace(os.sep, "/")

            dest_key = f"{dest_prefix.rstrip('/')}/{rel_key}"

            print(f"Uploading {local_path} -> s3://{BUCKET}/{dest_key}")
            s3.upload_file(
                Filename=local_path,
                Bucket=BUCKET,
                Key=dest_key,
            )

    print("Directory upload complete")
    
import os

def fetch_video(video_key: str,serviceId: str) -> str:
    download_dir = f"src/video/{serviceId}/"

    path = os.path.join(download_dir,serviceId+video_key.replace("/", "_"),)


    os.makedirs(os.path.dirname(path), exist_ok=True)

    s3 = get_s3_client()

    print(f"Downloading s3://{BUCKET}/{video_key} -> {path}")

    s3.download_file(
        Bucket=BUCKET,
        Key=video_key,
        Filename=path,
    )

    print("Download complete")

    return path