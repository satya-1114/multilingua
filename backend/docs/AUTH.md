# Authentication & Security Architecture

## Authentication Flow

```
Client                                Backend
  │  POST /auth/register              │
  │ ────────────────────────────────► │
  │                                   │ ─── validate policy ───┐
  │                                   │ ─── hash password  ────┤
  │                                   │ ─── create user + role │
  │                                   │ ─── password history   │
  │                                   │ ─── verification token │
  │ ◄─── { user, token, verify… } ─── │
  │                                   │
  │  POST /auth/login                 │
  │ ────────────────────────────────► │
  │                                   │ ─── check lockout ─────┐
  │                                   │ ─── verify credentials │
  │                                   │ ─── record attempt     │
  │                                   │ ─── mint JWT pair      │
  │                                   │ ─── create session     │
  │ ◄─── { user, accessToken, … } ─── │
  │                                   │
  │  Bearer <access> on every call    │
  │ ────────────────────────────────► │
  │                                   │
  │  POST /auth/refresh (rotation)    │
  │ ────────────────────────────────► │
  │                                   │ ─── revoke prior token │
  │                                   │ ─── mint new pair      │
  │ ◄─── new pair ─────────────────── │
```

## JWT Lifecycle

- **Access token** — 30 min, `type=access`, carries `sub`, `ws`, `roles`, `jti`.
- **Refresh token** — 14 days (28 with Remember-Me), `type=refresh`. Hashed
  (SHA-256) into `sessions.refresh_token_hash`.
- **Rotation** — every refresh revokes the prior session row and issues a fresh
  pair. Reuse of a rotated token triggers a **cascade revoke** on every active
  session for that user and a `refresh.reuse_detected` critical security event.

## Session Lifecycle

`sessions` rows persist `user_id`, hashed refresh, IP, user-agent, expiry, and
`revoked_at`. Devices are tracked in `trusted_devices` keyed by a client-issued
`deviceId` (stored in `localStorage`). Cleanup: `auth.cleanup_inactive_sessions`
removes revoked/expired rows older than 30 days.

## RBAC

Static grants live in `app.security.rbac.PERMISSIONS` keyed by role. The
resolver in `app.dependencies.rbac.resolve_permissions` composes and caches the
flattened grant set per user (60 s TTL). Middleware:

- `permission_required(*perms)` — enforces all listed permissions
- `any_permission(perms)` — enforces at least one
- `role_required(*roles)` — role-based gate
- `require_workspace()` — resolves and verifies the caller's active workspace
- `require_organization()` — enforces `X-Organization-Id`
- `check_ownership(...)` — resource-owner validation

`super_admin` and `org_admin` are treated as elevated for ownership and
workspace access checks.

## Password Policy

Configurable via `app.security.password_policy.PasswordPolicy`. Default:

| Rule | Value |
| ---- | ----- |
| Minimum length | 10 |
| Uppercase / lowercase / digit / symbol | required |
| Reuse window | last 5 hashes |
| Common tokens | blocked (`password`, `qwerty`, `welcome`, `admin`) |
| Max age | 180 days |

Strength score is a 0-100 blend of entropy bits + character-class variety.

## Account Lockout

Five failed login attempts within any window lock the account for 15 minutes.
Admins can force a lock via `POST /security/users/{id}/lock` and clear it via
`POST /security/users/{id}/unlock`. Both actions emit audit + security events.

## MFA

Provider-agnostic scaffolding under `app.services.mfa`:

- `MfaProvider` protocol — implement per factor (TOTP, SMS, email)
- `register_provider()` — wire concrete provider at startup
- `enroll_factor / verify_factor / disable_factor` — lifecycle
- Recovery codes: 10 single-use codes stored as SHA-256 hashes

## Security Center

`GET /security/overview` returns score, account status, active sessions,
devices, recent logins, and warning-or-critical alerts.

## Audit

Every security-sensitive action writes to `audit_logs` (search + export ready)
plus a lightweight `security_events` row for the security-center feed.

## Frontend Wiring

`src/api/auth.backend.ts` and `src/api/backend.ts` expose typed adapters
that call these endpoints directly. Toggle by setting:

```
VITE_MOCK_MODE=false
VITE_API_BASE_URL=https://your-api-host/api/v1
```

`AuthContext` remains the single source of truth for the UI — swap the
underlying `authService` call sites to `authBackend` in whichever order suits
your rollout.
