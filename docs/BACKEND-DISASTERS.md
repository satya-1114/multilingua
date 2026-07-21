# Backend — Disaster Management (Phase 4)

The Disaster module is the **operational envelope** that references
Campaigns, Volunteers, QR codes and Notifications. It MUST NOT duplicate
those modules — it stores foreign keys and delegates writes.

## RBAC

| Permission          | Super Admin | Campaign Manager | Volunteer | Viewer |
| ------------------- | ----------- | ---------------- | --------- | ------ |
| `disaster:view`     | ✓           | ✓                | ✓ (assigned only) | ✓ (public only) |
| `disaster:manage`   | ✓           | ✓                |           |        |
| `disaster:assign`   | ✓           | ✓                |           |        |

Enforce on every authenticated endpoint. `Volunteer` reads must be scoped
by `assigned_volunteer_ids`; `Viewer` reads must be scoped to
`is_public = true AND status IN ('preparing','active','resolved')`.

## Endpoints (mount under `/v1`, existing auth stack)

Authenticated:

| Method | Path                                                     | Permission           |
| ------ | -------------------------------------------------------- | -------------------- |
| GET    | `/v1/disasters`                                          | `disaster:view`      |
| GET    | `/v1/disasters/stats`                                    | `disaster:view`      |
| GET    | `/v1/disasters/{id}`                                     | `disaster:view`      |
| POST   | `/v1/disasters`                                          | `disaster:manage`    |
| PATCH  | `/v1/disasters/{id}`                                     | `disaster:manage`    |
| PATCH  | `/v1/disasters/{id}/status`                              | `disaster:manage`    |
| DELETE | `/v1/disasters/{id}`                                     | `disaster:manage`    |
| GET    | `/v1/disasters/{id}/activity`                            | `disaster:view`      |
| GET    | `/v1/disasters/{id}/volunteers`                          | `disaster:view`      |
| POST   | `/v1/disasters/{id}/volunteers`                          | `disaster:assign`    |
| DELETE | `/v1/disasters/{id}/volunteers/{volunteerId}`            | `disaster:assign`    |
| GET    | `/v1/disasters/{id}/campaigns`                           | `disaster:view`      |
| POST   | `/v1/disasters/{id}/campaigns`  `{ campaignId }`         | `disaster:manage`    |
| DELETE | `/v1/disasters/{id}/campaigns/{campaignId}`              | `disaster:manage`    |
| POST   | `/v1/disasters/{id}/campaigns/emergency`                 | `disaster:manage` + `campaign:create` |

Public (no auth):

| Method | Path                              | Purpose                         |
| ------ | --------------------------------- | ------------------------------- |
| GET    | `/v1/public/alerts/{slug}?language=` | Localised public alert payload. |

## Behavioural rules

1. **Volunteer assignment** — MUST reuse the existing `tasks` service. The
   endpoint creates a `volunteer_task` (task type = `disaster_response`,
   `disaster_id` FK) and returns the derived `DisasterVolunteerAssignment`
   projection. Do not build a parallel assignment table.
2. **Emergency campaign creation** — MUST call the existing Campaign
   creation service (`type = emergency`, `priority = critical`), then
   attach it via `disaster_campaigns`. The Campaign QR module auto-issues
   a QR through its existing pipeline; no duplicate QR code is created.
3. **Notifications** — reuse the existing notification service. Fire the
   following on state changes:
   - `disaster.status_changed` → notify assigned volunteers + subscribers.
   - `disaster.volunteer_assigned` → notify the volunteer (in-app + push).
   - `disaster.campaign_attached` → notify campaign owner.
   No new notification transport.
4. **Public endpoint** MUST 404 when `is_public = false` or
   `status = archived`. Increment a public view counter; do NOT store PII.
5. **Slug** is auto-generated on create (`slugify(title) + short-hash`) if
   not provided. Uniqueness enforced at the DB level.

## Response shapes

Mirror the TypeScript interfaces in `src/types/disaster.ts`. All responses
wrapped in the existing `ApiResponse<T>` / `ApiListResponse<T>` envelope.

## Data model (Alembic migration)

