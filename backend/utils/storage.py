import os
import io
from minio import Minio
from minio.error import S3Error

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
BUCKET = "projectwithbangla"

_client: Minio | None = None


def _get_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
        )
        if not _client.bucket_exists(BUCKET):
            _client.make_bucket(BUCKET)
    return _client


def upload_file(file_bytes: bytes, object_key: str, content_type: str = "application/octet-stream"):
    client = _get_client()
    client.put_object(
        BUCKET,
        object_key,
        io.BytesIO(file_bytes),
        length=len(file_bytes),
        content_type=content_type,
    )


def download_file(object_key: str) -> bytes:
    client = _get_client()
    response = client.get_object(BUCKET, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def delete_file(object_key: str):
    try:
        _get_client().remove_object(BUCKET, object_key)
    except Exception:
        pass


def file_exists(object_key: str) -> bool:
    try:
        _get_client().stat_object(BUCKET, object_key)
        return True
    except S3Error:
        return False
