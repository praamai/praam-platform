# praam-platform — status

**This repo is complete for v1.1.** Sibling apps should migrate to `PlatformClient` — see [SCHEMA_MIGRATIONS.md](SCHEMA_MIGRATIONS.md).

Last updated: 2026-06-06

## Shipped

| Area | What exists |
|------|-------------|
| **Infra** | Postgres, Redis, LiteLLM, platform-config API (`:3180`) |
| **Config API** | `GET /v1/apps/{app}/config`, `GET /v1/secrets/{name}` |
| **Secrets** | Local `~/.praam/secrets.env`; AWS SM via `secrets.backend=aws` |
| **SDK** | Python (`lib/praam_platform`) + TypeScript (`sdk/typescript`) |
| **Legacy** | `render-env` → `.env.platform.generated` |
| **Tooling** | `make bootstrap`, `make check`, `make sdk`, doctor, CI, `make backup-db`, AGENTS.md |
| **Ops** | JSON access logs, rate limits, `/v1/platform/health` rollup |

## App integration

Bootstrap only (2 env vars) — see [CONFIG_API.md](CONFIG_API.md):

```python
from praam_platform import PlatformClient
PlatformClient("findoc-ai").load()
```

## Commands

| Command | When |
|---------|------|
| `make bootstrap` | First clone |
| `make check` | Before PR (no Docker) |
| `make up` | Local dev full stack |
| `make doctor DOCTOR_FLAGS=--platform-only` | Health check |

## Next work (outside this repo)

1. Sibling apps: replace `load_dotenv(".env.platform.generated")` with `PlatformClient`
2. Wire prism, plan-copilot, pulse to platform
3. Suite CI with cloned repos
