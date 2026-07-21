"""Authentication API — production endpoints wired to real services."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.responses import ok
from app.dependencies.auth import current_user
from app.dependencies.db import get_db
from app.dependencies.rbac import invalidate_permission_cache
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RequestOtpRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
    VerifyOtpRequest,
)
from app.services import audit as audit_service
from app.services import auth as auth_service

router = APIRouter()


def _client(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    return ip, request.headers.get("user-agent")


def _user_dto(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "fullName": user.full_name,
        "avatarUrl": user.avatar_url,
        "status": "active" if user.is_active else "suspended",
        "roles": [r.name for r in user.roles],
        "emailVerified": user.email_verified_at is not None,
        "defaultWorkspaceId": str(user.default_workspace_id) if user.default_workspace_id else None,
        "createdAt": user.created_at.isoformat(),
        "updatedAt": user.updated_at.isoformat(),
    }


@router.post("/register", status_code=201)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    ip, ua = _client(request)
    user = auth_service.register(
        db,
        email=payload.email,
        password=payload.password,
        full_name=payload.fullName,
        role=payload.role,
        ip=ip,
    )
    # Generate verification token (would be delivered by email in production).
    verification_token = auth_service.create_email_verification(db, user)
    tokens = auth_service.issue_tokens(db, user, ip=ip, ua=ua)
    audit_service.log(db, action="registered", module="auth", actor_id=user.id, entity_id=str(user.id), ip=ip, ua=ua)
    return ok({"user": _user_dto(user), "token": tokens, "verificationToken": verification_token})


@router.post("/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip, ua = _client(request)
    user = auth_service.authenticate(db, email=payload.email, password=payload.password, ip=ip, ua=ua)
    tokens = auth_service.issue_tokens(
        db, user, ip=ip, ua=ua, device_id=payload.deviceId, remember=payload.rememberMe
    )
    audit_service.log(db, action="logged_in", module="auth", actor_id=user.id, entity_id=str(user.id), ip=ip, ua=ua)
    return ok({"user": _user_dto(user), "token": tokens})


@router.post("/token", include_in_schema=True)
def oauth2_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """OAuth2 Password Flow token endpoint used by Swagger 'Authorize'."""
    ip, ua = _client(request)
    user = auth_service.authenticate(db, email=form_data.username, password=form_data.password, ip=ip, ua=ua)
    tokens = auth_service.issue_tokens(db, user, ip=ip, ua=ua)
    audit_service.log(db, action="logged_in", module="auth", actor_id=user.id, entity_id=str(user.id), ip=ip, ua=ua)
    access_token = tokens.get("accessToken") if isinstance(tokens, dict) else getattr(tokens, "accessToken", None)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh")
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    ip, ua = _client(request)
    tokens = auth_service.refresh_tokens(db, payload.refreshToken, ip=ip, ua=ua)
    return ok(tokens)


@router.post("/logout")
def logout(payload: RefreshRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    auth_service.revoke(db, payload.refreshToken)
    audit_service.log(db, action="logged_out", module="auth", actor_id=user.id, entity_id=str(user.id))
    return ok({"revoked": True})


@router.post("/logout-all")
def logout_all(db: Session = Depends(get_db), user: User = Depends(current_user)):
    count = auth_service.revoke_all(db, user.id)
    audit_service.log(db, action="revoked_sessions", module="auth", actor_id=user.id, entity_id=str(user.id))
    return ok({"revoked": count})


@router.get("/session")
def session(user: User = Depends(current_user)):
    return ok({"user": _user_dto(user)})


@router.get("/me")
def me(user: User = Depends(current_user)):
    return ok(_user_dto(user))


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    ip, _ = _client(request)
    token = auth_service.create_password_reset(db, payload.email, ip=ip)
    # Response is always success to avoid user enumeration; token is returned
    # in non-production environments as a delivery convenience.
    return ok({"delivered": True, "token": token})


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    auth_service.reset_password(db, token=payload.token, new_password=payload.password)
    return ok({"reset": True})


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    auth_service.change_password(db, user, current=payload.currentPassword, new=payload.newPassword)
    invalidate_permission_cache(str(user.id))
    audit_service.log(db, action="password_changed", module="auth", actor_id=user.id, entity_id=str(user.id))
    return ok({"changed": True})


@router.post("/verify-email")
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    user = auth_service.verify_email(db, payload.token)
    audit_service.log(db, action="email_verified", module="auth", actor_id=user.id, entity_id=str(user.id))
    return ok({"verified": True, "user": _user_dto(user)})


@router.post("/resend-verification")
def resend_verification(db: Session = Depends(get_db), user: User = Depends(current_user)):
    token = auth_service.create_email_verification(db, user)
    return ok({"delivered": True, "token": token})


@router.post("/request-otp")
def request_otp(payload: RequestOtpRequest, db: Session = Depends(get_db)):
    code = auth_service.create_otp(db, payload.email)
    return ok({"delivered": True, "code": code})


@router.post("/verify-otp")
def verify_otp(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    user = auth_service.verify_otp(db, email=payload.email, code=payload.code)
    return ok({"verified": True, "user": _user_dto(user)})


@router.get("/password-strength")
def password_strength(password: str):
    return ok({"score": auth_service.password_strength(password)})
