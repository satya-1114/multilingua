"""Public access & QR enums / constants (Phase 4.1 — DB foundation).

Single source of truth for public-resource / QR enum literals. Pydantic
schemas in :mod:`app.schemas.public_access` mirror these via ``Literal``
types.
"""
from __future__ import annotations

from typing import Final


# -- Resource type ------------------------------------------------------------

RESOURCE_TYPE_DISASTER: Final = "disaster"
RESOURCE_TYPE_CAMPAIGN: Final = "campaign"
RESOURCE_TYPE_VOLUNTEER_RECRUITMENT: Final = "volunteer_recruitment"
RESOURCE_TYPE_EMERGENCY_INFO: Final = "emergency_info"
RESOURCE_TYPE_DONATION: Final = "donation"
RESOURCE_TYPE_ORGANIZATION: Final = "organization"
RESOURCE_TYPE_OTHER: Final = "other"

RESOURCE_TYPES: Final[tuple[str, ...]] = (
    RESOURCE_TYPE_DISASTER,
    RESOURCE_TYPE_CAMPAIGN,
    RESOURCE_TYPE_VOLUNTEER_RECRUITMENT,
    RESOURCE_TYPE_EMERGENCY_INFO,
    RESOURCE_TYPE_DONATION,
    RESOURCE_TYPE_ORGANIZATION,
    RESOURCE_TYPE_OTHER,
)


# -- Visibility ---------------------------------------------------------------

VISIBILITY_PUBLIC: Final = "public"
VISIBILITY_UNLISTED: Final = "unlisted"
VISIBILITY_PRIVATE: Final = "private"
VISIBILITY_EXPIRED: Final = "expired"
VISIBILITY_DISABLED: Final = "disabled"

VISIBILITIES: Final[tuple[str, ...]] = (
    VISIBILITY_PUBLIC,
    VISIBILITY_UNLISTED,
    VISIBILITY_PRIVATE,
    VISIBILITY_EXPIRED,
    VISIBILITY_DISABLED,
)

# Visibilities that permit anonymous retrieval of the resource.
VISIBILITIES_RETRIEVABLE: Final[tuple[str, ...]] = (
    VISIBILITY_PUBLIC,
    VISIBILITY_UNLISTED,
)


# -- QR status ----------------------------------------------------------------

QR_STATUS_PENDING: Final = "pending"
QR_STATUS_ACTIVE: Final = "active"
QR_STATUS_REVOKED: Final = "revoked"
QR_STATUS_EXPIRED: Final = "expired"

QR_STATUSES: Final[tuple[str, ...]] = (
    QR_STATUS_PENDING,
    QR_STATUS_ACTIVE,
    QR_STATUS_REVOKED,
    QR_STATUS_EXPIRED,
)


# -- QR format ----------------------------------------------------------------

QR_FORMAT_PNG: Final = "png"
QR_FORMAT_SVG: Final = "svg"
QR_FORMAT_PDF: Final = "pdf"

QR_FORMATS: Final[tuple[str, ...]] = (
    QR_FORMAT_PNG,
    QR_FORMAT_SVG,
    QR_FORMAT_PDF,
)


# -- View device type ---------------------------------------------------------

DEVICE_TYPE_MOBILE: Final = "mobile"
DEVICE_TYPE_TABLET: Final = "tablet"
DEVICE_TYPE_DESKTOP: Final = "desktop"
DEVICE_TYPE_BOT: Final = "bot"
DEVICE_TYPE_UNKNOWN: Final = "unknown"

DEVICE_TYPES: Final[tuple[str, ...]] = (
    DEVICE_TYPE_MOBILE,
    DEVICE_TYPE_TABLET,
    DEVICE_TYPE_DESKTOP,
    DEVICE_TYPE_BOT,
    DEVICE_TYPE_UNKNOWN,
)


__all__ = [
    "RESOURCE_TYPE_DISASTER",
    "RESOURCE_TYPE_CAMPAIGN",
    "RESOURCE_TYPE_VOLUNTEER_RECRUITMENT",
    "RESOURCE_TYPE_EMERGENCY_INFO",
    "RESOURCE_TYPE_DONATION",
    "RESOURCE_TYPE_ORGANIZATION",
    "RESOURCE_TYPE_OTHER",
    "RESOURCE_TYPES",
    "VISIBILITY_PUBLIC",
    "VISIBILITY_UNLISTED",
    "VISIBILITY_PRIVATE",
    "VISIBILITY_EXPIRED",
    "VISIBILITY_DISABLED",
    "VISIBILITIES",
    "VISIBILITIES_RETRIEVABLE",
    "QR_STATUS_PENDING",
    "QR_STATUS_ACTIVE",
    "QR_STATUS_REVOKED",
    "QR_STATUS_EXPIRED",
    "QR_STATUSES",
    "QR_FORMAT_PNG",
    "QR_FORMAT_SVG",
    "QR_FORMAT_PDF",
    "QR_FORMATS",
    "DEVICE_TYPE_MOBILE",
    "DEVICE_TYPE_TABLET",
    "DEVICE_TYPE_DESKTOP",
    "DEVICE_TYPE_BOT",
    "DEVICE_TYPE_UNKNOWN",
    "DEVICE_TYPES",
]
