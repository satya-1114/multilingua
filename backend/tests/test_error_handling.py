from __future__ import annotations

from fastapi import APIRouter
from starlette.testclient import TestClient

from main import app


_router = APIRouter()


@_router.get("/boom")
def _boom():
    raise RuntimeError("secret internal detail")


app.include_router(_router, prefix="/__test__")


def test_generic_500_no_stack_leak():
    c = TestClient(app, raise_server_exceptions=False)
    r = c.get("/__test__/boom")
    assert r.status_code == 500
    body = r.json()
    assert body["error"]["code"] == "internal_error"
    assert "secret internal detail" not in r.text
    assert "Traceback" not in r.text


def test_error_envelope_shape():
    c = TestClient(app, raise_server_exceptions=False)
    r = c.get("/__test__/boom")
    err = r.json()["error"]
    assert set(err.keys()) >= {"code", "message"}


def test_404_uses_envelope():
    r = TestClient(app).get("/api/v1/does-not-exist")
    assert r.status_code == 404
    assert r.json()["error"]["code"].startswith("http_")


def test_validation_errors_wrapped():
    r = TestClient(app).post("/api/v1/auth/login", data="not json")
    assert r.status_code in (400, 422)
    assert r.json()["error"]["code"] in {"validation_error", "http_400", "http_422"}
