# praam-platform SDK (reserved)

Phase 1 uses shell scripts (`scripts/v1/render-env.sh`) and `services.yaml`.

Future packages will read the same registry:

- **Python:** `from praam_platform import get_database_url, get_litellm_url, get_redis_url`
- **TypeScript:** `getDatabaseUrl()`, `getLitellmUrl()`, `getRedisUrl()`

Not implemented in Phase 1.
