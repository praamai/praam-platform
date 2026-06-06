"""Filesystem paths for praam-platform."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_platform_root(start: Path | None = None) -> Path:
    if raw := os.environ.get("PRAAM_PLATFORM_ROOT"):
        return Path(raw).resolve()
    here = (start or Path.cwd()).resolve()
    if (here / "services.yaml").is_file():
        return here
    for candidate in (here, *here.parents):
        if (candidate / "services.yaml").is_file():
            return candidate
    raise FileNotFoundError("Could not locate praam-platform root (services.yaml missing)")
