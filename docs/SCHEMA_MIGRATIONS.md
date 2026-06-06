# Schema migrations across the Praam suite

**Platform owns:** database `praam_dev`, schema creation, `vector` extension, grants, `render-env`, `verify-schema`.  
**Apps own:** tables, indexes, Alembic revisions inside their schema, Makefile wiring, `.env.platform.generated` load order.

Init SQL lives in `infra/postgres/init/01-schemas.sql` — never add app tables there.

> **Platform Phase 1 is complete in `praam-platform`.** The table below tracks **sibling repo** rollout only.

## Schema map

| Schema | App repo | Sibling rollout |
|--------|----------|-----------------|
| `findoc` | findoc-ai | Done — SQLAlchemy `create_all` + search_path |
| `knowledge_studio` | praam-knowledge-studio | Done — `make db-init` applies `schema.sql` |
| `askhr` | askHR | Done — platform compose + `render-env`; tables via API `init_db()` |
| `prism` | prism | Pending |
| `plan_copilot` | production-plan-copilot | Pending — partial `platform.mk` wiring |
| `pulse` | praam-pulse | Pending — partial `platform.mk` wiring |

## Migration order (sibling PRs)

1. **findoc-ai** ✓
2. **praam-demo-hub** ✓
3. **praam-knowledge-studio** ✓
4. **askHR** ✓
5. **production-plan-copilot**, **praam-pulse**, **prism** — pending

## Per-app checklist (sibling repos)

Apply in each product repo when wiring to the platform:

- [ ] Add `-include $(PRAAM_PLATFORM_ROOT)/make/v1/platform.mk` to Makefile
- [ ] Gitignore `.env.platform.generated`
- [ ] Load `.env` then `.env.platform.generated` in app config
- [ ] `make render-env` before `make up` when `PRAAM_USE_PLATFORM=1`
- [ ] Alembic `version_table_schema` = app schema (or equivalent isolation)
- [ ] `PRAAM_USE_PLATFORM=0` escape hatch still works in CI
- [ ] Set `platform_wired: true` in `services.yaml` when doctor env checks should apply

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
