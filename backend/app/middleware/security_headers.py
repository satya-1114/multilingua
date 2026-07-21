"""Security response headers.

Values come from :mod:`app.core.config` so they can be tightened per env.
CSP is emitted in report-only mode by default; flip
``SECURITY_CSP_ENFORCE`` to promote it to ``Content-Security-Policy``.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


def build_headers() -> dict[str, str]:
    csp_header = (
        "Content-Security-Policy"
        if settings.SECURITY_CSP_ENFORCE
        else "Content-Security-Policy-Report-Only"
    )
    hsts_parts = [f"max-age={settings.SECURITY_HSTS_MAX_AGE}", "includeSubDomains"]
    if settings.SECURITY_HSTS_PRELOAD:
        hsts_parts.append("preload")
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": settings.SECURITY_FRAME_OPTIONS,
        "X-XSS-Protection": "0",
        "Referrer-Policy": settings.SECURITY_REFERRER_POLICY,
        "Permissions-Policy": settings.SECURITY_PERMISSIONS_POLICY,
        "Strict-Transport-Security": "; ".join(hsts_parts),
        csp_header: settings.SECURITY_CSP_POLICY,
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "same-site",
    }


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for k, v in build_headers().items():
            response.headers.setdefault(k, v)
        return response


__all__ = ["SecurityHeadersMiddleware", "build_headers"]
