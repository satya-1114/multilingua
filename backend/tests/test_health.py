def test_health(client):
    r = client.get("/api/v1/system/health")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["data"]["status"] == "ok"


def test_version(client):
    r = client.get("/api/v1/system/version")
    assert r.json()["data"]["version"] == "1.0.0"
