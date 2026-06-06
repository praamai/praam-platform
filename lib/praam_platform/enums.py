"""Shared enumerations for praam-platform."""

from __future__ import annotations

from enum import StrEnum


class Runtime(StrEnum):
    HOST = "host"
    DOCKER = "docker"

    @classmethod
    def parse(cls, value: str | None, default: Runtime | None = None) -> Runtime:
        if value is None:
            return default or cls.DOCKER
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"runtime must be one of {[m.value for m in cls]}") from exc


class PlatformDependency(StrEnum):
    POSTGRES = "postgres"
    REDIS = "redis"
    LITELLM = "litellm"


class PlatformService(StrEnum):
    POSTGRES = "postgres"
    REDIS = "redis"
    LITELLM = "litellm"
    PLATFORM_CONFIG = "platform_config"


class SecretsBackendKind(StrEnum):
    LOCAL = "local"
    AWS = "aws"


class HealthStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class LogEvent(StrEnum):
    HTTP_ACCESS = "http.access"
    STARTUP = "startup"
    HEALTH = "health"


class ModelAlias(StrEnum):
    FAST = "fast"
    REASONING = "reasoning"
    EMBEDDING = "embedding"


class ProviderSecret(StrEnum):
    OPENAI = "openai-api-key"
    ANTHROPIC = "anthropic-api-key"
    GEMINI = "gemini-api-key"

    @property
    def env_key(self) -> str:
        mapping = {
            ProviderSecret.OPENAI: "OPENAI_API_KEY",
            ProviderSecret.ANTHROPIC: "ANTHROPIC_API_KEY",
            ProviderSecret.GEMINI: "GEMINI_API_KEY",
        }
        return mapping[self]
