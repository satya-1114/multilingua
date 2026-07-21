from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.responses import ok
from app.dependencies.db import get_db

router = APIRouter()


@router.get("/health")
def health():
    return ok({"status": "ok", "at": datetime.now(timezone.utc).isoformat()})


@router.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return ok({"ready": True})
    except Exception:
        return ok({"ready": False})


@router.get("/live")
def live():
    return ok({"live": True})


@router.get("/version")
def version():
    return ok({
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "buildAt": datetime.now(timezone.utc).isoformat(),
    })
