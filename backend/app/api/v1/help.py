from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import ok
from app.dependencies.db import get_db
from app.models.misc import HelpArticle

router = APIRouter()


@router.get("")
def list_articles(db: Session = Depends(get_db)):
    rows = db.query(HelpArticle).all()
    return ok([
        {"id": str(a.id), "title": a.title, "slug": a.slug, "category": a.category}
        for a in rows
    ])
