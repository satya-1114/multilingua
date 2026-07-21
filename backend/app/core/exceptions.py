from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.core.responses import error_envelope

log = get_logger(__name__)


class DomainError(Exception):
    status_code: int = 400
    code: str = "domain_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class UnauthorizedError(DomainError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(DomainError):
    status_code = 403
    code = "forbidden"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"


class ValidationError(DomainError):
    status_code = 422
    code = "validation_error"


class RateLimitError(DomainError):
    status_code = 429
    code = "rate_limited"


class SessionExpiredError(UnauthorizedError):
    code = "session_expired"


class TokenExpiredError(UnauthorizedError):
    code = "token_expired"


class TokenRevokedError(UnauthorizedError):
    code = "token_revoked"


class PasswordPolicyError(ValidationError):
    code = "password_policy"


class WorkspaceAccessError(ForbiddenError):
    code = "workspace_access_denied"


class OrganizationAccessError(ForbiddenError):
    code = "organization_access_denied"



def _sanitize_for_json(value: Any) -> Any:
    """Recursively convert values into JSON-serializable primitives.

    FastAPI/Pydantic validation errors can carry raw ``bytes`` in the ``input``
    or ``ctx`` fields (notably for OAuth2 password-flow form data), which
    ``orjson`` refuses to encode. Decode bytes to UTF-8 (fallback to hex) and
    stringify any other exotic objects while preserving dict/list structure so
    the existing error envelope schema is unchanged.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.hex()
    if isinstance(value, dict):
        return {str(_sanitize_for_json(k)): _sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_sanitize_for_json(v) for v in value]
    try:
        import orjson

        orjson.dumps(value)
        return value
    except Exception:
        return str(value)


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(_: Request, exc: DomainError):
        return ORJSONResponse(
            status_code=exc.status_code,
            content=error_envelope(exc.code, exc.message, exc.status_code, exc.details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        return ORJSONResponse(
            status_code=exc.status_code,
            content=error_envelope(f"http_{exc.status_code}", str(exc.detail), exc.status_code),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        return ORJSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_envelope(
                "validation_error",
                "Request validation failed",
                422,
                {"errors": _sanitize_for_json(exc.errors())},
            ),
        )

    @app.exception_handler(Exception)
    async def _fallback(_: Request, exc: Exception):
        log.exception("unhandled_error", error=str(exc))
        return ORJSONResponse(
            status_code=500,
            content=error_envelope("internal_error", "An unexpected error occurred", 500),
        )
