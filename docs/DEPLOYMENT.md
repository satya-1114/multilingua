# Deployment

This document covers installing, upgrading, and rolling back the platform.

## Prerequisites

- Kubernetes 1.24+ (or Docker Compose for single-node)
- PostgreSQL 15+ and Redis 7+ reachable from the cluster
- Ingress controller (nginx-ingress or equivalent) and a TLS certificate manager
- Container registry hosting `platform/backend` and `platform/frontend` images

## Environment variables

| Variable | Where | Required | Notes |
| --- | --- | --- | --- |
| `APP_ENV` | ConfigMap | yes | `production`, `staging`, `development` |
| `LOG_LEVEL` | ConfigMap | no | Default `INFO` |
| `CORS_ORIGINS` | ConfigMap | yes | Comma-separated allow list |
| `DATABASE_URL` | Secret | yes | SQLAlchemy DSN |
| `REDIS_URL` | Secret | yes | Broker + result backend for Celery |
| `APP_SECRET_KEY` | Secret | yes | ≥ 32 chars; used for token signing |
| `WEBHOOK_SECRET` | Secret | yes | HMAC signing key for inbound webhooks |
| `RATE_LIMIT_ENABLED` | ConfigMap | no | `true` / `false` |
| `WORKER_CONCURRENCY` | ConfigMap | no | Celery worker concurrency |

## Docker Compose (single node)

```
docker compose -f docker/docker-compose.prod.yml up -d
```

## Kubernetes (raw manifests)

```
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/configmap.yaml
kubectl apply -f deploy/k8s/secret.example.yaml   # edit first
kubectl apply -f deploy/k8s/backend-deployment.yaml
kubectl apply -f deploy/k8s/worker-deployment.yaml
kubectl apply -f deploy/k8s/scheduler-deployment.yaml
kubectl apply -f deploy/k8s/frontend-deployment.yaml
kubectl apply -f deploy/k8s/ingress.yaml
kubectl apply -f deploy/k8s/hpa.yaml
```

## Kubernetes (Helm)

See `deploy/helm/README.md`. Standard flow:

```
helm install platform ./deploy/helm --namespace platform --create-namespace
helm upgrade platform ./deploy/helm --namespace platform --set image.backend.tag=1.2.4
helm rollback platform 1 --namespace platform
```

## Production checklist

- [ ] All Secrets populated (no `replace-me` values)
- [ ] `APP_SECRET_KEY` is ≥ 32 chars and unique per environment
- [ ] Managed Postgres has automated backups enabled
- [ ] Redis persistence configured (AOF)
- [ ] TLS certificate valid and auto-renewing
- [ ] Ingress `proxy-body-size` matches largest expected upload
- [ ] HPA min/max replicas sized for peak traffic
- [ ] Log aggregation and metric scraping enabled
- [ ] Alerts wired to `/health/ready` and Celery queue depth
- [ ] Runbook (`docs/RUNBOOK.md`) accessible to on-call
- [ ] Backups verified via a test restore in staging

## Rollback

```
helm rollback platform <revision> --namespace platform
# or, raw manifests:
kubectl set image deployment/backend backend=platform/backend:<previous-tag> -n platform
kubectl set image deployment/worker  worker=platform/backend:<previous-tag>  -n platform
```

Roll back the database only via a restore procedure — never by rolling back
the application image alone when a migration ran. See
`docs/BACKUP_AND_RECOVERY.md`.