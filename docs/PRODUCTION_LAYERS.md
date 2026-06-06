# Production 13-layer stack — what lives where in Praam

Generic production checklist mapped to **repo ownership**. Layers are concerns, not one service each.

| # | Layer | praam-platform | Other owner |
|---|--------|----------------|-------------|
| 1 | Frontend | — | Product repos |
| 2 | API & backend logic | Config API only | Product repos |
| 3 | Database & storage | Postgres + schemas | App tables; S3/MinIO per app |
| 4 | Auth & permissions | Dev token on secrets API | **praam-pulse** + app JWT validate |
| 5 | Hosting & deployment | Docker Compose (dev) | Phase 4 K8s/Helm |
| 6 | Cloud & compute | — | Production infra |
| 7 | CI/CD | GHA, `make check` | demo-hub suite CI |
| 8 | Security & secrets | Secrets API, AWS SM backend | App RLS in migrations |
| 9 | Rate limiting | Config API middleware | App APIs |
| 10 | Cache & CDN | Redis | CDN in prod edge |
| 11 | Load balancing | — | Production |
| 12 | Error tracking | JSON access logs, `/v1/platform/health` | Phase 3 Prometheus |
| 13 | Availability & DR | `make backup-db` (dev) | Production Multi-AZ |

## Added in platform v1.1+

- Structured JSON access logs (`LOG_JSON=true`)
- Rate limiting on config API (`RATE_LIMIT_*`)
- Platform health rollup: `GET /v1/platform/health?runtime=host|docker`
- `services.yaml` validation at API startup
- Local DB backup: `make backup-db`

See also [SUITE_LAYERS.md](SUITE_LAYERS.md) (Praam-specific ownership model).
