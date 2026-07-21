"""Template engine, translation, and communication provider tests."""
from __future__ import annotations

import pytest

from app.services.template_engine import render, validate, variables_in
from app.services.translation import detect_language, apply_glossary, register_glossary_term


# ---------- template engine ----------


def test_render_basic_variables():
    body = "Hello {{ recipient.name }}, welcome to {{ org }}!"
    out, missing = render(body, {"recipient": {"name": "Amit"}, "org": "Ministry"})
    assert out == "Hello Amit, welcome to Ministry!"
    assert missing == []


def test_render_default_and_missing():
    body = "Hi {{ name|default:friend }}, ref {{ ref }}"
    out, missing = render(body, {})
    assert "Hi friend" in out
    assert missing == ["ref"]


def test_render_conditional():
    body = "{% if premium %}Premium: {{ tier }}{% endif %} plain"
    out, _ = render(body, {"premium": True, "tier": "Gold"})
    assert "Premium: Gold" in out
    out2, _ = render(body, {"premium": False})
    assert "Premium" not in out2


def test_render_filters():
    body = "{{ name|upper }}"
    out, _ = render(body, {"name": "amit"})
    assert out == "AMIT"


def test_render_strict_raises():
    from app.core.exceptions import ValidationError
    with pytest.raises(ValidationError):
        render("hi {{missing}}", {}, strict=True)


def test_variables_in_extracts_paths():
    body = "hi {{ a.b }} {{ c|default:x }} {% if d %}{{d}}{% endif %}"
    assert variables_in(body) == ["a.b", "c", "d"]


def test_validate_returns_missing():
    body = "hi {{ name }} {{ email }}"
    result = validate(body, {"name": "A"})
    assert result["variables"] == ["email", "name"]
    assert result["missing"] == ["email"]
    assert result["valid"] is False


# ---------- translation helpers ----------


def test_detect_language_indic():
    assert detect_language("नमस्ते") == "hi"
    assert detect_language("வணக்கம்") == "ta"
    assert detect_language("Hello") == "en"


def test_glossary_replacement():
    register_glossary_term("Ministry", {"hi": "मंत्रालय"})
    assert apply_glossary("Ministry of Health", "hi") == "मंत्रालय of Health"
    assert apply_glossary("Ministry of Health", "en") == "Ministry of Health"


# ---------- communication provider skip when unconfigured ----------


def test_smtp_skipped_when_unconfigured(monkeypatch):
    from app.services import communication as comm
    from app.core import config

    monkeypatch.setattr(config.settings, "SMTP_HOST", "")
    provider = comm.SmtpEmailProvider()
    result = provider.send(comm.ProviderMessage(to="a@b.c", subject="s", body="b"))
    assert result.status == "skipped"


def test_twilio_skipped_when_unconfigured(monkeypatch):
    from app.services import communication as comm
    from app.core import config

    monkeypatch.setattr(config.settings, "TWILIO_ACCOUNT_SID", "")
    monkeypatch.setattr(config.settings, "TWILIO_AUTH_TOKEN", "")
    monkeypatch.setattr(config.settings, "TWILIO_FROM", "")
    provider = comm.TwilioProvider(channel="sms")
    result = provider.send(comm.ProviderMessage(to="+1", body="hi"))
    assert result.status == "skipped"


def test_communication_provider_registry_has_all_channels():
    from app.services import communication as comm
    channels = {p["channel"] for p in comm.provider_health()}
    assert {"email", "sms", "whatsapp", "push", "webhook"} <= channels
