# Backend — Campaign QR Codes (Phase 3)

QR codes are an **optional extension of a Campaign**, not a standalone
entity. Each campaign has 0 or 1 QR code. Only Super Admin and Campaign
Manager can manage them; Viewer / Volunteer can view / scan.

## RBAC

- `campaign_qr:view` — Super Admin, Campaign Manager, Viewer, Volunteer
- `campaign_qr:manage` — Super Admin, Campaign Manager

## Endpoints (mount under existing `/v1`)

Authenticated (require session + `campaign_qr:*`):

| Method | Path                                            | Permission              | Purpose                                             |
| ------ | ----------------------------------------------- | ----------------------- | --------------------------------------------------- |
| GET    | `/v1/campaigns/{id}/qr`                         | `campaign_qr:view`      | Return the campaign's QR, or `data: null`.          |
| POST   | `/v1/campaigns/{id}/qr`                         | `campaign_qr:manage`    | Generate the QR (409 if it already exists).         |
| POST   | `/v1/campaigns/{id}/qr/regenerate`              | `campaign_qr:manage`    | Rotate token, bump `version`, invalidate old code.  |
| PATCH  | `/v1/campaigns/{id}/qr`                         | `campaign_qr:manage`    | `{ status: "active" \| "disabled" }`.               |
| GET    | `/v1/campaigns/{id}/qr/analytics`               | `campaign_qr:view`      | Aggregated analytics (`QrAnalytics`).               |
| GET    | `/v1/campaigns/{id}/qr/scans?page&pageSize`     | `campaign_qr:view`      | Paginated raw scan events.                          |

Public (no auth — mount as an unauthenticated router):

| Method | Path                                     | Purpose                                                            |
| ------ | ---------------------------------------- | ------------------------------------------------------------------ |
| GET    | `/v1/public/campaigns/{token}?language=` | Return `PublicCampaign`, increment scan counters, record analytics.|

The public endpoint MUST:

1. Reject if QR `status = disabled` (404) or campaign is not published.
2. Record a `qr_scan` row per hit; mark `is_unique = true` when the
   `(qr_id, visitor_hash)` pair is new. `visitor_hash` = SHA-256 of
   `ip + user_agent + daily_salt`. Do NOT store raw IP or UA.
3. Derive `country` from IP (GeoLite / CF header) and `device_type` from
   the UA (mobile / tablet / desktop / unknown).
4. Trust only the `language` query param for `language_selected`.

## Response shapes

Mirror the TypeScript interfaces in `src/types/qr.ts` — the frontend is the
contract. All responses wrapped in the existing `ApiResponse<T>` envelope.

## Data model (Alembic migration)

```sql
CREATE TABLE campaign_qr_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL UNIQUE REFERENCES campaigns(id) ON DELETE CASCADE,
    token VARCHAR(24) NOT NULL UNIQUE,          -- opaque, URL-safe
    target_url TEXT NOT NULL,                   -- absolute public URL
    status VARCHAR(16) NOT NULL DEFAULT 'active', -- active | disabled
    version INTEGER NOT NULL DEFAULT 1,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_qr_codes_token ON campaign_qr_codes(token);

CREATE TABLE qr_scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    qr_id UUID NOT NULL REFERENCES campaign_qr_codes(id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    country VARCHAR(2),
    device_type VARCHAR(16) NOT NULL DEFAULT 'unknown',
    language VARCHAR(8),
    visitor_hash CHAR(64) NOT NULL,
    is_unique BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX idx_qr_scans_qr_at ON qr_scans(qr_id, at DESC);
CREATE UNIQUE INDEX idx_qr_scans_unique_visitor
  ON qr_scans(qr_id, visitor_hash) WHERE is_unique = true;
```

## FastAPI / SQLAlchemy models

```python
class CampaignQrCode(Base):
    __tablename__ = "campaign_qr_codes"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), unique=True)
    token: Mapped[str] = mapped_column(String(24), unique=True)
    target_url: Mapped[str]
    status: Mapped[str] = mapped_column(default="active")
    version: Mapped[int] = mapped_column(default=1)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

class QrScan(Base):
    __tablename__ = "qr_scans"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    qr_id: Mapped[UUID] = mapped_column(ForeignKey("campaign_qr_codes.id", ondelete="CASCADE"))
    campaign_id: Mapped[UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    at: Mapped[datetime] = mapped_column(default=func.now())
    country: Mapped[str | None] = mapped_column(String(2))
    device_type: Mapped[str] = mapped_column(default="unknown")
    language: Mapped[str | None] = mapped_column(String(8))
    visitor_hash: Mapped[str] = mapped_column(String(64))
    is_unique: Mapped[bool] = mapped_column(default=False)
```

## Token generation

`secrets.token_urlsafe(12)` → 16-char URL-safe token. Regenerate updates
`token` (and thus `target_url`), bumps `version`, keeps `qr_scans` history.

## `target_url`

`${PUBLIC_BASE_URL}/public/campaigns/{token}` — must match the frontend
route `src/routes/public.campaigns.$token.tsx`. Expose `PUBLIC_BASE_URL`
as an environment variable, defaulting to the deployed frontend origin.
