# tests/test_microservice.py

from __future__ import annotations

from fastapi.testclient import TestClient

from sysmaint import __brand__, __version__
from sysmaint.service.server import create_app


def test_health_endpoint():
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == __version__
    assert data["brand"] == __brand__
    assert resp.headers.get("X-Powered-By") == __brand__


def test_repair_dry_run_endpoint():
    client = TestClient(create_app())
    resp = client.post("/v1/repair", json={"disk": True, "files": True, "network": True, "dry_run": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["dry_run"] is True
    assert "disk" in data
    assert "integrity" in data
    assert "network" in data


def test_ai_status_endpoint():
    client = TestClient(create_app())
    resp = client.get("/v1/ai/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "ready" in data
    assert "setup_guide" in data
