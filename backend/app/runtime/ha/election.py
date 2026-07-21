"""Default election singleton (Phase 9.2).

Rather than sprinkling `LeaderElector(...)` construction across the
codebase, callers ask the module for the current default. Tests can swap
the elector via :func:`set_default_elector`.
"""
from __future__ import annotations

from .leader import LeaderElector

_default: LeaderElector | None = None


def default_elector() -> LeaderElector:
    global _default
    if _default is None:
        _default = LeaderElector()
    return _default


def set_default_elector(elector: LeaderElector | None) -> LeaderElector | None:
    global _default
    previous = _default
    _default = elector
    return previous


def reset_default_elector() -> None:
    set_default_elector(None)


__all__ = ["default_elector", "set_default_elector", "reset_default_elector"]
