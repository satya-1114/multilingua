from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.responses import ok, paginated
from app.dependencies.auth import require_perm
from app.dependencies.db import get_db
from app.dependencies.pagination import PageParams, page_params
from app.models.ai import AIHistory, AIPrompt, WorkspaceAiSettings
from app.models.user import User
from app.schemas.ai import AiGenerationRequest
from app.services import ai as ai_service
from app.services.ai_providers import SUPPORTED_PROVIDERS
from app.services.ai_providers import _redact as _redact_secret  # noqa: WPS450 — internal helper
from app.security.crypto import decrypt_secret, encrypt_secret, mask_secret

router = APIRouter()


DEFAULT_SYSTEM_PROMPTS: list[dict] = [
    {"name": "Emergency Alert", "category": "emergency",
     "description": "Broadcast an urgent public-safety alert.",
     "body": ("Draft an emergency alert for {{event}} affecting {{district}}. Include the issuing "
              "authority {{department}}, action to take, and helpline {{helpline}}. Keep under 280 characters."),
     "variables": ["district", "event", "department", "helpline"],
     "tags": ["emergency", "sms", "public-safety"]},
    {"name": "Government Notice", "category": "government",
     "description": "Formal government notice with reference codes and clear actions.",
     "body": ("Draft a formal government notice from {{department}} regarding {{event}}. "
              "Cite the reference number, applicable date {{date}}, and citizen actions required."),
     "variables": ["department", "event", "date"], "tags": ["government", "notice"]},
    {"name": "Healthcare Advisory", "category": "healthcare",
     "description": "Public-health advisory in plain, WHO-compliant language.",
     "body": ("Draft a healthcare advisory for {{audience}} about {{topic}}. Use plain language, "
              "list preventive steps, and include the contact {{helpline}}."),
     "variables": ["audience", "topic", "helpline"], "tags": ["healthcare", "advisory"]},
    {"name": "NGO Awareness Campaign", "category": "ngo",
     "description": "Community-friendly NGO awareness message.",
     "body": ("Write an inclusive awareness message for {{city}} on {{topic}}, organised by {{organization}}. "
              "Include event date {{date}} and time {{time}}."),
     "variables": ["organization", "city", "topic", "date", "time"], "tags": ["ngo", "awareness"]},
    {"name": "Education Notice", "category": "education",
     "description": "Semester or scholarship notice.",
     "body": ("Draft an official notice from {{organization}} for {{event}} affecting all students. "
              "Include revised schedule, deadline {{date}} and contact department {{department}}."),
     "variables": ["organization", "event", "date", "department"], "tags": ["education", "notice"]},
    {"name": "Disaster Alert", "category": "emergency",
     "description": "Rapid situational alert for a natural disaster.",
     "body": ("Draft a rapid alert for a {{event}} affecting {{district}}. Include evacuation route, "
              "shelter location, helpline {{helpline}}, and issuing department {{department}}."),
     "variables": ["event", "district", "helpline", "department"], "tags": ["disaster", "alert", "sms"]},
    {"name": "Festival Greeting", "category": "general",
     "description": "Warm, inclusive festival greeting.",
     "body": "Write a warm, inclusive greeting for the {{event}} festival from {{organization}} to citizens of {{city}}.",
     "variables": ["event", "organization", "city"], "tags": ["festival", "greeting"]},
    {"name": "Public Safety Reminder", "category": "emergency",
     "description": "Non-urgent public safety reminder.",
     "body": ("Draft a friendly public safety reminder for {{audience}} about {{topic}} in {{city}}. "
              "Include a clear action."),
     "variables": ["audience", "topic", "city"], "tags": ["safety", "reminder"]},
    {"name": "Vaccination Reminder", "category": "healthcare",
     "description": "SMS-length reminder for the next vaccination visit.",
     "body": ("Write a friendly reminder to {{recipient_name}} about the {{event}} vaccination "
              "visit at {{time}} on {{date}}. Sign off from {{organization}}."),
     "variables": ["recipient_name", "event", "date", "time", "organization"],
     "tags": ["vaccination", "healthcare", "sms"]},
]


