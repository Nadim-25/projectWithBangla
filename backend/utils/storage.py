import os

STORAGE_DIR = os.getenv("STORAGE_DIR", "/app/uploads")


def _path(object_key: str) -> str:
    full = os.path.join(STORAGE_DIR, object_key)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    return full


def upload_file(file_bytes: bytes, object_key: str, content_type: str = "application/octet-stream"):
    with open(_path(object_key), "wb") as f:
        f.write(file_bytes)


def download_file(object_key: str) -> bytes:
    with open(_path(object_key), "rb") as f:
        return f.read()


def delete_file(object_key: str):
    try:
        os.remove(_path(object_key))
    except FileNotFoundError:
        pass


def file_exists(object_key: str) -> bool:
    return os.path.exists(_path(object_key))
