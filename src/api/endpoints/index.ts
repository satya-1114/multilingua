/**
 * Central endpoint registry. Every service references paths from here so
 * migrations to a real backend touch a single file.
 */

export const ENDPOINTS = {
  auth: {
    login: "/auth/login",
    logout: "/auth/logout",
    refresh: "/auth/refresh",
    session: "/auth/session",
    forgot: "/auth/forgot-password",
    reset: "/auth/reset-password",
    verifyEmail: "/auth/verify-email",
    verifyOtp: "/auth/verify-otp",
  },
  users: {
    root: "/users",
    byId: (id: string) => `/users/${id}`,
  },
  organizations: {
    root: "/organizations",
    byId: (id: string) => `/organizations/${id}`,
  },
  workspaces: {
    root: "/workspaces",
    byId: (id: string) => `/workspaces/${id}`,
    settings: (id: string) => `/workspaces/${id}/settings`,
  },
  audience: {
    root: "/audience",
    byId: (id: string) => `/audience/${id}`,
    import: "/audience/import",
    groups: "/audience/groups",
    tags: "/audience/tags",
  },
  campaigns: {
    root: "/campaigns",
    byId: (id: string) => `/campaigns/${id}`,
    approvals: "/campaigns/approvals",
    delivery: (id: string) => `/campaigns/${id}/delivery`,
  },
  templates: {
    root: "/templates",
    byId: (id: string) => `/templates/${id}`,
  },
  communication: {
    channels: "/communication/channels",
    delivery: "/communication/delivery",
    scheduling: "/communication/scheduling",
    engagement: "/communication/engagement",
    retryPolicies: "/communication/retry-policies",
  },
  analytics: {
    overview: "/analytics/overview",
    reports: "/analytics/reports",
    builder: "/analytics/builder",
  },
  automation: {
    root: "/automation",
    byId: (id: string) => `/automation/${id}`,
  },
  notifications: {
    root: "/notifications",
    preferences: "/notifications/preferences",
  },
  media: { root: "/media" },
  ai: {
    generate: "/ai/generate",
    prompts: "/ai/prompts",
    history: "/ai/history",
    drafts: "/ai/drafts",
  },
  translation: { root: "/translation" },
  monitoring: {
    health: "/monitoring/health",
    logs: "/monitoring/logs",
    queues: "/monitoring/queues",
  },
  security: {
    sessions: "/security/sessions",
    policy: "/security/policy",
    events: "/security/events",
  },
  help: { root: "/help" },
  system: {
    version: "/system/version",
    health: "/system/health",
    license: "/system/license",
  },
} as const;
