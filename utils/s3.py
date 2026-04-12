import os
from utils.minio_client import get_s3_client

BUCKET = os.getenv("BUCKET", "videos")

def upload_result_dir(local_dir: str, dest_prefix: str):
    if not os.path.isdir(local_dir):
        raise NotADirectoryError(f"Directory not found: {local_dir}")

    s3 = get_s3_client()

    for filename in os.listdir(local_dir):
        local_download_dir = os.path.join(local_dir, filename)

        if not os.path.isfile(local_download_dir):
            continue  

        dest_key = os.path.join(dest_prefix, filename)

        print(f"Uploading {local_download_dir} -> s3://{BUCKET}/{dest_prefix}")
        s3.upload_file(
            Filename=local_download_dir,
            Bucket=BUCKET,
            Key=dest_key,
        )

    print("Directory upload complete")

def fetch_video(file_key: str) -> str:
    download_dir = "/tmp"

    s3 = get_s3_client()

    path = os.path.join(download_dir, file_key.split("/")[-1])

    os.makedirs(os.path.dirname(path), exist_ok=True)

    print(f"Downloading s3://{BUCKET}/{file_key} -> {path}")

    s3.download_file(
        Bucket=BUCKET,
        Key=file_key,
        Filename=path,
    )

    print("Download complete")

    return path