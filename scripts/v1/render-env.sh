#!/usr/bin/env bash
# Render .env.platform.generated for one app or all apps.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GITHUB_ROOT="${GITHUB_ROOT:-$(cd "$ROOT/.." && pwd)}"
PY="${ROOT}/scripts/v1/_services.py"

usage() {
  echo "Usage: render-env.sh <app-key|repo-name> | --all"
  exit 1
}

if [ "$#" -lt 1 ]; then
  usage
fi

if ! python3 -c "import yaml" >/dev/null 2>&1; then
  echo "ERROR: PyYAML not installed. Run: make install-dev  (or: uv sync --all-extras)"
  exit 1
fi

if [ "$1" = "--all" ]; then
  while IFS= read -r app; do
    python3 "$PY" render "$ROOT" "$GITHUB_ROOT" "$app"
  done < <(python3 "$PY" list-apps "$ROOT" "$GITHUB_ROOT")
  exit 0
fi

python3 "$PY" render "$ROOT" "$GITHUB_ROOT" "$1"