```sql
CREATE TYPE disaster_category AS ENUM (
  'flood','cyclone','earthquake','fire','heatwave',
  'pandemic','landslide','tsunami','other'
);
CREATE TYPE disaster_severity AS ENUM ('low','medium','high','critical');
CREATE TYPE disaster_status   AS ENUM ('preparing','active','resolved','archived');

CREATE TABLE disasters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(24) NOT NULL UNIQUE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    category disaster_category NOT NULL,
    severity disaster_severity NOT NULL,
    status   disaster_status   NOT NULL DEFAULT 'preparing',
    affected_areas TEXT[] NOT NULL DEFAULT '{}',
    start_date TIMESTAMPTZ NOT NULL,
    end_date   TIMESTAMPTZ,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    radius_km DOUBLE PRECISION,
    region VARCHAR(120),
    safety_instructions TEXT,
    required_volunteers INTEGER NOT NULL DEFAULT 0,
    languages TEXT[] NOT NULL DEFAULT '{"en"}',
    is_public BOOLEAN NOT NULL DEFAULT true,
    public_slug VARCHAR(140) UNIQUE,
    organization_id UUID REFERENCES organizations(id),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_disasters_status_start ON disasters(status, start_date DESC);
CREATE INDEX idx_disasters_public_slug  ON disasters(public_slug) WHERE is_public;

CREATE TABLE disaster_emergency_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disaster_id UUID NOT NULL REFERENCES disasters(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    role VARCHAR(80),
    organization VARCHAR(120),
    phone VARCHAR(32) NOT NULL,
    email VARCHAR(120)
);

CREATE TABLE disaster_shelters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disaster_id UUID NOT NULL REFERENCES disasters(id) ON DELETE CASCADE,
    name VARCHAR(160) NOT NULL,
    address TEXT NOT NULL,
    capacity INTEGER,
    contact_phone VARCHAR(32),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION
);

CREATE TABLE disaster_medical_centers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disaster_id UUID NOT NULL REFERENCES disasters(id) ON DELETE CASCADE,
    name VARCHAR(160) NOT NULL,
    address TEXT NOT NULL,
    phone VARCHAR(32),
    services TEXT[] NOT NULL DEFAULT '{}',
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION
);

CREATE TABLE disaster_media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disaster_id UUID NOT NULL REFERENCES disasters(id) ON DELETE CASCADE,
    type VARCHAR(8) NOT NULL,               -- 'image' | 'video'
    url TEXT NOT NULL,
    caption TEXT,
    poster TEXT
);

CREATE TABLE disaster_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disaster_id UUID NOT NULL REFERENCES disasters(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    url TEXT NOT NULL,
    mime_type VARCHAR(80),
    size_bytes BIGINT
);

CREATE TABLE disaster_campaigns (
    disaster_id UUID NOT NULL REFERENCES disasters(id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    attached_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    attached_by UUID REFERENCES users(id),
    PRIMARY KEY (disaster_id, campaign_id)
);

-- Assignments are DERIVED from volunteer_tasks (existing table) using a
-- FK column added in the same migration:
ALTER TABLE volunteer_tasks
  ADD COLUMN disaster_id UUID REFERENCES disasters(id) ON DELETE SET NULL;
CREATE INDEX idx_tasks_disaster ON volunteer_tasks(disaster_id) WHERE disaster_id IS NOT NULL;

CREATE TABLE disaster_activity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disaster_id UUID NOT NULL REFERENCES disasters(id) ON DELETE CASCADE,
    type VARCHAR(40) NOT NULL,
    message TEXT NOT NULL,
    actor VARCHAR(120) NOT NULL,
    at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    meta JSONB
);
CREATE INDEX idx_disaster_activity ON disaster_activity(disaster_id, at DESC);
```

## FastAPI / SQLAlchemy models (excerpt)

```python
class Disaster(Base):
    __tablename__ = "disasters"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(24), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[DisasterCategoryEnum]
    severity: Mapped[DisasterSeverityEnum]
    status:   Mapped[DisasterStatusEnum] = mapped_column(default="preparing")
    affected_areas: Mapped[list[str]] = mapped_column(ARRAY(String))
    start_date: Mapped[datetime]
    end_date: Mapped[datetime | None]
    latitude: Mapped[float | None]
    longitude: Mapped[float | None]
    radius_km: Mapped[float | None]
    region: Mapped[str | None] = mapped_column(String(120))
    safety_instructions: Mapped[str | None] = mapped_column(Text)
    required_volunteers: Mapped[int] = mapped_column(default=0)
    languages: Mapped[list[str]] = mapped_column(ARRAY(String), default=lambda: ["en"])
    is_public: Mapped[bool] = mapped_column(default=True)
    public_slug: Mapped[str | None] = mapped_column(String(140), unique=True)
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id"))
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
```

`code` is generated as `DIS-YYYY-####` on insert. Use a Postgres sequence
or count-based generator, matching the existing `CMP-YYYY-####` pattern.

## Map integration (deferred)

`latitude`, `longitude`, `radius_km`, and per-resource lat/lng are stored
now but no map provider is bound. When adding a provider (Leaflet /
Mapbox), keep it dynamically imported behind `<ClientOnly>` per the
project's SSR guidance — the data model requires no schema change.
