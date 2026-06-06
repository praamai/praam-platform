#!/usr/bin/env bash
# Remove legacy .env.platform.generated from sibling app repos.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GITHUB_ROOT="${GITHUB_ROOT:-$(cd "$ROOT/.." && pwd)}"
PY="${ROOT}/scripts/v1/_services.py"

python3 "$PY" clean-render-all "$ROOT" "$GITHUB_ROOT"
