"""Upload pipeline.

Adds chunked uploads, checksum verification, HMAC-signed URL generation,
and lightweight image metadata extraction on top of the base storage
adapter. Virus scanning is exposed as an opt-in hook that no-ops when
no scanner is configured; wire ClamAV/S3 antivirus by replacing the hook.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import io
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from app.core.config import settings
from app.core.exceptions import DomainError
from app.services import storage

VirusScanner = Callable[[bytes], bool]  # returns True when clean


@dataclass
class UploadSession:
    id: str
    name: str
    mime: str
    total_size: int
    chunk_size: int
    chunks_received: int = 0
    buffer: bytearray = field(default_factory=bytearray)
    checksum_expected: str | None = None
    created_at: float = field(default_factory=time.time)

    def is_complete(self) -> bool:
        return len(self.buffer) >= self.total_size

    def append(self, index: int, data: bytes) -> None:
        expected = index * self.chunk_size
        if expected != len(self.buffer):
            raise DomainError(f"Chunk out of order (expected offset {len(self.buffer)}, got {expected})")
        self.buffer.extend(data)
        self.chunks_received += 1


_sessions: dict[str, UploadSession] = {}
CHUNK_SIZE_DEFAULT = 5 * 1024 * 1024


def start_session(*, name: str, mime: str, total_size: int, chunk_size: int = CHUNK_SIZE_DEFAULT,
                  checksum: str | None = None) -> UploadSession:
    storage.validate(name=name, mime=mime, size=total_size)
    sid = hashlib.sha1(f"{name}:{time.time_ns()}".encode()).hexdigest()[:16]
    session = UploadSession(
        id=sid, name=name, mime=mime, total_size=total_size,
        chunk_size=chunk_size, checksum_expected=checksum,
    )
    _sessions[sid] = session
    return session


def get_session(sid: str) -> UploadSession:
    s = _sessions.get(sid)
    if not s:
        raise DomainError("Upload session not found or expired")
    return s


def append_chunk(sid: str, *, index: int, data: bytes) -> UploadSession:
    session = get_session(sid)
    session.append(index, data)
    return session


def finalize(sid: str, *, scanner: VirusScanner | None = None) -> dict:
    session = get_session(sid)
    if not session.is_complete():
        raise DomainError("Upload not complete")

    data = bytes(session.buffer)
    computed = hashlib.sha256(data).hexdigest()
    if session.checksum_expected and computed != session.checksum_expected:
        raise DomainError("Checksum mismatch")
    if scanner and not scanner(data):
        raise DomainError("File failed virus scan")

    path, checksum = storage.save_local(name=session.name, data=data)
    metadata = extract_metadata(mime=session.mime, data=data)
    _sessions.pop(sid, None)
    return {
        "path": path,
        "checksum": checksum,
        "name": session.name,
        "mime": session.mime,
        "size": len(data),
        "url": signed_url(path),
        "metadata": metadata,
    }


def signed_url(path: str, *, expires_in: int = 3600) -> str:
    """Generate an HMAC-signed URL that ``settings.APP_SECRET_KEY`` verifies."""
    base = storage.signed_url(path, expires_in=expires_in)
    exp = int(time.time()) + expires_in
    sig = _sign(f"{Path(path).name}:{exp}")
    joiner = "&" if "?" in base else "?"
    return f"{base}{joiner}exp={exp}&sig={sig}"


def verify_url(name: str, exp: int, sig: str) -> bool:
    if exp < int(time.time()):
        return False
    expected = _sign(f"{name}:{exp}")
    return hmac.compare_digest(sig, expected)


def _sign(payload: str) -> str:
    digest = hmac.new(settings.APP_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def extract_metadata(*, mime: str, data: bytes) -> dict:
    """Best-effort metadata extraction (image dimensions, byte counts)."""
    meta: dict[str, object] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    if mime.startswith("image/"):
        try:
            from PIL import Image  # type: ignore

            with Image.open(io.BytesIO(data)) as img:
                meta.update({"width": img.width, "height": img.height, "format": img.format,
                             "mode": img.mode})
        except Exception:  # pragma: no cover
            pass
    return meta


def optimize_image(data: bytes, *, quality: int = 82, max_dim: int = 2400) -> bytes:
    """Return a compressed variant of the image; original bytes on failure."""
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        return data
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.thumbnail((max_dim, max_dim))
            buf = io.BytesIO()
            fmt = "JPEG" if img.mode in {"RGB", "L"} else "PNG"
            img.convert("RGB" if fmt == "JPEG" else img.mode).save(buf, format=fmt, quality=quality, optimize=True)
            return buf.getvalue()
    except Exception:  # pragma: no cover
        return data
