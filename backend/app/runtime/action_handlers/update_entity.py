"""Production EntityUpdateHandler (Phase 8.4).

Bridges workflow actions to the existing entity services. Supported
entities: ``volunteer``, ``disaster``, ``public_resource`` (aliases:
``public_information``, ``public``).

Operations:

* ``create`` — create a new entity from ``payload``
* ``update`` — merge ``payload`` into an existing entity
* ``status`` — transition status via the dedicated service call
* ``attribute`` — alias for ``update``, expects a scoped ``payload``

Permissions default to ``["super_admin"]`` so workflow-owned mutations
bypass RBAC. Override by supplying ``roles`` in the action config.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable

from app.constants.workflow import ACTION_TYPE_UPDATE_ENTITY
from app.core.exceptions import (
    ConflictError,
    DomainError,
    NotFoundError,
    ValidationError,
)
from app.runtime.action_handlers._base import (
    BusinessError,
    ConfigurationError,
    ProductionActionHandler,
)
from app.runtime.context import WorkflowExecutionContext

SUPPORTED_ENTITIES: tuple[str, ...] = (
    "volunteer",
    "disaster",
    "public_resource",
    "public_information",
    "public",
)
SUPPORTED_OPERATIONS: tuple[str, ...] = ("create", "update", "status", "attribute")

DEFAULT_ROLES: tuple[str, ...] = ("super_admin",)

# Map of aliased entity → canonical.
_ENTITY_ALIASES: dict[str, str] = {
    "public": "public_resource",
    "public_information": "public_resource",
    "public_resource": "public_resource",
    "volunteer": "volunteer",
    "disaster": "disaster",
}


class EntityUpdateHandler(ProductionActionHandler):
    action_type = ACTION_TYPE_UPDATE_ENTITY
    entity = "entity"
    required_keys = ("entity_type", "operation")

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def validate(self, config: dict[str, Any]) -> None:
        super().validate(config)
        entity_type = str(config.get("entity_type") or "").strip().lower()
        if entity_type not in SUPPORTED_ENTITIES:
            raise ConfigurationError(
                "update_entity: unsupported entity_type",
                details={
                    "entity_type": entity_type,
                    "allowed": list(SUPPORTED_ENTITIES),
                },
            )
        operation = str(config.get("operation") or "").strip().lower()
        if operation not in SUPPORTED_OPERATIONS:
            raise ConfigurationError(
                "update_entity: unsupported operation",
                details={
                    "operation": operation,
                    "allowed": list(SUPPORTED_OPERATIONS),
                },
            )
        if operation == "create":
            if not isinstance(config.get("payload"), dict):
                raise ConfigurationError(
                    "update_entity: create requires payload object",
                )
        elif operation == "status":
            if not config.get("entity_id"):
                raise ConfigurationError(
                    "update_entity: status requires entity_id",
                )
            if not config.get("status"):
                raise ConfigurationError(
                    "update_entity: status requires target status",
                )
        else:  # update / attribute
            if not config.get("entity_id"):
                raise ConfigurationError(
                    "update_entity: update requires entity_id",
                )
            if not isinstance(config.get("payload"), dict):
                raise ConfigurationError(
                    "update_entity: update requires payload object",
                )
        roles = config.get("roles")
        if roles is not None and (
            not isinstance(roles, (list, tuple))
            or not all(isinstance(r, str) for r in roles)
        ):
            raise ConfigurationError("update_entity: roles must be list of strings")

    # ------------------------------------------------------------------ #
    # Execution
    # ------------------------------------------------------------------ #

    def run(
        self,
        context: WorkflowExecutionContext,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        entity_type = _ENTITY_ALIASES[
            str(config["entity_type"]).strip().lower()
        ]
        operation = str(config["operation"]).strip().lower()
        roles: Iterable[str] = config.get("roles") or DEFAULT_ROLES

        dispatcher = self._resolve_dispatcher(entity_type, operation)
        try:
            entity = dispatcher(context, config, roles=roles)
        except (ValidationError, NotFoundError, ConflictError):
            raise
        except DomainError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise BusinessError(
                f"update_entity: {entity_type}.{operation} failed: {exc}",
                details={"entity_type": entity_type, "operation": operation},
            ) from exc

        return {
            "entityType": entity_type,
            "operation": operation,
            "entityId": str(getattr(entity, "id", "")) or None,
            "status": getattr(entity, "status", None),
        }

    # ------------------------------------------------------------------ #
    # Dispatch table
    # ------------------------------------------------------------------ #

    def _resolve_dispatcher(
        self, entity_type: str, operation: str
    ) -> Callable[..., Any]:
        table: dict[tuple[str, str], Callable[..., Any]] = {
            ("volunteer", "create"): _volunteer_create,
            ("volunteer", "update"): _volunteer_update,
            ("volunteer", "attribute"): _volunteer_update,
            ("volunteer", "status"): _volunteer_status,
            ("disaster", "create"): _disaster_create,
            ("disaster", "update"): _disaster_update,
            ("disaster", "attribute"): _disaster_update,
            ("disaster", "status"): _disaster_status,
            ("public_resource", "create"): _public_create,
            ("public_resource", "update"): _public_update,
            ("public_resource", "attribute"): _public_update,
            ("public_resource", "status"): _public_status,
        }
        try:
            return table[(entity_type, operation)]
        except KeyError as exc:
            raise ConfigurationError(
                "update_entity: unsupported (entity, operation) combo",
                details={"entity_type": entity_type, "operation": operation},
            ) from exc


# --------------------------------------------------------------------------- #
# Volunteer dispatchers
# --------------------------------------------------------------------------- #


def _volunteer_create(
    context: WorkflowExecutionContext,
    config: dict[str, Any],
    *,
    roles: Iterable[str],
) -> Any:
    from app.services import volunteer as svc

    return svc.create_volunteer(
        context.db, roles=list(roles), payload=config["payload"]
    )


def _volunteer_update(
    context: WorkflowExecutionContext,
    config: dict[str, Any],
    *,
    roles: Iterable[str],
) -> Any:
    from app.services import volunteer as svc

    return svc.update_volunteer(
        context.db,
        roles=list(roles),
        volunteer_id=config["entity_id"],
        payload=config["payload"],
    )


def _volunteer_status(
    context: WorkflowExecutionContext,
    config: dict[str, Any],
    *,
    roles: Iterable[str],
) -> Any:
    from app.services import volunteer as svc

    return svc.set_status(
        context.db,
        roles=list(roles),
        volunteer_id=config["entity_id"],
        status=str(config["status"]),
    )


# --------------------------------------------------------------------------- #
# Disaster dispatchers
# --------------------------------------------------------------------------- #


_DISASTER_STATUS_ACTIONS: dict[str, str] = {
    "verified": "verify_disaster",
    "active": "activate_disaster",
    "contained": "contain_disaster",
    "resolved": "resolve_disaster",
    "closed": "close_disaster",
    "reopened": "reopen_disaster",
}


def _disaster_create(
    context: WorkflowExecutionContext,
    config: dict[str, Any],
    *,
    roles: Iterable[str],
) -> Any:
    from app.services import disaster as svc

    return svc.create_disaster(
        context.db,
        roles=list(roles),
        created_by=_coerce_uuid(context.actor_id),
        payload=config["payload"],
    )


def _disaster_update(
    context: WorkflowExecutionContext,
    config: dict[str, Any],
    *,
    roles: Iterable[str],
) -> Any:
    from app.services import disaster as svc

    return svc.update_disaster(
        context.db,
        roles=list(roles),
        disaster_id=config["entity_id"],
        payload=config["payload"],
    )


def _disaster_status(
    context: WorkflowExecutionContext,
    config: dict[str, Any],
    *,
    roles: Iterable[str],
) -> Any:
    from app.services import disaster as svc

    status = str(config["status"]).lower()
    fn_name = _DISASTER_STATUS_ACTIONS.get(status)
    if not fn_name:
        raise ConfigurationError(
            "update_entity: unsupported disaster status transition",
            details={"status": status, "allowed": list(_DISASTER_STATUS_ACTIONS)},
        )
    fn = getattr(svc, fn_name)
    return fn(context.db, roles=list(roles), disaster_id=config["entity_id"])


# --------------------------------------------------------------------------- #
# Public resource dispatchers
# --------------------------------------------------------------------------- #


_PUBLIC_STATUS_ACTIONS: dict[str, str] = {
    "publish": "publish_public_resource",
    "published": "publish_public_resource",
    "unpublish": "unpublish_public_resource",
    "unpublished": "unpublish_public_resource",
    "expire": "expire_public_resource",
    "expired": "expire_public_resource",
}


def _public_create(
    context: WorkflowExecutionContext,
    config: dict[str, Any],
    *,
    roles: Iterable[str],
) -> Any:
    from app.services import public_access as svc

    return svc.create_public_resource(
        context.db,
        roles=list(roles),
        created_by=_coerce_uuid(context.actor_id),
        payload=config["payload"],
    )


def _public_update(
    context: WorkflowExecutionContext,
    config: dict[str, Any],
    *,
    roles: Iterable[str],
) -> Any:
    from app.services import public_access as svc

    return svc.update_public_resource(
        context.db,
        roles=list(roles),
        resource_id=config["entity_id"],
        payload=config["payload"],
    )


def _public_status(
    context: WorkflowExecutionContext,
    config: dict[str, Any],
    *,
    roles: Iterable[str],
) -> Any:
    from app.services import public_access as svc

    status = str(config["status"]).lower()
    fn_name = _PUBLIC_STATUS_ACTIONS.get(status)
    if not fn_name:
        raise ConfigurationError(
            "update_entity: unsupported public_resource status transition",
            details={"status": status, "allowed": list(_PUBLIC_STATUS_ACTIONS)},
        )
    fn = getattr(svc, fn_name)
    return fn(context.db, roles=list(roles), resource_id=config["entity_id"])


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _coerce_uuid(value: Any) -> Any:
    import uuid

    if value is None or isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


__all__ = ["EntityUpdateHandler"]