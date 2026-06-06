"""services.yaml validation tests."""

from __future__ import annotations

from pathlib import Path

from praam_platform.registry import load_services
from praam_platform.validate import validate_services

ROOT = Path(__file__).resolve().parents[1]


def test_services_yaml_valid() -> None:
    services = load_services(ROOT)
    errors = validate_services(services)
    assert errors == [], errors


def test_validate_catches_missing_schema() -> None:
    services = {
        "version": 1,
        "platform": {
            "postgres": {"host_port": 1, "container_host": "postgres", "database": "d"},
            "redis": {"host_port": 1, "container_host": "redis"},
            "litellm": {"host_port": 1, "container_host": "litellm"},
            "config_api": {"host_port": 1, "container_host": "cfg"},
        },
        "apps": {
            "bad": {"runtime": "docker", "dependencies": ["postgres"]},
        },
    }
    errors = validate_services(services)
    assert any("schema" in err for err in errors)
