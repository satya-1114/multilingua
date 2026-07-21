"""MFA scaffolding — provider-agnostic interfaces.

Concrete providers (Twilio SMS, TOTP with pyotp, email OTP) plug into
:func:`register_factor` behind their factor type without changing callers.
"""
from __future__ import annotations

import hashlib
import secrets
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.models.auth_extras import MfaFactor, RecoveryCode
from app.models.user import User


class MfaProvider(Protocol):
    factor_type: str

    def enroll(self, user: User) -> dict: ...
    def verify(self, factor: MfaFactor, code: str) -> bool: ...


_providers: dict[str, MfaProvider] = {}


def register_provider(provider: MfaProvider) -> None:
    _providers[provider.factor_type] = provider


def get_provider(factor_type: str) -> MfaProvider:
    if factor_type not in _providers:
        raise NotFoundError(f"MFA provider not configured: {factor_type}")
    return _providers[factor_type]


def list_factors(db: Session, user: User) -> list[dict]:
    rows = db.query(MfaFactor).filter(MfaFactor.user_id == user.id).all()
    return [{"id": str(r.id), "type": r.factor_type, "label": r.label, "verified": r.verified} for r in rows]


def enroll_factor(db: Session, user: User, factor_type: str, *, label: str = "") -> dict:
    if db.query(MfaFactor).filter(MfaFactor.user_id == user.id, MfaFactor.factor_type == factor_type, MfaFactor.verified.is_(True)).first():
        raise ConflictError(f"{factor_type} factor already enrolled")
    provider = get_provider(factor_type)
    payload = provider.enroll(user)
    factor = MfaFactor(
        user_id=user.id, factor_type=factor_type, label=label or factor_type,
        secret=payload.get("secret"), verified=False,
    )
    db.add(factor)
    db.commit()
    db.refresh(factor)
    payload["factorId"] = str(factor.id)
    return payload


def verify_factor(db: Session, user: User, factor_id: str, code: str) -> None:
    factor = db.query(MfaFactor).filter(MfaFactor.user_id == user.id, MfaFactor.id == factor_id).one_or_none()
    if not factor:
        raise NotFoundError("MFA factor not found")
    provider = get_provider(factor.factor_type)
    if not provider.verify(factor, code):
        raise UnauthorizedError("Invalid MFA code")
    factor.verified = True
    db.commit()


def disable_factor(db: Session, user: User, factor_id: str) -> None:
    factor = db.query(MfaFactor).filter(MfaFactor.user_id == user.id, MfaFactor.id == factor_id).one_or_none()
    if not factor:
        raise NotFoundError("MFA factor not found")
    db.delete(factor)
    db.commit()


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def generate_recovery_codes(db: Session, user: User, *, count: int = 10) -> list[str]:
    db.query(RecoveryCode).filter(RecoveryCode.user_id == user.id).delete()
    codes = [secrets.token_hex(5) for _ in range(count)]
    for c in codes:
        db.add(RecoveryCode(user_id=user.id, code_hash=_hash_code(c)))
    db.commit()
    return codes


def consume_recovery_code(db: Session, user: User, code: str) -> bool:
    row = (
        db.query(RecoveryCode)
        .filter(RecoveryCode.user_id == user.id, RecoveryCode.code_hash == _hash_code(code), RecoveryCode.used_at.is_(None))
        .first()
    )
    if not row:
        return False
    from datetime import datetime, timezone
    row.used_at = datetime.now(timezone.utc)
    db.commit()
    return True
