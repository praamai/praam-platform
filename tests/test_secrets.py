"""Tests for secrets backends."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from praam_platform.exceptions import SecretNotFoundError, SecretsBackendError
from praam_platform.secrets import AwsSecretsBackend, LocalFileSecretsBackend, build_secrets_backend


def test_local_secrets_backend(tmp_path: Path) -> None:
    secrets = tmp_path / "secrets.env"
    secrets.write_text("OPENAI_API_KEY=sk-test\n", encoding="utf-8")
    backend = LocalFileSecretsBackend(
        secrets_file=secrets,
        mapping={"openai-api-key": "OPENAI_API_KEY"},
    )
    assert backend.get("openai-api-key") == "sk-test"
    assert "openai-api-key" in backend.list_names()


def test_local_secrets_missing_raises(tmp_path: Path) -> None:
    secrets = tmp_path / "secrets.env"
    secrets.write_text("OTHER=1\n", encoding="utf-8")
    backend = LocalFileSecretsBackend(
        secrets_file=secrets,
        mapping={"openai-api-key": "OPENAI_API_KEY"},
    )
    with pytest.raises(SecretNotFoundError):
        backend.get("openai-api-key")


def test_aws_secrets_backend() -> None:
    import sys

    backend = AwsSecretsBackend({"openai-api-key": "arn:aws:secretsmanager:us-east-1:1:secret:x"})
    fake_client = MagicMock()
    fake_client.get_secret_value.return_value = {"SecretString": "aws-secret-value"}
    fake_boto3 = MagicMock()
    fake_boto3.client.return_value = fake_client
    with patch.dict(sys.modules, {"boto3": fake_boto3}):
        assert backend.get("openai-api-key") == "aws-secret-value"


def test_build_secrets_backend_aws_requires_arns() -> None:
    with pytest.raises(SecretsBackendError):
        build_secrets_backend({"secrets": {"backend": "aws", "aws_arns": {}}})