def _ensure_system_prompts(db: Session, workspace_id: uuid.UUID) -> None:
    """Seed the default system prompt library for a workspace, once."""
    existing = {
        row.name for row in db.query(AIPrompt.name)
        .filter(AIPrompt.workspace_id == workspace_id, AIPrompt.is_system.is_(True))
        .all()
    }
    added = False
    for p in DEFAULT_SYSTEM_PROMPTS:
        if p["name"] in existing:
            continue
        db.add(AIPrompt(
            workspace_id=workspace_id,
            name=p["name"], category=p["category"], body=p["body"],
            description=p["description"], variables=p["variables"], tags=p["tags"],
            is_system=True, favorite=False, usage_count=0,
        ))
        added = True
    if added:
        db.commit()


def _prompt_dto(p: AIPrompt) -> dict:
    return {
        "id": str(p.id),
        "workspaceId": str(p.workspace_id),
        "name": p.name,
        "title": p.name,
        "description": p.description or "",
        "category": p.category,
        "body": p.body,
        "variables": p.variables or [],
        "tags": p.tags or [],
        "favorite": bool(p.favorite),
        "isSystem": bool(p.is_system),
        "usageCount": int(p.usage_count or 0),
        "createdBy": str(p.user_id) if p.user_id else "system",
        "createdAt": p.created_at.isoformat(),
        "updatedAt": p.updated_at.isoformat(),
    }


def _history_dto(h: AIHistory) -> dict:
    return {
        "id": str(h.id),
        "title": h.title or (h.prompt[:80] + ("…" if len(h.prompt) > 80 else "")),
        "prompt": h.prompt,
        "content": h.content,
        "preview": (h.content or "")[:180],
        "provider": h.provider,
        "model": h.model,
        "mode": h.mode,
        "language": h.language,
        "tokens": h.tokens,
        "promptTokens": h.prompt_tokens,
        "completionTokens": h.completion_tokens,
        "responseTimeMs": h.response_time_ms,
        "status": h.status,
        "contentType": h.mode,
        "createdBy": str(h.user_id) if h.user_id else "",
        "createdAt": h.created_at.isoformat(),
        "updatedAt": h.updated_at.isoformat(),
        "versions": 1,
    }


def _load_settings(db: Session, workspace_id: uuid.UUID | None) -> dict:
    if not workspace_id:
        return {}
    row = db.query(WorkspaceAiSettings).filter(WorkspaceAiSettings.workspace_id == workspace_id).one_or_none()
    if not row:
        return {}
    from app.services.ai_providers import _is_deprecated_gemini_model
    stored_model = row.model or ""
    # Coerce known-deprecated Gemini ids so downstream resolution falls back
    # to settings.GEMINI_MODEL. Prevents stale DB rows from pinning a model
    # Google has retired.
    if (row.provider or "").lower() == "gemini" and _is_deprecated_gemini_model(stored_model):
        stored_model = ""
    return {
        "provider": row.provider,
        "model": stored_model,
        "api_key": decrypt_secret(row.api_key_ciphertext) if row.api_key_ciphertext else "",
        "base_url": row.base_url,
        "project_id": row.project_id,
        "temperature": row.temperature,
        "max_tokens": row.max_tokens,
    }


class ReviewRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    checks: list[str] | None = None
    provider: str | None = None


class RenderPromptRequest(BaseModel):
    body: str
    variables: dict = {}


@router.get("/providers")
def providers(_: User = Depends(require_perm("ai:use"))):
    available = ai_service.available_providers()
    return ok({
        "providers": available,
        "supported": list(SUPPORTED_PROVIDERS),
        "default": available[0] if available else None,
    })


