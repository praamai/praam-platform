# praam-platform SDK

Runtime config and secrets via **platform-config API** (AWS Secrets Manager pattern).

## Python (uv)

From **praam-platform** root:

```bash
uv sync --all-extras
uv run python -c "from praam_platform import PlatformClient; PlatformClient('findoc-ai').load()"
```

## TypeScript

```bash
cd sdk/typescript && npm install && npm run build
```

```typescript
import { PlatformClient } from "@praam/platform";

const loaded = await PlatformClient.load("findoc-ai");
console.log(loaded.config.postgres?.url);
```

## Bootstrap env (only these)

| Variable | Purpose |
|----------|---------|
| `PRAAM_CONFIG_URL` | Config API base (default `http://127.0.0.1:3180`) |
| `PRAAM_SERVICE_TOKEN` | Bearer token for secrets API (dev: `praam-platform-dev`) |

Everything else — DB, Redis, LiteLLM, ports — is fetched at startup.

See [docs/CONFIG_API.md](../docs/CONFIG_API.md).

Legacy `make render-env` still works as a fallback.
