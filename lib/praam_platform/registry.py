"""Load services.yaml and resolve app entries."""

from __future__ import annotations

from pathlib import Path

import yaml

from praam_platform.exceptions import AppNotFoundError


def load_services(platform_root: Path) -> dict:
    path = platform_root / "services.yaml"
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid services.yaml at {path}")
    return data


def slug_to_app_key(slug: str) -> str:
    return slug.replace("-", "_")


def resolve_app(services: dict, selector: str) -> tuple[str, dict]:
    apps = services.get("apps") or {}
    if selector in apps:
        return selector, apps[selector]
    normalized = slug_to_app_key(selector)
    if normalized in apps:
        return normalized, apps[normalized]
    for key, app in apps.items():
        if app.get("repo") == selector:
            return key, app
    raise AppNotFoundError(f"Unknown app '{selector}' — check services.yaml apps section")


def list_apps(services: dict) -> list[str]:
    return sorted((services.get("apps") or {}).keys())


def list_wired_apps(services: dict) -> list[str]:
    return sorted(
        key
        for key, app in (services.get("apps") or {}).items()
        if app.get("platform_wired")
    )


def expected_schemas(services: dict) -> list[str]:
    return sorted(
        {
            app["schema"]
            for app in (services.get("apps") or {}).values()
            if app.get("schema")
        }
    )


def output_path(platform_root: Path, github_root: Path, app_key: str, app: dict) -> Path:
    repo = app.get("repo") or app_key.replace("_", "-")
    env_dir = app.get("env_dir") or "."
    return github_root / repo / env_dir / ".env.platform.generated"
