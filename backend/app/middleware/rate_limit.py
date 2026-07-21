"""ASGI rate-limit middleware.

Selects a :class:`~app.security.rate_limit.Policy` from the request path,
keys the counter by authenticated user (JWT ``sub``) when possible and by
client IP otherwise, and returns HTTP 429 with a JSON envelope and
``Retry-After`` when the policy is exceeded.
"""
from __future__ import annotations

from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.responses import error_envelope
from app.security.jwt import decode_token
from app.security.rate_limit import Decision, RateLimiter, default_limiter

# Paths for which rate limiting is a no-op (used by liveness probes).
_EXEMPT_PATHS = {"/healthz", "/", "/docs", "/redoc", "/openapi.json"}


def _client_ip(request: Request) -> str:
    if settings.RATE_LIMIT_TRUST_FORWARDED:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
    return request.client.host if request.client else "anonymous"


def _identity(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        try:
            payload = decode_token(token)
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
        except Exception:  # noqa: BLE001
            pass
    return f"ip:{_client_ip(request)}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Attach rate-limit headers to every response; emit 429 on breach."""

    def __init__(self, app, *, limiter: RateLimiter | None = None) -> None:
        super().__init__(app)
        self.limiter = limiter or default_limiter

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        if not settings.RATE_LIMIT_ENABLED or request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        policy = self.limiter.resolve_policy(request.url.path)
        decision: Decision = self.limiter.check(_identity(request), policy)

        if not decision.allowed:
            try:
                from app.services.audit import security_event

                security_event(
                    action="rate_limit_exceeded",
                    ip=_client_ip(request),
                    ua=request.headers.get("user-agent"),
                    metadata={
                        "policy": policy.name,
                        "path": request.url.path,
                        "method": request.method,
                    },
                )
            except Exception:  # noqa: BLE001
                pass

            headers = _limit_headers(decision)
            headers["Retry-After"] = str(max(decision.retry_after, 1))
            return JSONResponse(
                status_code=429,
                content=error_envelope(
                    "rate_limited",
                    f"Too many requests (policy: {policy.name})",
                    429,
                    {
                        "policy": policy.name,
                        "limit": policy.limit,
                        "windowSeconds": policy.window_s,
                        "retryAfter": decision.retry_after,
                    },
                ),
                headers=headers,
            )

        response = await call_next(request)
        for k, v in _limit_headers(decision).items():
            response.headers.setdefault(k, v)
        return response


def _limit_headers(decision: Decision) -> dict[str, str]:
    return {
        "X-RateLimit-Limit": str(decision.policy.limit),
        "X-RateLimit-Remaining": str(decision.remaining),
        "X-RateLimit-Reset": str(int(decision.reset_at)),
        "X-RateLimit-Policy": decision.policy.name,
    }


__all__ = ["RateLimitMiddleware"]
