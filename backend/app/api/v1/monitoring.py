from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.responses import ok
from app.dependencies.auth import require_perm
from app.dependencies.db import get_db
from app.models.communication import Delivery, DeliveryRecipient
from app.models.user import User
from app.services import communication as comm
from app.services import monitoring as mon

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db), _: User = Depends(require_perm("monitoring:view"))):
    checks = []
    try:
        db.execute(text("SELECT 1"))
        checks.append({"name": "postgres", "ok": True})
    except Exception as exc:
        checks.append({"name": "postgres", "ok": False, "error": str(exc)[:200]})
    for provider in comm.provider_health():
        checks.append({"name": f"{provider['channel']}:{provider['provider']}", "ok": provider["configured"]})
    status = "ok" if all(c["ok"] for c in checks) else "degraded"
    return ok({"status": status, "at": datetime.now(timezone.utc).isoformat(), "checks": checks})


@router.get("/system")
def system(_: User = Depends(require_perm("monitoring:view"))):
    return ok(mon.system_snapshot())


@router.get("/database")
def database(db: Session = Depends(get_db), _: User = Depends(require_perm("monitoring:view"))):
    return ok(mon.database_snapshot(db))


@router.get("/logs")
def logs(_: User = Depends(require_perm("monitoring:view"))):
    return ok([])


@router.get("/queues")
def queues(_: User = Depends(require_perm("monitoring:view"))):
    try:
        from app.workers.celery_app import celery_app
        inspect = celery_app.control.inspect(timeout=1.0)
        active = inspect.active() or {}
        reserved = inspect.reserved() or {}
        scheduled = inspect.scheduled() or {}
        stats = inspect.stats() or {}
    except Exception:
        active, reserved, scheduled, stats = {}, {}, {}, {}

    worker_names = sorted(set(list(active.keys()) + list(reserved.keys()) + list(stats.keys())))
    workers = [
        {
            "name": w,
            "active": len(active.get(w, [])),
            "reserved": len(reserved.get(w, [])),
            "scheduled": len(scheduled.get(w, [])),
            "pool": (stats.get(w, {}) or {}).get("pool", {}),
        }
        for w in worker_names
    ]
    return ok({"workers": workers, "queues": [
        {"name": q, "pending": 0, "running": 0}
        for q in ("default", "ai", "translation", "delivery", "delivery_high", "notifications", "analytics", "scheduled")
    ]})


@router.get("/deliveries")
def delivery_stats(db: Session = Depends(get_db), _: User = Depends(require_perm("monitoring:view"))):
    from sqlalchemy import func
    by_status = dict(db.query(Delivery.status, func.count(Delivery.id)).group_by(Delivery.status).all())
    recipient_by_status = dict(
        db.query(DeliveryRecipient.status, func.count(DeliveryRecipient.id)).group_by(DeliveryRecipient.status).all()
    )
    return ok({"deliveries": by_status, "recipients": recipient_by_status})


@router.post("/queues/{task_id}/cancel")
def cancel_job(task_id: str, _: User = Depends(require_perm("monitoring:view"))):
    try:
        from app.workers.celery_app import celery_app
        celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
        return ok({"cancelled": True, "taskId": task_id})
    except Exception as exc:
        return ok({"cancelled": False, "error": str(exc)[:200]})


@router.get("/providers")
def providers(_: User = Depends(require_perm("monitoring:view"))):
    return ok(comm.provider_health())


@router.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
def prometheus_metrics(db: Session = Depends(get_db)):
    """Prometheus text-format exposition.

    Emits a small set of live gauges even when ``prometheus_client`` is
    absent so scrapers still see structured output.
    """
    from sqlalchemy import func
    sys = mon.system_snapshot()
    db_stats = mon.database_snapshot(db)
    delivery_total = db.scalar(func.count(DeliveryRecipient.id).select()) if False else db.query(DeliveryRecipient).count()

    lines = [
        "# HELP app_uptime_seconds Process uptime in seconds",
        "# TYPE app_uptime_seconds gauge",
        f"app_uptime_seconds {sys.get('uptimeSeconds', 0)}",
        "# HELP app_delivery_recipients_total Total delivery recipients recorded",
        "# TYPE app_delivery_recipients_total counter",
        f"app_delivery_recipients_total {delivery_total}",
        "# HELP app_database_connections Active DB connections",
        "# TYPE app_database_connections gauge",
        f"app_database_connections {int(db_stats.get('connections') or 0)}",
    ]
    if isinstance(sys.get("memory"), dict):
        lines += [
            "# HELP app_memory_percent Process memory percent utilisation",
            "# TYPE app_memory_percent gauge",
            f"app_memory_percent {sys['memory'].get('percent', 0)}",
        ]
    return "\n".join(lines) + "\n"
