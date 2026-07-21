"""System monitoring helpers: performance, DB, and process metrics."""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging import get_logger

log = get_logger(__name__)


def system_snapshot() -> dict:
    snapshot: dict[str, object] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
        "uptimeSeconds": int(time.time() - _START_TS),
    }
    try:
        import psutil  # type: ignore

        vm = psutil.virtual_memory()
        snapshot.update({
            "cpuPercent": psutil.cpu_percent(interval=0.05),
            "memory": {"total": vm.total, "used": vm.used, "percent": vm.percent},
            "disk": {p.mountpoint: psutil.disk_usage(p.mountpoint).percent
                     for p in psutil.disk_partitions(all=False) if p.fstype and os.path.exists(p.mountpoint)},
            "loadAverage": os.getloadavg() if hasattr(os, "getloadavg") else None,
        })
    except Exception:  # pragma: no cover
        snapshot["note"] = "psutil unavailable; install psutil for full metrics"
    return snapshot


def database_snapshot(db: Session) -> dict:
    stats: dict[str, object] = {}
    try:
        stats["version"] = db.execute(text("SELECT version()")).scalar()
        stats["connections"] = db.execute(text("SELECT count(*) FROM pg_stat_activity")).scalar()
        stats["databaseSize"] = db.execute(text("SELECT pg_database_size(current_database())")).scalar()
    except Exception as exc:  # pragma: no cover
        stats["error"] = str(exc)[:200]
    return stats


_START_TS = time.time()
