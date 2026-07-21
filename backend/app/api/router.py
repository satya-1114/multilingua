from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    ai,
    analytics,
    audience,
    auth,
    automation,
    campaigns,
    communication,
    disasters,
    public_access,
    workflow,
    favorites,
    help,
    integrations,
    media,
    monitoring,
    notifications,
    organizations,
    reports,
    runtime,
    search,
    security,
    settings as settings_router,
    system,
    tasks,
    templates,
    translation,
    translations as translations_router,

    users,
    volunteers,
    workspaces,
)


api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(audience.router, prefix="/audience", tags=["audience"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(media.router, prefix="/media", tags=["media"])
api_router.include_router(communication.router, prefix="/communication", tags=["communication"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(automation.router, prefix="/automation", tags=["automation"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(security.router, prefix="/security", tags=["security"])
api_router.include_router(help.router, prefix="/help", tags=["help"])
api_router.include_router(settings_router.router, prefix="/settings", tags=["settings"])
api_router.include_router(favorites.router, prefix="/favorites", tags=["favorites"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(translation.router, prefix="/translation", tags=["translation"])
api_router.include_router(translations_router.router, prefix="/translations", tags=["translations"])

api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(volunteers.router, prefix="/volunteers", tags=["volunteers"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(disasters.router, prefix="/disasters", tags=["disasters"])
api_router.include_router(public_access.router, prefix="/public-resources", tags=["public-access"])
api_router.include_router(workflow.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(runtime.router, prefix="/runtime", tags=["workflow-runtime"])
