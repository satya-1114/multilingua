"""Webhook signing / verification.

Uses HMAC-SHA256 over ``"<timestamp>.<body>"``. Timestamps are validated
against a configurable clock-skew tolerance. Optional nonce tracking gives
a small in-memory replay window; production deployments should back the
:class:`ReplayCache` protocol with Redis (or equivalent shared store).
"""
from __future__ import annotations

import hashlib
import hmac
import threading
import time
from dataclasses import dataclass, field

from app.core.config import settings

SIGNATURE_HEADER = "X-Webhook-Signature"
TIMESTAMP_HEADER = "X-Webhook-Timestamp"
NONCE_HEADER = "X-Webhook-Nonce"
SCHEME = "v1"


class WebhookSecurityError(Exception):
    """Base error for webhook verification failures."""


class MissingSignature(WebhookSecurityError):
    pass


class InvalidSignature(WebhookSecurityError):
    pass


class ExpiredTimestamp(WebhookSecurityError):
    pass


class ReplayedRequest(WebhookSecurityError):
    pass


@dataclass
class ReplayCache:
    """Thread-safe TTL cache used for nonce-based replay protection."""

    ttl_s: int = 600
    _seen: dict[str, float] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _sweep(self, now: float) -> None:
        stale = [k for k, exp in self._seen.items() if exp <= now]
        for k in stale:
            self._seen.pop(k, None)

    def remember(self, nonce: str) -> bool:
        """Return True if the nonce is new, False if replayed."""
        now = time.time()
        with self._lock:
            self._sweep(now)
            if nonce in self._seen:
                return False
            self._seen[nonce] = now + self.ttl_s
            return True

    def reset(self) -> None:
        with self._lock:
            self._seen.clear()


default_replay_cache = ReplayCache(ttl_s=settings.WEBHOOK_NONCE_TTL_S)


def _canonical(timestamp: str, body: bytes) -> bytes:
    return timestamp.encode("ascii") + b"." + body


def sign(
    body: bytes,
    secret: str,
    *,
    timestamp: int | None = None,
    nonce: str | None = None,
) -> dict[str, str]:
    """Return the headers a caller should attach to an outbound webhook."""
    if not secret:
        raise WebhookSecurityError("webhook signing secret is empty")
    ts = str(int(timestamp if timestamp is not None else time.time()))
    mac = hmac.new(secret.encode("utf-8"), _canonical(ts, body), hashlib.sha256)
    sig = f"{SCHEME}={mac.hexdigest()}"
    headers = {SIGNATURE_HEADER: sig, TIMESTAMP_HEADER: ts}
    if nonce:
        headers[NONCE_HEADER] = nonce
    return headers


def _parse_signature(header: str) -> str:
    """Extract the hex digest from a ``v1=<hex>`` header (or bare hex)."""
    if "=" in header:
        scheme, _, hex_ = header.partition("=")
        if scheme.strip().lower() != SCHEME:
            raise InvalidSignature(f"unsupported signature scheme: {scheme}")
        return hex_.strip()
    return header.strip()


def verify(
    body: bytes,
    secret: str,
    signature_header: str | None,
    timestamp_header: str | None,
    *,
    tolerance_s: int | None = None,
    nonce_header: str | None = None,
    replay_cache: ReplayCache | None = None,
    now: float | None = None,
) -> bool:
    """Verify an inbound webhook payload; raise on failure, return True on ok."""
    if not secret:
        raise WebhookSecurityError("webhook signing secret is empty")
    if not signature_header or not timestamp_header:
        raise MissingSignature("missing signature or timestamp header")

    try:
        ts_int = int(timestamp_header)
    except (TypeError, ValueError) as exc:
        raise InvalidSignature("timestamp header is not an integer") from exc

    tolerance = (
        settings.WEBHOOK_TIMESTAMP_TOLERANCE_S if tolerance_s is None else tolerance_s
    )
    current = time.time() if now is None else now
    if abs(current - ts_int) > tolerance:
        raise ExpiredTimestamp(
            f"timestamp outside tolerance window ({tolerance}s)"
        )

    provided = _parse_signature(signature_header)
    expected = hmac.new(
        secret.encode("utf-8"),
        _canonical(str(ts_int), body),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(provided, expected):
        raise InvalidSignature("HMAC digest mismatch")

    if nonce_header:
        cache = replay_cache or default_replay_cache
        if not cache.remember(nonce_header):
            raise ReplayedRequest("nonce has already been used")

    return True


__all__ = [
    "SIGNATURE_HEADER",
    "TIMESTAMP_HEADER",
    "NONCE_HEADER",
    "SCHEME",
    "WebhookSecurityError",
    "MissingSignature",
    "InvalidSignature",
    "ExpiredTimestamp",
    "ReplayedRequest",
    "ReplayCache",
    "default_replay_cache",
    "sign",
    "verify",
]
