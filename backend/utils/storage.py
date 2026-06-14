import boto3
import os
from botocore.exceptions import ClientError

def _get_client():
    account_id = os.getenv("R2_ACCOUNT_ID")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )

BUCKET = lambda: os.getenv("R2_BUCKET_NAME")


def upload_file(file_bytes: bytes, object_key: str, content_type: str = "application/octet-stream"):
    _get_client().put_object(
        Bucket=BUCKET(),
        Key=object_key,
        Body=file_bytes,
        ContentType=content_type,
    )


def download_file(object_key: str) -> bytes:
    response = _get_client().get_object(Bucket=BUCKET(), Key=object_key)
    return response["Body"].read()


def delete_file(object_key: str):
    try:
        _get_client().delete_object(Bucket=BUCKET(), Key=object_key)
    except ClientError:
        pass


def file_exists(object_key: str) -> bool:
    try:
        _get_client().head_object(Bucket=BUCKET(), Key=object_key)
        return True
    except ClientError:
        return False
