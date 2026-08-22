import os
import httpx

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
BUCKET = "projectWithBangla"

def _headers() -> dict:
    return {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
    }

def _storage_url(object_key: str) -> str:
    return f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{object_key}"


def upload_file(file_bytes: bytes, object_key: str, content_type: str = "application/octet-stream"):
    headers = {**_headers(), "Content-Type": content_type, "x-upsert": "true"}
    r = httpx.post(_storage_url(object_key), content=file_bytes, headers=headers, timeout=30)
    r.raise_for_status()


def download_file(object_key: str) -> bytes:
    r = httpx.get(_storage_url(object_key), headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.content


def delete_file(object_key: str):
    try:
        import json
        headers = {**_headers(), "Content-Type": "application/json"}
        httpx.delete(
            f"{SUPABASE_URL}/storage/v1/object/{BUCKET}",
            content=json.dumps({"prefixes": [object_key]}).encode(),
            headers=headers,
            timeout=15,
        )
    except Exception:
        pass


def file_exists(object_key: str) -> bool:
    try:
        r = httpx.head(_storage_url(object_key), headers=_headers(), timeout=10)
        return r.status_code == 200
    except Exception:
        return False
