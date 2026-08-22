import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
BUCKET = "projectWithBangla"

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def upload_file(file_bytes: bytes, object_key: str, content_type: str = "application/octet-stream"):
    _get_client().storage.from_(BUCKET).upload(
        object_key,
        file_bytes,
        {"content-type": content_type, "x-upsert": "true"},
    )


def download_file(object_key: str) -> bytes:
    return bytes(_get_client().storage.from_(BUCKET).download(object_key))


def delete_file(object_key: str):
    try:
        _get_client().storage.from_(BUCKET).remove([object_key])
    except Exception:
        pass


def file_exists(object_key: str) -> bool:
    try:
        files = _get_client().storage.from_(BUCKET).list()
        return any(f.get("name") == object_key for f in files)
    except Exception:
        return False
