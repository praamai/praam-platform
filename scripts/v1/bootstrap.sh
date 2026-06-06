#!/usr/bin/env bash
# Ensure ~/.praam/secrets.env exists before starting the platform stack.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SECRETS_FILE="${PRAAM_SECRETS_FILE:-${HOME}/.praam/secrets.env}"
EXAMPLE="${ROOT}/.env.example"

mkdir -p "$(dirname "${SECRETS_FILE}")"

if [ ! -f "${SECRETS_FILE}" ]; then
  if [ -f "${EXAMPLE}" ]; then
    cp "${EXAMPLE}" "${SECRETS_FILE}"
    echo "Created ${SECRETS_FILE} from .env.example"
  else
    touch "${SECRETS_FILE}"
    echo "Created empty ${SECRETS_FILE} — add provider keys for LiteLLM"
  fi
fi
