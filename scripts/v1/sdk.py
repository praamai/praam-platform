#!/usr/bin/env python3
"""Generate SDK artifacts and sync them to sibling product repos."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lib"))

from praam_platform.registry import list_apps, load_services  # noqa: E402

PYTHON_LIB = ROOT / "lib" / "praam_platform"
TS_ROOT = ROOT / "sdk" / "typescript"
TS_GENERATED = TS_ROOT / "src" / "generated"
PY_GENERATED = PYTHON_LIB / "generated"
VERSION_FILE = ROOT / "VERSION"
PYPROJECT = ROOT / "pyproject.toml"
TS_PACKAGE = TS_ROOT / "package.json"
MANIFEST_NAME = ".praam-sdk-sync.json"


def read_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def sync_package_versions(version: str) -> None:
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    if not re.search(r'(?m)^version = "', pyproject):
        raise RuntimeError(f"Could not find version field in {PYPROJECT}")
    updated = re.sub(
        r'(?m)^version = "[^"]+"',
        f'version = "{version}"',
        pyproject,
        count=1,
    )
    PYPROJECT.write_text(updated, encoding="utf-8")

    package = json.loads(TS_PACKAGE.read_text(encoding="utf-8"))
    package["version"] = version
    TS_PACKAGE.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")


def write_generated_sources(version: str, app_keys: list[str]) -> None:
    PY_GENERATED.mkdir(parents=True, exist_ok=True)
    (PY_GENERATED / "__init__.py").write_text(
        '"""Generated SDK metadata — do not edit."""\n\n'
        f'from praam_platform.generated.app_keys import APP_KEYS\n'
        f'from praam_platform.generated.version import __version__\n\n'
        f"__all__ = ['APP_KEYS', '__version__']\n",
        encoding="utf-8",
    )
    keys_literal = ", ".join(repr(key) for key in app_keys)
    (PY_GENERATED / "app_keys.py").write_text(
        '"""Generated from services.yaml — do not edit."""\n\n'
        f"APP_KEYS: tuple[str, ...] = ({keys_literal},)\n",
        encoding="utf-8",
    )
    (PY_GENERATED / "version.py").write_text(
        f'__version__ = "{version}"\n',
        encoding="utf-8",
    )

    TS_GENERATED.mkdir(parents=True, exist_ok=True)
    keys_ts = ", ".join(json.dumps(key) for key in app_keys)
    (TS_GENERATED / "app-keys.ts").write_text(
        "/** Generated from services.yaml — do not edit. */\n\n"
        f"export const APP_KEYS = [{keys_ts}] as const;\n"
        f"export type AppKey = (typeof APP_KEYS)[number];\n",
        encoding="utf-8",
    )
    (TS_GENERATED / "version.ts").write_text(
        f'export const SDK_VERSION = "{version}";\n',
        encoding="utf-8",
    )


def build_typescript() -> bool:
    if shutil.which("npm") is None:
        print("  WARN — npm not found; skipping TypeScript build")
        return False
    try:
        subprocess.run(["npm", "install"], cwd=TS_ROOT, check=True)
        subprocess.run(["npm", "run", "build"], cwd=TS_ROOT, check=True)
    except subprocess.CalledProcessError:
        print("  WARN — TypeScript build failed; Python SDK still generated")
        return False
    return True


def generate(platform_root: Path) -> str:
    version = read_version()
    services = load_services(platform_root)
    app_keys = list_apps(services)
    sync_package_versions(version)
    write_generated_sources(version, app_keys)
    ts_built = build_typescript()
    print(f"  generated SDK v{version} ({len(app_keys)} apps)")
    if not ts_built:
        print("  TypeScript dist not rebuilt — install Node.js for full SDK output")
    return version


def _python_dest(app: dict, sdk_cfg: dict) -> str:
    app_sdk = app.get("sdk") or {}
    return str(app_sdk.get("python") or sdk_cfg.get("python_relpath", "vendor/praam_platform"))


def _typescript_dest(app: dict, sdk_cfg: dict) -> str:
    app_sdk = app.get("sdk") or {}
    return str(
        app_sdk.get("typescript")
        or sdk_cfg.get("typescript_relpath", "vendor/@praam/platform")
    )


def _apps_to_sync(services: dict) -> list[tuple[str, dict]]:
    sdk_cfg = services.get("sdk") or {}
    mode = sdk_cfg.get("sync_apps", "wired")
    apps = services.get("apps") or {}
    selected: list[tuple[str, dict]] = []
    for key, app in sorted(apps.items()):
        app_sdk = app.get("sdk") or {}
        if app_sdk is False:
            continue
        if mode == "all":
            if app.get("type") == "shell":
                continue
            selected.append((key, app))
        elif app.get("platform_wired") or app_sdk.get("sync"):
            selected.append((key, app))
    return selected


def _copy_python_lib(dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(
        PYTHON_LIB,
        dest,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )


def _copy_typescript_pkg(dest: Path) -> None:
    dist = TS_ROOT / "dist"
    if not dist.is_dir():
        raise RuntimeError("TypeScript dist/ missing — run make sdk-generate with Node.js")
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    shutil.copytree(dist, dest / "dist")
    shutil.copy2(TS_PACKAGE, dest / "package.json")
    readme = TS_ROOT / "README.md"
    if readme.is_file():
        shutil.copy2(readme, dest / "README.md")


def _write_manifest(dest_root: Path, *, version: str, app_key: str, languages: list[str]) -> None:
    payload = {
        "version": version,
        "app": app_key,
        "synced_at": datetime.now(UTC).isoformat(),
        "source": str(ROOT),
        "languages": languages,
    }
    (dest_root / MANIFEST_NAME).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def push(platform_root: Path, github_root: Path, *, typescript: bool = True) -> int:
    version = read_version()
    services = load_services(platform_root)
    sdk_cfg = services.get("sdk") or {}
    targets = _apps_to_sync(services)
    if not targets:
        print("  no apps selected for SDK sync")
        return 0

    errors = 0
    for app_key, app in targets:
        repo = app.get("repo") or app_key.replace("_", "-")
        repo_path = github_root / repo
        if not repo_path.is_dir():
            print(f"  SKIP {app_key} — {repo_path} not found")
            continue

        app_sdk = app.get("sdk") or {}
        languages: list[str] = []
        py_rel = _python_dest(app, sdk_cfg)
        py_dest = repo_path / py_rel
        _copy_python_lib(py_dest)
        languages.append("python")
        print(f"  OK {app_key} → {py_dest}")

        sync_ts = typescript and app_sdk.get("typescript") is not False
        if sync_ts:
            ts_rel = _typescript_dest(app, sdk_cfg)
            ts_dest = repo_path / ts_rel
            try:
                _copy_typescript_pkg(ts_dest)
                languages.append("typescript")
                print(f"  OK {app_key} → {ts_dest}")
            except RuntimeError as exc:
                print(f"  WARN {app_key} — {exc}")
                errors += 1

        _write_manifest(repo_path, version=version, app_key=app_key, languages=languages)

    if errors:
        return 1
    print(f"  synced SDK v{version} to {len(targets)} app(s)")
    return 0


def check(platform_root: Path, github_root: Path) -> int:
    version = read_version()
    services = load_services(platform_root)
    failures = 0
    for app_key, app in _apps_to_sync(services):
        repo = app.get("repo") or app_key.replace("_", "-")
        repo_path = github_root / repo
        manifest_path = repo_path / MANIFEST_NAME
        if not manifest_path.is_file():
            print(f"  MISSING {app_key} — {manifest_path}")
            failures += 1
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("version") != version:
            print(f"  STALE {app_key} — manifest {manifest.get('version')} != {version}")
            failures += 1
            continue
        print(f"  OK {app_key}")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "Usage: sdk.py generate|push|check <platform_root> [github_root]",
            file=sys.stderr,
        )
        return 2

    cmd = argv[1]
    platform_root = Path(argv[2]).resolve()
    github_root = Path(argv[3]).resolve() if len(argv) > 3 else platform_root.parent

    if cmd == "generate":
        generate(platform_root)
        return 0
    if cmd == "push":
        ts = os.environ.get("SDK_SKIP_TYPESCRIPT", "0") != "1"
        return push(platform_root, github_root, typescript=ts)
    if cmd == "check":
        return check(platform_root, github_root)
    if cmd == "all":
        generate(platform_root)
        return push(platform_root, github_root)

    print(f"Unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
