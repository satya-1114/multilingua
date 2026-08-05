from __future__ import annotations

from app.integrations.communication import (
    ProviderMessage,
    get_provider,
)


class CommunicationDispatcher:
    """
    Dispatches messages through the configured communication provider.

    The dispatcher is provider-agnostic. It simply resolves the
    correct provider from the registry and delegates the send call.
    """

    def dispatch(
        self,
        *,
        channel: str,
        recipient: str,
        body: str,
        subject: str | None = None,
        html: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        provider = get_provider(channel)

        message = ProviderMessage(
            to=recipient,
            body=body,
            subject=subject,
            html=html,
            metadata=metadata or {},
        )

        result = provider.send(message)

        return {
            "status": result.status,
            "provider": result.provider,
            "provider_message_id": result.provider_message_id,
            "error_code": result.error_code,
            "error_message": result.error_message,
            "raw": result.raw,
        }


dispatcher = CommunicationDispatcher()