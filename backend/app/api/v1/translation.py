from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.responses import ok
from app.dependencies.auth import require_perm
from app.dependencies.db import get_db
from app.models.ai import Translation
from app.models.user import User
from app.schemas.translation import TranslateRequest
from app.services import translation as tr

router = APIRouter()


class BatchTranslateRequest(BaseModel):
    items: list[str] = Field(min_length=1, max_length=200)
    targetLanguage: str
    sourceLanguage: str | None = None
    concurrency: int = 4


class GlossaryTermRequest(BaseModel):
    term: str
    translations: dict[str, str]


@router.get("/languages")
def languages():
    return ok(tr.supported_languages())


@router.post("/detect")
def detect(payload: dict, _: User = Depends(require_perm("translation:use"))):
    text = (payload or {}).get("text", "")
    return ok({"language": tr.detect_language(text)})


@router.post("")
async def translate(payload: TranslateRequest, db: Session = Depends(get_db), user: User = Depends(require_perm("translation:use"))):
    result = await tr.translate(
        text=payload.text, target_language=payload.targetLanguage, source_language=payload.sourceLanguage,
    )
    ws = payload.workspaceId or user.default_workspace_id
    if ws:
        entry = Translation(
            workspace_id=ws,
            source_language=result["sourceLanguage"], target_language=result["targetLanguage"],
            source_text=result["sourceText"], translated_text=result["translatedText"],
            quality=result["quality"],
        )
        db.add(entry); db.commit()
    return ok(result)


@router.post("/batch")
async def batch(payload: BatchTranslateRequest, _: User = Depends(require_perm("translation:use"))):
    results = await tr.translate_batch(
        items=payload.items, target_language=payload.targetLanguage,
        source_language=payload.sourceLanguage, concurrency=payload.concurrency,
    )
    return ok({"results": results, "count": len(results)})


@router.post("/compare")
async def compare(payload: TranslateRequest, _: User = Depends(require_perm("translation:use"))):
    return ok(await tr.compare(
        text=payload.text, target_language=payload.targetLanguage, source_language=payload.sourceLanguage,
    ))


@router.post("/glossary")
def add_glossary(payload: GlossaryTermRequest, _: User = Depends(require_perm("translation:use"))):
    tr.register_glossary_term(payload.term, payload.translations)
    return ok({"term": payload.term, "translations": payload.translations})


@router.get("/history")
def history(db: Session = Depends(get_db), _: User = Depends(require_perm("translation:use"))):
    rows = db.query(Translation).order_by(Translation.created_at.desc()).limit(200).all()
    return ok([
        {"id": str(t.id), "sourceLanguage": t.source_language, "targetLanguage": t.target_language,
         "sourceText": t.source_text, "translatedText": t.translated_text, "quality": float(t.quality),
         "createdAt": t.created_at.isoformat(), "updatedAt": t.updated_at.isoformat()}
        for t in rows
    ])
