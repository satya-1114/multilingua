# Platform Backend

Production-oriented FastAPI service for the enterprise communication platform.

## Stack

- Python 3.12, FastAPI, SQLAlchemy 2, Alembic
- PostgreSQL 16, Redis 7, RabbitMQ 3
- Celery workers for AI, translation, delivery, analytics, retries
- JWT auth with refresh rotation, RBAC, per-workspace scoping
- OpenAI + IndicTrans2 (optional local fallback)

## Layout

```
backend/
  app/
    api/v1/           REST endpoints (one router per domain)
    core/             config, logging, exceptions, response envelope
    database/         SQLAlchemy engine, session, mixins
    dependencies/     FastAPI dependencies (auth, db, pagination)
    middleware/       request context, security headers, rate limiting
    models/           SQLAlchemy ORM models
    repositories/     data-access layer
    schemas/          Pydantic v2 DTOs (mirror frontend contracts)
    security/         password hashing, JWT, RBAC
    services/         business logic (AI, translation, comms, storage)
    workers/          Celery app + task modules
  alembic/            database migrations
  tests/              pytest suites
  Dockerfile          production image
  docker-compose.yml  local stack (api, worker, postgres, redis, rabbitmq, nginx)
  nginx.conf          reverse proxy
  main.py             ASGI entry
```

## Quickstart

```
cp .env.example .env
docker compose up --build
```

Once healthy:

- Swagger: http://localhost:8000/docs
- ReDoc:   http://localhost:8000/redoc
- Health:  http://localhost:8000/api/v1/system/health

Run migrations:

```
docker compose exec api alembic upgrade head
```

## Frontend wiring

Point the frontend at the API:

```
# frontend .env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_MOCK_MODE=false
```

Response envelopes match `src/api/contracts/index.ts` — `ApiResponse<T>`,
`ApiListResponse<T>`, `ApiFailure` — so services swap over without adapter
changes.
