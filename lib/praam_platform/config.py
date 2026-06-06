"""Build structured app config from services.yaml (API + SDK source of truth)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

from praam_platform.enums import ModelAlias, PlatformDependency, Runtime


def _runtime_value(runtime: Runtime | str) -> Runtime:
    return runtime if isinstance(runtime, Runtime) else Runtime.parse(runtime)


def host_for_runtime(runtime: Runtime | str, container_host: str) -> str:
    return "127.0.0.1" if _runtime_value(runtime) is Runtime.HOST else container_host


def port_for_runtime(runtime: Runtime | str, service: dict) -> int:
    if _runtime_value(runtime) is Runtime.HOST:
        return int(service["host_port"])
    return int(service.get("container_port", service["host_port"]))


def database_url(
    *,
    runtime: Runtime | str,
    platform: dict,
    schema: str,
    driver: str = "postgresql+psycopg",
) -> str:
    pg = platform["postgres"]
    host = host_for_runtime(runtime, pg["container_host"])
    port = port_for_runtime(runtime, pg)
    user = pg.get("user", "praam")
    password = pg.get("password", "praam_dev")
    database = pg["database"]
    options = quote(f"-csearch_path={schema},public", safe="")
    return f"{driver}://{user}:{password}@{host}:{port}/{database}?options={options}"


def redis_url(*, runtime: Runtime | str, platform: dict, db_index: int) -> str:
    redis = platform["redis"]
    host = host_for_runtime(runtime, redis["container_host"])
    port = port_for_runtime(runtime, redis)
    return f"redis://{host}:{port}/{db_index}"


def litellm_base_url(*, runtime: Runtime | str, platform: dict) -> str:
    llm = platform["litellm"]
    host = host_for_runtime(runtime, llm["container_host"])
    port = port_for_runtime(runtime, llm)
    path = llm.get("path", "/v1").rstrip("/")
    return f"http://{host}:{port}{path}"


def config_api_base_url(*, runtime: Runtime | str, platform: dict) -> str:
    api = platform.get("config_api") or {}
    if not api:
        return ""
    host = host_for_runtime(runtime, api["container_host"])
    port = port_for_runtime(runtime, api)
    return f"http://{host}:{port}"


@dataclass
class AppConfig:
    """Runtime config for one suite app."""

    version: int
    app: str
    schema: str
    runtime: str
    platform_wired: bool
    ports: dict[str, int] = field(default_factory=dict)
    port_env: dict[str, int] = field(default_factory=dict)
    postgres: dict[str, Any] | None = None
    redis: dict[str, Any] | None = None
    litellm: dict[str, Any] | None = None
    config_api: dict[str, Any] | None = None
    embed_urls: dict[str, str] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> AppConfig:
        return cls(
            version=int(payload["version"]),
            app=str(payload["app"]),
            schema=str(payload.get("schema", "")),
            runtime=str(payload["runtime"]),
            platform_wired=bool(payload.get("platform_wired")),
            ports=dict(payload.get("ports") or {}),
            port_env=dict(payload.get("port_env") or {}),
            postgres=payload.get("postgres"),
            redis=payload.get("redis"),
            litellm=payload.get("litellm"),
            config_api=payload.get("config_api"),
            embed_urls=dict(payload.get("embed_urls") or {}),
            dependencies=list(payload.get("dependencies") or []),
        )

    def to_env(self) -> dict[str, str]:
        env: dict[str, str] = {
            "PRAAM_USE_PLATFORM": "1",
            "PRAAM_PLATFORM_VERSION": str(self.version),
            "PRAAM_SCHEMA": self.schema,
            "PRAAM_APP": self.app,
        }
        for key, value in self.ports.items():
            env[f"{key.upper()}_PORT"] = str(value)
        for name, value in self.port_env.items():
            env[name] = str(value)
        if self.postgres:
            env["DATABASE_URL"] = self.postgres["url"]
            env["POSTGRES_HOST"] = self.postgres["host"]
            env["POSTGRES_HOST_PORT"] = str(self.postgres["host_port"])
            env["POSTGRES_DB"] = self.postgres["database"]
        if self.redis:
            env["REDIS_HOST_PORT"] = str(self.redis["host_port"])
            if self.redis.get("url"):
                env["REDIS_URL"] = self.redis["url"]
            for role, spec in (self.redis.get("roles") or {}).items():
                env[f"REDIS_{role.upper()}_URL"] = spec["url"]
                env[f"REDIS_{role.upper()}_DB"] = str(spec["db"])
            if self.redis.get("celery_broker_url"):
                env["CELERY_BROKER_URL"] = self.redis["celery_broker_url"]
            if self.redis.get("celery_result_backend"):
                env["CELERY_RESULT_BACKEND"] = self.redis["celery_result_backend"]
        if self.litellm:
            env["LITELLM_BASE_URL"] = self.litellm["base_url"]
            env["OPENAI_API_BASE"] = self.litellm["base_url"]
            env["LITELLM_MASTER_KEY"] = self.litellm["master_key"]
            for alias, model in (self.litellm.get("models") or {}).items():
                env[f"PRAAM_LLM_MODEL_{alias.upper()}"] = model
        if self.config_api and self.config_api.get("base_url"):
            env["PRAAM_CONFIG_URL"] = self.config_api["base_url"]
        for name, url in self.embed_urls.items():
            env[name] = url
        return env

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "app": self.app,
            "schema": self.schema,
            "runtime": self.runtime,
            "platform_wired": self.platform_wired,
            "dependencies": self.dependencies,
            "ports": self.ports,
            "port_env": self.port_env,
            "postgres": self.postgres,
            "redis": self.redis,
            "litellm": self.litellm,
            "config_api": self.config_api,
            "embed_urls": self.embed_urls,
            "env": self.to_env(),
        }


def build_app_config(
    app_key: str,
    app: dict,
    services: dict,
    *,
    runtime_override: Runtime | str | None = None,
) -> AppConfig:
    platform = services["platform"]
    runtime = _runtime_value(runtime_override or app.get("runtime", Runtime.DOCKER.value))
    schema = app.get("schema", "")
    deps = [str(dep) for dep in (app.get("dependencies") or [])]

    ports: dict[str, int] = {}
    if app.get("api") is not None:
        ports["api"] = int(app["api"])
    if app.get("ui") is not None:
        ports["ui"] = int(app["ui"])
    if app.get("realtime") is not None:
        ports["realtime"] = int(app["realtime"])

    port_env: dict[str, int] = {}
    for env_name, port_key in (app.get("port_env") or {}).items():
        if app.get(port_key) is not None:
            port_env[env_name] = int(app[port_key])

    postgres: dict[str, Any] | None = None
    if PlatformDependency.POSTGRES.value in deps and schema:
        driver = app.get("database_driver", "postgresql+psycopg")
        pg = platform["postgres"]
        postgres = {
            "host": host_for_runtime(runtime, pg["container_host"]),
            "host_port": int(pg["host_port"]),
            "database": pg["database"],
            "schema": schema,
            "user": pg.get("user", "praam"),
            "url": database_url(
                runtime=runtime,
                platform=platform,
                schema=schema,
                driver=driver,
            ),
        }

    redis_block: dict[str, Any] | None = None
    redis_roles = app.get("redis") or {}
    if PlatformDependency.REDIS.value in deps and redis_roles:
        roles: dict[str, dict[str, Any]] = {}
        cache_url = ""
        for role, db_index in sorted(redis_roles.items()):
            url = redis_url(runtime=runtime, platform=platform, db_index=int(db_index))
            roles[role] = {"db": int(db_index), "url": url}
            if role == "cache":
                cache_url = url
        redis_block = {
            "host_port": int(platform["redis"]["host_port"]),
            "url": cache_url,
            "roles": roles,
        }
        cache_idx = redis_roles.get("cache")
        celery_idx = redis_roles.get("celery")
        if cache_idx is not None:
            redis_block["celery_broker_url"] = redis_url(
                runtime=runtime,
                platform=platform,
                db_index=int(cache_idx),
            )
        if celery_idx is not None:
            redis_block["celery_result_backend"] = redis_url(
                runtime=runtime,
                platform=platform,
                db_index=int(celery_idx),
            )

    litellm_block: dict[str, Any] | None = None
    if PlatformDependency.LITELLM.value in deps:
        models_cfg = platform["litellm"].get("models") or {}
        litellm_block = {
            "base_url": litellm_base_url(runtime=runtime, platform=platform),
            "master_key": platform["litellm"].get("master_key", "praam-litellm-dev"),
            "models": {
                alias.value: alias.value for alias in ModelAlias if alias.value in models_cfg
            },
        }

    config_api_block: dict[str, Any] | None = None
    if platform.get("config_api"):
        api = platform["config_api"]
        config_api_block = {
            "host_port": int(api["host_port"]),
            "base_url": config_api_base_url(runtime=runtime, platform=platform),
        }

    embed_urls: dict[str, str] = {}
    if app_key == "demo-hub":
        embed_host = app.get("embed_host", "127.0.0.1")
        for other_key, other in sorted((services.get("apps") or {}).items()):
            if other_key == "demo-hub":
                continue
            ui_port = other.get("ui")
            if ui_port is None:
                continue
            env_name = f"APP_URL_{other_key.replace('-', '_').upper()}"
            embed_urls[env_name] = f"http://{embed_host}:{ui_port}"

    return AppConfig(
        version=int(services.get("version", 1)),
        app=app_key,
        schema=schema,
        runtime=runtime.value,
        platform_wired=bool(app.get("platform_wired")),
        ports=ports,
        port_env=port_env,
        postgres=postgres,
        redis=redis_block,
        litellm=litellm_block,
        config_api=config_api_block,
        embed_urls=embed_urls,
        dependencies=deps,
    )


def render_env_lines(app_key: str, app: dict, services: dict) -> list[str]:
    cfg = build_app_config(app_key, app, services)
    lines = [
        "# Generated by praam-platform — do not edit",
        f"# App: {app_key}  schema: {cfg.schema}  runtime: {cfg.runtime}",
        "# Prefer: PlatformClient(app=...).load() — see sdk/python/",
    ]
    lines.extend(f"{key}={value}" for key, value in cfg.to_env().items())
    return lines
