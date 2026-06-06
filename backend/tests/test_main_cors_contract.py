from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app


def _assert_dev_origin_allowed(origin: str) -> None:
    client = TestClient(app)

    response = client.options(
        "/chats/stream",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_cors_allows_workbench_dev_port_3021_for_browser_e2e() -> None:
    _assert_dev_origin_allowed("http://127.0.0.1:3021")
    _assert_dev_origin_allowed("http://localhost:3021")
