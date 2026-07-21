/**
 * Central query-key factory. Keeps invalidation surface stable and
 * discoverable across the app. Only Phase 5.5 (Translation Platform) keys
 * are registered here; other services still inline their keys until they
 * are migrated. Never mutate — always return fresh arrays.
 */

export const queryKeys = {
  translations: {
    all: ["translations"] as const,
    list: (filters: Record<string, unknown>) => ["translations", "list", filters] as const,
    detail: (id: string) => ["translations", "detail", id] as const,
    entity: (entityType: string, entityId: string, locale?: string) =>
      ["translations", "entity", entityType, entityId, locale ?? null] as const,
  },
  translationJobs: {
    all: ["translation-jobs"] as const,
    list: (filters: Record<string, unknown>) => ["translation-jobs", "list", filters] as const,
    detail: (id: string) => ["translation-jobs", "detail", id] as const,
  },
  translationLocales: {
    all: ["translation-locales"] as const,
    list: (enabledOnly?: boolean) =>
      ["translation-locales", "list", enabledOnly ?? false] as const,
  },
  analytics: {
    all: ["analytics"] as const,
    overview: () => ["analytics", "overview"] as const,
    platform: (filters: Record<string, unknown>) => ["analytics", "platform", filters] as const,
    platformOverview: () => ["analytics", "platform-overview"] as const,
  },
  analyticsMetrics: {
    all: ["analytics-metrics"] as const,
    list: (filters: Record<string, unknown>) => ["analytics-metrics", "list", filters] as const,
    detail: (id: string) => ["analytics-metrics", "detail", id] as const,
    aggregate: (params: Record<string, unknown>) => ["analytics-metrics", "aggregate", params] as const,
  },
  analyticsSnapshots: {
    all: ["analytics-snapshots"] as const,
    list: (filters: Record<string, unknown>) => ["analytics-snapshots", "list", filters] as const,
    detail: (id: string) => ["analytics-snapshots", "detail", id] as const,
  },
  analyticsReports: {
    all: ["analytics-reports"] as const,
    list: (filters: Record<string, unknown>) => ["analytics-reports", "list", filters] as const,
    detail: (id: string) => ["analytics-reports", "detail", id] as const,
  },
  workflow: {
    all: ["workflow"] as const,
    dashboard: () => ["workflow", "dashboard"] as const,
    runtimeHealth: () => ["workflow", "runtime", "health"] as const,
    runtimeStatistics: (since?: string) =>
      ["workflow", "runtime", "statistics", since ?? "all"] as const,
    retryHistory: (executionId: string) =>
      ["workflow", "runtime", "retries", executionId] as const,
    observabilityMetrics: () =>
      ["workflow", "runtime", "observability"] as const,
    executionTrace: (executionId: string) =>
      ["workflow", "runtime", "trace", executionId] as const,
  },
  workflowDefinitions: {
    all: ["workflow-definitions"] as const,
    list: (filters: Record<string, unknown>) =>
      ["workflow-definitions", "list", filters] as const,
    detail: (id: string) => ["workflow-definitions", "detail", id] as const,
  },
  workflowTriggers: {
    all: ["workflow-triggers"] as const,
    list: (workflowId: string) => ["workflow-triggers", "list", workflowId] as const,
  },
  workflowActions: {
    all: ["workflow-actions"] as const,
    list: (workflowId: string) => ["workflow-actions", "list", workflowId] as const,
  },
  workflowExecutions: {
    all: ["workflow-executions"] as const,
    list: (workflowId: string, filters: Record<string, unknown>) =>
      ["workflow-executions", "list", workflowId, filters] as const,
    detail: (id: string) => ["workflow-executions", "detail", id] as const,
  },
  workflowSteps: {
    all: ["workflow-steps"] as const,
    list: (executionId: string, filters: Record<string, unknown>) =>
      ["workflow-steps", "list", executionId, filters] as const,
  },
} as const;
