import os
import boto3

def get_s3_client():
    endpoint_url = os.getenv("MINIO_ENDPOINT", "http://172.24.207.98:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "user")
    secret_key = os.getenv("MINIO_SECRET_KEY", "password")
    region = os.getenv("MINIO_REGION", "eu-west-1")

    s3_client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )
    return s3_client