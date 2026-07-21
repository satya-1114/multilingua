from __future__ import annotations

import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.observability.correlation import (
    build_context,
    use_correlation,
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ctx = build_context(
            correlation_id=request.headers.get("X-Correlation-Id"),
            request_id=request.headers.get("X-Request-Id"),
            trace_id=request.headers.get("X-Trace-Id"),
            organization_id=request.headers.get("X-Organization-Id"),
        )
        structlog.contextvars.bind_contextvars(
            path=request.url.path,
            method=request.method,
        )
        start = time.perf_counter()
        try:
            with use_correlation(ctx):
                response: Response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers["X-Request-Id"] = ctx.request_id
        response.headers["X-Correlation-Id"] = ctx.correlation_id
        if ctx.trace_id:
            response.headers["X-Trace-Id"] = ctx.trace_id
        response.headers["X-Response-Time-Ms"] = f"{(time.perf_counter() - start) * 1000:.1f}"
        return response
