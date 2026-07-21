/**
 * Role-Based Access Control primitives.
 *
 * The platform supports exactly four roles:
 *   - Super Admin       (seeded / manual only — never selectable in registration)
 *   - Campaign Manager  (also covers organization management)
 *   - Volunteer
 *   - Viewer
 */

export const ROLES = {
  SUPER_ADMIN: "super_admin",
  CAMPAIGN_MANAGER: "campaign_manager",
  VOLUNTEER: "volunteer",
  VIEWER: "viewer",
} as const;

export type Role = (typeof ROLES)[keyof typeof ROLES];

/** Roles that end users may select when signing up. Super Admin is intentionally excluded. */
export const REGISTRATION_ROLES: Role[] = [
  ROLES.VIEWER,
  ROLES.VOLUNTEER,
  ROLES.CAMPAIGN_MANAGER,
];

export interface RoleMetadata {
  key: Role;
  label: string;
  description: string;
  tone: "primary" | "accent" | "warning" | "muted";
}

export const ROLE_METADATA: Record<Role, RoleMetadata> = {
  [ROLES.SUPER_ADMIN]: {
    key: ROLES.SUPER_ADMIN,
    label: "Super Admin",
    description: "Full platform access. Seeded or manually provisioned only.",
    tone: "warning",
  },
  [ROLES.CAMPAIGN_MANAGER]: {
    key: ROLES.CAMPAIGN_MANAGER,
    label: "Campaign Manager",
    description:
      "Plans, launches, and measures multilingual campaigns. Manages the organization workspace.",
    tone: "primary",
  },
  [ROLES.VOLUNTEER]: {
    key: ROLES.VOLUNTEER,
    label: "Volunteer",
    description: "Contributes to campaigns, content, and outreach on the ground.",
    tone: "accent",
  },
  [ROLES.VIEWER]: {
    key: ROLES.VIEWER,
    label: "Viewer",
    description: "Read-only access to campaigns, audiences, and analytics.",
    tone: "muted",
  },
};

export const PERMISSIONS = {
  // Campaigns
  CAMPAIGN_VIEW: "campaign:view",
  CAMPAIGN_CREATE: "campaign:create",
  CAMPAIGN_EDIT: "campaign:edit",
  CAMPAIGN_DELETE: "campaign:delete",
  CAMPAIGN_LAUNCH: "campaign:launch",
  // Content
  CONTENT_VIEW: "content:view",
  CONTENT_CREATE: "content:create",
  CONTENT_EDIT: "content:edit",
  CONTENT_APPROVE: "content:approve",
  // Audience
  AUDIENCE_VIEW: "audience:view",
  AUDIENCE_CREATE: "audience:create",
  AUDIENCE_EDIT: "audience:edit",
  AUDIENCE_DELETE: "audience:delete",
  AUDIENCE_IMPORT: "audience:import",
  AUDIENCE_EXPORT: "audience:export",
  AUDIENCE_MANAGE: "audience:manage",
  // Groups & Tags
  GROUP_MANAGE: "group:manage",
  TAG_MANAGE: "tag:manage",
  // Analytics
  ANALYTICS_VIEW: "analytics:view",
  ANALYTICS_EXPORT: "analytics:export",
  ANALYTICS_MANAGE: "analytics:manage",
  // Users
  USER_VIEW: "user:view",
  USER_MANAGE: "user:manage",
  // Organization
  ORG_VIEW: "org:view",
  ORG_CREATE: "org:create",
  ORG_EDIT: "org:edit",
  ORG_DELETE: "org:delete",
  ORG_MANAGE: "org:manage",
  // Audit
  AUDIT_VIEW: "audit:view",
  // Settings
  SETTINGS_VIEW: "settings:view",
  SETTINGS_MANAGE: "settings:manage",
  // Billing
  BILLING_VIEW: "billing:view",
  BILLING_MANAGE: "billing:manage",
  // Templates
  TEMPLATE_VIEW: "template:view",
  TEMPLATE_CREATE: "template:create",
  TEMPLATE_EDIT: "template:edit",
  TEMPLATE_DELETE: "template:delete",
  TEMPLATE_APPROVE: "template:approve",
  // Media
  MEDIA_VIEW: "media:view",
  MEDIA_UPLOAD: "media:upload",
  MEDIA_DELETE: "media:delete",
  // Workflow / approvals
  WORKFLOW_VIEW: "workflow:view",
  WORKFLOW_CREATE: "workflow:create",
  WORKFLOW_UPDATE: "workflow:update",
  WORKFLOW_EXECUTE: "workflow:execute",
  WORKFLOW_MANAGE: "workflow:manage",
  APPROVAL_ACT: "approval:act",
  // AI Studio
  AI_USE: "ai:use",
  AI_GENERATE: "ai:generate",
  AI_MANAGE_PROMPTS: "ai:manage_prompts",
  AI_HISTORY_VIEW: "ai:history_view",
  // Translation
  TRANSLATION_USE: "translation:use",
  TRANSLATION_MANAGE_GLOSSARY: "translation:manage_glossary",
  // Jobs
  JOB_VIEW: "job:view",
  JOB_MANAGE: "job:manage",
  // Workspaces
  WORKSPACE_VIEW: "workspace:view",
  WORKSPACE_MANAGE: "workspace:manage",
  WORKSPACE_SWITCH: "workspace:switch",
  // System / admin
  SYSTEM_VIEW: "system:view",
  SYSTEM_MANAGE: "system:manage",
  FEATURE_FLAG_MANAGE: "feature_flag:manage",
  // Automation
  AUTOMATION_VIEW: "automation:view",
  AUTOMATION_MANAGE: "automation:manage",
  // Integrations
  INTEGRATION_VIEW: "integration:view",
  INTEGRATION_MANAGE: "integration:manage",
  WEBHOOK_MANAGE: "webhook:manage",
  // Monitoring
  MONITORING_VIEW: "monitoring:view",
  // Security
  SECURITY_VIEW: "security:view",
  SECURITY_MANAGE: "security:manage",
  // Communication
  COMMUNICATION_VIEW: "communication:view",
  COMMUNICATION_MANAGE: "communication:manage",
  CHANNEL_VIEW: "channel:view",
  CHANNEL_MANAGE: "channel:manage",
  DELIVERY_VIEW: "delivery:view",
  DELIVERY_MANAGE: "delivery:manage",
  SCHEDULER_MANAGE: "scheduler:manage",
  RETRY_POLICY_MANAGE: "retry_policy:manage",
  ENGAGEMENT_VIEW: "engagement:view",
  // Volunteer management
  VOLUNTEER_VIEW: "volunteer:view",
  VOLUNTEER_MANAGE: "volunteer:manage",
  // Tasks
  TASK_VIEW: "task:view",
  TASK_ASSIGN: "task:assign",
  TASK_MANAGE: "task:manage",
  TASK_ACT: "task:act",
  // Campaign QR Codes
  CAMPAIGN_QR_VIEW: "campaign_qr:view",
  CAMPAIGN_QR_MANAGE: "campaign_qr:manage",
  // Disaster management
  DISASTER_VIEW: "disaster:view",
  DISASTER_MANAGE: "disaster:manage",
  DISASTER_ASSIGN: "disaster:assign",
  // Public information & QR
  PUBLIC_VIEW: "public:view",
  PUBLIC_MANAGE: "public:manage",
  QR_MANAGE: "qr:manage",
} as const;




