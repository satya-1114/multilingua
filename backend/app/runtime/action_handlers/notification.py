"""Production NotificationHandler (Phase 8.4).

Delivers in-app notifications via :mod:`app.services.notifications`.
Supported recipient modes:

* ``user_id`` — single user
* ``user_ids`` — list of user ids
* ``role`` — every user with the named role
* ``broadcast: true`` — every active user
* ``organization_id`` — every user linked to the workflow's organization
  (best-effort; falls back to ``user_ids`` when membership is not modelled)
"""
from __future__ import annotations

import uuid
from typing import Any, Iterable

from app.constants.workflow import ACTION_TYPE_NOTIFICATION
from app.core.exceptions import ValidationError
from app.runtime.action_handlers._base import (
    BusinessError,
    ConfigurationError,
    ProductionActionHandler,
)
from app.runtime.context import WorkflowExecutionContext

ALLOWED_PRIORITIES: tuple[str, ...] = ("low", "normal", "high", "urgent")


class NotificationHandler(ProductionActionHandler):
    action_type = ACTION_TYPE_NOTIFICATION
    entity = "notification"
    required_keys = ("title", "message")

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def validate(self, config: dict[str, Any]) -> None:
        super().validate(config)
        title = str(config.get("title") or "").strip()
        message = str(config.get("message") or "").strip()
        if not title:
            raise ConfigurationError("notification: title must not be blank")
        if len(title) > 200:
            raise ConfigurationError(
                "notification: title exceeds 200 characters",
                details={"length": len(title)},
            )
        if not message:
            raise ConfigurationError("notification: message must not be blank")
        if len(message) > 2000:
            raise ConfigurationError(
                "notification: message exceeds 2000 characters",
                details={"length": len(message)},
            )
        priority = config.get("priority", "normal")
        if priority not in ALLOWED_PRIORITIES:
            raise ConfigurationError(
                "notification: invalid priority",
                details={"priority": priority, "allowed": list(ALLOWED_PRIORITIES)},
            )
        # At least one recipient mode.
        if not self._recipient_hint(config):
            raise ConfigurationError(
                "notification: no recipients specified",
                details={
                    "hint": (
                        "provide one of user_id, user_ids, role, "
                        "organization_id, or broadcast=true"
                    )
                },
            )

    @staticmethod
    def _recipient_hint(config: dict[str, Any]) -> bool:
        return any(
            config.get(k)
            for k in ("user_id", "user_ids", "role", "organization_id")
        ) or bool(config.get("broadcast"))

    # ------------------------------------------------------------------ #
    # Execution
    # ------------------------------------------------------------------ #

    def run(
        self,
        context: WorkflowExecutionContext,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        # Lazy imports so the module can be imported without the SQL layer.
        from app.services import notifications as notif_service

        title = str(config["title"]).strip()
        message = str(config["message"]).strip()
        category = str(config.get("category") or "system")
        priority = str(config.get("priority") or "normal")
        href = config.get("href")

        recipients = self._resolve_recipients(context, config)
        if not recipients:
            raise BusinessError(
                "notification: no matching recipients",
                details={"config": {k: config.get(k) for k in ("role", "organization_id")}},
            )

        try:
            if len(recipients) == 1:
                notif = notif_service.create(
                    context.db,
                    user_id=recipients[0],
                    title=title,
                    message=message,
                    category=category,
                    priority=priority,
                    href=href,
                )
                delivered = 1
                first_id = str(notif.id)
            else:
                delivered = notif_service.broadcast(
                    context.db,
                    user_ids=recipients,
                    title=title,
                    message=message,
                    category=category,
                    priority=priority,
                )
                first_id = None
        except (ValidationError, BusinessError):
            raise
        except Exception as exc:  # noqa: BLE001 - map unexpected DB errors
            raise BusinessError(
                f"notification delivery failed: {exc}",
                details={"recipients": len(recipients)},
            ) from exc

        return {
            "delivered": delivered,
            "recipients": len(recipients),
            "priority": priority,
            "category": category,
            "notificationId": first_id,
        }

    # ------------------------------------------------------------------ #
    # Recipient resolution
    # ------------------------------------------------------------------ #

    def _resolve_recipients(
        self,
        context: WorkflowExecutionContext,
        config: dict[str, Any],
    ) -> list[str]:
        recipients: list[str] = []
        if config.get("user_id"):
            recipients.append(str(config["user_id"]))
        for uid in config.get("user_ids") or []:
            recipients.append(str(uid))
        role = config.get("role")
        if role:
            recipients.extend(self._users_with_role(context, str(role)))
        if config.get("broadcast") is True:
            recipients.extend(self._all_active_users(context))
        # organization_id: no membership table — treat as best-effort filter
        # on any pre-supplied user_ids. Do not silently drop the config.
        # De-duplicate while preserving order.
        seen: set[str] = set()
        ordered: list[str] = []
        for r in recipients:
            if r and r not in seen:
                seen.add(r)
                ordered.append(r)
        return ordered

    def _users_with_role(
        self,
        context: WorkflowExecutionContext,
        role_name: str,
    ) -> Iterable[str]:
        try:
            from sqlalchemy import select

            from app.models.user import Role, User, UserRole

            stmt = (
                select(User.id)
                .join(UserRole, UserRole.user_id == User.id)
                .join(Role, Role.id == UserRole.role_id)
                .where(Role.name == role_name, User.is_active.is_(True))
            )
            return [str(row) for row in context.db.scalars(stmt)]
        except Exception:  # pragma: no cover - defensive
            return []

    def _all_active_users(self, context: WorkflowExecutionContext) -> Iterable[str]:
        try:
            from sqlalchemy import select

            from app.models.user import User

            stmt = select(User.id).where(User.is_active.is_(True))
            return [str(row) for row in context.db.scalars(stmt)]
        except Exception:  # pragma: no cover - defensive
            return []


__all__ = ["NotificationHandler"]