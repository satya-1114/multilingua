from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import ok
from app.dependencies.auth import current_user
from app.dependencies.db import get_db
from app.models.misc import UserPreference
from app.models.user import User

router = APIRouter()


@router.get("")
def get_settings(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.query(UserPreference).filter(UserPreference.user_id == user.id).all()
    return ok({r.key: r.value for r in rows})
