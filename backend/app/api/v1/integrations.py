from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import ok, paginated
from app.dependencies.auth import require_perm
from app.dependencies.db import get_db
from app.dependencies.pagination import PageParams, page_params
from app.models.integration import Integration, Webhook
from app.models.user import User

router = APIRouter()


@router.get("")
def list_(pp: PageParams = Depends(page_params), db: Session = Depends(get_db), _: User = Depends(require_perm("integration:view"))):
    total = db.query(Integration).count()
    rows = db.query(Integration).offset((pp.page - 1) * pp.page_size).limit(pp.page_size).all()
    return paginated([
        {"id": str(i.id), "provider": i.provider, "kind": i.kind, "status": i.status, "settings": i.settings,
         "createdAt": i.created_at.isoformat(), "updatedAt": i.updated_at.isoformat()}
        for i in rows
    ], pp.page, pp.page_size, total)


@router.get("/webhooks")
def webhooks(db: Session = Depends(get_db), _: User = Depends(require_perm("webhook:manage"))):
    rows = db.query(Webhook).all()
    return ok([
        {"id": str(w.id), "url": w.url, "events": w.events, "enabled": w.enabled, "retryCount": w.retry_count}
        for w in rows
    ])
