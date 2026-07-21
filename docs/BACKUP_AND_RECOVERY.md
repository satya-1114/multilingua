# Backup and Recovery

## What must be backed up

| Store | Contents | Recommended frequency | Retention |
| --- | --- | --- | --- |
| PostgreSQL | Application data | Continuous WAL + daily full | 30 days full, 7 days PITR |
| Redis | Celery broker/result, idempotency store | AOF snapshot hourly | 7 days |
| Object storage (if used) | Uploaded files | Managed replication | Per compliance |
| Kubernetes | ConfigMaps + Secrets | On change (GitOps) | Indefinite in Git |

## Backup strategy

- **Primary**: managed Postgres automated backups (RDS / Cloud SQL /
  equivalent). Enable point-in-time recovery.
- **Secondary**: nightly `pg_dump` archived to object storage with a
  30-day retention lifecycle rule.
- **Redis**: enable AOF `appendfsync everysec`; ship snapshots to
  object storage nightly.
- Verify every backup with a scripted restore into a staging database
  at least weekly. An unverified backup does not exist.

## Restore procedure (Postgres)

1. Provision a new database instance from the latest backup or PITR.
2. Point the target environment's `DATABASE_URL` at the new instance.
3. Run `alembic upgrade head` if the restore target predates current schema.
4. Scale `backend` and `worker` to 0, redirect traffic, then scale up.
5. Confirm `/health/ready` returns 200 and Celery queue drains.
6. Post-restore, run reconciliation queries documented per module.

## Restore procedure (Redis)

Redis is treated as ephemeral for workflow execution:

1. Provision a new Redis instance from the latest AOF snapshot if available.
2. Restart Celery workers; unfinished tasks are safe to retry because
   the runtime enforces idempotency at the execution level (Phase 9.2).
3. Any in-flight webhook idempotency keys older than the snapshot age
   will be re-processed — this is documented behavior.

## Disaster recovery targets

| Metric | Target |
| --- | --- |
| RPO (data loss window) | ≤ 5 minutes (WAL streaming) |
| RTO (time to service) | ≤ 60 minutes for full restore |
| Backup verification | Weekly automated restore into staging |