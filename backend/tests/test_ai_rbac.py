"""RBAC tests for ai:use — verifies administrative roles are granted access
to AI endpoints while unauthorized roles receive 403.

Regression coverage for Milestone 10.1 authorization bug where org_admin
and campaign_manager could not call /api/v1/ai/* endpoints.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import ForbiddenError
from app.security.rbac import has_permission, require_permission


AI_PERMS = ("ai:use", "ai:generate", "ai:history_view")
AUTHORIZED_ROLES = ("super_admin", "org_admin", "campaign_manager", "content_creator")
UNAUTHORIZED_ROLES = ("viewer", "volunteer", "data_analyst", "reviewer", "translator")


@pytest.mark.parametrize("role", AUTHORIZED_ROLES)
@pytest.mark.parametrize("perm", AI_PERMS)
def test_admin_roles_have_ai_permissions(role: str, perm: str) -> None:
    assert has_permission([role], perm), f"{role} should have {perm}"


@pytest.mark.parametrize("role", UNAUTHORIZED_ROLES)
def test_unauthorized_roles_lack_ai_use(role: str) -> None:
    assert not has_permission([role], "ai:use"), f"{role} must not have ai:use"
    with pytest.raises(ForbiddenError):
        require_permission([role], "ai:use")


def _mini_app() -> FastAPI:
    """Minimal FastAPI app mirroring the ai:use dependency contract, so we
    can assert 200/403 responses without spinning up the full auth stack."""
    from fastapi import Depends, Header, HTTPException

    app = FastAPI()

    def require_perm(perm: str):
        def _dep(x_roles: str = Header(default="")) -> None:
            roles = [r.strip() for r in x_roles.split(",") if r.strip()]
            try:
                require_permission(roles, perm)
            except ForbiddenError as exc:
                raise HTTPException(status_code=403, detail=str(exc))

        return _dep

    @app.get("/ai/providers")
    def providers(_: None = Depends(require_perm("ai:use"))) -> dict:
        return {"ok": True}

    return app


@pytest.mark.parametrize("role", AUTHORIZED_ROLES)
def test_authorized_role_receives_200(role: str) -> None:
    client = TestClient(_mini_app())
    resp = client.get("/ai/providers", headers={"X-Roles": role})
    assert resp.status_code == 200


@pytest.mark.parametrize("role", UNAUTHORIZED_ROLES)
def test_unauthorized_role_receives_403(role: str) -> None:
    client = TestClient(_mini_app())
    resp = client.get("/ai/providers", headers={"X-Roles": role})
    assert resp.status_code == 403
    assert "ai:use" in resp.json()["detail"]