@router.post("/generate")
async def generate(
    payload: AiGenerationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("ai:use")),
):
    workspace_id = payload.workspaceId or user.default_workspace_id
    ws_settings = _load_settings(db, workspace_id if workspace_id else None) if workspace_id else {}
    result = await ai_service.generate(
        prompt=payload.prompt, mode=payload.mode, tone=payload.tone,
        language=payload.language, rate_limit_key=str(user.id),
        workspace_settings=ws_settings,
    )
    history_id = None
    if workspace_id:
        history = AIHistory(
            workspace_id=workspace_id, user_id=user.id, prompt=payload.prompt,
            model=result["model"], tokens=result["tokens"], content=result["content"],
            provider=result.get("provider", ""), mode=payload.mode, language=payload.language,
            title=(payload.prompt[:80]),
            response_time_ms=int(result.get("responseTimeMs") or 0),
            prompt_tokens=int(result.get("promptTokens") or 0),
            completion_tokens=int(result.get("completionTokens") or 0),
            status="ok",
        )
        db.add(history); db.commit(); db.refresh(history)
        history_id = str(history.id)
    return ok({
        "id": history_id or "",
        "prompt": payload.prompt,
        "provider": result.get("provider"),
        "model": result["model"],
        "tokens": result["tokens"],
        "content": result["content"],
        "cached": result.get("cached", False),
        "responseTimeMs": result.get("responseTimeMs", 0),
        "mode": payload.mode,
        "language": payload.language,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    })


@router.post("/stream")
async def stream(payload: AiGenerationRequest, _: User = Depends(require_perm("ai:use"))):
    async def _gen():
        async for chunk in ai_service.stream(prompt=payload.prompt, mode=payload.mode):
            yield chunk
    return StreamingResponse(_gen(), media_type="text/plain")


@router.post("/review")
async def review(payload: ReviewRequest, _: User = Depends(require_perm("ai:use"))):
    return ok(await ai_service.review(content=payload.content, checks=payload.checks, provider=payload.provider))


@router.post("/render")
def render(payload: RenderPromptRequest, _: User = Depends(require_perm("ai:use"))):
    rendered, missing = ai_service.render_prompt(payload.body, payload.variables)
    return ok({"rendered": rendered, "missing": missing})


# ------------------------------------------------------------------ prompts

class PromptInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str = "general"
    description: str = ""
    body: str = Field(min_length=1)
    variables: list = []
    tags: list = []
    favorite: bool = False
    workspaceId: str | None = None


@router.get("/prompts")
def list_prompts(
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("ai:use")),
    search: str | None = None,
    category: str | None = None,
    favorites_only: bool = False,
):
    workspace_id = user.default_workspace_id
    if workspace_id:
        _ensure_system_prompts(db, workspace_id)
    q = db.query(AIPrompt)
    if workspace_id:
        q = q.filter(AIPrompt.workspace_id == workspace_id)
    if category and category != "all":
        q = q.filter(AIPrompt.category == category)
    if favorites_only:
        q = q.filter(AIPrompt.favorite.is_(True))
    if search:
        pattern = f"%{search}%"
        q = q.filter(or_(AIPrompt.name.ilike(pattern), AIPrompt.description.ilike(pattern), AIPrompt.body.ilike(pattern)))
    total = q.count()
    rows = q.order_by(AIPrompt.favorite.desc(), AIPrompt.updated_at.desc())\
        .offset((pp.page - 1) * pp.page_size).limit(pp.page_size).all()
    return paginated([_prompt_dto(p) for p in rows], pp.page, pp.page_size, total)


@router.post("/prompts")
def create_prompt(payload: PromptInput, db: Session = Depends(get_db), user: User = Depends(require_perm("ai:use"))):
    workspace_id = payload.workspaceId or user.default_workspace_id
    if not workspace_id:
        raise HTTPException(400, "workspaceId required")
    row = AIPrompt(
        workspace_id=workspace_id, user_id=user.id,
        name=payload.name, category=payload.category, description=payload.description,
        body=payload.body, variables=payload.variables, tags=payload.tags,
        favorite=payload.favorite, is_system=False, usage_count=0,
    )
    db.add(row); db.commit(); db.refresh(row)
    return ok(_prompt_dto(row))