export type Permission = (typeof PERMISSIONS)[keyof typeof PERMISSIONS];

const READ_ALL: Permission[] = [
  PERMISSIONS.CAMPAIGN_VIEW,
  PERMISSIONS.CONTENT_VIEW,
  PERMISSIONS.AUDIENCE_VIEW,
  PERMISSIONS.ANALYTICS_VIEW,
  PERMISSIONS.ORG_VIEW,
  PERMISSIONS.SETTINGS_VIEW,
];

const AUDIENCE_FULL: Permission[] = [
  PERMISSIONS.AUDIENCE_VIEW,
  PERMISSIONS.AUDIENCE_CREATE,
  PERMISSIONS.AUDIENCE_EDIT,
  PERMISSIONS.AUDIENCE_DELETE,
  PERMISSIONS.AUDIENCE_IMPORT,
  PERMISSIONS.AUDIENCE_EXPORT,
  PERMISSIONS.AUDIENCE_MANAGE,
  PERMISSIONS.GROUP_MANAGE,
  PERMISSIONS.TAG_MANAGE,
];

const TEMPLATE_AUTHOR: Permission[] = [
  PERMISSIONS.TEMPLATE_VIEW,
  PERMISSIONS.TEMPLATE_CREATE,
  PERMISSIONS.TEMPLATE_EDIT,
];

const MEDIA_AUTHOR: Permission[] = [
  PERMISSIONS.MEDIA_VIEW,
  PERMISSIONS.MEDIA_UPLOAD,
];

