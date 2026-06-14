import os
from supabase import create_client, Client

def _get_client() -> Client:
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY"),
    )

def _bucket() -> str:
    return os.getenv("SUPABASE_BUCKET", "documents")


def upload_file(file_bytes: bytes, object_key: str, content_type: str = "application/octet-stream"):
    _get_client().storage.from_(_bucket()).upload(
        path=object_key,
        file=file_bytes,
        file_options={"content-type": content_type},
    )


def download_file(object_key: str) -> bytes:
    return _get_client().storage.from_(_bucket()).download(object_key)


def delete_file(object_key: str):
    try:
        _get_client().storage.from_(_bucket()).remove([object_key])
    except Exception:
        pass


def file_exists(object_key: str) -> bool:
    try:
        _get_client().storage.from_(_bucket()).download(object_key)
        return True
    except Exception:
        return False
