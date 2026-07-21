from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.router import api_router
from app.api.public import router as public_router
from app.core.config import settings
from app.core.exceptions import install_exception_handlers
from app.core.logging import configure_logging
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.runtime import load_default_handlers
from app.runtime.events import install_default_subscribers
from app.security.startup import validate_secrets_at_startup


configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_secrets_at_startup()
    load_default_handlers()
    install_default_subscribers()
    yield


app = FastAPI(
    title="Platform API",
    version="1.0.0",
    description="Enterprise communication platform backend.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id", "X-Correlation-Id"],
)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1024)


@app.get("/", include_in_schema=False)
def root():
    return {"name": "platform-api", "version": app.version, "env": settings.APP_ENV}


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok"}

install_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")
app.include_router(public_router, prefix="/api/public", tags=["public"])
