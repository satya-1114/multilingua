from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import ok, paginated
from app.dependencies.auth import require_perm
from app.dependencies.db import get_db
from app.dependencies.pagination import PageParams, page_params
from app.models.automation import LegacyWorkflowDefinition
from app.models.user import User
from app.schemas.automation import AutomationCreate

router = APIRouter()


def _serialize(w: LegacyWorkflowDefinition) -> dict:
    return {
        "id": str(w.id), "name": w.name, "status": w.status, "version": w.version,
        "definition": w.definition, "createdAt": w.created_at.isoformat(), "updatedAt": w.updated_at.isoformat(),
    }


@router.get("")
def list_(pp: PageParams = Depends(page_params), db: Session = Depends(get_db), _: User = Depends(require_perm("automation:view"))):
    total = db.query(LegacyWorkflowDefinition).count()
    rows = db.query(LegacyWorkflowDefinition).offset((pp.page - 1) * pp.page_size).limit(pp.page_size).all()
    return paginated([_serialize(w) for w in rows], pp.page, pp.page_size, total)


@router.post("", status_code=201)
def create(payload: AutomationCreate, db: Session = Depends(get_db), _: User = Depends(require_perm("automation:manage"))):
    obj = LegacyWorkflowDefinition(workspace_id=payload.workspaceId, name=payload.name, definition=payload.definition)
    db.add(obj); db.commit(); db.refresh(obj)
    return ok(_serialize(obj))
