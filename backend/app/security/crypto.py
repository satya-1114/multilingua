"""Symmetric encryption for workspace-managed AI secrets.

Uses Fernet (AES-128-CBC + HMAC-SHA256) from the already-installed
``cryptography`` package. The key is either:

* ``settings.AI_SECRET_ENCRYPTION_KEY`` when set (URL-safe base64), or
* derived from ``APP_SECRET_KEY`` via SHA-256 for dev convenience.

Ciphertext is stored as a UTF-8 string in the database. Plaintext is
returned only inside server-side code paths — never serialised to API
responses, logs, or audit records.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _key() -> bytes:
    raw = (settings.AI_SECRET_ENCRYPTION_KEY or "").strip()
    if raw:
        try:
            # Accept Fernet URL-safe base64 keys directly.
            Fernet(raw.encode())
            return raw.encode()
        except (ValueError, InvalidToken):
            pass
    digest = hashlib.sha256((settings.APP_SECRET_KEY or "dev").encode()).digest()
    return base64.urlsafe_b64encode(digest)


_fernet: Fernet | None = None


def _cipher() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_key())
    return _fernet


def encrypt_secret(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _cipher().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        return _cipher().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""


def mask_secret(plaintext: str) -> str:
    """Return a UI-safe masked view (`sk-****xyz`)."""
    if not plaintext:
        return ""
    if len(plaintext) <= 6:
        return "•" * len(plaintext)
    return f"{plaintext[:3]}••••{plaintext[-3:]}"