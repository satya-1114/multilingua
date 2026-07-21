from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    APP_SECRET_KEY: str = Field(default="dev-secret-change-me", min_length=16)
    APP_ACCESS_TOKEN_MINUTES: int = 30
    APP_REFRESH_TOKEN_DAYS: int = 14

    DATABASE_URL: str = "postgresql+psycopg2://platform:platform@localhost:5432/platform"
    DATABASE_URL_ASYNC: str = "postgresql+asyncpg://platform:platform@localhost:5432/platform"

    REDIS_URL: str = "redis://localhost:6379/0"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672//"

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8080"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    LOVABLE_API_KEY: str = ""
    LOVABLE_AI_MODEL: str = "google/gemini-3-flash-preview"

    AI_PROVIDER: str = ""            # "openai" | "lovable" | "" (auto)
    AI_RATE_LIMIT_PER_MINUTE: int = 60

    # ---- AI Intelligence Platform (Phase 10) --------------------------
    # Free-first: Gemini > Ollama > HuggingFace > Watsonx > OpenAI.
    # Any provider left blank is skipped by the auto-bootstrap.
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-flash-latest"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"
    OLLAMA_ENABLED: bool = True  # auto-detected on /api/tags probe

    HUGGINGFACE_API_KEY: str = ""
    HUGGINGFACE_MODEL: str = "mistralai/Mistral-7B-Instruct-v0.3"

    WATSONX_API_KEY: str = ""
    WATSONX_PROJECT_ID: str = ""
    WATSONX_URL: str = "https://us-south.ml.cloud.ibm.com"
    WATSONX_MODEL: str = "ibm/granite-13b-chat-v2"

    # Fernet key for workspace AI secret storage. Derived from APP_SECRET_KEY
    # when unset — override in production to allow key rotation.
    AI_SECRET_ENCRYPTION_KEY: str = ""

    AI_DEFAULT_TEMPERATURE: float = 0.4
    AI_DEFAULT_MAX_TOKENS: int = 1024

    TRANSLATION_BACKEND: str = "ai"  # "ai" | "indictrans2"
    INDICTRANS2_MODEL: str = "ai4bharat/indictrans2-en-indic-1B"

    FCM_SERVER_KEY: str = ""

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "no-reply@example.com"

    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM: str = ""

    STORAGE_BACKEND: str = "local"
    STORAGE_LOCAL_ROOT: str = "/var/lib/platform/uploads"
    S3_BUCKET: str = ""
    S3_REGION: str = ""
    S3_ENDPOINT: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""

    RATE_LIMIT_PER_MINUTE: int = 240

    # --- Phase 9.1 Security Hardening ---------------------------------
    # Rate-limiting policies (requests / seconds).
    RATE_LIMIT_AUTH_PER_MINUTE: int = 5
    RATE_LIMIT_PASSWORD_RESET_PER_HOUR: int = 3
    RATE_LIMIT_PUBLIC_PER_MINUTE: int = 100
    RATE_LIMIT_ADMIN_PER_MINUTE: int = 50
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_TRUST_FORWARDED: bool = True

    # Security headers.
    SECURITY_CSP_ENFORCE: bool = False
    SECURITY_CSP_POLICY: str = (
        "default-src 'self'; "
        "img-src 'self' data: blob: https:; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "connect-src 'self' https:; "
        "font-src 'self' data: https:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    SECURITY_HSTS_MAX_AGE: int = 63072000
    SECURITY_HSTS_PRELOAD: bool = True
    SECURITY_FRAME_OPTIONS: str = "DENY"
    SECURITY_REFERRER_POLICY: str = "strict-origin-when-cross-origin"
    SECURITY_PERMISSIONS_POLICY: str = (
        "geolocation=(), camera=(), microphone=(), payment=()"
    )

    # Webhook signing.
    WEBHOOK_SIGNING_SECRET: str = ""
    WEBHOOK_TIMESTAMP_TOLERANCE_S: int = 300
    WEBHOOK_NONCE_TTL_S: int = 600

    # File uploads.
    UPLOAD_MAX_BYTES: int = 25 * 1024 * 1024
    UPLOAD_ALLOWED_MIME: str = (
        "image/png,image/jpeg,image/webp,image/gif,"
        "application/pdf,text/plain,text/csv,"
        "application/vnd.ms-excel,"
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    UPLOAD_ALLOWED_EXT: str = (
        ".png,.jpg,.jpeg,.webp,.gif,.pdf,.txt,.csv,.xls,.xlsx,.doc,.docx"
    )
    UPLOAD_BLOCKED_EXT: str = (
        ".exe,.dll,.bat,.cmd,.sh,.ps1,.msi,.scr,.jar,.php,.py,.rb,.js,.html,.htm,.svg"
    )

    FEATURE_ANALYTICS: bool = True
    FEATURE_SEARCH: bool = True
    FEATURE_UPLOADS: bool = True
    FEATURE_AI: bool = True
    MAINTENANCE_MODE: bool = False

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def upload_allowed_mime(self) -> set[str]:
        return {m.strip().lower() for m in self.UPLOAD_ALLOWED_MIME.split(",") if m.strip()}

    @property
    def upload_allowed_ext(self) -> set[str]:
        return {e.strip().lower() for e in self.UPLOAD_ALLOWED_EXT.split(",") if e.strip()}

    @property
    def upload_blocked_ext(self) -> set[str]:
        return {e.strip().lower() for e in self.UPLOAD_BLOCKED_EXT.split(",") if e.strip()}

    def validate_production(self) -> list[str]:
        """Return a list of misconfiguration warnings for the current env."""
        warnings: list[str] = []
        # Environment-agnostic — dev secrets are always weak.
        if len(self.APP_SECRET_KEY) < 32:
            warnings.append(
                "APP_SECRET_KEY is shorter than 32 chars — HS256 JWTs are weak"
            )
        if self.APP_SECRET_KEY.lower() in {
            "dev-secret-change-me",
            "changeme",
            "secret",
            "test-secret-that-is-long-enough",
        }:
            warnings.append("APP_SECRET_KEY is a known default/test value")
        if self.APP_ENV == "production":
            if self.APP_SECRET_KEY == "dev-secret-change-me":
                warnings.append("APP_SECRET_KEY must be rotated in production")
            if self.APP_DEBUG:
                warnings.append("APP_DEBUG must be false in production")
            if not self.DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg2://")):
                warnings.append("DATABASE_URL should point at a managed PostgreSQL")
            if not self.WEBHOOK_SIGNING_SECRET:
                warnings.append(
                    "WEBHOOK_SIGNING_SECRET is empty — outbound webhooks unsigned"
                )
            if not self.SECURITY_CSP_ENFORCE:
                warnings.append(
                    "SECURITY_CSP_ENFORCE is off — CSP is report-only in production"
                )
        return warnings


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
