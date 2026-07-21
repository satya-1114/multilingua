from __future__ import annotations

import hashlib
import os
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import DomainError

ALLOWED_MIME = {
    "image/png", "image/jpeg", "image/gif", "image/webp",
    "application/pdf", "text/csv", "text/plain",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
MAX_BYTES = 50 * 1024 * 1024


def validate(*, name: str, mime: str, size: int) -> None:
    if size > MAX_BYTES:
        raise DomainError("File exceeds 50MB limit")
    if mime not in ALLOWED_MIME:
        raise DomainError(f"Unsupported file type: {mime}")
    if ".." in name or "/" in name or "\\" in name:
        raise DomainError("Invalid file name")


def save_local(*, name: str, data: bytes) -> tuple[str, str]:
    root = Path(settings.STORAGE_LOCAL_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    checksum = hashlib.sha256(data).hexdigest()
    target = root / f"{checksum[:12]}_{name}"
    target.write_bytes(data)
    return str(target), checksum


def signed_url(path: str, *, expires_in: int = 3600) -> str:
    if settings.STORAGE_BACKEND == "s3" and settings.S3_ENDPOINT:
        return f"{settings.S3_ENDPOINT.rstrip('/')}/{settings.S3_BUCKET}/{os.path.basename(path)}?expires={expires_in}"
    return f"/media/{os.path.basename(path)}"
