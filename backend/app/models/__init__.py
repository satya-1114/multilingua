"""Import surface for SQLAlchemy metadata registration."""
from app.models.user import Role, Session, User, UserRole  # noqa: F401
from app.models.volunteer import Volunteer, VolunteerTask  # noqa: F401
from app.models.disaster import Disaster, DisasterAssignment, DisasterAttachment  # noqa: F401
from app.models.public_access import PublicResource, PublicView, QRCode  # noqa: F401
from app.models.organization import Organization  # noqa: F401
from app.models.workspace import Workspace, WorkspaceMember  # noqa: F401
from app.models.audience import Audience, AudienceGroup, AudienceTag  # noqa: F401
from app.models.campaign import Approval, Campaign, CampaignAudience, CampaignTemplate  # noqa: F401
from app.models.template import Template, TemplateVersion  # noqa: F401
from app.models.media import Media  # noqa: F401
from app.models.communication import (  # noqa: F401
    CommunicationChannel,
    Delivery,
    DeliveryRecipient,
    RetryPolicy,
)
from app.models.notification import Notification, NotificationPreference  # noqa: F401
from app.models.analytics import (  # noqa: F401
    AnalyticsMetric,
    AnalyticsReport,
    AnalyticsSnapshot,
    Report,
)
from app.models.automation import (  # noqa: F401
    LegacyWorkflowDefinition,
    LegacyWorkflowExecution,
)
from app.models.workflow import (  # noqa: F401
    WorkflowAction,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowExecutionStep,
    WorkflowTrigger,
)
from app.models.audit import ActivityLog, AuditLog  # noqa: F401
from app.models.integration import Integration, Webhook  # noqa: F401
from app.models.ai import (  # noqa: F401
    AIHistory,
    AIPrompt,
    Translation as AITranslation,
    TranslationHistory,
    WorkspaceAiSettings,
)
from app.models.translation import (  # noqa: F401
    Translation,
    TranslationJob,
    TranslationLocale,
)
from app.models.system import (  # noqa: F401
    BackgroundJob,
    FeatureFlag,
    HealthCheck,
    License,
    MonitoringMetric,
    SystemConfiguration,
)
from app.models.security import APIKey, SecurityEvent  # noqa: F401
from app.models.misc import Favorite, HelpArticle, KnowledgeArticle, UserPreference  # noqa: F401
from app.models.auth_extras import (  # noqa: F401
    AccountLockout,
    LoginAttempt,
    MfaFactor,
    PasswordHistory,
    RecoveryCode,
    TrustedDevice,
    VerificationToken,
)

