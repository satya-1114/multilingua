"""End-to-end tests for the auth, session, and RBAC flows."""
from __future__ import annotations


REG = {"email": "user@example.com", "password": "SuperSecret1!", "fullName": "Test User"}


def _register(client, **overrides):
    payload = {**REG, **overrides}
    return client.post("/api/v1/auth/register", json=payload)


def test_register_and_login(client):
    r = _register(client)
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    assert data["user"]["email"] == "user@example.com"
    assert data["token"]["accessToken"]

    r = client.post("/api/v1/auth/login", json={"email": REG["email"], "password": REG["password"]})
    assert r.status_code == 200
    assert r.json()["data"]["token"]["accessToken"]


def test_login_invalid(client):
    r = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "WrongPass99!"})
    assert r.status_code == 401


def test_password_policy_rejects_weak(client):
    r = _register(client, email="weak@example.com", password="password")
    assert r.status_code == 422


def test_refresh_rotation_and_reuse_detection(client):
    _register(client, email="rot@example.com")
    r = client.post("/api/v1/auth/login", json={"email": "rot@example.com", "password": REG["password"]})
    original_refresh = r.json()["data"]["token"]["refreshToken"]

    r = client.post("/api/v1/auth/refresh", json={"refreshToken": original_refresh})
    assert r.status_code == 200
    new_refresh = r.json()["data"]["refreshToken"]
    assert new_refresh != original_refresh

    # Reusing the rotated (revoked) refresh must be rejected.
    r = client.post("/api/v1/auth/refresh", json={"refreshToken": original_refresh})
    assert r.status_code == 401


def test_logout_revokes_session(client):
    _register(client, email="lo@example.com")
    r = client.post("/api/v1/auth/login", json={"email": "lo@example.com", "password": REG["password"]})
    tokens = r.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {tokens['accessToken']}"}
    r = client.post("/api/v1/auth/logout", json={"refreshToken": tokens["refreshToken"]}, headers=headers)
    assert r.status_code == 200
    r = client.post("/api/v1/auth/refresh", json={"refreshToken": tokens["refreshToken"]})
    assert r.status_code == 401


def test_account_lockout_after_failures(client):
    _register(client, email="lock@example.com")
    for _ in range(5):
        client.post("/api/v1/auth/login", json={"email": "lock@example.com", "password": "WrongPass99!"})
    r = client.post("/api/v1/auth/login", json={"email": "lock@example.com", "password": REG["password"]})
    assert r.status_code == 403


def test_me_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    _register(client, email="me@example.com")
    r = client.post("/api/v1/auth/login", json={"email": "me@example.com", "password": REG["password"]})
    token = r.json()["data"]["token"]["accessToken"]
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["data"]["email"] == "me@example.com"


def test_password_reset_flow(client):
    _register(client, email="reset@example.com")
    r = client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})
    token = r.json()["data"]["token"]
    assert token
    r = client.post("/api/v1/auth/reset-password", json={"token": token, "password": "AnotherStrong9!"})
    assert r.status_code == 200
    # Old password no longer works.
    r = client.post("/api/v1/auth/login", json={"email": "reset@example.com", "password": REG["password"]})
    assert r.status_code == 401
    r = client.post("/api/v1/auth/login", json={"email": "reset@example.com", "password": "AnotherStrong9!"})
    assert r.status_code == 200


def test_password_reuse_prevention(client):
    _register(client, email="reuse@example.com")
    r = client.post("/api/v1/auth/login", json={"email": "reuse@example.com", "password": REG["password"]})
    token = r.json()["data"]["token"]["accessToken"]
    r = client.post(
        "/api/v1/auth/change-password",
        json={"currentPassword": REG["password"], "newPassword": REG["password"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


def test_security_overview_requires_auth(client):
    assert client.get("/api/v1/security/overview").status_code == 401
    _register(client, email="sec@example.com")
    r = client.post("/api/v1/auth/login", json={"email": "sec@example.com", "password": REG["password"]})
    token = r.json()["data"]["token"]["accessToken"]
    r = client.get("/api/v1/security/overview", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert "score" in data and "sessions" in data and "recentLogins" in data


def test_rbac_enforced_on_admin_endpoints(client):
    _register(client, email="viewer@example.com")
    r = client.post("/api/v1/auth/login", json={"email": "viewer@example.com", "password": REG["password"]})
    token = r.json()["data"]["token"]["accessToken"]
    r = client.get("/api/v1/security/events", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
