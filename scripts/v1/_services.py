#!/usr/bin/env python3
"""CLI for praam-platform registry (render-env, schema list)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lib"))

from praam_platform.config import render_env_lines  # noqa: E402
from praam_platform.exceptions import AppNotFoundError  # noqa: E402
from praam_platform.registry import (  # noqa: E402
    expected_schemas,
    list_apps,
    list_wired_apps,
    load_services,
    output_path,
    resolve_app,
)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: _services.py render <platform_root> <github_root> <app>", file=sys.stderr)
        return 2

    cmd = argv[1]
    platform_root = Path(argv[2]).resolve()
    github_root = Path(argv[3]).resolve()

    try:
        if cmd == "list-apps":
            services = load_services(platform_root)
            for key in list_apps(services):
                print(key)
            return 0

        if cmd == "list-wired-apps":
            services = load_services(platform_root)
            for key in list_wired_apps(services):
                print(key)
            return 0

        if cmd == "render":
            app_selector = argv[4]
            services = load_services(platform_root)
            app_key, app = resolve_app(services, app_selector)
            lines = render_env_lines(app_key, app, services)
            out = output_path(platform_root, github_root, app_key, app)
            out.parent.mkdir(parents=True, exist_ok=True)
            content = "\n".join(lines) + "\n"
            out.write_text(content, encoding="utf-8")
            print(f"Wrote {out}")
            return 0

        if cmd == "expected-schemas":
            for schema in expected_schemas(load_services(platform_root)):
                print(schema)
            return 0

        if cmd == "check-render":
            app_selector = argv[4]
            services = load_services(platform_root)
            app_key, app = resolve_app(services, app_selector)
            path = output_path(platform_root, github_root, app_key, app)
            expected = "\n".join(render_env_lines(app_key, app, services)) + "\n"
            if not path.is_file():
                print(f"MISSING\t{path}")
                return 1
            actual = path.read_text(encoding="utf-8")
            if actual != expected:
                print(f"STALE\t{path}")
                return 1
            print(f"OK\t{path}")
            return 0

        if cmd == "render-json":
            app_selector = argv[4]
            services = load_services(platform_root)
            app_key, app = resolve_app(services, app_selector)
            lines = render_env_lines(app_key, app, services)
            print(
                json.dumps(
                    {
                        "lines": lines,
                        "path": str(output_path(platform_root, github_root, app_key, app)),
                    }
                )
            )
            return 0

        if cmd == "check-render-all":
            services = load_services(platform_root)
            apps = services.get("apps") or {}
            for app_key, app in apps.items():
                out = output_path(platform_root, github_root, app_key, app)
                out.parent.mkdir(parents=True, exist_ok=True)
                content = "\n".join(render_env_lines(app_key, app, services)) + "\n"
                out.write_text(content, encoding="utf-8")
            print(f"check-render-all OK ({len(apps)} apps → {github_root})")
            return 0

        if cmd == "clean-render-all":
            services = load_services(platform_root)
            apps = services.get("apps") or {}
            removed = 0
            for app_key, app in apps.items():
                out = output_path(platform_root, github_root, app_key, app)
                if out.is_file():
                    out.unlink()
                    print(f"Removed {out}")
                    removed += 1
            print(f"clean-render-all OK ({removed} file(s) removed)")
            return 0

    except AppNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
