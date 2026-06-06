"""Shared praam-platform registry, config, secrets, and runtime client."""

from praam_platform.client import LoadedPlatform, PlatformClient, get_database_url, get_litellm_url
from praam_platform.config import AppConfig, build_app_config
from praam_platform.enums import (
    HealthStatus,
    LogEvent,
    LogLevel,
    ModelAlias,
    PlatformDependency,
    PlatformService,
    ProviderSecret,
    Runtime,
    SecretsBackendKind,
)
from praam_platform.health import PlatformHealthReport, ServiceCheck, check_platform_health
from praam_platform.logging import LogRecord, StructuredLogger
from praam_platform.ratelimit import RateLimiter
from praam_platform.registry import AppNotFoundError, load_services, resolve_app
from praam_platform.settings import PlatformSettings

__all__ = [
    "AppConfig",
    "AppNotFoundError",
    "HealthStatus",
    "LoadedPlatform",
    "LogEvent",
    "LogLevel",
    "LogRecord",
    "ModelAlias",
    "PlatformClient",
    "PlatformDependency",
    "PlatformHealthReport",
    "PlatformService",
    "PlatformSettings",
    "ProviderSecret",
    "RateLimiter",
    "Runtime",
    "SecretsBackendKind",
    "ServiceCheck",
    "StructuredLogger",
    "build_app_config",
    "check_platform_health",
    "get_database_url",
    "get_litellm_url",
    "load_services",
    "resolve_app",
]
