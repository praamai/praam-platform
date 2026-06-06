"""Praam platform config API — runtime config and secrets (AWS Secrets Manager pattern)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from praam_platform.config import build_app_config
from praam_platform.enums import Runtime
from praam_platform.exceptions import (
    AppNotFoundError,
    SecretNotFoundError,
    SecretsBackendError,
)
from praam_platform.health import check_platform_health
from praam_platform.paths import resolve_platform_root
from praam_platform.registry import list_apps, load_services, resolve_app
from praam_platform.secrets import build_secrets_backend
from praam_platform.settings import PlatformSettings
from praam_platform.validate import validate_services

from app.middleware import AccessLogMiddleware, RateLimitMiddleware

PLATFORM_ROOT = resolve_platform_root(Path(__file__))
settings = PlatformSettings.from_env(PLATFORM_ROOT)
bearer = HTTPBearer(auto_error=False)


def get_services() -> dict:
    return load_services(settings.platform_root)


def require_token(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
) -> None:
    if not credentials or credentials.credentials != settings.service_token:
        raise HTTPException(status_code=401, detail="Invalid or missing service token")


class SecretValue(BaseModel):
    name: str
    value: str


@asynccontextmanager
async def lifespan(_: FastAPI):
    errors = validate_services(load_services(settings.platform_root))
    if errors:
        raise RuntimeError(f"Invalid services.yaml: {errors}")
    yield


app = FastAPI(
    title="praam-platform-config",
    version="1.1.0",
    lifespan=lifespan,
)
app.add_middleware(RateLimitMiddleware, settings=settings)
app.add_middleware(AccessLogMiddleware, settings=settings)


@app.get("/v1/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok", "service": "platform-config"}


@app.get("/v1/platform/health")
def health_platform(
    runtime: str = Query(default="docker", description="host|docker check targets"),
    services: dict = Depends(get_services),
) -> dict:
    try:
        rt = Runtime.parse(runtime)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return check_platform_health(
        services,
        runtime=rt,
        timeout=settings.health_timeout_seconds,
    ).to_dict()


@app.get("/v1/apps")
def apps_list(services: dict = Depends(get_services)) -> dict[str, list[str]]:
    return {"apps": list_apps(services)}


@app.get("/v1/apps/{selector}/config")
def app_config(
    selector: str,
    runtime: str | None = Query(default=None, description="Override host|docker"),
    services: dict = Depends(get_services),
) -> dict:
    try:
        app_key, app = resolve_app(services, selector)
    except AppNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    runtime_override = Runtime.parse(runtime) if runtime is not None else None
    cfg = build_app_config(app_key, app, services, runtime_override=runtime_override)
    return cfg.to_dict()


@app.get("/v1/secrets")
def secrets_list(
    _: None = Depends(require_token),
    services: dict = Depends(get_services),
) -> dict[str, list[str]]:
    try:
        backend = build_secrets_backend(services)
    except SecretsBackendError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"secrets": backend.list_names()}


@app.get("/v1/secrets/{name}")
def secret_get(
    name: str,
    _: None = Depends(require_token),
    services: dict = Depends(get_services),
) -> SecretValue:
    try:
        backend = build_secrets_backend(services)
        value = backend.get(name)
    except SecretNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SecretsBackendError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return SecretValue(name=name, value=value)