@router.patch("/prompts/{pid}")
def update_prompt(pid: str, payload: PromptInput, db: Session = Depends(get_db), user: User = Depends(require_perm("ai:use"))):
    row = db.get(AIPrompt, pid)
    if not row or (user.default_workspace_id and row.workspace_id != user.default_workspace_id):
        raise HTTPException(404, "Prompt not found")
    if row.is_system:
        raise HTTPException(400, "System prompts cannot be edited — duplicate first")
    for field in ("name", "category", "description", "body"):
        setattr(row, field, getattr(payload, field))
    row.variables = payload.variables
    row.tags = payload.tags
    row.favorite = payload.favorite
    db.commit(); db.refresh(row)
    return ok(_prompt_dto(row))


@router.delete("/prompts/{pid}")
def delete_prompt(pid: str, db: Session = Depends(get_db), user: User = Depends(require_perm("ai:use"))):
    row = db.get(AIPrompt, pid)
    if not row or (user.default_workspace_id and row.workspace_id != user.default_workspace_id):
        raise HTTPException(404, "Prompt not found")
    if row.is_system:
        raise HTTPException(400, "System prompts cannot be deleted")
    db.delete(row); db.commit()
    return ok({"deleted": True})


@router.post("/prompts/{pid}/favorite")
def toggle_favorite(pid: str, db: Session = Depends(get_db), user: User = Depends(require_perm("ai:use"))):
    row = db.get(AIPrompt, pid)
    if not row or (user.default_workspace_id and row.workspace_id != user.default_workspace_id):
        raise HTTPException(404, "Prompt not found")
    row.favorite = not row.favorite
    db.commit(); db.refresh(row)
    return ok(_prompt_dto(row))


@router.post("/prompts/{pid}/duplicate")
def duplicate_prompt(pid: str, db: Session = Depends(get_db), user: User = Depends(require_perm("ai:use"))):
    source = db.get(AIPrompt, pid)
    if not source or (user.default_workspace_id and source.workspace_id != user.default_workspace_id):
        raise HTTPException(404, "Prompt not found")
    copy = AIPrompt(
        workspace_id=source.workspace_id, user_id=user.id,
        name=f"{source.name} (copy)", category=source.category, description=source.description,
        body=source.body, variables=source.variables, tags=source.tags,
        favorite=False, is_system=False, usage_count=0,
    )
    db.add(copy); db.commit(); db.refresh(copy)
    return ok(_prompt_dto(copy))


@router.get("/history")
def history(
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("ai:history_view")),
    search: str | None = None,
    language: str | None = None,
    provider: str | None = None,
):
    q = db.query(AIHistory).filter(AIHistory.user_id == user.id)
    if search:
        pattern = f"%{search}%"
        q = q.filter(or_(AIHistory.prompt.ilike(pattern), AIHistory.content.ilike(pattern), AIHistory.title.ilike(pattern)))
    if language:
        q = q.filter(AIHistory.language == language)
    if provider:
        q = q.filter(AIHistory.provider == provider)
    total = q.count()
    rows = q.order_by(AIHistory.created_at.desc()).offset((pp.page - 1) * pp.page_size).limit(pp.page_size).all()
    return paginated([_history_dto(h) for h in rows], pp.page, pp.page_size, total)


@router.delete("/history/{hid}")
def delete_history(hid: str, db: Session = Depends(get_db), user: User = Depends(require_perm("ai:history_view"))):
    row = db.get(AIHistory, hid)
    if not row or row.user_id != user.id:
        return ok({"deleted": False})
    db.delete(row); db.commit()
    return ok({"deleted": True})


# ------------------------------------------------------------------ workspace settings

class WorkspaceAiSettingsInput(BaseModel):
    provider: str = "gemini"
    model: str = ""
    apiKey: str | None = None  # None → keep existing, "" → clear
    baseUrl: str = ""
    projectId: str = ""
    temperature: float = 0.4
    maxTokens: int = 1024
    autoReview: bool = True
    autoSave: bool = True
    defaultTone: str = "professional"
    defaultLanguage: str = "en"


