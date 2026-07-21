"""Production action handler base class (Phase 8.4).

Common scaffolding for real handler implementations:

* Structured logging with ``workflow_id`` / ``execution_id`` / ``handler`` /
  ``entity`` / ``duration`` / ``status``.
* Error taxonomy mapping — configuration / validation errors are
  non-retryable, transient / IO errors are retryable, business errors
  are non-retryable but distinct.
* Dry-run short-circuit — when the caller marks the execution as a
  dry run (via ``context.metadata['dry_run'] = True``) or no database
  session is attached, real service side-effects are skipped and a
  success ``ActionResult`` with ``skipped=True`` is returned.

Subclasses implement :meth:`run` — the actual work — and optionally
:meth:`validate`. :meth:`execute` wraps everything with timing and
error mapping.
"""
from __future__ import annotations

from typing import Any

from app.constants.workflow import (
    STEP_STATUS_COMPLETED,
    STEP_STATUS_FAILED,
)
from app.core.exceptions import (
    ConflictError,
    DomainError,
    NotFoundError,
    ValidationError,
)
from app.runtime.base import BaseActionHandler
from app.runtime.context import WorkflowExecutionContext
from app.runtime.exceptions import ActionExecutionError
from app.runtime.result import ActionResult, _now


class ConfigurationError(ValidationError):
    """Handler configuration is invalid (author error)."""


class TransientError(Exception):
    """A retryable failure — e.g. network timeout, 5xx, 429."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class BusinessError(Exception):
    """A non-retryable business-logic failure raised by a downstream service."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ProductionActionHandler(BaseActionHandler):
    """Base class for real action handlers.

    Subclasses implement :meth:`run` which either returns an ``output``
    dict (success) or raises. The base class handles logging, timing,
    validation, dry-run and error mapping.
    """

    #: Required top-level configuration keys.
    required_keys: tuple[str, ...] = ()

    #: What kind of entity this handler operates on (surfaced in logs).
    entity: str = ""

    #: Set to ``False`` to disable runtime retries for this handler
    #: even when the failure is transient.
    retry_supported: bool = True

    # ------------------------------------------------------------------ #
    # BaseActionHandler contract
    # ------------------------------------------------------------------ #

    def supports_retry(self) -> bool:  # pragma: no cover - trivial
        return self.retry_supported

    def validate(self, config: dict[str, Any]) -> None:
        if not isinstance(config, dict):
            raise ConfigurationError(
                f"{self.action_type}: configuration must be an object",
                details={"got": type(config).__name__},
            )
        missing = [k for k in self.required_keys if config.get(k) in (None, "")]
        if missing:
            raise ConfigurationError(
                f"{self.action_type}: missing required configuration",
                details={"missing": missing},
            )

    def execute(
        self,
        context: WorkflowExecutionContext,
        config: dict[str, Any],
    ) -> ActionResult:
        started = _now()
        log = context.bind_logger(
            workflow_id=context.workflow_id,
            execution_id=context.execution_id,
            action_type=self.action_type,
            handler=self.name,
            entity=self.entity or None,
        )
        # -- validation ------------------------------------------------ #
        try:
            self.validate(config)
        except ValidationError as exc:
            log.warning(
                "workflow.action.validation_error",
                error=str(exc),
            )
            raise ActionExecutionError(
                str(exc),
                action_type=self.action_type,
                retryable=False,
                details=getattr(exc, "details", {}) or {},
            ) from exc

        # -- dry-run short-circuit ------------------------------------- #
        if context.dry_run or context.db is None:
            completed = _now()
            log.info(
                "workflow.action.dry_run",
                duration=(completed - started).total_seconds(),
                status=STEP_STATUS_COMPLETED,
                success=True,
            )
            return ActionResult(
                action_type=self.action_type,
                success=True,
                status=STEP_STATUS_COMPLETED,
                started_at=started,
                completed_at=completed,
                output={
                    "skipped": True,
                    "reason": "dry_run" if context.dry_run else "no_db",
                    "handler": self.name,
                },
                handler=self.name,
            )

        # -- real work ------------------------------------------------- #
        log.info("workflow.action.start", config_keys=sorted(config.keys()))
        try:
            output = self.run(context, config)
        except ValidationError as exc:
            completed = _now()
            log.warning(
                "workflow.action.validation_error",
                error=str(exc),
                duration=(completed - started).total_seconds(),
            )
            raise ActionExecutionError(
                str(exc),
                action_type=self.action_type,
                retryable=False,
                details=getattr(exc, "details", {}) or {},
            ) from exc
        except (NotFoundError, ConflictError, BusinessError, DomainError) as exc:
            completed = _now()
            log.warning(
                "workflow.action.business_error",
                error=str(exc),
                duration=(completed - started).total_seconds(),
            )
            raise ActionExecutionError(
                str(exc),
                action_type=self.action_type,
                retryable=False,
                details=getattr(exc, "details", {}) or {},
            ) from exc
        except TransientError as exc:
            completed = _now()
            log.error(
                "workflow.action.transient_error",
                error=exc.message,
                duration=(completed - started).total_seconds(),
            )
            raise ActionExecutionError(
                exc.message,
                action_type=self.action_type,
                retryable=self.retry_supported,
                details=exc.details,
            ) from exc

        completed = _now()
        result_output: dict[str, Any] = {"handler": self.name}
        if isinstance(output, dict):
            result_output.update(output)
        log.info(
            "workflow.action.completed",
            duration=(completed - started).total_seconds(),
            status=STEP_STATUS_COMPLETED,
            success=True,
        )
        return ActionResult(
            action_type=self.action_type,
            success=True,
            status=STEP_STATUS_COMPLETED,
            started_at=started,
            completed_at=completed,
            output=result_output,
            handler=self.name,
        )

    # ------------------------------------------------------------------ #
    # Subclass hook
    # ------------------------------------------------------------------ #

    def run(
        self,
        context: WorkflowExecutionContext,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Perform the real work. Override in subclasses.

        Return a serialisable ``dict`` of output, or raise one of:

        * :class:`ValidationError` — bad config discovered late.
        * :class:`BusinessError` / :class:`NotFoundError` / :class:`ConflictError`
          — non-retryable business failure.
        * :class:`TransientError` — retryable failure (network, 5xx, timeout).
        """
        raise NotImplementedError


__all__ = [
    "BusinessError",
    "ConfigurationError",
    "ProductionActionHandler",
    "TransientError",
    "STEP_STATUS_FAILED",  # re-exported for handler modules
]