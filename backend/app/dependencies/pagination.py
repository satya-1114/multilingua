from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query


@dataclass(slots=True)
class PageParams:
    page: int
    page_size: int
    search: str | None
    sort_by: str | None
    sort_dir: str


def page_params(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    search: str | None = Query(None, max_length=200),
    sort_by: str | None = Query(None, max_length=64),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
) -> PageParams:
    return PageParams(page=page, page_size=page_size, search=search, sort_by=sort_by, sort_dir=sort_dir)
