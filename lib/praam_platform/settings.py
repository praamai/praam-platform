"""Runtime settings shared by API, SDK, and scripts."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG_URL = "http://127.0.0.1:3180"
DEFAULT_SERVICE_TOKEN = "praam-platform-dev"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return int(raw)


@dataclass(frozen=True)
class PlatformSettings:
    platform_root: Path
    service_token: str = DEFAULT_SERVICE_TOKEN
    config_url: str = DEFAULT_CONFIG_URL
    log_json: bool = True
    log_level: str = "INFO"
    rate_limit_enabled: bool = True
    rate_limit_max: int = 120
    rate_limit_window_seconds: int = 60
    health_timeout_seconds: float = 2.0
    use_platform: bool = True

    @classmethod
    def from_env(cls, platform_root: Path) -> PlatformSettings:
        return cls(
            platform_root=platform_root.resolve(),
            service_token=os.environ.get("PRAAM_SERVICE_TOKEN", DEFAULT_SERVICE_TOKEN),
            config_url=os.environ.get("PRAAM_CONFIG_URL", DEFAULT_CONFIG_URL).rstrip("/"),
            log_json=_env_bool("LOG_JSON", True),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
            rate_limit_enabled=_env_bool("RATE_LIMIT_ENABLED", True),
            rate_limit_max=_env_int("RATE_LIMIT_MAX", 120),
            rate_limit_window_seconds=_env_int("RATE_LIMIT_WINDOW_SECONDS", 60),
            health_timeout_seconds=float(
                os.environ.get("PLATFORM_HEALTH_TIMEOUT_SECONDS", "2")
            ),
            use_platform=_env_bool("PRAAM_USE_PLATFORM", True),
        )
