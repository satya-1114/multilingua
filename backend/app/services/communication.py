"""Communication providers.

Provider protocol + concrete adapters for SMTP, Twilio SMS, Twilio WhatsApp,
Firebase Cloud Messaging (FCM), and generic webhooks. A registry chooses the
provider by channel kind at dispatch time.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import smtplib
import time
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Protocol

import httpx

from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.logging import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------- protocol


@dataclass
class ProviderMessage:
    to: str
    body: str
    subject: str | None = None
    html: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderResult:
    status: str  # sent | queued | failed | skipped
    provider: str
    provider_message_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class CommunicationProvider(Protocol):
    channel: str  # email | sms | whatsapp | push | webhook
    name: str

    def health(self) -> dict[str, Any]: ...
    def send(self, message: ProviderMessage) -> ProviderResult: ...


# ---------------------------------------------------------------- SMTP


class SmtpEmailProvider:
    channel = "email"
    name = "smtp"

    def __init__(self) -> None:
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_addr = settings.SMTP_FROM

    def health(self) -> dict[str, Any]:
        return {"configured": bool(self.host), "provider": self.name, "channel": self.channel}

    def send(self, message: ProviderMessage) -> ProviderResult:
        if not self.host:
            return ProviderResult(status="skipped", provider=self.name, error_code="not_configured")
        msg = MIMEMultipart("alternative") if message.html else MIMEText(message.body, "plain", "utf-8")
        if isinstance(msg, MIMEMultipart):
            msg.attach(MIMEText(message.body, "plain", "utf-8"))
            msg.attach(MIMEText(message.html or "", "html", "utf-8"))
        msg["Subject"] = message.subject or "(no subject)"
        msg["From"] = self.from_addr
        msg["To"] = message.to
        try:
            with smtplib.SMTP(self.host, self.port, timeout=30) as smtp:
                smtp.ehlo()
                try:
                    smtp.starttls()
                    smtp.ehlo()
                except smtplib.SMTPException:
                    pass
                if self.user:
                    smtp.login(self.user, self.password)
                smtp.sendmail(self.from_addr, [message.to], msg.as_string())
            provider_id = msg.get("Message-ID") or f"smtp-{int(time.time())}"
            return ProviderResult(status="sent", provider=self.name, provider_message_id=provider_id)
        except smtplib.SMTPResponseException as exc:
            return ProviderResult(status="failed", provider=self.name, error_code=str(exc.smtp_code), error_message=exc.smtp_error.decode() if isinstance(exc.smtp_error, bytes) else str(exc.smtp_error))
        except Exception as exc:  # noqa: BLE001
            return ProviderResult(status="failed", provider=self.name, error_code="smtp_error", error_message=str(exc)[:500])


# ---------------------------------------------------------------- Twilio (SMS + WhatsApp)


class TwilioProvider:
    """Handles SMS and WhatsApp when `channel` is set accordingly."""

    def __init__(self, *, channel: str) -> None:
        assert channel in {"sms", "whatsapp"}
        self.channel = channel
        self.name = f"twilio-{channel}"
        self.sid = settings.TWILIO_ACCOUNT_SID
        self.token = settings.TWILIO_AUTH_TOKEN
        self.from_ = settings.TWILIO_FROM

    def _configured(self) -> bool:
        return bool(self.sid and self.token and self.from_)

    def health(self) -> dict[str, Any]:
        return {"configured": self._configured(), "provider": self.name, "channel": self.channel}

    def send(self, message: ProviderMessage) -> ProviderResult:
        if not self._configured():
            return ProviderResult(status="skipped", provider=self.name, error_code="not_configured")
        prefix = "whatsapp:" if self.channel == "whatsapp" else ""
        data = {"From": f"{prefix}{self.from_}", "To": f"{prefix}{message.to}", "Body": message.body}
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.sid}/Messages.json"
        try:
            resp = httpx.post(url, auth=(self.sid, self.token), data=data, timeout=30)
        except httpx.HTTPError as exc:
            return ProviderResult(status="failed", provider=self.name, error_code="network", error_message=str(exc)[:500])
        if resp.status_code >= 400:
            return ProviderResult(
                status="failed", provider=self.name,
                error_code=str(resp.status_code), error_message=resp.text[:500], raw=self._json_or_empty(resp),
            )
        payload = resp.json()
        return ProviderResult(
            status="sent", provider=self.name,
            provider_message_id=payload.get("sid"), raw=payload,
        )

    @staticmethod
    def _json_or_empty(resp: httpx.Response) -> dict[str, Any]:
        try:
            return resp.json()
        except Exception:  # noqa: BLE001
            return {}


# ---------------------------------------------------------------- FCM (Push)


class FcmPushProvider:
    channel = "push"
    name = "fcm"

    def __init__(self) -> None:
        self.server_key = getattr(settings, "FCM_SERVER_KEY", "") or ""

    def health(self) -> dict[str, Any]:
        return {"configured": bool(self.server_key), "provider": self.name, "channel": self.channel}

    def send(self, message: ProviderMessage) -> ProviderResult:
        if not self.server_key:
            return ProviderResult(status="skipped", provider=self.name, error_code="not_configured")
        url = "https://fcm.googleapis.com/fcm/send"
        payload = {
            "to": message.to,
            "notification": {
                "title": message.subject or "Notification",
                "body": message.body,
            },
            "data": message.metadata or {},
        }
        try:
            resp = httpx.post(
                url,
                headers={"Authorization": f"key={self.server_key}", "Content-Type": "application/json"},
                json=payload, timeout=30,
            )
        except httpx.HTTPError as exc:
            return ProviderResult(status="failed", provider=self.name, error_code="network", error_message=str(exc)[:500])
        if resp.status_code >= 400:
            return ProviderResult(status="failed", provider=self.name, error_code=str(resp.status_code), error_message=resp.text[:500])
        data = resp.json()
        return ProviderResult(status="sent", provider=self.name, provider_message_id=str(data.get("multicast_id", "")), raw=data)


# ---------------------------------------------------------------- Webhook


class WebhookProvider:
    channel = "webhook"
    name = "webhook"

    def health(self) -> dict[str, Any]:
        return {"configured": True, "provider": self.name, "channel": self.channel}

    def send(self, message: ProviderMessage) -> ProviderResult:
        url = message.metadata.get("url") or message.to
        if not url:
            return ProviderResult(status="failed", provider=self.name, error_code="missing_url", error_message="No webhook URL")
        secret = message.metadata.get("secret") or ""
        payload = {"body": message.body, "subject": message.subject, "meta": message.metadata}
        body = json.dumps(payload).encode()
        headers = {"Content-Type": "application/json"}
        if secret:
            sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
            headers["X-Signature-SHA256"] = sig
            headers["X-Signature-Timestamp"] = str(int(time.time()))
        try:
            resp = httpx.post(url, content=body, headers=headers, timeout=30)
        except httpx.HTTPError as exc:
            return ProviderResult(status="failed", provider=self.name, error_code="network", error_message=str(exc)[:500])
        if resp.status_code >= 400:
            return ProviderResult(status="failed", provider=self.name, error_code=str(resp.status_code), error_message=resp.text[:500])
        return ProviderResult(status="sent", provider=self.name, provider_message_id=resp.headers.get("X-Request-Id", ""))


# ---------------------------------------------------------------- registry


_registry: dict[str, CommunicationProvider] = {}


def register_provider(provider: CommunicationProvider) -> None:
    _registry[provider.channel] = provider


def _bootstrap() -> None:
    register_provider(SmtpEmailProvider())
    register_provider(TwilioProvider(channel="sms"))
    register_provider(TwilioProvider(channel="whatsapp"))
    register_provider(FcmPushProvider())
    register_provider(WebhookProvider())


_bootstrap()


def get_provider(channel: str) -> CommunicationProvider:
    if channel not in _registry:
        raise DomainError(f"No provider registered for channel: {channel}")
    return _registry[channel]


def provider_health() -> list[dict[str, Any]]:
    return [p.health() for p in _registry.values()]


# ---------------------------------------------------------------- convenience


def send_email(*, to: str, subject: str, body: str, html: str | None = None) -> dict[str, Any]:
    result = get_provider("email").send(ProviderMessage(to=to, subject=subject, body=body, html=html))
    return _to_dict(result)


def send_sms(*, to: str, body: str) -> dict[str, Any]:
    result = get_provider("sms").send(ProviderMessage(to=to, body=body))
    return _to_dict(result)


def send_whatsapp(*, to: str, body: str) -> dict[str, Any]:
    result = get_provider("whatsapp").send(ProviderMessage(to=to, body=body))
    return _to_dict(result)


def send_push(*, to: str, title: str, body: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    result = get_provider("push").send(ProviderMessage(to=to, subject=title, body=body, metadata=data or {}))
    return _to_dict(result)


def send_webhook(*, url: str, body: str, secret: str | None = None, subject: str | None = None) -> dict[str, Any]:
    result = get_provider("webhook").send(
        ProviderMessage(to=url, body=body, subject=subject, metadata={"url": url, "secret": secret or ""}),
    )
    return _to_dict(result)


def _to_dict(result: ProviderResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "provider": result.provider,
        "providerMessageId": result.provider_message_id,
        "errorCode": result.error_code,
        "errorMessage": result.error_message,
    }
