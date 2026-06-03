# praam-platform

Shared local development platform for the Praam product suite (Postgres, Redis, LiteLLM, service registry, orchestration).

**Version:** see [VERSION](VERSION)

## Quick start

```bash
# From sibling layout: ~/dev/github/praam-platform
python3 -m pip install -r requirements-dev.txt   # once, for render-env scripts

make up          # postgres :15430, redis :16380, litellm :3100
make wait        # health checks
make render-env APP=findoc-ai
make verify-schema
make doctor      # health + env freshness
```

Secrets for LiteLLM providers: copy [.env.secrets.example](.env.secrets.example) to `~/.praam/secrets.env`.

## Docs

| Doc | Purpose |
|-----|---------|
| [docs/PLATFORM_PLAN.md](docs/PLATFORM_PLAN.md) | Approved architecture and Phase 1 plan |
| [docs/SCHEMA_MIGRATIONS.md](docs/SCHEMA_MIGRATIONS.md) | Schema ownership and sibling migration order |

## Layout

```text
praam-platform/
├── services.yaml          # ports, deps, redis roles, schemas
├── docker-compose.yml     # postgres, redis, litellm on praam-network
├── make/v1/platform.mk    # included by product repos
└── scripts/v1/            # render-env, doctor, verify-schema
```

## Product repo integration

```makefile
PRAAM_PLATFORM_ROOT ?= $(abspath ../praam-platform)
PRAAM_PLATFORM_API ?= v1
PRAAM_USE_PLATFORM ?= 1
-include $(PRAAM_PLATFORM_ROOT)/make/$(PRAAM_PLATFORM_API)/platform.mk
```

Developer flow:

```text
make up  →  platform-ensure  →  platform-wait  →  render-env  →  verify-schema  →  up-app
```

Set `PRAAM_USE_PLATFORM=0` to use per-repo Postgres/Redis (CI escape hatch).

## Wired apps

| App | Notes |
|-----|--------|
| findoc-ai | Host runtime; `make migrate` |
| praam-knowledge-studio | Docker on `praam-network`; `make db-init` then `make up` |

## Clone location

Sibling repos expect this directory next to them:

```text
~/dev/github/
├── praam-platform/
├── praam-demo-hub/
├── findoc-ai/
└── ...
```

Override: `PRAAM_PLATFORM_ROOT=/path/to/praam-platform`
