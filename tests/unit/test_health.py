from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"status": "ok"}


def test_health_route_is_registered() -> None:
    assert "/health" in app.openapi()["paths"]
