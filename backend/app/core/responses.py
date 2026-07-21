"""Response envelopes that mirror the frontend `src/api/contracts` module."""
from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


def _meta() -> dict[str, Any]:
    return {
        "requestId": f"req_{uuid.uuid4().hex[:10]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0",
    }


class Pagination(BaseModel):
    page: int
    pageSize: int
    total: int
    totalPages: int
    hasMore: bool


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    meta: dict[str, Any]


class ApiListResponse(BaseModel, Generic[T]):
    success: bool = True
    data: list[T]
    pagination: Pagination
    meta: dict[str, Any]


def ok(data: Any) -> dict[str, Any]:
    return {"success": True, "data": data, "meta": _meta()}


def paginated(items: list[Any], page: int, page_size: int, total: int) -> dict[str, Any]:
    total_pages = max(1, math.ceil(total / max(1, page_size)))
    return {
        "success": True,
        "data": items,
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": total_pages,
            "hasMore": page < total_pages,
        },
        "meta": _meta(),
    }


def error_envelope(code: str, message: str, status: int, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "success": False,
        "error": {"code": code, "message": message, "status": status, "details": details or {}},
        "meta": _meta(),
    }
