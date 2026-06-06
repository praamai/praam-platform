"""Tests for PlatformClient (local fallback)."""

from __future__ import annotations

from pathlib import Path

from praam_platform.client import PlatformClient

ROOT = Path(__file__).resolve().parents[1]


def test_client_local_fallback(monkeypatch) -> None:
    monkeypatch.setenv("PRAAM_USE_PLATFORM", "0")
    monkeypatch.delenv("PRAAM_CONFIG_URL", raising=False)
    loaded = PlatformClient(
        "findoc-ai",
        platform_root=ROOT,
    ).load(apply_env=False)
    assert "findoc" in loaded.config.schema
    assert "15430" in loaded.database_url
