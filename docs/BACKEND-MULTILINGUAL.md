# Backend — Multilingual Communication (Phase 5)

This module extends existing Campaign and Disaster entities with AI
translation, TTS audio, and AI content variants. It does NOT introduce a
new parent entity; every translation lives inside the Campaign or Disaster
it belongs to.

## Design rules

1. One multilingual bundle per parent (`campaigns` or `disasters`).
2. Reuse the existing media pipeline for TTS audio — audio is stored as a
   regular `media_assets` row and referenced by id.
3. Reuse the existing AI gateway (`ai.service` on the frontend, whichever
   provider you wire on the backend) for both translation and variants.
4. Public routes (`/public/campaigns/:token`, `/public/alerts/:slug`) must
   return translated fields when a `language` query param is supplied and
   fall back to the source language otherwise.

## Endpoints

All endpoints are prefixed with the parent's REST root
(`/v1/campaigns/{id}` or `/v1/disasters/{id}`). The rest of the path is
identical. Only Super Admin and Campaign Manager may write; all
authenticated roles may read.

| Method | Path | Purpose |
|-------|------|--------|
| GET | `/multilingual` | Fetch the bundle (all entries + audio + variants). |
| POST | `/multilingual/translate` | Generate translations for `targetLanguages`. |
| POST | `/multilingual/translate/{lang}/regenerate` | Regenerate one language. |
| PATCH | `/multilingual/translations/{lang}` | Manual edit / publish. |
| DELETE | `/multilingual/translations/{lang}` | Remove entry (source language rejected). |
| POST | `/multilingual/translations/{lang}/audio` | Generate/replace TTS audio. |
| DELETE | `/multilingual/translations/{lang}/audio` | Remove audio only. |
| POST | `/multilingual/translations/{lang}/variants` | Generate an AI variant. |

Public read paths already exist and gain optional translated fields:

- `GET /v1/public/campaigns/{token}?language=hi`
- `GET /v1/public/alerts/{slug}?language=hi`

Both should return the translated `title`, `description`/`content`,
`safetyInstructions` (disasters), and an `audioUrl` when the entry has
generated audio.

## RBAC

Reuses existing permissions — no new ones added:

- `translation:use` — required for translate/regenerate/edit/delete.
- `ai:generate` — required for TTS and variant generation.
- `content:edit` — required for manual edits and publishing.

Public alert and campaign routes remain unauthenticated.

## Database

### `content_translations`

| Column | Type | Notes |
|-------|------|------|
| id | uuid PK | |
| parent_type | enum('campaign','disaster') | |
| parent_id | uuid | FK enforced application-side per parent_type. |
| language | text | ISO 639-1 code, lowercase. |
| title | text | nullable |
| content | text | nullable while status='draft' |
| safety_instructions | text | disasters only, nullable |
| status | enum('draft','generated','edited','published') | |
| audio_media_id | uuid | FK → `media_assets.id` nullable |
| variants | jsonb | `{ summary: "...", emergency_sms: "...", ... }` |
| updated_at | timestamptz | |
| updated_by | uuid | FK → users.id nullable |

Unique constraint: `(parent_type, parent_id, language)`.

### GRANTs (Data API)

```sql
GRANT SELECT, INSERT, UPDATE, DELETE ON public.content_translations TO authenticated;
GRANT ALL ON public.content_translations TO service_role;
-- No anon grant: public read is served through /v1/public/... server code
-- using the service client, not direct PostgREST.
```

## Alembic migration (sketch)

```python
def upgrade() -> None:
    op.create_table(
        "content_translations",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("parent_type", sa.Enum("campaign", "disaster", name="ml_parent_type"), nullable=False),
        sa.Column("parent_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("language", sa.String(8), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("content", sa.Text()),
        sa.Column("safety_instructions", sa.Text()),
        sa.Column("status", sa.Enum("draft", "generated", "edited", "published", name="ml_status"), nullable=False, server_default="draft"),
        sa.Column("audio_media_id", pg.UUID(as_uuid=True), sa.ForeignKey("media_assets.id", ondelete="SET NULL")),
        sa.Column("variants", pg.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.UniqueConstraint("parent_type", "parent_id", "language"),
    )
    op.create_index("idx_ml_parent", "content_translations", ["parent_type", "parent_id"])
```

## SQLAlchemy model (sketch)

```python
class ContentTranslation(Base):
    __tablename__ = "content_translations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_type: Mapped[MlParentType]
    parent_id: Mapped[UUID]
    language: Mapped[str] = mapped_column(String(8))
    title: Mapped[str | None]
    content: Mapped[str | None]
    safety_instructions: Mapped[str | None]
    status: Mapped[MlStatus] = mapped_column(default=MlStatus.draft)
    audio_media_id: Mapped[UUID | None] = mapped_column(ForeignKey("media_assets.id", ondelete="SET NULL"))
    variants: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime]
    updated_by: Mapped[UUID | None]
```

## AI integration points

- **Translation**: `POST /translate` and `regenerate` call the AI gateway
  chat endpoint with a system prompt that preserves variables (`{{name}}`,
  URLs, dates) and returns pure translated text.
- **TTS**: `POST /audio` calls the gateway `/audio/speech` endpoint using
  the translated `content` (or edited version), stores the returned audio
  through the existing media pipeline, and links the resulting media id.
  Audio always reflects the latest saved content — replace when the
  translation changes.
- **Variants**: `POST /variants` calls the gateway chat endpoint with a
  variant-specific system prompt (SMS length limits, poster line breaks,
  radio pacing) and writes the result into `variants[kind]`.

Rate limits and credit-exhaustion errors from the gateway must be
surfaced to the API caller as `429` / `402` so the frontend can show the
existing error toast.

## Multilingual public delivery

Public routes accept `?language=xx`:

1. Look up the parent by token / slug.
2. Load the matching translation entry where
   `status IN ('generated','edited','published')`.
3. Fall back to the source language when the requested entry is missing.
4. Return `audioUrl` when `audio_media_id` is set.
5. The frontend caches the last selected language per parent in
   `localStorage` (`multilingua:public-lang:{token|slug}`), so the same
   viewer sees their preferred language on the next scan.

## Notification integration

No new transport. When a translation is published or audio is
regenerated, the existing notification service emits
`translation.published` and `translation.audio_ready` events consumed by
the current in-app notification centre.
