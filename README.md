# praam-platform

Shared **local development platform** for the [Praam](https://github.com/orgs/praamai) product suite — one Postgres, one Redis, one LiteLLM gateway, and a single registry (`services.yaml`) instead of duplicating infra in every repo.

**Version:** see [VERSION](VERSION)

## What is this?

When you run six demos locally, you do not want six Postgres containers, six Redis instances, and six copies of `OPENAI_API_KEY` in `.env` files. **praam-platform** is the shared layer:

```text
Application layer          Platform layer (this repo)
─────────────────          ──────────────────────────
praam-demo-hub             PostgreSQL  praam_dev + per-app schemas
praam-knowledge-studio  →  Redis       logical DB indexes per app
findoc-ai                  LiteLLM     provider keys in ~/.praam/secrets.env
prism, askHR, …            praam-network
```

Production uses managed RDS, ElastiCache, and a real AI gateway — **this repo is dev-only.**

## How it works

### 1. Start platform

```bash
make    # up + wait + render-env-all + verify-schema
```

Starts three containers on **`praam-network`**:

| Service | Host port | In-container hostname |
|---------|-----------|------------------------|
| Postgres (pgvector) | 15430 | `postgres:5432` |
| Redis | 16380 | `redis:6379` |
| LiteLLM | 3100 → 4000 | `litellm:4000` |

Database **`praam_dev`** holds **schemas** (not separate databases): `findoc`, `knowledge_studio`, `prism`, `askhr`, `plan_copilot`, `pulse`.

### 2. Render app environment

```bash
make render-env APP=findoc-ai
# writes ../findoc-ai/backend/.env.platform.generated
```

[`services.yaml`](services.yaml) is the single source of truth for ports, `runtime: host|docker`, Redis roles (`cache`, `celery`), and health paths. Scripts never edit your private `.env` — only generate `.env.platform.generated`.

Apps load:

```text
.env  →  .env.platform.generated  (later wins)
```

### 3. Product repo starts

Each wired app includes `make/v1/platform.mk`:

```makefile
PRAAM_USE_PLATFORM ?= 1
-include $(PRAAM_PLATFORM_ROOT)/make/v1/platform.mk
```

Typical flow:

```text
make up  →  platform-ensure  →  platform-wait  →  render-env  →  up-app
```

- **Docker apps** (e.g. knowledge-studio) talk to `postgres`, `redis`, `litellm` on `praam-network`.
- **Host apps** (e.g. findoc API) use `127.0.0.1:15430`, `127.0.0.1:16380`, `127.0.0.1:3100`.

### 4. Full suite from demo hub

```bash
cd ../praam-demo-hub && make all
```

The hub runs platform first, then each sibling `make up`, then the showcase on :3000.

## Quick start

```bash
python3 -m pip install -r requirements-dev.txt
cp .env.secrets.example ~/.praam/secrets.env   # provider keys for LiteLLM

make
make doctor
```

| Command | Action |
|---------|--------|
| `make` / `make up` | Start postgres, redis, litellm |
| `make wait` | Wait until all services healthy |
| `make render-env APP=<key>` | Write one app’s `.env.platform.generated` |
| `make render-env-all` | Render for every app in `services.yaml` |
| `make verify-schema` | Check schemas exist in Postgres |
| `make doctor` | Platform health + wired-app env freshness |
| `make down` | Stop platform containers |

Set **`PRAAM_USE_PLATFORM=0`** in any product Makefile to use that repo’s own Postgres/Redis (escape hatch for CI or debugging).

## Wired apps

| App | Notes |
|-----|--------|
| [findoc-ai](https://github.com/praamai/findoc-ai) | Host runtime; `make migrate` |
| [praam-knowledge-studio](https://github.com/praamai/praam-knowledge-studio) | Docker + `praam-network`; `make db-init` once, then `make up` |
| Others | `render-env` works; full platform migration pending — see [docs/SCHEMA_MIGRATIONS.md](docs/SCHEMA_MIGRATIONS.md) |

## Repo layout

```text
praam-platform/
├── services.yaml              # registry: ports, schemas, redis, deps
├── docker-compose.yml
├── config/litellm.yaml          # model aliases: fast, reasoning, embedding
├── infra/postgres/init/        # CREATE SCHEMA only (no app tables)
├── make/v1/platform.mk         # stable API — pin PRAAM_PLATFORM_API=v1
├── scripts/v1/                 # render-env, doctor, verify-schema
└── docs/
    ├── PLATFORM_PLAN.md        # architecture
    └── SCHEMA_MIGRATIONS.md    # per-app rollout order
```

## Clone layout

```text
~/dev/github/
├── praam-platform/       ← this repo
├── praam-demo-hub/
├── findoc-ai/
├── praam-knowledge-studio/
└── ...
```

Override path: `PRAAM_PLATFORM_ROOT=/path/to/praam-platform`

## Docs

| Doc | Purpose |
|-----|---------|
| [docs/PLATFORM_PLAN.md](docs/PLATFORM_PLAN.md) | Approved architecture and phases |
| [docs/SCHEMA_MIGRATIONS.md](docs/SCHEMA_MIGRATIONS.md) | Who owns schemas vs Alembic |

## Future (not in Phase 1)

Ollama, Prometheus/Grafana, Python/TypeScript SDK reading `services.yaml`, Kubernetes manifests.
