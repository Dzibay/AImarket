"""Файлы чата поддержки: проверка картинок и хранение на диске."""

from __future__ import annotations

import re
import secrets
from pathlib import Path

from app.config import settings

MAX_IMAGES = 4
MAX_BYTES = 8 * 1024 * 1024

_ALLOWED = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


class ImageError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def upload_dir() -> Path:
    raw = (settings.support_upload_dir or "").strip()
    path = Path(raw) if raw else Path(__file__).resolve().parent.parent / "data" / "support"
    path.mkdir(parents=True, exist_ok=True)
    return path


def sniff_mime(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def safe_filename(name: str, mime: str) -> str:
    base = Path(name or "image").name
    base = _NAME_RE.sub("-", base).strip(".-")[:80] or "image"
    ext = _ALLOWED[mime]
    if not base.lower().endswith(ext):
        stem = Path(base).stem or "image"
        base = stem + ext
    return base


def store_image(data: bytes, filename: str = "") -> dict:
    if not data:
        raise ImageError("image")
    if len(data) > MAX_BYTES:
        raise ImageError("too-big")
    mime = sniff_mime(data)
    if mime is None:
        raise ImageError("image")
    name = safe_filename(filename, mime)
    storage_name = f"{secrets.token_hex(16)}{_ALLOWED[mime]}"
    target = upload_dir() / storage_name
    target.write_bytes(data)
    return {
        "mime": mime,
        "filename": name,
        "storage_name": storage_name,
        "size_bytes": len(data),
    }


def file_path(storage_name: str) -> Path | None:
    name = Path(storage_name or "").name
    if not name or name != storage_name or ".." in storage_name:
        return None
    path = upload_dir() / name
    if not path.is_file():
        return None
    return path


async def read_upload_images(files) -> list[dict]:
    """Читает UploadFile / form parts. Пустые пропускает."""
    items = [item for item in (files or []) if item is not None and getattr(item, "filename", None)]
    if len(items) > MAX_IMAGES:
        raise ImageError("too-many")
    stored: list[dict] = []
    try:
        for item in items:
            data = await item.read()
            stored.append(store_image(data, getattr(item, "filename", "") or ""))
    except ImageError:
        for row in stored:
            path = file_path(row["storage_name"])
            if path is not None:
                path.unlink(missing_ok=True)
        raise
    return stored