def _settings_dto(row: WorkspaceAiSettings) -> dict:
    plaintext = decrypt_secret(row.api_key_ciphertext) if row.api_key_ciphertext else ""
    return {
        "id": str(row.id),
        "workspaceId": str(row.workspace_id),
        "provider": row.provider,
        "model": row.model,
        "apiKeyMasked": mask_secret(plaintext),
        "hasApiKey": bool(plaintext),
        "baseUrl": row.base_url,
        "projectId": row.project_id,
        "temperature": float(row.temperature),
        "maxTokens": int(row.max_tokens),
        "autoReview": bool(row.auto_review),
        "autoSave": bool(row.auto_save),
        "defaultTone": row.default_tone,
        "defaultLanguage": row.default_language,
        "updatedAt": row.updated_at.isoformat(),
    }


@router.get("/workspace-settings")
def get_workspace_settings(db: Session = Depends(get_db), user: User = Depends(require_perm("ai:use"))):
    wid = user.default_workspace_id
    if not wid:
        raise HTTPException(400, "No default workspace")
    row = db.query(WorkspaceAiSettings).filter(WorkspaceAiSettings.workspace_id == wid).one_or_none()
    if not row:
        row = WorkspaceAiSettings(workspace_id=wid, provider="gemini", model="")
        db.add(row); db.commit(); db.refresh(row)
    return ok(_settings_dto(row))


@router.put("/workspace-settings")
def put_workspace_settings(
    payload: WorkspaceAiSettingsInput,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("settings:manage")),
):
    wid = user.default_workspace_id
    if not wid:
        raise HTTPException(400, "No default workspace")
    if payload.provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(400, f"Unsupported provider '{payload.provider}'")
    row = db.query(WorkspaceAiSettings).filter(WorkspaceAiSettings.workspace_id == wid).one_or_none()
    if not row:
        row = WorkspaceAiSettings(workspace_id=wid)
        db.add(row)
    row.provider = payload.provider
    row.model = payload.model
    row.base_url = payload.baseUrl
    row.project_id = payload.projectId
    row.temperature = float(max(0.0, min(2.0, payload.temperature)))
    row.max_tokens = int(max(1, min(8192, payload.maxTokens)))
    row.auto_review = bool(payload.autoReview)
    row.auto_save = bool(payload.autoSave)
    row.default_tone = payload.defaultTone
    row.default_language = payload.defaultLanguage
    # Only update the secret when explicitly provided; empty string clears it.
    if payload.apiKey is not None:
        row.api_key_ciphertext = encrypt_secret(payload.apiKey) if payload.apiKey else ""
    db.commit(); db.refresh(row)
    return ok(_settings_dto(row))


@router.post("/workspace-settings/test")
async def test_workspace_settings(
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("ai:use")),
):
    wid = user.default_workspace_id
    if not wid:
        raise HTTPException(400, "No default workspace")
    ws_settings = _load_settings(db, wid)
    try:
        result = await ai_service.generate(
            prompt="Reply with the single word: ok",
            mode="generate", tone="neutral", language="en",
            cache=False, workspace_settings=ws_settings,
        )
        return ok({"ok": True, "provider": result.get("provider"), "model": result["model"]})
    except Exception as exc:  # noqa: BLE001
        # Never let a stringified exception carry the workspace API key back
        # to the browser (Gemini's URL embeds ``?key=<secret>``).
        return ok({"ok": False, "error": _redact_secret(str(exc))})


# ------------------------------------------------------------------ prompt use

@router.post("/prompts/{pid}/use")
def mark_prompt_used(pid: str, db: Session = Depends(get_db), user: User = Depends(require_perm("ai:use"))):
    row = db.get(AIPrompt, pid)
    if not row or (user.default_workspace_id and row.workspace_id != user.default_workspace_id):
        raise HTTPException(404, "Prompt not found")
    row.usage_count = (row.usage_count or 0) + 1
    db.commit(); db.refresh(row)
    return ok(_prompt_dto(row))
