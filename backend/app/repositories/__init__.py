from app.crud.base import CRUDBase
from app.models.audience import Audience
from app.models.campaign import Campaign
from app.models.communication import CommunicationChannel, Delivery
from app.models.media import Media
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.template import Template
from app.models.user import User
from app.models.workspace import Workspace


users = CRUDBase(User)
organizations = CRUDBase(Organization)
workspaces = CRUDBase(Workspace)
audience = CRUDBase(Audience)
campaigns = CRUDBase(Campaign)
templates = CRUDBase(Template)
media = CRUDBase(Media)
channels = CRUDBase(CommunicationChannel)
deliveries = CRUDBase(Delivery)
notifications = CRUDBase(Notification)

from app.repositories.volunteer import (  # noqa: E402,F401
    VolunteerRepository,
    VolunteerTaskRepository,
    volunteer_tasks,
    volunteers,
)
