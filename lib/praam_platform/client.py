"""Runtime client — fetch config and secrets from platform-config API."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from praam_platform.config import AppConfig, build_app_config
from praam_platform.enums import Runtime
from praam_platform.exceptions import PlatformError
from praam_platform.registry import load_services, resolve_app
from praam_platform.secrets import build_secrets_backend
from praam_platform.settings import (
    DEFAULT_CONFIG_URL,
    DEFAULT_SERVICE_TOKEN,
    PlatformSettings,
)


@dataclass
class LoadedPlatform:
    config: AppConfig
    secrets: dict[str, str]

    @property
    def database_url(self) -> str:
        if not self.config.postgres:
            raise PlatformError("App config has no postgres block")
        return self.config.postgres["url"]

    @property
    def litellm_base_url(self) -> str | None:
        if not self.config.litellm:
            return None
        return self.config.litellm["base_url"]

    def apply_env(self, *, override: bool = False) -> None:
        for key, value in self.config.to_env().items():
            if override or key not in os.environ:
                os.environ[key] = value
        for name, value in self.secrets.items():
            env_key = name.upper().replace("-", "_")
            if override or env_key not in os.environ:
                os.environ[env_key] = value


class PlatformClient:
    """Fetch suite config at runtime (no .env.platform.generated required)."""

    def __init__(
        self,
        app: str,
        *,
        base_url: str | None = None,
        token: str | None = None,
        platform_root: Path | None = None,
        timeout_seconds: float = 10.0,
        settings: PlatformSettings | None = None,
    ) -> None:
        self.app = app
        root = platform_root
        if settings is None and root is not None:
            settings = PlatformSettings.from_env(root)
        self.settings = settings
        self.base_url = (
            base_url
            or (settings.config_url if settings else os.environ.get("PRAAM_CONFIG_URL", DEFAULT_CONFIG_URL))
        ).rstrip("/")
        self.token = token or (
            settings.service_token
            if settings
            else os.environ.get("PRAAM_SERVICE_TOKEN", DEFAULT_SERVICE_TOKEN)
        )
        if root:
            self.platform_root = root.resolve()
        elif settings:
            self.platform_root = settings.platform_root
        else:
            env_root = os.environ.get("PRAAM_PLATFORM_ROOT")
            self.platform_root = Path(env_root).resolve() if env_root else None
        self.timeout_seconds = timeout_seconds

    def _fetch_json(self, path: str, *, auth: bool = False) -> dict[str, Any]:
        req = urllib.request.Request(f"{self.base_url}{path}")
        req.add_header("Accept", "application/json")
        if auth:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise PlatformError(f"Platform API {path} failed ({exc.code}): {body}") from exc
        except urllib.error.URLError as exc:
            raise PlatformError(f"Platform API unreachable at {self.base_url}: {exc}") from exc

    def _load_local(self, runtime: Runtime | str | None = None) -> AppConfig:
        root = self.platform_root
        if not root or not (root / "services.yaml").is_file():
            raise PlatformError(
                "Local fallback requires PRAAM_PLATFORM_ROOT pointing at praam-platform"
            )
        services = load_services(root)
        app_key, app = resolve_app(services, self.app)
        return build_app_config(app_key, app, services, runtime_override=runtime)

    def get_config(self, *, runtime: Runtime | str | None = None) -> AppConfig:
        use_platform = self.settings.use_platform if self.settings else os.environ.get("PRAAM_USE_PLATFORM", "1") != "0"
        if not use_platform:
            return self._load_local(runtime=runtime)
        try:
            query = ""
            if runtime is not None:
                rt = runtime if isinstance(runtime, Runtime) else Runtime.parse(str(runtime))
                query = f"?runtime={rt.value}"
            payload = self._fetch_json(f"/v1/apps/{self.app}/config{query}")
        except PlatformError:
            if self.platform_root:
                return self._load_local(runtime=runtime)
            raise
        return AppConfig.from_api(payload)

    def get_secret(self, name: str) -> str:
        payload = self._fetch_json(f"/v1/secrets/{name}", auth=True)
        return str(payload["value"])

    def load(
        self,
        *,
        apply_env: bool = True,
        fetch_secrets: list[str] | None = None,
        runtime: Runtime | str | None = None,
        override_env: bool = False,
    ) -> LoadedPlatform:
        config = self.get_config(runtime=runtime)
        secrets: dict[str, str] = {}
        use_platform = self.settings.use_platform if self.settings else os.environ.get("PRAAM_USE_PLATFORM", "1") != "0"
        if fetch_secrets:
            if use_platform:
                try:
                    for name in fetch_secrets:
                        secrets[name] = self.get_secret(name)
                except PlatformError:
                    if self.platform_root:
                        backend = build_secrets_backend(load_services(self.platform_root))
                        for name in fetch_secrets:
                            secrets[name] = backend.get(name)
                    else:
                        raise
            elif self.platform_root:
                backend = build_secrets_backend(load_services(self.platform_root))
                for name in fetch_secrets:
                    secrets[name] = backend.get(name)

        loaded = LoadedPlatform(config=config, secrets=secrets)
        if apply_env:
            loaded.apply_env(override=override_env)
        return loaded


def get_database_url(app: str, **kwargs: Any) -> str:
    return PlatformClient(app, **kwargs).load(apply_env=False).database_url


def get_litellm_url(app: str, **kwargs: Any) -> str | None:
    return PlatformClient(app, **kwargs).load(apply_env=False).litellm_base_url
