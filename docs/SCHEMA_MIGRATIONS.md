# Schema migrations across the Praam suite

**Platform owns:** database `praam_dev`, schema creation, `vector` extension, grants.  
**Apps own:** tables, indexes, Alembic revisions inside their schema.

Init SQL lives in `infra/postgres/init/01-schemas.sql` — never add app tables there.

## Schema map

| Schema | App repo | Status |
|--------|----------|--------|
| `findoc` | findoc-ai | Done — SQLAlchemy `create_all` + search_path |
| `knowledge_studio` | praam-knowledge-studio | Done — `make db-init` applies `schema.sql`; `make migrate-legacy-users` copies accounts from legacy `:15431` |
| `prism` | prism | Pending |
| `askhr` | askHR | Done — platform compose + `render-env`; tables via API `init_db()` |
| `plan_copilot` | production-plan-copilot | Pending |
| `pulse` | praam-pulse | Pending |

## Migration order (sibling PRs)

1. **findoc-ai** — host runtime, `.env.platform.generated`, `PRAAM_USE_PLATFORM=1` ✓
2. **praam-demo-hub** — suite calls platform before sibling `make up` ✓
3. **praam-knowledge-studio** — docker runtime, `praam-network`, `make db-init` ✓
4. **prism**, **askHR**, **production-plan-copilot**, **praam-pulse** — pending

## Per-app checklist

- [ ] Add `-include $(PRAAM_PLATFORM_ROOT)/make/v1/platform.mk` to Makefile
- [ ] Gitignore `.env.platform.generated`
- [ ] Load `.env` then `.env.platform.generated` in app config
- [ ] `make render-env` before `make up` when `PRAAM_USE_PLATFORM=1`
- [ ] Alembic `version_table_schema` = app schema (or equivalent isolation)
- [ ] `PRAAM_USE_PLATFORM=0` escape hatch still works in CI

## Connection string pattern

Host-run apps use localhost ports from `services.yaml`:

```text
postgresql+psycopg://praam:praam_dev@127.0.0.1:15430/praam_dev?options=-csearch_path%3Dfindoc%2Cpublic
```

Container-run apps use Docker DNS on `praam-network`:

```text
postgresql://praam:praam_dev@postgres:5432/praam_dev?options=-csearch_path%3Dknowledge_studio%2Cpublic
```

## Verify

```bash
make -C ../praam-platform verify-schema
make -C ../findoc-ai verify-schema   # after app wiring
```
