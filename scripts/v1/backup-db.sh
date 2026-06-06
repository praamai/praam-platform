#!/usr/bin/env bash
# Backup local praam-platform Postgres volume to ./backups/
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE="${COMPOSE:-docker compose -f $ROOT/docker-compose.yml}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="${ROOT}/backups"
OUT_FILE="${OUT_DIR}/praam_dev-${STAMP}.sql.gz"

mkdir -p "${OUT_DIR}"

if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker not running"
  exit 1
fi

$COMPOSE exec -T postgres pg_dump -U praam -d praam_dev | gzip > "${OUT_FILE}"
echo "Wrote ${OUT_FILE}"
