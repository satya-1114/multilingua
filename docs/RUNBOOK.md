# Runbook

On-call procedures for the platform.

## Health & probes

| Endpoint | Purpose | Component |
| --- | --- | --- |
| `GET /health` | Generic liveness | Backend |
| `GET /health/live` | Kubernetes liveness | Backend |
| `GET /health/ready` | Readiness (DB, Redis, registry) | Backend |
| `GET /v1/runtime/health` | Workflow runtime health | Backend |
| `GET /healthz` | Nginx (frontend) | Frontend |

## Common incidents

### 1. Backend pods flapping

1. `kubectl logs -n platform deploy/backend --tail=200`
2. Check `/health/ready` from within the cluster.
3. If DB unreachable, verify `DATABASE_URL` secret and network policy.
4. If startup probe fails, extend `failureThreshold` (default 30) rather
   than disabling — startup migrations can be slow.

### 2. Workflow queue backlog

1. `GET /v1/runtime/health` — check queue depth and worker count.
2. Scale workers: `kubectl scale deploy/worker -n platform --replicas=8`.
3. Confirm Redis is not the bottleneck (`INFO memory`, `INFO clients`).
4. If backlog persists, inspect failing action handlers via
   `GET /v1/runtime/observability/metrics` (Phase 9.3).

### 3. Scheduler down (no scheduled runs)

1. Scheduler runs single-replica with leader election. Check pod state.
2. `kubectl rollout restart deploy/scheduler -n platform`.
3. Verify Redis is reachable; the leader lease lives in Redis.

### 4. High latency

1. Consult `avgResponseTime` on `/v1/runtime/observability/metrics`.
2. Check `cache.hitRatio` — a sudden drop often precedes regressions.
3. Scale backend via HPA (already enabled) or increase `maxReplicas`.
4. Inspect slow queries in Postgres (`pg_stat_statements`).

### 5. Rate limit false positives

1. Set `RATE_LIMIT_ENABLED=false` in ConfigMap and roll backend.
2. Investigate the offending source IP / user ID.
3. Re-enable rate limiting once tuned.

## Scaling guidance

| Load | Backend | Worker | Scheduler |
| --- | --- | --- | --- |
| < 50 rps | 2 | 2 | 1 |
| 50–200 rps | 4 | 4 | 1 |
| 200–1000 rps | 8+ (HPA) | 8+ (HPA) | 1 |
| Sustained > 1000 rps | shard Postgres reads, consider read replicas | scale worker concurrency + replicas | 1 |

## Incident response

1. Declare severity (SEV-1 outage, SEV-2 degraded, SEV-3 minor).
2. Post to incident channel with impact summary.
3. Mitigate first, root-cause second.
4. Capture timeline in incident doc; hold blameless review within 5 days.
5. File follow-up issues for every action item.