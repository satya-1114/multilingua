/**
 * Automation & Workflow Engine — Phase 7.5 (frontend).
 *
 * These types mirror the payload shape produced by
 * `backend/app/api/v1/workflow.py` (camelCase envelopes).
 */

export type WorkflowTriggerType = "event" | "schedule" | "manual";

export type WorkflowStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export type WorkflowStepStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "skipped";

export const WORKFLOW_TRIGGER_TYPES: WorkflowTriggerType[] = [
  "event",
  "schedule",
  "manual",
];

export const WORKFLOW_STATUSES: WorkflowStatus[] = [
  "pending",
  "running",
  "completed",
  "failed",
  "cancelled",
];

export const WORKFLOW_STEP_STATUSES: WorkflowStepStatus[] = [
  "pending",
  "running",
  "completed",
  "failed",
  "skipped",
];

export interface WorkflowDefinition {
  id: string;
  name: string;
  description: string | null;
  triggerType: WorkflowTriggerType;
  enabled: boolean;
  organizationId: string | null;
  version: number;
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface WorkflowDefinitionInput {
  name: string;
  description?: string | null;
  triggerType: WorkflowTriggerType;
  enabled?: boolean;
  organizationId?: string | null;
  version?: number;
  metadata?: Record<string, unknown>;
}

export interface WorkflowTrigger {
  id: string;
  workflowDefinitionId: string;
  eventName: string;
  eventSource: string | null;
  conditionsJson: Record<string, unknown>;
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface WorkflowTriggerInput {
  eventName: string;
  eventSource?: string | null;
  conditionsJson?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface WorkflowAction {
  id: string;
  workflowDefinitionId: string;
  sequence: number;
  actionType: string;
  configurationJson: Record<string, unknown>;
  enabled: boolean;
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface WorkflowActionInput {
  sequence?: number;
  actionType: string;
  configurationJson?: Record<string, unknown>;
  enabled?: boolean;
  metadata?: Record<string, unknown>;
}

export interface WorkflowExecution {
  id: string;
  workflowDefinitionId: string;
  triggerEvent: string | null;
  status: WorkflowStatus;
  startedAt: string | null;
  completedAt: string | null;
  failureReason: string | null;
  contextJson: Record<string, unknown>;
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface WorkflowExecutionStep {
  id: string;
  workflowExecutionId: string;
  workflowActionId: string;
  status: WorkflowStepStatus;
  startedAt: string | null;
  completedAt: string | null;
  retryCount: number;
  outputJson: Record<string, unknown>;
  errorMessage: string | null;
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface WorkflowDefinitionListQuery {
  q?: string;
  triggerType?: WorkflowTriggerType;
  enabled?: boolean;
  organizationId?: string;
  createdFrom?: string;
  createdTo?: string;
  page?: number;
  pageSize?: number;
}

export interface WorkflowExecutionListQuery {
  status?: WorkflowStatus;
  startedFrom?: string;
  startedTo?: string;
  page?: number;
  pageSize?: number;
}

export interface WorkflowStepListQuery {
  status?: WorkflowStepStatus;
  page?: number;
  pageSize?: number;
}

export interface WorkflowDashboardStats {
  totalWorkflows: number;
  enabledWorkflows: number;
  runningExecutions: number;
  failedExecutions: number;
  completedExecutions: number;
  recentExecutions: WorkflowExecution[];
}

// ─── Phase 8.5 — Runtime monitoring ─────────────────────────────────────

export type RuntimeHealthStatus = "ok" | "degraded" | "unhealthy" | "unknown";

export interface RuntimeHealthCheck {
  status: RuntimeHealthStatus;
  detail?: string;
  [key: string]: unknown;
}

export interface RuntimeHealth {
  status: RuntimeHealthStatus;
  checks: {
    registry: RuntimeHealthCheck;
    scheduler: RuntimeHealthCheck;
    queue: RuntimeHealthCheck;
    celery: RuntimeHealthCheck;
    handlers: RuntimeHealthCheck;
  };
}

export interface RuntimeStatisticsOverview {
  total: number;
  byStatus: Record<string, number>;
  completed: number;
  failed: number;
  cancelled: number;
  running: number;
  successRate: number;
  failureRate: number;
  retryRate: number;
  avgDurationSeconds: number;
  totalRetries: number;
  retryExecutions: number;
  since: string | null;
}

export interface RuntimeTopWorkflow {
  workflowDefinitionId: string;
  name: string | null;
  total: number;
}

export interface RuntimeTopFailure {
  workflowDefinitionId: string;
  name: string | null;
  failed: number;
}

export interface RuntimeMetricsAggregate {
  count: number;
  total: number;
  average: number;
  min: number | null;
  max: number | null;
}

export interface RuntimeMetricsSnapshot {
  executionsTotal: number;
  executionsByStatus: Record<string, number>;
  executionsByWorkflow: Record<string, number>;
  duration: RuntimeMetricsAggregate;
  handlerDuration: Record<string, RuntimeMetricsAggregate>;
  queueLatency: RuntimeMetricsAggregate;
  retryCount: number;
  actionSuccess: number;
  actionFailure: number;
  generatedAt: string;
}

export interface RuntimeStatistics {
  overview: RuntimeStatisticsOverview;
  topWorkflows: RuntimeTopWorkflow[];
  topFailures: RuntimeTopFailure[];
  metrics: RuntimeMetricsSnapshot;
}

export interface RetryHistoryStep {
  stepId: string;
  actionId: string;
  attempt: number;
  retryCount: number;
  status: WorkflowStepStatus;
  finalStatus: WorkflowStepStatus | null;
  lastError: string | null;
  startedAt: string | null;
  completedAt: string | null;
}

export interface RetryHistory {
  executionId: string;
  workflowDefinitionId: string;
  status: WorkflowStatus;
  totalSteps: number;
  totalRetries: number;
  steps: RetryHistoryStep[];
}
