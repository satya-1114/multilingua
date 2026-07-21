"""In-process fixed-window rate limiter.

Deliberately dependency-free (no slowapi / redis) so the limiter runs in
any environment. Suitable for single-process deployments and tests; for
multi-process production use, swap :class:`InMemoryStore` for a Redis
backend implementing the same ``(count, reset_at)`` protocol.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Iterable

from app.core.config import settings


@dataclass(frozen=True)
class Policy:
    name: str
    limit: int
    window_s: int

    @property
    def rate_key(self) -> str:
        return f"{self.limit}/{self.window_s}"


def _policies() -> dict[str, Policy]:
    return {
        "auth": Policy("auth", settings.RATE_LIMIT_AUTH_PER_MINUTE, 60),
        "password_reset": Policy(
            "password_reset", settings.RATE_LIMIT_PASSWORD_RESET_PER_HOUR, 3600
        ),
        "public": Policy("public", settings.RATE_LIMIT_PUBLIC_PER_MINUTE, 60),
        "admin": Policy("admin", settings.RATE_LIMIT_ADMIN_PER_MINUTE, 60),
        "default": Policy("default", settings.RATE_LIMIT_PER_MINUTE, 60),
    }


class InMemoryStore:
    """Thread-safe fixed-window counter store."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, window_s: int) -> tuple[int, float]:
        now = time.time()
        with self._lock:
            count, reset_at = self._data.get(key, (0, now + window_s))
            if now >= reset_at:
                count, reset_at = 0, now + window_s
            count += 1
            self._data[key] = (count, reset_at)
            return count, reset_at

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._data.clear()
            else:
                self._data.pop(key, None)

    # ------------------------------------------------------------------
    # Introspection helpers (tests / /admin dashboards)
    # ------------------------------------------------------------------
    def snapshot(self) -> dict[str, tuple[int, float]]:
        with self._lock:
            return dict(self._data)


@dataclass(frozen=True)
class Decision:
    allowed: bool
    remaining: int
    reset_at: float
    retry_after: int
    policy: Policy


class RateLimiter:
    def __init__(self, store: InMemoryStore | None = None) -> None:
        self.store = store or InMemoryStore()
        self.policies = _policies()

    def resolve_policy(self, path: str) -> Policy:
        """Route path -> policy. Longest-prefix match on API v1 paths."""
        # Auth endpoints (strictest).
        if any(path.startswith(p) for p in _AUTH_PREFIXES):
            return self.policies["auth"]
        if any(path.startswith(p) for p in _PWD_RESET_PREFIXES):
            return self.policies["password_reset"]
        if path.startswith("/api/public"):
            return self.policies["public"]
        if any(path.startswith(p) for p in _ADMIN_PREFIXES):
            return self.policies["admin"]
        return self.policies["default"]

    def check(self, key: str, policy: Policy) -> Decision:
        count, reset_at = self.store.hit(f"{policy.name}:{key}", policy.window_s)
        remaining = max(policy.limit - count, 0)
        retry_after = max(int(reset_at - time.time()), 0) if count > policy.limit else 0
        return Decision(
            allowed=count <= policy.limit,
            remaining=remaining,
            reset_at=reset_at,
            retry_after=retry_after,
            policy=policy,
        )


_AUTH_PREFIXES: Iterable[str] = (
    "/api/v1/auth/login",
    "/api/v1/auth/token",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
)
_PWD_RESET_PREFIXES: Iterable[str] = (
    "/api/v1/auth/password/reset",
    "/api/v1/auth/password/forgot",
    "/api/v1/auth/password-reset",
)
_ADMIN_PREFIXES: Iterable[str] = (
    "/api/v1/security",
    "/api/v1/system",
    "/api/v1/settings",
    "/api/v1/runtime",
    "/api/v1/workspaces",
    "/api/v1/organizations",
)


default_limiter = RateLimiter()


__all__ = ["Policy", "Decision", "RateLimiter", "InMemoryStore", "default_limiter"]
