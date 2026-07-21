# Environment Variables

All frontend variables are prefixed with `VITE_` and are exposed to the
client bundle. **Never put secrets in `VITE_*` variables** — they end up
in the browser.

Backend secrets live in the FastAPI service's own environment and never
appear in the frontend build.

## Frontend (`.env`)

| Name                       | Required | Example                            | Purpose                                                       |
| -------------------------- | -------- | ---------------------------------- | ------------------------------------------------------------- |
| `VITE_API_BASE_URL`        | ✅       | `https://api.example.com`          | Root URL for all `apiService` calls                            |
| `VITE_API_VERSION`         | ✅       | `v1`                               | Path segment appended to base URL                              |
| `VITE_ENVIRONMENT`         | ✅       | `production` / `staging` / `dev`   | Displayed in TopBar env badge, read by `environmentService`    |
| `VITE_MOCK_MODE`           | ➖       | `true` / `false`                   | When `true`, services return seeded fixtures                    |
| `VITE_SENTRY_DSN`          | ➖       | `https://…@sentry.io/…`            | Error monitoring                                               |
| `VITE_PUBLIC_APP_NAME`     | ➖       | `Multilingua`                      | Overrides default in meta tags                                 |
| `VITE_QR_BASE_URL`         | ➖       | `https://reachout.example.com`     | Public scan landing root; defaults to `window.location.origin` |

## Backend (`backend/.env`)

| Name                       | Required | Purpose                                              |
| -------------------------- | -------- | ---------------------------------------------------- |
| `DATABASE_URL`             | ✅       | Postgres connection string                            |
| `JWT_SECRET`               | ✅       | HMAC secret for signing access tokens                 |
| `JWT_REFRESH_SECRET`       | ✅       | HMAC secret for signing refresh tokens                |
| `ACCESS_TOKEN_TTL_SECONDS` | ➖       | Default 900                                           |
| `REFRESH_TOKEN_TTL_SECONDS`| ➖       | Default 604800                                        |
| `REDIS_URL`                | ✅       | Cache + async queue                                    |
| `S3_BUCKET`                | ✅       | Object storage for media + exports                     |
| `S3_REGION`, `S3_ENDPOINT` | ✅       | S3-compatible endpoint config                          |
| `OPENAI_API_KEY` (or similar) | ➖    | AI translation / TTS provider (per deployment)         |
| `SENTRY_DSN`               | ➖       | Server-side error monitoring                           |
| `CORS_ALLOW_ORIGINS`       | ✅       | Comma-separated allow list                             |

## Example `.env.example`

```
# Frontend
VITE_API_BASE_URL=http://localhost:8000
VITE_API_VERSION=v1
VITE_ENVIRONMENT=development
VITE_MOCK_MODE=true
VITE_PUBLIC_APP_NAME=Multilingua
# VITE_SENTRY_DSN=
# VITE_QR_BASE_URL=
```

## Rules

1. Never read `process.env.*` from client code — the browser has no
   `process`. Use `import.meta.env.VITE_*`.
2. Access env values through `environmentService` so mock mode and defaults
   are centralised.
3. Rotate `JWT_SECRET` and `JWT_REFRESH_SECRET` on every deploy that
   changes ownership.
4. Never log env values — even in dev.
