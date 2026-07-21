# AI, Translation, Communication & Workers

## AI

### Provider abstraction

Every model call goes through `app.services.ai_providers.AIProvider`:

```
ChatMessage[] -> AIProvider.complete/stream -> Generation
```

Concrete providers:

| Provider | When registered |
| -------- | --------------- |
| `openai` | `OPENAI_API_KEY` present |
| `lovable` | `LOVABLE_API_KEY` present — uses `https://ai.gateway.lovable.dev/v1` (OpenAI-compatible) |
| Azure / Anthropic / Gemini / Local | Implement `AIProvider` and call `register_provider(...)`. No callers change. |

Selection order: explicit `provider=` argument → `AI_PROVIDER` env var → first
registered (Lovable when present, else OpenAI).

### Modes

`app.services.ai.generate(mode=...)` supports the full domain preset list:
`generate | rewrite | expand | shorten | summarize | improve | grammar | tone |
subject | headline | simplify | compliance | sentiment | readability |
inclusive | email | sms | whatsapp | circular | emergency | healthcare |
university | ngo | press_release` plus aliases (`email_generation`,
`government_circular`, `press_release_generation`, ...).

### Safety and quotas

- **Prompt injection**: regex-based filter rejects override/jailbreak phrases
- **Length cap**: 8000 characters
- **Rate limit**: `AI_RATE_LIMIT_PER_MINUTE` per caller key (defaults to 60)
- **TTL cache**: identical (mode, prompt, language, tone) tuples reuse for 5 min

### Review

`ai.review(content=..., checks=[...])` runs `compliance`, `sentiment`,
`readability`, `inclusive` in parallel and returns a `qualityScore` 0-100
derived from risk level, inclusive-language issues, and reading grade.

## Translation

`app.services.translation.translate` accepts 12 languages (en, hi, te, ta, kn,
ml, mr, gu, pa, or, bn, ur, as).

- **Detection** — Unicode-range heuristic
- **Backend** — `TRANSLATION_BACKEND=indictrans2` loads
  `INDICTRANS2_MODEL` lazily; failures fall back to the AI provider
- **Cache** — SHA-256 keyed, 1h TTL
- **Glossary** — `register_glossary_term(term, {lang: replacement})` enforced post-translate
- **Batch** — `translate_batch(items, target_language, concurrency=4)`
- **Compare** — returns two candidates plus the higher-confidence pick

## Communication

`app.services.communication` exposes a `CommunicationProvider` protocol and
registers concrete providers at import time. Every provider returns a
`ProviderResult` with `status`, `provider`, `providerMessageId`, `errorCode`,
`errorMessage`.

| Channel | Provider | Requirements |
| ------- | -------- | ------------ |
| email | SMTP | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` |
| sms | Twilio | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM` |
| whatsapp | Twilio | same as SMS (prefixed with `whatsapp:`) |
| push | FCM | `FCM_SERVER_KEY` |
| webhook | HTTP + optional HMAC | `metadata.url` + optional `metadata.secret` |

Unconfigured providers return `status="skipped"` and never raise, so campaign
execution proceeds gracefully in dev.

## Template Engine

`{{ path.to.var }}`, `{{ var|default:fallback }}`, `{{ var|upper|lower|title|trim }}`,
and `{% if var %}...{% endif %}`. `render(body, vars)` returns
`(text, missing_variables)`; `validate(body, vars)` returns variable coverage.
Language-aware fallback: campaign execution prefers a template matching the
recipient's `language`, then falls back to `en`.

## Campaign Execution

`services/campaign_execution.publish` is the single entry point. It:

1. Validates the campaign is `approved` or `scheduled`
2. Loads active recipients from `campaign_audience`
3. For each channel, creates a `Delivery` row plus one `DeliveryRecipient`
   per recipient (skipping those missing an address or template variables)
4. Enqueues `delivery.dispatch` (or `eta=scheduled_at` for future launches)
5. Writes an `audit_logs` row (`action=campaign_published`)

## Celery

`celery_app.py` declares priority queues with dead-letter routing to
`platform.dlx`. Beat schedule:

| Task | Interval | Purpose |
| ---- | -------- | ------- |
| `scheduled.run_scheduled_campaigns` | 60s | Launch due campaigns |
| `cleanup.expired_sessions` | 3600s | Purge revoked sessions |
| `cleanup.expired_verification` | 3600s | Purge dead reset/verify tokens |
| `analytics.aggregate` | 300s | Rollup |

Retries: exponential with jitter (`base * 2^attempt`, capped at 15 min). After
`max_retries`, payloads are written to the structured `task_dead_letter` log.

## Frontend integration

`src/api/engine.backend.ts` — typed adapters for `ai`, `translation`,
`communication`, and `monitoring`. Aggregated in `src/api/backend.ts` under
`backendApi.ai`, `.translation`, `.communication`, `.monitoring`.
