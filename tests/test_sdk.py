"""Tests for SDK generate and sync."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "v1"))

import sdk as sdk_script  # noqa: E402


def test_generate_writes_versions_and_app_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    platform = tmp_path / "platform"
    platform.mkdir()
    (platform / "VERSION").write_text("9.9.9\n", encoding="utf-8")
    (platform / "services.yaml").write_text(
        (ROOT / "services.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    pyproject = platform / "pyproject.toml"
    pyproject.parent.mkdir(parents=True, exist_ok=True)
    pyproject.write_text('version = "0.0.0"\n', encoding="utf-8")

    ts_pkg = platform / "sdk" / "typescript" / "package.json"
    ts_pkg.parent.mkdir(parents=True)
    ts_pkg.write_text('{"name":"@praam/platform","version":"0.0.0"}\n', encoding="utf-8")

    monkeypatch.setattr(sdk_script, "ROOT", platform)
    monkeypatch.setattr(sdk_script, "PYTHON_LIB", ROOT / "lib" / "praam_platform")
    monkeypatch.setattr(sdk_script, "TS_ROOT", platform / "sdk" / "typescript")
    monkeypatch.setattr(
        sdk_script,
        "TS_GENERATED",
        platform / "sdk" / "typescript" / "src" / "generated",
    )
    monkeypatch.setattr(sdk_script, "PY_GENERATED", ROOT / "lib" / "praam_platform" / "generated")
    monkeypatch.setattr(sdk_script, "VERSION_FILE", platform / "VERSION")
    monkeypatch.setattr(sdk_script, "PYPROJECT", pyproject)
    monkeypatch.setattr(sdk_script, "TS_PACKAGE", ts_pkg)
    monkeypatch.setattr(sdk_script, "build_typescript", lambda: False)

    version = sdk_script.generate(platform)
    assert version == "9.9.9"
    assert 'version = "9.9.9"' in pyproject.read_text(encoding="utf-8")
    assert json.loads(ts_pkg.read_text(encoding="utf-8"))["version"] == "9.9.9"
    app_keys = (ROOT / "lib" / "praam_platform" / "generated" / "app_keys.py").read_text(
        encoding="utf-8"
    )
    assert "findoc-ai" in app_keys


def test_push_copies_python_to_sibling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    platform = tmp_path / "platform"
    github = tmp_path / "github"
    platform.mkdir()
    github.mkdir()
    (platform / "services.yaml").write_text(
        (ROOT / "services.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (platform / "VERSION").write_text("1.1.0\n", encoding="utf-8")
    (github / "findoc-ai").mkdir()

    monkeypatch.setattr(sdk_script, "ROOT", platform)
    monkeypatch.setattr(sdk_script, "PYTHON_LIB", ROOT / "lib" / "praam_platform")
    monkeypatch.setattr(sdk_script, "TS_ROOT", platform / "sdk" / "typescript")
    monkeypatch.setenv("SDK_SKIP_TYPESCRIPT", "1")

    rc = sdk_script.push(platform, github, typescript=False)
    assert rc == 0
    dest = github / "findoc-ai" / "vendor" / "praam_platform" / "client.py"
    assert dest.is_file()
    manifest = json.loads((github / "findoc-ai" / ".praam-sdk-sync.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "1.1.0"
    assert manifest["app"] == "findoc-ai"
