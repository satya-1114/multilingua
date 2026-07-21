"""Cache abstraction (Phase 9.4).

A small, dependency-free cache API used by workflow runtime statistics,
health snapshots, and other read-mostly caches. The default backend is
:class:`InMemoryCache`; a Redis backend can be plugged in later without
touching call sites via :func:`set_default_cache`.
"""
from __future__ import annotations

from .backend import CacheBackend, CacheEntry, get_default_cache, set_default_cache
from .decorators import cached
from .keys import make_key
from .memory import InMemoryCache

__all__ = [
    "CacheBackend",
    "CacheEntry",
    "InMemoryCache",
    "cached",
    "get_default_cache",
    "make_key",
    "set_default_cache",
]