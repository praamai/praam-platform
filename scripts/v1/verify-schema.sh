#!/usr/bin/env bash
# Verify expected Postgres schemas exist in praam_dev.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE="${COMPOSE:-docker compose -f $ROOT/docker-compose.yml}"
PY="${ROOT}/scripts/v1/_services.py"

if ! python3 -c "import yaml" >/dev/null 2>&1; then
  echo "ERROR: PyYAML not installed. Run: make install-dev  (or: uv sync --all-extras)"
  exit 1
fi

missing=0

while IFS= read -r schema; do
  [ -n "$schema" ] || continue
  found="$($COMPOSE exec -T postgres psql -U praam -d praam_dev -tAc \
    "SELECT 1 FROM information_schema.schemata WHERE schema_name = '$schema'" 2>/dev/null < /dev/null | tr -d '[:space:]')"
  if [ "$found" = "1" ]; then
    echo "  OK — schema $schema"
  else
    echo "  FAIL — schema $schema missing"
    missing=1
  fi
done < <(python3 "$PY" expected-schemas "$ROOT" "$(cd "$ROOT/.." && pwd)")

if [ "$missing" -ne 0 ]; then
  echo ""
  echo "Run platform init: make -C $ROOT up"
  exit 1
fi

echo "verify-schema OK"
