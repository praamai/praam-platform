"""Contract tests — every app in services.yaml."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from praam_platform.registry import list_apps, load_services

ROOT = None  # set by fixture in conftest if needed


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    secrets = tmp_path / "secrets.env"
    secrets.write_text("OPENAI_API_KEY=test-key\n", encoding="utf-8")
    monkeypatch.setenv("PRAAM_PLATFORM_ROOT", str(root))
    monkeypatch.setenv("PRAAM_SERVICE_TOKEN", "test-token")
    monkeypatch.setenv("PRAAM_SECRETS_FILE", str(secrets))

    sys.path.insert(0, str(root / "services" / "platform-config"))
    if "app.main" in sys.modules:
        del sys.modules["app.main"]
    from app.main import app

    return TestClient(app)


@pytest.fixture
def services():
    from pathlib import Path

    return load_services(Path(__file__).resolve().parents[1])


def test_all_apps_config_dynamic(client: TestClient, services: dict) -> None:
    for app_key in list_apps(services):
        resp = client.get(f"/v1/apps/{app_key}/config")
        assert resp.status_code == 200, app_key
        body = resp.json()
        assert body["app"] == app_key
        assert isinstance(body["env"], dict)


def test_apps_list(client: TestClient, services: dict) -> None:
    resp = client.get("/v1/apps")
    assert resp.status_code == 200
    assert resp.json()["apps"] == list_apps(services)


def test_secrets_list(client: TestClient) -> None:
    resp = client.get("/v1/secrets", headers={"Authorization": "Bearer test-token"})
    assert resp.status_code == 200
    names = resp.json()["secrets"]
    assert "openai-api-key" in names
