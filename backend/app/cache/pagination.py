"""Pagination helpers (Phase 9.4).

Utility functions used by API layers to normalize pagination
parameters, compute cursor windows, and build response envelopes
without duplicating math across endpoints.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 200


@dataclass(frozen=True)
class PageParams:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def normalize_page_params(
    page: int | None,
    page_size: int | None,
    *,
    default_size: int = DEFAULT_PAGE_SIZE,
    max_size: int = MAX_PAGE_SIZE,
) -> PageParams:
    p = 1 if page is None or page < 1 else int(page)
    if page_size is None:
        s = default_size
    else:
        s = int(page_size)
        if s < 1:
            s = default_size
    if s > max_size:
        s = max_size
    return PageParams(page=p, page_size=s)


def paginate_sequence(
    items: Sequence[Any],
    *,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[Any], int]:
    params = normalize_page_params(page, page_size)
    total = len(items)
    start = params.offset
    end = start + params.limit
    return list(items[start:end]), total


def page_envelope(
    items: Iterable[Any],
    *,
    page: int,
    page_size: int,
    total: int,
) -> dict[str, Any]:
    params = normalize_page_params(page, page_size)
    total = max(int(total), 0)
    total_pages = (total + params.page_size - 1) // params.page_size if params.page_size else 0
    materialized = list(items)
    return {
        "items": materialized,
        "page": params.page,
        "pageSize": params.page_size,
        "total": total,
        "totalPages": total_pages,
        "hasNext": params.page < total_pages,
        "hasPrev": params.page > 1,
    }


def batched(iterable: Iterable[Any], size: int) -> Iterable[list[Any]]:
    """Yield successive ``size`` chunks from ``iterable``."""
    if size <= 0:
        raise ValueError("size must be positive")
    bucket: list[Any] = []
    for item in iterable:
        bucket.append(item)
        if len(bucket) >= size:
            yield bucket
            bucket = []
    if bucket:
        yield bucket


__all__ = [
    "PageParams",
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "normalize_page_params",
    "paginate_sequence",
    "page_envelope",
    "batched",
]