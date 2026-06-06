"""Validate services.yaml structure."""

from __future__ import annotations

from typing import Any

from praam_platform.enums import Runtime


def validate_services(services: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if services.get("version") != 1:
        errors.append("version must be 1")

    platform = services.get("platform")
    if not isinstance(platform, dict):
        errors.append("platform section is required")
        return errors

    for key in ("postgres", "redis", "litellm", "config_api"):
        if key not in platform:
            errors.append(f"platform.{key} is required")

    pg = platform.get("postgres") or {}
    for field in ("host_port", "container_host", "database"):
        if field not in pg:
            errors.append(f"platform.postgres.{field} is required")

    apps = services.get("apps")
    if not isinstance(apps, dict) or not apps:
        errors.append("apps must be a non-empty mapping")
        return errors

    for app_key, app in apps.items():
        if not isinstance(app, dict):
            errors.append(f"apps.{app_key} must be a mapping")
            continue
        if "runtime" not in app:
            errors.append(f"apps.{app_key}.runtime is required")
        runtime = app.get("runtime")
        if runtime not in (None, *[member.value for member in Runtime]):
            errors.append(f"apps.{app_key}.runtime must be host or docker")
        deps = app.get("dependencies") or []
        if "postgres" in deps and not app.get("schema"):
            errors.append(f"apps.{app_key}.schema required when postgres is a dependency")

    return errors
