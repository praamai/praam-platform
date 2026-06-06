"""Tests for platform-config FastAPI service."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = ROOT / "services" / "platform-config"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    secrets = tmp_path / "secrets.env"
    secrets.write_text("OPENAI_API_KEY=test-openai-key\n", encoding="utf-8")
    monkeypatch.setenv("PRAAM_PLATFORM_ROOT", str(ROOT))
    monkeypatch.setenv("PRAAM_SERVICE_TOKEN", "test-token")
    monkeypatch.setenv("PRAAM_SECRETS_FILE", str(secrets))

    import sys

    sys.path.insert(0, str(ROOT / "lib"))
    service_path = str(SERVICE_ROOT)
    if service_path not in sys.path:
        sys.path.insert(0, service_path)

    # Reload main so settings pick up env
    if "app.main" in sys.modules:
        del sys.modules["app.main"]
    from app.main import app  # noqa: WPS433

    return TestClient(app)


def test_health_live(client: TestClient) -> None:
    resp = client.get("/v1/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_app_config_findoc(client: TestClient) -> None:
    resp = client.get("/v1/apps/findoc-ai/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["app"] == "findoc-ai"
    assert "15430" in body["postgres"]["url"]
    assert body["config_api"]["base_url"] == "http://127.0.0.1:3180"


def test_secrets_require_auth(client: TestClient) -> None:
    resp = client.get("/v1/secrets/openai-api-key")
    assert resp.status_code == 401


def test_secrets_with_token(client: TestClient) -> None:
    resp = client.get(
        "/v1/secrets/openai-api-key",
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp.status_code == 200
    assert resp.json()["value"] == "test-openai-key"


def test_platform_health_shape(client: TestClient) -> None:
    resp = client.get("/v1/platform/health?runtime=host")
    assert resp.status_code == 200
    body = resp.json()
    assert "checks" in body
    assert "postgres" in body["checks"]
    assert body["runtime"] == "host"


def test_rate_limit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import sys

    secrets = tmp_path / "secrets.env"
    secrets.write_text("OPENAI_API_KEY=k\n", encoding="utf-8")
    monkeypatch.setenv("PRAAM_PLATFORM_ROOT", str(ROOT))
    monkeypatch.setenv("PRAAM_SERVICE_TOKEN", "test-token")
    monkeypatch.setenv("PRAAM_SECRETS_FILE", str(secrets))
    monkeypatch.setenv("RATE_LIMIT_MAX", "2")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")

    for mod in ("app.main", "app.middleware"):
        sys.modules.pop(mod, None)

    sys.path.insert(0, str(ROOT / "lib"))
    sys.path.insert(0, str(SERVICE_ROOT))
    from app.main import app as rate_app

    limited = TestClient(rate_app)
    assert limited.get("/v1/apps").status_code == 200
    assert limited.get("/v1/apps").status_code == 200
    assert limited.get("/v1/apps").status_code == 429

