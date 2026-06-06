"""Secrets backends — local file (dev) and AWS Secrets Manager (prod)."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path

from praam_platform.enums import ProviderSecret, SecretsBackendKind
from praam_platform.exceptions import SecretNotFoundError, SecretsBackendError

DEFAULT_PROVIDER_SECRETS = {secret.value: secret.env_key for secret in ProviderSecret}


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


class SecretsBackend(ABC):
    @abstractmethod
    def get(self, name: str) -> str: ...

    @abstractmethod
    def list_names(self) -> list[str]: ...


class LocalFileSecretsBackend(SecretsBackend):
    """Read secrets from ~/.praam/secrets.env (or PRAAM_SECRETS_FILE)."""

    def __init__(
        self,
        *,
        secrets_file: Path | None = None,
        mapping: dict[str, str] | None = None,
    ) -> None:
        self.secrets_file = secrets_file or Path(
            os.environ.get("PRAAM_SECRETS_FILE", Path.home() / ".praam" / "secrets.env")
        )
        self.mapping = mapping or dict(DEFAULT_PROVIDER_SECRETS)

    def _merged(self) -> dict[str, str]:
        return _parse_env_file(self.secrets_file)

    def list_names(self) -> list[str]:
        return sorted(self.mapping.keys())

    def get(self, name: str) -> str:
        env_key = self.mapping.get(name)
        if not env_key:
            raise SecretNotFoundError(f"Unknown secret name '{name}'")
        value = self._merged().get(env_key, "").strip()
        if not value:
            raise SecretNotFoundError(
                f"Secret '{name}' ({env_key}) not set in {self.secrets_file}"
            )
        return value


class AwsSecretsBackend(SecretsBackend):
    """Fetch secrets from AWS Secrets Manager by ARN map in services.yaml."""

    def __init__(self, arn_map: dict[str, str], region: str | None = None) -> None:
        self.arn_map = arn_map
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")

    def list_names(self) -> list[str]:
        return sorted(self.arn_map.keys())

    def get(self, name: str) -> str:
        arn = self.arn_map.get(name)
        if not arn:
            raise SecretNotFoundError(f"Unknown secret name '{name}'")
        try:
            import boto3  # type: ignore[import-untyped]
        except ImportError as exc:
            raise SecretsBackendError(
                "AWS secrets backend requires boto3: uv sync --extra aws"
            ) from exc
        client = boto3.client("secretsmanager", region_name=self.region)
        response = client.get_secret_value(SecretId=arn)
        value = (response.get("SecretString") or "").strip()
        if not value:
            raise SecretNotFoundError(f"Secret '{name}' is empty in AWS")
        return value


def build_secrets_backend(services: dict) -> SecretsBackend:
    secrets_cfg = services.get("secrets") or {}
    backend = SecretsBackendKind(secrets_cfg.get("backend", SecretsBackendKind.LOCAL.value))
    if backend is SecretsBackendKind.AWS:
        arn_map = secrets_cfg.get("aws_arns") or {}
        if not arn_map:
            raise SecretsBackendError("secrets.backend=aws but secrets.aws_arns is empty")
        return AwsSecretsBackend(arn_map)
    providers = secrets_cfg.get("providers") or {}
    mapping = {
        name: spec.get("local_key", name.upper().replace("-", "_"))
        for name, spec in providers.items()
    } or dict(DEFAULT_PROVIDER_SECRETS)
    return LocalFileSecretsBackend(
        secrets_file=Path(
            os.environ.get("PRAAM_SECRETS_FILE", Path.home() / ".praam" / "secrets.env")
        ),
        mapping=mapping,
    )
