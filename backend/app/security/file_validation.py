"""File-upload validation helpers."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from app.core.config import settings

# Very defensive filename regex — restrict to a POSIX-safe subset.
_FILENAME_RE = re.compile(r"^[A-Za-z0-9._\- ()]{1,180}$")

# Basic MIME-vs-extension consistency map. Left minimal on purpose.
_MIME_EXT_HINT: dict[str, set[str]] = {
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/webp": {".webp"},
    "image/gif": {".gif"},
    "application/pdf": {".pdf"},
    "text/plain": {".txt"},
    "text/csv": {".csv"},
}


@dataclass
class FileValidationError(ValueError):
    reason: str
    field: str = "file"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.reason


def _ext(name: str) -> str:
    return os.path.splitext(name)[1].lower()


def validate_filename(name: str) -> str:
    """Return the sanitized basename or raise :class:`FileValidationError`."""
    if not name or "\x00" in name:
        raise FileValidationError("filename is empty or contains NULL bytes")
    if ".." in name.replace("\\", "/").split("/"):
        raise FileValidationError("filename contains a path-traversal segment")
    base = os.path.basename(name.replace("\\", "/"))
    if base in {"", ".", ".."}:
        raise FileValidationError("filename is not a valid basename")
    if not _FILENAME_RE.match(base):
        raise FileValidationError("filename contains disallowed characters")
    return base


def validate_extension(name: str) -> str:
    ext = _ext(name)
    if not ext:
        raise FileValidationError("filename has no extension")
    if ext in settings.upload_blocked_ext:
        raise FileValidationError(f"extension {ext} is not allowed")
    if ext not in settings.upload_allowed_ext:
        raise FileValidationError(f"extension {ext} is not in the allow-list")
    return ext


def validate_mime(mime: str, *, name: str | None = None) -> str:
    m = (mime or "").strip().lower()
    if not m:
        raise FileValidationError("mime type is empty")
    if m not in settings.upload_allowed_mime:
        raise FileValidationError(f"mime type {m} is not in the allow-list")
    if name is not None:
        ext = _ext(name)
        allowed_exts = _MIME_EXT_HINT.get(m)
        if allowed_exts and ext and ext not in allowed_exts:
            raise FileValidationError(
                f"mime {m} does not match extension {ext}"
            )
    return m


def validate_size(size: int, *, limit: int | None = None) -> int:
    max_bytes = limit if limit is not None else settings.UPLOAD_MAX_BYTES
    if size < 0:
        raise FileValidationError("size must be non-negative")
    if size > max_bytes:
        raise FileValidationError(
            f"file size {size} exceeds limit {max_bytes}"
        )
    return size


def validate_upload(
    *,
    name: str,
    mime: str,
    size: int,
    limit: int | None = None,
) -> dict[str, str | int]:
    """Run all checks in one call; return a normalized record."""
    n = validate_filename(name)
    validate_extension(n)
    validate_mime(mime, name=n)
    validate_size(size, limit=limit)
    return {"name": n, "mime": mime.lower(), "size": size}


# ---------------------------------------------------------------------- #
# URL validation (for webhook callbacks, redirects, etc.)
# ---------------------------------------------------------------------- #

_HTTP_URL_RE = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)


def validate_http_url(url: str, *, require_https: bool = False) -> str:
    if not url or not _HTTP_URL_RE.match(url):
        raise FileValidationError("url is not a valid http(s) URL", field="url")
    if require_https and not url.lower().startswith("https://"):
        raise FileValidationError("url must use https", field="url")
    return url


__all__ = [
    "FileValidationError",
    "validate_filename",
    "validate_extension",
    "validate_mime",
    "validate_size",
    "validate_upload",
    "validate_http_url",
]
