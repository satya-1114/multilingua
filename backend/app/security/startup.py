"""Startup secret / configuration validation."""
from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


def validate_secrets_at_startup() -> list[str]:
    """Log configuration warnings and return them. Never fatal."""
    warnings = settings.validate_production()
    for w in warnings:
        log.warning("startup_config_warning", warning=w, env=settings.APP_ENV)
    return warnings


__all__ = ["validate_secrets_at_startup"]
