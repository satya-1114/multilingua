"""Translation platform enums / constants (Phase 5.1 — DB foundation).

Single source of truth for translation-related enum literals. Pydantic
schemas in :mod:`app.schemas.translation` mirror these via ``Literal``
types. Reusable across every entity in the platform — no module-specific
logic lives here.
"""
from __future__ import annotations

from typing import Final


# -- Translation status -------------------------------------------------------

TRANSLATION_STATUS_DRAFT: Final = "draft"
TRANSLATION_STATUS_TRANSLATED: Final = "translated"
TRANSLATION_STATUS_REVIEWED: Final = "reviewed"
TRANSLATION_STATUS_PUBLISHED: Final = "published"

TRANSLATION_STATUSES: Final[tuple[str, ...]] = (
    TRANSLATION_STATUS_DRAFT,
    TRANSLATION_STATUS_TRANSLATED,
    TRANSLATION_STATUS_REVIEWED,
    TRANSLATION_STATUS_PUBLISHED,
)


# -- Job status ---------------------------------------------------------------

JOB_STATUS_PENDING: Final = "pending"
JOB_STATUS_PROCESSING: Final = "processing"
JOB_STATUS_COMPLETED: Final = "completed"
JOB_STATUS_FAILED: Final = "failed"
JOB_STATUS_CANCELLED: Final = "cancelled"

JOB_STATUSES: Final[tuple[str, ...]] = (
    JOB_STATUS_PENDING,
    JOB_STATUS_PROCESSING,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_CANCELLED,
)


# -- Supported entity types ---------------------------------------------------

ENTITY_TYPE_DISASTER: Final = "disaster"
ENTITY_TYPE_PUBLIC_RESOURCE: Final = "public_resource"
ENTITY_TYPE_CAMPAIGN: Final = "campaign"
ENTITY_TYPE_ORGANIZATION: Final = "organization"

SUPPORTED_ENTITY_TYPES: Final[tuple[str, ...]] = (
    ENTITY_TYPE_DISASTER,
    ENTITY_TYPE_PUBLIC_RESOURCE,
    ENTITY_TYPE_CAMPAIGN,
    ENTITY_TYPE_ORGANIZATION,
)


# -- Provider (advisory only — repositories/services enforce) ----------------

PROVIDER_MANUAL: Final = "manual"
PROVIDER_AI: Final = "ai"
PROVIDER_MACHINE: Final = "machine"

PROVIDERS: Final[tuple[str, ...]] = (
    PROVIDER_MANUAL,
    PROVIDER_AI,
    PROVIDER_MACHINE,
)


__all__ = [
    "TRANSLATION_STATUS_DRAFT",
    "TRANSLATION_STATUS_TRANSLATED",
    "TRANSLATION_STATUS_REVIEWED",
    "TRANSLATION_STATUS_PUBLISHED",
    "TRANSLATION_STATUSES",
    "JOB_STATUS_PENDING",
    "JOB_STATUS_PROCESSING",
    "JOB_STATUS_COMPLETED",
    "JOB_STATUS_FAILED",
    "JOB_STATUS_CANCELLED",
    "JOB_STATUSES",
    "ENTITY_TYPE_DISASTER",
    "ENTITY_TYPE_PUBLIC_RESOURCE",
    "ENTITY_TYPE_CAMPAIGN",
    "ENTITY_TYPE_ORGANIZATION",
    "SUPPORTED_ENTITY_TYPES",
    "PROVIDER_MANUAL",
    "PROVIDER_AI",
    "PROVIDER_MACHINE",
    "PROVIDERS",
]
