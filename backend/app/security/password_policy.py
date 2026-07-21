"""Configurable password policy engine.

Validates a candidate password against a set of rules and computes a
strength score in the 0-100 range.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from app.core.exceptions import ValidationError


@dataclass(frozen=True)
class PasswordPolicy:
    min_length: int = 10
    max_length: int = 128
    require_upper: bool = True
    require_lower: bool = True
    require_digit: bool = True
    require_symbol: bool = True
    history_size: int = 5           # last N passwords cannot be reused
    max_age_days: int = 180         # 0 disables expiration
    disallow_common: bool = True
    forbid_substrings: tuple[str, ...] = field(default_factory=lambda: ("password", "qwerty", "welcome", "admin"))


DEFAULT_POLICY = PasswordPolicy()


_SYMBOL_RE = re.compile(r"[^A-Za-z0-9]")


def _entropy_bits(password: str) -> float:
    pool = 0
    if re.search(r"[a-z]", password): pool += 26
    if re.search(r"[A-Z]", password): pool += 26
    if re.search(r"\d", password): pool += 10
    if _SYMBOL_RE.search(password): pool += 32
    if pool == 0:
        return 0.0
    return len(password) * math.log2(pool)


def strength_score(password: str) -> int:
    """Return a 0-100 strength score derived from entropy + variety."""
    bits = _entropy_bits(password)
    # 80 bits ~ strong, 128 bits ~ excellent.
    score = min(100, int(bits / 1.28))
    variety = sum([
        bool(re.search(r"[a-z]", password)),
        bool(re.search(r"[A-Z]", password)),
        bool(re.search(r"\d", password)),
        bool(_SYMBOL_RE.search(password)),
    ])
    score = min(100, score + (variety - 1) * 5)
    return max(0, score)


def validate_password(password: str, *, policy: PasswordPolicy = DEFAULT_POLICY, previous_hashes: list[str] | None = None) -> None:
    """Raise :class:`ValidationError` when a password fails policy."""
    errors: list[str] = []
    if len(password) < policy.min_length:
        errors.append(f"Password must be at least {policy.min_length} characters")
    if len(password) > policy.max_length:
        errors.append(f"Password must be at most {policy.max_length} characters")
    if policy.require_upper and not re.search(r"[A-Z]", password):
        errors.append("Password must include an uppercase letter")
    if policy.require_lower and not re.search(r"[a-z]", password):
        errors.append("Password must include a lowercase letter")
    if policy.require_digit and not re.search(r"\d", password):
        errors.append("Password must include a digit")
    if policy.require_symbol and not _SYMBOL_RE.search(password):
        errors.append("Password must include a symbol")
    lowered = password.lower()
    if policy.disallow_common:
        for token in policy.forbid_substrings:
            if token in lowered:
                errors.append(f"Password must not contain '{token}'")
                break
    if errors:
        raise ValidationError("Password does not satisfy policy", details={"errors": errors, "score": strength_score(password)})


def check_history(new_hash_verifier, previous_hashes: list[str]) -> None:
    """Reject the password when any previous hash validates against it."""
    for prev in previous_hashes:
        if new_hash_verifier(prev):
            raise ValidationError("Password has been used recently and cannot be reused", details={"code": "password_reuse"})
