from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.responses import ok
from app.dependencies.auth import current_user
from app.dependencies.db import get_db
from app.models.misc import Favorite
from app.models.user import User

router = APIRouter()


class FavoriteBody(BaseModel):
    targetType: str
    targetId: str


@router.get("")
def list_favorites(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.query(Favorite).filter(Favorite.user_id == user.id).all()
    return ok([{"targetType": r.target_type, "targetId": r.target_id} for r in rows])


@router.post("")
def add_favorite(body: FavoriteBody, db: Session = Depends(get_db), user: User = Depends(current_user)):
    fav = Favorite(user_id=user.id, target_type=body.targetType, target_id=body.targetId)
    db.merge(fav)
    db.commit()
    return ok({"added": True})


@router.delete("")
def remove_favorite(body: FavoriteBody, db: Session = Depends(get_db), user: User = Depends(current_user)):
    db.query(Favorite).filter(
        Favorite.user_id == user.id,
        Favorite.target_type == body.targetType,
        Favorite.target_id == body.targetId,
    ).delete()
    db.commit()
    return ok({"removed": True})
