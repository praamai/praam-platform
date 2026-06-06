#!/usr/bin/env python3
"""Smoke-test platform-config API for every app in services.yaml."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "services" / "platform-config"))

from praam_platform.registry import list_apps, load_services  # noqa: E402


def smoke_offline() -> int:
    os.environ.setdefault("PRAAM_PLATFORM_ROOT", str(ROOT))
    os.environ.setdefault("PRAAM_SERVICE_TOKEN", "praam-platform-dev")
    secrets = ROOT / ".env.example"
    os.environ.setdefault("PRAAM_SECRETS_FILE", str(secrets))

    from app.main import app  # noqa: WPS433
    from fastapi.testclient import TestClient

    client = TestClient(app)
    services = load_services(ROOT)
    failed = 0
    for app_key in list_apps(services):
        resp = client.get(f"/v1/apps/{app_key}/config")
        if resp.status_code != 200:
            print(f"  FAIL — {app_key} ({resp.status_code})")
            failed += 1
            continue
        body = resp.json()
        if body.get("app") != app_key:
            print(f"  FAIL — {app_key} wrong app id")
            failed += 1
            continue
        print(f"  OK — {app_key}")
    if failed:
        return 1
    print("config-smoke-offline OK")
    return 0


def smoke_live(base_url: str, *, strict: bool = False) -> int:
    failed = 0
    unavailable = False
    services = load_services(ROOT)
    for app_key in list_apps(services):
        url = f"{base_url.rstrip('/')}/v1/apps/{app_key}/config"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            if strict:
                print(f"  FAIL — config API unavailable: {exc}")
                return 1
            print(f"  SKIP — live config API unavailable ({exc})")
            unavailable = True
            break
        if body.get("app") != app_key:
            print(f"  FAIL — {app_key}")
            failed += 1
        else:
            print(f"  OK — {app_key} (live)")
    if unavailable:
        return 0
    if failed:
        return 1
    print("config-smoke OK")
    return 0


def main() -> int:
    if os.environ.get("PRAAM_OFFLINE") == "1":
        return smoke_offline()
    base = os.environ.get("PRAAM_CONFIG_URL", "http://127.0.0.1:3180")
    strict = os.environ.get("PRAAM_CONFIG_STRICT") == "1"
    print("== Config API smoke ==")
    return smoke_live(base, strict=strict)


if __name__ == "__main__":
    raise SystemExit(main())
