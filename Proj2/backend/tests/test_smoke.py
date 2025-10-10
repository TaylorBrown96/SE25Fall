from starlette.testclient import TestClient
from app.main import app

def test_root_status():
    c = TestClient(app)
    r = c.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["service"] == "proj2"

def test_ping_async():
    c = TestClient(app)
    r = c.get("/v1/ping?simulated_ms=10")
    assert r.status_code == 200
    assert r.json()["pong"] is True