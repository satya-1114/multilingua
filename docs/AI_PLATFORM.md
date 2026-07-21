# AI Intelligence Platform

Milestone 10 wires the AI Workspace, Prompt Library, History and Workspace
Settings to a real FastAPI backend with a **Free-First** provider stack.

## Provider priority (auto-selected on boot)

1. **Google Gemini** — `GEMINI_API_KEY` (default free tier).
2. **Ollama** — local `OLLAMA_BASE_URL` (default `http://localhost:11434`).
3. **Hugging Face** — free inference API via `HUGGINGFACE_API_KEY`.
4. **IBM watsonx.ai** — `WATSONX_API_KEY` + `WATSONX_PROJECT_ID`.
5. **OpenAI** — `OPENAI_API_KEY` (optional, never default).

Workspaces can override the global provider/model/API key from
`/ai/settings`. Per-workspace API keys are stored **encrypted at rest**
with Fernet (`AI_SECRET_ENCRYPTION_KEY`) and never returned to the
browser — the API only echoes a masked preview and a `hasApiKey` flag.

## Endpoints

- `POST /api/v1/ai/generate` — run a generation. Auto-logs into `ai_history`.
- `GET  /api/v1/ai/providers` — list active providers.
- `GET/POST/PATCH/DELETE /api/v1/ai/prompts` + `/duplicate`, `/favorite`, `/use`.
- `GET/DELETE /api/v1/ai/history` — searchable execution log.
- `GET/PUT /api/v1/ai/workspace-settings` — provider config.
- `POST /api/v1/ai/workspace-settings/test` — provider connectivity check.

## Frontend integration

- `src/services/ai.service.ts` — generation + workspace settings.
- `src/services/prompt.service.ts` — Prompt Library CRUD.
- `src/services/history.service.ts` — History list/delete.
- **No silent mock fallback.** A failed real AI request surfaces the
  provider error in the UI toast. Mocks are only used when the frontend
  is explicitly built with `VITE_ENABLE_AI_MOCKS=true` — the AI Workspace
  then shows a visible **“Demo mocks”** badge.
- Prompt Library "Use" hands off the prompt body to `/ai/workspace` via
  `sessionStorage`, preserving the existing routing structure.

## Security

- No provider keys are ever shipped to the browser.
- Workspace keys are encrypted using `AI_SECRET_ENCRYPTION_KEY` (Fernet).
- Provider error messages are scrubbed of `?key=…` query params and
  `Authorization: Bearer …` headers before they reach logs, audit
  records, or the `/workspace-settings/test` response.
- Auth, RBAC and routes are unchanged from Milestone 9.

## Manual real-provider smoke test

Automated tests never require a live provider — external HTTP is mocked
at the `httpx` boundary. To verify a real Gemini flow end-to-end:

1. Log in, open **Settings → AI**.
2. Provider → `Google Gemini (free)`. Model → `gemini-flash-latest`
   (the backend will auto-select the best available `generateContent` model
   from Google's model list).
3. Paste a real Gemini API key (https://aistudio.google.com/app/apikey)
   and click **Save**, then **Test connection**. Expect
   `Connection OK · gemini/<model>`.
4. Go to **AI → Workspace**. Enter “Write a short flood safety alert for
   Chennai residents” and press **Generate**. Expect a real response
   with provider metadata; the “Demo mocks” badge must not be visible.
5. Open **AI → History** and confirm the run is persisted with provider,
   model, tokens, and latency.
6. Open **AI → Prompts**, click **Use** on any prompt, confirm the body
   arrives in the Workspace prompt field.

If **Test connection** fails, the toast shows the normalised provider
error (`invalid_api_key`, `rate_limited`, `provider_unavailable`,
`provider_timeout`) — with the API key stripped from any embedded URL.