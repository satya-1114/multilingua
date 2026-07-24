"""Auth support tables: password history, login attempts, verification
tokens, trusted devices, MFA factors, and account lockouts.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import BaseMixin


class PasswordHistory(BaseMixin, Base):
    __tablename__ = "password_history"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)


class LoginAttempt(BaseMixin, Base):
    __tablename__ = "login_attempts"
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    reason: Mapped[str | None] = mapped_column(String(120), nullable=True)


class AccountLockout(BaseMixin, Base):
    __tablename__ = "account_lockouts"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str | None] = mapped_column(String(120), nullable=True)


class VerificationToken(BaseMixin, Base):
    """Single-use token for email verification, password reset, or OTP."""
    __tablename__ = "verification_tokens"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # email_verify|password_reset|otp
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)


class TrustedDevice(BaseMixin, Base):
    __tablename__ = "trusted_devices"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    device_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    device_type: Mapped[str] = mapped_column(String(32), nullable=False, default="browser")
    browser: Mapped[str | None] = mapped_column(String(64), nullable=True)
    operating_system: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trusted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MfaFactor(BaseMixin, Base):
    __tablename__ = "mfa_factors"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    factor_type: Mapped[str] = mapped_column(String(20), nullable=False)  # totp|sms|email|recovery
    label: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    secret: Mapped[str | None] = mapped_column(String(255), nullable=True)   # encrypted at rest in production
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RecoveryCode(BaseMixin, Base):
    __tablename__ = "mfa_recovery_codes"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
