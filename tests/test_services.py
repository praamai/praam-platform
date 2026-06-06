"""Unit tests for render-env / registry (lib/praam_platform)."""

from __future__ import annotations

from pathlib import Path

import pytest

from praam_platform.config import build_app_config, render_env_lines
from praam_platform.exceptions import AppNotFoundError
from praam_platform.registry import load_services, output_path, resolve_app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def services() -> dict:
    return load_services(ROOT)


def test_load_services_has_platform_and_apps(services: dict) -> None:
    assert services["version"] == 1
    assert "postgres" in services["platform"]
    assert "config_api" in services["platform"]
    assert "findoc-ai" in services["apps"]


def test_resolve_app_by_key_and_repo(services: dict) -> None:
    key, app = resolve_app(services, "findoc-ai")
    assert key == "findoc-ai"
    assert app["repo"] == "findoc-ai"

    key3, app3 = resolve_app(services, "askHR")
    assert key3 == "askhr"
    assert app3["repo"] == "askHR"


def test_resolve_app_unknown_raises(services: dict) -> None:
    with pytest.raises(AppNotFoundError):
        resolve_app(services, "not-a-real-app")


def test_build_app_config_findoc_host(services: dict) -> None:
    app_key, app = resolve_app(services, "findoc-ai")
    cfg = build_app_config(app_key, app, services)
    env = cfg.to_env()
    assert env["PRAAM_USE_PLATFORM"] == "1"
    assert "127.0.0.1:15430" in env["DATABASE_URL"]
    assert env["REDIS_URL"] == "redis://127.0.0.1:16380/2"
    assert env["LITELLM_BASE_URL"] == "http://127.0.0.1:3100/v1"
    assert env["PRAAM_CONFIG_URL"] == "http://127.0.0.1:3180"
    assert cfg.config_api is not None


def test_build_app_config_knowledge_studio_docker(services: dict) -> None:
    app_key, app = resolve_app(services, "knowledge-studio")
    cfg = build_app_config(app_key, app, services)
    env = cfg.to_env()
    assert "postgres:5432" in env["DATABASE_URL"]
    assert env["CELERY_BROKER_URL"] == "redis://redis:6379/0"
    assert env["PROPOSAL_CORE_PORT"] == "3011"


def test_render_env_lines_compat(services: dict) -> None:
    app_key, app = resolve_app(services, "findoc-ai")
    lines = render_env_lines(app_key, app, services)
    joined = "\n".join(lines)
    assert "DATABASE_URL=" in joined
    assert "PRAAM_CONFIG_URL=" in joined


def test_output_path(services: dict) -> None:
    github_root = Path("/tmp/github")
    app_key, app = resolve_app(services, "findoc-ai")
    path = output_path(ROOT, github_root, app_key, app)
    assert path == github_root / "findoc-ai" / "backend" / ".env.platform.generated"


def test_check_render_all_writes_without_sibling_repos(tmp_path: Path) -> None:
    import subprocess

    result = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts/v1/_services.py"),
            "check-render-all",
            str(ROOT),
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    for app_key, app in load_services(ROOT)["apps"].items():
        out = output_path(ROOT, tmp_path, app_key, app)
        assert out.is_file(), app_key
