# praam-platform — agent guide

Evidence-first: cite `services.yaml`, `lib/praam_platform/`, or command output. Do not invent env vars or ports.

## What this repo is

Shared **local dev platform** for the Praam suite: Postgres (`praam_dev` + schemas), Redis, LiteLLM, **platform-config API** (`:3180`).

**Not in scope here:** app tables, human login (see praam-pulse), sibling app business logic.

## Source of truth

| File | Purpose |
|------|---------|
| `services.yaml` | Ports, schemas, Redis roles, secrets map |
| `lib/praam_platform/` | Config builder, secrets backends, `PlatformClient` |
| `services/platform-config/` | FastAPI config + secrets API |

## How apps get config (preferred)

```python
from praam_platform import PlatformClient
PlatformClient("findoc-ai").load()  # bootstrap: PRAAM_CONFIG_URL, PRAAM_SERVICE_TOKEN
```

Legacy: `make render-env` → sibling `.env.platform.generated`.

## Commands

```bash
make bootstrap   # first time: secrets + uv sync
make check       # offline tests + config contract (no Docker)
make up          # full stack
make sdk         # generate SDK + sync to wired sibling repos
make doctor DOCTOR_FLAGS=--platform-only
```

## Do not

- Add app tables to `infra/postgres/init/` (schemas only)
- Mutate sibling `.env` files from this repo
- Commit real secrets (`~/.praam/secrets.env`)
- Move suite auth into this repo

## Suite architecture

**13-layer stack** (concerns, not deployables): see [.cursor/rules/praam-suite-layers.mdc](.cursor/rules/praam-suite-layers.mdc) and [docs/SUITE_LAYERS.md](docs/SUITE_LAYERS.md).

**praam-platform owns layers 7–12** (config registry → LLM gateway). **praam-pulse owns 5–6** (identity, watch). Product repos own 1–4.

## Docs

- [docs/CONFIG_API.md](docs/CONFIG_API.md)
- [docs/STATUS.md](docs/STATUS.md)
- [docs/PRODUCTION_LAYERS.md](docs/PRODUCTION_LAYERS.md) — generic 13-layer → repo map
