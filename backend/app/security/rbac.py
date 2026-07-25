from __future__ import annotations

from collections.abc import Iterable

from app.core.exceptions import ForbiddenError

PERMISSIONS: dict[str, tuple[str, ...]] = {
    "super_admin": ("*",),

    "org_admin": (
        "campaign:*",
        "content:*",
        "audience:*",
        "template:*",
        "media:*",

        "analytics:*",

        "org:*",
        "user:*",

        "workspace:*",

        "communication:*",
        "delivery:*",
        "channel:*",

        "settings:*",
        "audit:*",
        "billing:*",

        "disaster:*",
        "assignment:*",
        "volunteer:*",
        "task:*",

        "public:*",
        "qr:*",

        "translation:*",

        "workflow:*",

        "ai:*",
    ),

    "automation_admin": (
        "workflow:*",
    ),

    "campaign_manager": (
        # Campaigns
        "campaign:*",

        # Organization
        "org:*",

        # Users
        "user:*",

        # Workspaces
        "workspace:*",

        # Content
        "content:*",
        "audience:*",
        "template:*",
        "media:*",

        # Analytics
        "analytics:*",

        # Communication
        "communication:*",
        "delivery:*",
        "channel:*",

        # Settings
        "settings:*",

        # Audit
        "audit:*",

        # Billing
        "billing:*",

        # Volunteers
        "volunteer:*",

        # Tasks
        "task:*",

        # Disaster
        "disaster:*",

        # Assignment
        "assignment:*",

        # Public Portal
        "public:*",

        # QR
        "qr:*",

        # Translation
        "translation:*",

        # Workflow
        "workflow:*",

        # AI
        "ai:*",
    ),

    "volunteer": (
        "task:view",
        "task:act",

        "assignment:view",
        "assignment:act",

        "disaster:view",

        "public:view",

        "translation:view",
    ),

    "content_creator": (
        "campaign:view",

        "content:*",
        "template:*",
        "media:*",

        "public:*",

        "qr:*",

        "translation:*",

        "ai:*",
    ),

    "communication_officer": (
        "campaign:view",
        "campaign:launch",

        "audience:*",

        "communication:*",
        "delivery:*",
        "channel:*",

        "disaster:view",

        "public:*",

        "qr:*",

        "translation:*",

        "ai:use",
    ),

   "translator": (
    "translation:view",
    "translation:create",
    "translation:update",

    "campaign:view",
    "disaster:view",
    "public:view",
),

    "reviewer": (
        "translation:view",
        "translation:review",
        "translation:publish",

        "campaign:view",

        "disaster:view",

        "public:view",
    ),

    "data_analyst": (
        "campaign:view",

        "audience:view",

        "analytics:*",

        "audit:view",

        "template:view",
        "media:view",

        "disaster:view",

        "public:view",

        "qr:view",

        "translation:view",
    ),

    "viewer": (
        "campaign:view",

        "audience:view",

        "template:view",
        "media:view",

        "analytics:view",

        "disaster:view",

        "public:view",

        "qr:view",

        "translation:view",

        "workflow:view",

        "workspace:view",

        "org:view",
    ),
}

def _role_grants(role: str) -> tuple[str, ...]:
    return PERMISSIONS.get(role, ())


def has_permission(roles: Iterable[str], required: str) -> bool:
    domain = required.split(":", 1)[0]
    for role in roles:
        for grant in _role_grants(role):
            if grant == "*" or grant == required or grant == f"{domain}:*":
                return True
    return False


def require_permission(roles: Iterable[str], required: str) -> None:
    if not has_permission(roles, required):
        raise ForbiddenError(f"Missing permission: {required}", details={"required": required})
