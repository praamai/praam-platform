# Platform config API

Runtime configuration and secrets — **no `.env.platform.generated` required** when apps use the SDK.

## Architecture

```text
App startup
  → PRAAM_CONFIG_URL + PRAAM_SERVICE_TOKEN (bootstrap only)
  → GET /v1/apps/{app}/config          (infra: DB, Redis, LiteLLM, ports)
  → GET /v1/secrets/{name}             (provider keys — auth required)
  → apply to process env or use structured config
```

Same pattern as **AWS Secrets Manager**: bootstrap credential → fetch at runtime → cache in memory.

## Endpoints

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| GET | `/v1/health/live` | No | Config service liveness |
| GET | `/v1/platform/health` | No | Postgres + Redis + LiteLLM rollup (`?runtime=host\|docker`) |
| GET | `/v1/apps` | No | App keys from `services.yaml` |
| GET | `/v1/apps/{app}/config` | No | Structured config + flat `env` map |
| GET | `/v1/secrets` | Bearer | Secret names |
| GET | `/v1/secrets/{name}` | Bearer | Secret value |

Optional query: `?runtime=host|docker` overrides app runtime from `services.yaml`.

## Local dev

```bash
make up
curl http://127.0.0.1:3180/v1/apps/findoc-ai/config
curl -H "Authorization: Bearer praam-platform-dev" \
  http://127.0.0.1:3180/v1/secrets/openai-api-key
```

Secrets are read from **`~/.praam/secrets.env`** only (override with `PRAAM_SECRETS_FILE`). LiteLLM uses the same file.

### Ops

| Env | Default | Purpose |
|-----|---------|---------|
| `LOG_JSON` | `true` | JSON access logs on stdout |
| `RATE_LIMIT_ENABLED` | `true` | Enable API rate limiting |
| `RATE_LIMIT_MAX` | `120` | Requests per window per client |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate limit window |

```bash
curl "http://127.0.0.1:3180/v1/platform/health?runtime=docker"
make backup-db   # local Postgres dump → backups/
```

Use `runtime=docker` when the API runs in Compose (checks `postgres`, `redis`, `litellm` on `praam-network`). Use `runtime=host` when running `make run-config-api` on the host.

## Python SDK

```python
from praam_platform import PlatformClient

# Fetches config from API; applies os.environ by default
PlatformClient("findoc-ai").load()

# With provider secret (usually LiteLLM handles this — apps rarely need it)
PlatformClient("findoc-ai").load(fetch_secrets=["openai-api-key"])
```

Install: `uv sync --all-extras` from repo root (or `PYTHONPATH=lib` for scripts only).

## TypeScript SDK

```typescript
import { PlatformClient } from "@praam/platform";
await PlatformClient.load("findoc-ai");
```

## Production (AWS)

Set in `services.yaml`:

```yaml
secrets:
  backend: aws
  aws_arns:
    openai-api-key: arn:aws:secretsmanager:us-east-1:123456789:secret:openai
```

Apps still bootstrap with `PRAAM_CONFIG_URL` and IAM role / service token. AWS extras: `uv sync --extra aws`.

## Legacy fallback

`make render-env` writes `.env.platform.generated` for apps not yet on the SDK. Both paths read the same `services.yaml` logic from `lib/praam_platform/`.

## Security

- Config endpoint exposes **dev DB passwords** — local dev only; production should use IAM auth + scoped tokens.
- Secrets endpoint **always requires** `Authorization: Bearer $PRAAM_SERVICE_TOKEN`.
- Never commit real keys; use `~/.praam/secrets.env`.
