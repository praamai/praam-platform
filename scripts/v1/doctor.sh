#!/usr/bin/env bash
# Verify platform Postgres schemas and optionally compare rendered env files.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GITHUB_ROOT="${GITHUB_ROOT:-$(cd "$ROOT/.." && pwd)}"
COMPOSE="${COMPOSE:-docker compose -f $ROOT/docker-compose.yml}"
PY="${ROOT}/scripts/v1/_services.py"
PLATFORM_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --platform-only) PLATFORM_ONLY=1 ;;
  esac
done

if ! python3 -c "import yaml" >/dev/null 2>&1; then
  echo "ERROR: PyYAML not installed. Run: make install-dev  (or: uv sync --all-extras)"
  exit 1
fi

echo "praam-platform doctor"
echo ""

echo "== Platform containers =="
if ! docker info >/dev/null 2>&1; then
  echo "  FAIL — Docker daemon not running"
  exit 1
fi

$COMPOSE ps

echo ""
echo "== Service health =="
pg_ok=0
redis_ok=0
llm_ok=0
cfg_ok=0
$COMPOSE exec -T postgres pg_isready -U praam -d praam_dev >/dev/null 2>&1 && pg_ok=1 || true
$COMPOSE exec -T redis redis-cli ping 2>/dev/null | grep -q PONG && redis_ok=1 || true
curl -sf http://127.0.0.1:3100/health/liveliness >/dev/null 2>&1 && llm_ok=1 || true
curl -sf http://127.0.0.1:3180/v1/health/live >/dev/null 2>&1 && cfg_ok=1 || true

check() {
  local label=$1 ok=$2
  if [ "$ok" = "1" ]; then
    echo "  OK — $label"
  else
    echo "  FAIL — $label"
  fi
}

check "postgres" "$pg_ok"
check "redis" "$redis_ok"
check "litellm" "$llm_ok"
check "platform-config" "$cfg_ok"

if [ "$pg_ok" != "1" ] || [ "$redis_ok" != "1" ] || [ "$llm_ok" != "1" ] || [ "$cfg_ok" != "1" ]; then
  echo ""
  echo "Start platform: make -C $ROOT up && make -C $ROOT wait"
  exit 1
fi

echo ""
echo "== Postgres schemas =="
bash "$ROOT/scripts/v1/verify-schema.sh"

if [ "$PLATFORM_ONLY" = "1" ]; then
  echo ""
  echo "== Platform rollup health =="
  if curl -sf "http://127.0.0.1:3180/v1/platform/health?runtime=docker" >/dev/null 2>&1; then
    echo "  OK — /v1/platform/health"
  else
    echo "  FAIL — /v1/platform/health"
    exit 1
  fi
  echo ""
  echo "== Config API smoke =="
  if PRAAM_CONFIG_STRICT=1 python3 "$ROOT/scripts/v1/config-smoke.py"; then
    echo "  Config API OK"
  else
    echo "  FAIL — config API smoke"
    exit 1
  fi
  echo ""
  echo "Doctor OK (platform-only)"
  exit 0
fi

echo ""
echo "== Rendered env freshness =="
stale=0
while IFS= read -r app; do
  [ -n "$app" ] || continue
  result="$(python3 "$PY" check-render "$ROOT" "$GITHUB_ROOT" "$app" 2>/dev/null || true)"
  status="${result%%$'\t'*}"
  path="${result#*$'\t'}"
  case "$status" in
    OK) echo "  OK — $path" ;;
    MISSING)
      echo "  MISSING — $path (run: make -C $ROOT render-env APP=$app)"
      stale=1
      ;;
    STALE)
      echo "  STALE — $path (run: make -C $ROOT render-env APP=$app)"
      stale=1
      ;;
    *)
      echo "  FAIL — $app ($result)"
      stale=1
      ;;
  esac
done < <(python3 "$PY" list-wired-apps "$ROOT" "$GITHUB_ROOT" 2>/dev/null || python3 "$PY" list-apps "$ROOT" "$GITHUB_ROOT")

if [ "$stale" -ne 0 ]; then
  exit 1
fi

echo ""
echo "Doctor OK"
