# Operations Guide

## Environments

| Env         | Notes                                                             |
| ----------- | ----------------------------------------------------------------- |
| development | `APP_DEBUG=true`, local Postgres/Redis/RabbitMQ                   |
| testing     | Ephemeral DB in CI, deterministic secrets                         |
| staging     | Production build, staging providers, real Celery workers          |
| production  | `APP_DEBUG=false`, rotated `APP_SECRET_KEY`, HTTPS, backups on    |

`Settings.validate_production()` returns a list of warnings for missing
or unsafe configuration; call it during boot in your deployment scripts.

## Docker

`backend/docker-compose.yml` starts Postgres, Redis, RabbitMQ, the API,
and Celery workers/beat. Bring the stack up with:

```
cd backend
docker compose up --build
```

## Health & metrics

- Liveness: `GET /healthz`
- API health: `GET /api/v1/monitoring/health`
- System metrics: `GET /api/v1/monitoring/system`
- Prometheus scrape: `GET /api/v1/monitoring/metrics`

## Backups

The default deployment expects nightly `pg_dump` of the platform DB and
weekly snapshots of `STORAGE_LOCAL_ROOT` (or S3 versioning). Restore by
recreating the DB and pointing `DATABASE_URL` at the restored instance.

## Maintenance mode

Set `MAINTENANCE_MODE=true` and redeploy — the middleware returns a 503
envelope for mutating endpoints while keeping monitoring/health
endpoints reachable.

## CI/CD

`.github/workflows/ci.yml` runs backend tests + frontend build/typecheck
on every push. The `docker` job builds the API image without publishing.
Add environment-specific deploy jobs to push the image to your registry
and roll out via Compose / Kubernetes.