export const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  [ROLES.SUPER_ADMIN]: Object.values(PERMISSIONS),
  // Campaign Manager also covers organization management responsibilities.
  [ROLES.CAMPAIGN_MANAGER]: [
    ...READ_ALL,
    PERMISSIONS.CAMPAIGN_CREATE,
    PERMISSIONS.CAMPAIGN_EDIT,
    PERMISSIONS.CAMPAIGN_DELETE,
    PERMISSIONS.CAMPAIGN_LAUNCH,
    PERMISSIONS.CONTENT_CREATE,
    PERMISSIONS.CONTENT_EDIT,
    PERMISSIONS.CONTENT_APPROVE,
    ...AUDIENCE_FULL,
    PERMISSIONS.ANALYTICS_EXPORT,
    PERMISSIONS.ANALYTICS_MANAGE,
    PERMISSIONS.USER_VIEW,
    PERMISSIONS.ORG_EDIT,
    PERMISSIONS.ORG_MANAGE,
    PERMISSIONS.ORG_CREATE,
    PERMISSIONS.AUDIT_VIEW,
    PERMISSIONS.SETTINGS_MANAGE,
    PERMISSIONS.BILLING_VIEW,
    PERMISSIONS.BILLING_MANAGE,
    ...TEMPLATE_AUTHOR,
    PERMISSIONS.TEMPLATE_DELETE,
    PERMISSIONS.TEMPLATE_APPROVE,
    ...MEDIA_AUTHOR,
    PERMISSIONS.MEDIA_DELETE,
    PERMISSIONS.WORKFLOW_VIEW,
    PERMISSIONS.WORKFLOW_CREATE,
    PERMISSIONS.WORKFLOW_UPDATE,
    PERMISSIONS.WORKFLOW_EXECUTE,
    PERMISSIONS.WORKFLOW_MANAGE,
    PERMISSIONS.APPROVAL_ACT,
    PERMISSIONS.AI_USE,
    PERMISSIONS.AI_GENERATE,
    PERMISSIONS.AI_MANAGE_PROMPTS,
    PERMISSIONS.AI_HISTORY_VIEW,
    PERMISSIONS.TRANSLATION_USE,
    PERMISSIONS.TRANSLATION_MANAGE_GLOSSARY,
    PERMISSIONS.JOB_VIEW,
    PERMISSIONS.JOB_MANAGE,
    PERMISSIONS.WORKSPACE_VIEW,
    PERMISSIONS.WORKSPACE_MANAGE,
    PERMISSIONS.WORKSPACE_SWITCH,
    PERMISSIONS.AUTOMATION_VIEW,
    PERMISSIONS.AUTOMATION_MANAGE,
    PERMISSIONS.INTEGRATION_VIEW,
    PERMISSIONS.INTEGRATION_MANAGE,
    PERMISSIONS.WEBHOOK_MANAGE,
    PERMISSIONS.MONITORING_VIEW,
    PERMISSIONS.COMMUNICATION_VIEW,
    PERMISSIONS.COMMUNICATION_MANAGE,
    PERMISSIONS.CHANNEL_VIEW,
    PERMISSIONS.CHANNEL_MANAGE,
    PERMISSIONS.DELIVERY_VIEW,
    PERMISSIONS.DELIVERY_MANAGE,
    PERMISSIONS.SCHEDULER_MANAGE,
    PERMISSIONS.RETRY_POLICY_MANAGE,
    PERMISSIONS.ENGAGEMENT_VIEW,
    PERMISSIONS.VOLUNTEER_VIEW,
    PERMISSIONS.VOLUNTEER_MANAGE,
    PERMISSIONS.TASK_VIEW,
    PERMISSIONS.TASK_ASSIGN,
    PERMISSIONS.TASK_MANAGE,
    PERMISSIONS.CAMPAIGN_QR_VIEW,
    PERMISSIONS.CAMPAIGN_QR_MANAGE,
    PERMISSIONS.DISASTER_VIEW,
    PERMISSIONS.DISASTER_MANAGE,
    PERMISSIONS.DISASTER_ASSIGN,
    PERMISSIONS.PUBLIC_VIEW,
    PERMISSIONS.PUBLIC_MANAGE,
    PERMISSIONS.QR_MANAGE,
  ],

  [ROLES.VOLUNTEER]: [
    PERMISSIONS.CAMPAIGN_VIEW,
    PERMISSIONS.CONTENT_VIEW,
    PERMISSIONS.CONTENT_CREATE,
    PERMISSIONS.CONTENT_EDIT,
    PERMISSIONS.AUDIENCE_VIEW,
    PERMISSIONS.TEMPLATE_VIEW,
    ...MEDIA_AUTHOR,
    PERMISSIONS.AI_USE,
    PERMISSIONS.AI_GENERATE,
    PERMISSIONS.AI_HISTORY_VIEW,
    PERMISSIONS.TRANSLATION_USE,
    PERMISSIONS.SETTINGS_VIEW,
    PERMISSIONS.TASK_VIEW,
    PERMISSIONS.TASK_ACT,
    PERMISSIONS.CAMPAIGN_QR_VIEW,
    PERMISSIONS.DISASTER_VIEW,
    PERMISSIONS.PUBLIC_VIEW,
    // Phase 6 — volunteers see their personal contribution analytics.
    PERMISSIONS.ANALYTICS_VIEW,
  ],

  [ROLES.VIEWER]: [
    // Phase 6 — viewers explicitly do NOT get analytics access.
    ...READ_ALL.filter((p) => p !== PERMISSIONS.ANALYTICS_VIEW),
    PERMISSIONS.TEMPLATE_VIEW,
    PERMISSIONS.MEDIA_VIEW,
    PERMISSIONS.CAMPAIGN_QR_VIEW,
    PERMISSIONS.DISASTER_VIEW,
    PERMISSIONS.PUBLIC_VIEW,

  ],
};



export const ORGANIZATION_TYPES = [
  "Government",
  "NGO / Non-profit",
  "Healthcare",
  "Education",
  "Enterprise",
  "Media",
  "Other",
] as const;

export type OrganizationType = (typeof ORGANIZATION_TYPES)[number];

export const VOLUNTEER_AVAILABILITY = [
  "Weekdays",
  "Weekends",
  "Evenings",
  "Full-time",
  "On-call",
] as const;

export type VolunteerAvailability = (typeof VOLUNTEER_AVAILABILITY)[number];
