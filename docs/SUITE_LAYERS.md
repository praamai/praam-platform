# Praam suite — 13-layer stack

Persistent architecture reference for the whole suite. **Layers = boundaries, not one container per layer.**

Last updated: 2026-06-06

## Stack (top → bottom)

| # | Layer | Owner |
|---|--------|--------|
| 1 | Product UI | Product repos |
| 2 | Product API | Product repos |
| 3 | Product domain | Product repos |
| 4 | Product data (schema on `praam_dev`) | Product repos |
| 5 | Suite identity (JWT issuer) | **praam-pulse** |
| 6 | Suite watch / security events | **praam-pulse** |
| 7 | Config registry | **praam-platform** (`services.yaml`) |
| 8 | Config + secrets API | **praam-platform** (`:3180`) |
| 9 | Platform SDK | **praam-platform** (`PlatformClient`) |
| 10 | Shared Postgres | **praam-platform** |
| 11 | Shared Redis | **praam-platform** |
| 12 | LLM gateway (LiteLLM) | **praam-platform** |
| 13 | Dev orchestration | platform + demo-hub |

## What praam-platform implements

Layers **7–12**, plus layer **13** tooling (`make`, doctor, CI).

**Complete for v1.1** — sibling apps still need to adopt the SDK (layers 1–4 + pulse 5–6 are separate repos).

## Config contract

Bootstrap only:

- `PRAAM_CONFIG_URL` (default `http://127.0.0.1:3180`)
- `PRAAM_SERVICE_TOKEN` (dev: `praam-platform-dev`)

```python
from praam_platform import PlatformClient
PlatformClient("findoc-ai").load()
```

## Related

- [CONFIG_API.md](CONFIG_API.md)
- [STATUS.md](STATUS.md)
- [PLATFORM_PLAN.md](PLATFORM_PLAN.md)
