"""Extended RBAC dependencies: permission-resolver cache, workspace and
organization access guards, ownership checks, and permission decorators.
"""
from __future__ import annotations

import time
from collections.abc import Iterable
from typing import Any, Callable

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ForbiddenError,
    OrganizationAccessError,
    UnauthorizedError,
    WorkspaceAccessError,
)
from app.dependencies.db import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.security.rbac import PERMISSIONS, has_permission, require_permission

# In-process permission resolver cache. Real deployments should back this
# with Redis; the interface stays the same.
_CACHE_TTL_SECONDS = 60
_permission_cache: dict[str, tuple[float, frozenset[str]]] = {}


def resolve_permissions(user: User) -> frozenset[str]:
    key = str(user.id)
    now = time.monotonic()
    cached = _permission_cache.get(key)
    if cached and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]
    grants: set[str] = set()
    for role in user.roles:
        for grant in PERMISSIONS.get(role.name, ()):
            grants.add(grant)
    frozen = frozenset(grants)
    _permission_cache[key] = (now, frozen)
    return frozen


def invalidate_permission_cache(user_id: str | None = None) -> None:
    if user_id is None:
        _permission_cache.clear()
    else:
        _permission_cache.pop(str(user_id), None)


def permission_required(*required: str) -> Callable[..., User]:
    from app.dependencies.auth import current_user  # avoid circular import

    def _dep(user: User = Depends(current_user)) -> User:
        roles = [r.name for r in user.roles]
        for perm in required:
            require_permission(roles, perm)
        return user

    return _dep


def role_required(*required_roles: str) -> Callable[..., User]:
    from app.dependencies.auth import current_user

    def _dep(user: User = Depends(current_user)) -> User:
        user_roles = {r.name for r in user.roles}
        if "super_admin" in user_roles:
            return user
        if not user_roles.intersection(required_roles):
            raise ForbiddenError(f"Requires one of roles: {', '.join(required_roles)}")
        return user

    return _dep


def workspace_context(
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    db: Session = Depends(get_db),
    user: "User | None" = None,
) -> Workspace | None:
    """Resolve the caller's active workspace from an X-Workspace-Id header.

    When absent, falls back to the user's default workspace. Membership is
    always verified.
    """
    from app.dependencies.auth import current_user

    if user is None:
        user = current_user(db=db)  # type: ignore[call-arg]
    workspace_id = x_workspace_id or (str(user.default_workspace_id) if user.default_workspace_id else None)
    if not workspace_id:
        return None
    ws = db.get(Workspace, workspace_id)
    if not ws:
        raise WorkspaceAccessError("Workspace not found")
    membership = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.workspace_id == ws.id, WorkspaceMember.user_id == user.id)
        .one_or_none()
    )
    roles = {r.name for r in user.roles}
    if not membership and not roles.intersection({"super_admin", "org_admin"}):
        raise WorkspaceAccessError("You are not a member of this workspace")
    return ws


def require_workspace() -> Callable[..., Workspace]:
    from app.dependencies.auth import current_user

    def _dep(
        x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
        db: Session = Depends(get_db),
        user: User = Depends(current_user),
    ) -> Workspace:
        ws = workspace_context(x_workspace_id=x_workspace_id, db=db, user=user)
        if not ws:
            raise WorkspaceAccessError("A workspace context is required for this request")
        return ws

    return _dep


def require_organization() -> Callable[..., str]:
    from app.dependencies.auth import current_user

    def _dep(
        x_organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
        user: User = Depends(current_user),
    ) -> str:
        if not x_organization_id:
            raise OrganizationAccessError("Organization context is required")
        return x_organization_id

    return _dep


def check_ownership(*, actor: User, resource_owner_id: Any) -> None:
    roles = {r.name for r in actor.roles}
    if "super_admin" in roles or "org_admin" in roles:
        return
    if str(actor.id) != str(resource_owner_id):
        raise ForbiddenError("You do not own this resource")


def any_permission(perms: Iterable[str]) -> Callable[..., User]:
    from app.dependencies.auth import current_user

    def _dep(user: User = Depends(current_user)) -> User:
        roles = [r.name for r in user.roles]
        if not any(has_permission(roles, p) for p in perms):
            raise ForbiddenError(f"Requires any of: {', '.join(perms)}")
        return user

    return _dep
