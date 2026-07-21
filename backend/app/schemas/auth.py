"""Additional auth schemas."""
from __future__ import annotations

from datetime import datetime

from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    rememberMe: bool = False
    deviceId: str | None = None


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    fullName: str = Field(min_length=2, max_length=160)
    # Self-registration is limited to non-privileged roles. Any other value
    # (including omitted) falls back to "viewer".
    role: Literal["viewer", "volunteer", "campaign_manager"] = "viewer"
    phone: str | None = None
    profile: dict[str, Any] | None = None


class TokenPair(BaseModel):
    accessToken: str
    refreshToken: str
    tokenType: str = "Bearer"
    expiresAt: datetime
    sessionId: str | None = None


class RefreshRequest(BaseModel):
    refreshToken: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class VerifyEmailRequest(BaseModel):
    token: str


class RequestOtpRequest(BaseModel):
    email: EmailStr


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=8)


class ChangePasswordRequest(BaseModel):
    currentPassword: str = Field(min_length=8, max_length=128)
    newPassword: str = Field(min_length=8, max_length=128)


class LockAccountRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=120)
    minutes: int = Field(default=60, ge=1, le=60 * 24 * 30)


class MfaEnrollRequest(BaseModel):
    factorType: str = Field(pattern="^(totp|sms|email)$")
    label: str = ""


class MfaVerifyRequest(BaseModel):
    factorId: str
    code: str = Field(min_length=4, max_length=10)
