# @praam/platform

Runtime config client for the Praam platform — fetch DB URLs, Redis, LiteLLM from the config API instead of `.env` files.

```bash
npm install @praam/platform
```

```typescript
import { PlatformClient } from "@praam/platform";

const loaded = await PlatformClient.load("findoc-ai");
console.log(loaded.config.postgres?.url);
loaded.applyEnv(process.env);
```

Bootstrap env (only these in production):

- `PRAAM_CONFIG_URL` — e.g. `http://127.0.0.1:3180`
- `PRAAM_SERVICE_TOKEN` — dev default `praam-platform-dev`

See [praam-platform](https://github.com/praamai/praam-platform) docs.
