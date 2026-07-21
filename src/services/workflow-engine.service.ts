/**
 * Workflow Engine service — thin facade over the backend workflow REST API
 * (Phase 7.5). All business rules (state transitions, uniqueness, sequence
 * ordering) live in the backend. This file only shapes requests / responses
 * and normalises pagination.
 *
 * Kept distinct from the legacy `workflow.service.ts` (which drives the
 * campaign status machine) so the two responsibilities do not collide.
 */
import { apiService } from "@/services/api.service";
import { httpClient } from "@/api/client/http-client";
import type { Paginated } from "@/types/common";
import type {
  WorkflowAction,
  WorkflowActionInput,
  WorkflowDashboardStats,
  WorkflowDefinition,
  WorkflowDefinitionInput,
  WorkflowDefinitionListQuery,
  WorkflowExecution,
  WorkflowExecutionListQuery,
  WorkflowExecutionStep,
  WorkflowStepListQuery,
  WorkflowStepStatus,
  WorkflowTrigger,
  WorkflowTriggerInput,
  RuntimeHealth,
  RuntimeStatistics,
  RetryHistory,
} from "@/types/workflow";

const BASE = "/v1/workflows";

type Params = Record<string, string | number | boolean | undefined>;

async function listPaginated<T>(path: string, params: Params): Promise<Paginated<T>> {
  const env = await httpClient.request<T[]>({ method: "GET", path, params });
  const items = Array.isArray(env.data) ? env.data : [];
  const pg = env.pagination;
  return {
    items,
    total: pg?.total ?? items.length,
    page: pg?.page ?? Number(params.page ?? 1),
    pageSize: pg?.pageSize ?? Number(params.pageSize ?? items.length),
  };
}

export const workflowEngineService = {
  // ─── Definitions ─────────────────────────────────────────────────────
  listDefinitions(q: WorkflowDefinitionListQuery = {}) {
    return listPaginated<WorkflowDefinition>(BASE, {
      q: q.q,
      triggerType: q.triggerType,
      enabled: q.enabled,
      organizationId: q.organizationId,
      createdFrom: q.createdFrom,
      createdTo: q.createdTo,
      page: q.page,
      pageSize: q.pageSize,
    });
  },
  getDefinition(id: string) {
    return apiService.get<WorkflowDefinition>(`${BASE}/${id}`);
  },
  createDefinition(input: WorkflowDefinitionInput) {
    return apiService.post<WorkflowDefinition>(BASE, input);
  },
  updateDefinition(id: string, patch: Partial<WorkflowDefinitionInput>) {
    return apiService.patch<WorkflowDefinition>(`${BASE}/${id}`, patch);
  },
  deleteDefinition(id: string) {
    return apiService.delete<{ id: string; deleted: boolean }>(`${BASE}/${id}`);
  },
  enableDefinition(id: string) {
    return apiService.post<WorkflowDefinition>(`${BASE}/${id}/enable`);
  },
  disableDefinition(id: string) {
    return apiService.post<WorkflowDefinition>(`${BASE}/${id}/disable`);
  },

  // ─── Triggers ────────────────────────────────────────────────────────
  listTriggers(workflowId: string) {
    return listPaginated<WorkflowTrigger>(`${BASE}/${workflowId}/triggers`, {
      pageSize: 200,
    });
  },
  createTrigger(workflowId: string, input: WorkflowTriggerInput) {
    return apiService.post<WorkflowTrigger>(`${BASE}/${workflowId}/triggers`, input);
  },
  updateTrigger(triggerId: string, patch: Partial<WorkflowTriggerInput>) {
    return apiService.patch<WorkflowTrigger>(`${BASE}/triggers/${triggerId}`, patch);
  },
  deleteTrigger(triggerId: string) {
    return apiService.delete<{ id: string; deleted: boolean }>(
      `${BASE}/triggers/${triggerId}`,
    );
  },

  // ─── Actions ─────────────────────────────────────────────────────────
  async listActions(workflowId: string): Promise<WorkflowAction[]> {
    return apiService.get<WorkflowAction[]>(`${BASE}/${workflowId}/actions`);
  },
  createAction(workflowId: string, input: WorkflowActionInput) {
    return apiService.post<WorkflowAction>(`${BASE}/${workflowId}/actions`, input);
  },
  updateAction(actionId: string, patch: Partial<WorkflowActionInput>) {
    return apiService.patch<WorkflowAction>(`${BASE}/actions/${actionId}`, patch);
  },
  deleteAction(actionId: string) {
    return apiService.delete<{ id: string; deleted: boolean }>(
      `${BASE}/actions/${actionId}`,
    );
  },
  reorderActions(workflowId: string, orderedActionIds: string[]) {
    return apiService.post<WorkflowAction[]>(
      `${BASE}/${workflowId}/actions/reorder`,
      { orderedActionIds },
    );
  },

  // ─── Executions ──────────────────────────────────────────────────────
  listExecutions(workflowId: string, q: WorkflowExecutionListQuery = {}) {
    return listPaginated<WorkflowExecution>(`${BASE}/${workflowId}/executions`, {
      status: q.status,
      startedFrom: q.startedFrom,
      startedTo: q.startedTo,
      page: q.page,
      pageSize: q.pageSize,
    });
  },
  getExecution(id: string) {
    return apiService.get<WorkflowExecution>(`${BASE}/executions/${id}`);
  },
  startExecution(
    workflowId: string,
    input: { triggerEvent?: string; contextJson?: Record<string, unknown> } = {},
  ) {
    return apiService.post<WorkflowExecution>(
      `${BASE}/${workflowId}/executions`,
      input,
    );
  },
  completeExecution(id: string) {
    return apiService.post<WorkflowExecution>(`${BASE}/executions/${id}/complete`);
  },
  failExecution(id: string, reason?: string) {
    return apiService.post<WorkflowExecution>(`${BASE}/executions/${id}/fail`, {
      reason,
    });
  },
  cancelExecution(id: string, reason?: string) {
    return apiService.post<WorkflowExecution>(`${BASE}/executions/${id}/cancel`, {
      reason,
    });
  },
  deleteExecution(id: string) {
    return apiService.delete<{ id: string; deleted: boolean }>(
      `${BASE}/executions/${id}`,
    );
  },

  // ─── Steps ───────────────────────────────────────────────────────────
  listSteps(executionId: string, q: WorkflowStepListQuery = {}) {
    return listPaginated<WorkflowExecutionStep>(
      `${BASE}/executions/${executionId}/steps`,
      { status: q.status, page: q.page, pageSize: q.pageSize ?? 100 },
    );
  },
  transitionStep(
    stepId: string,
    status: WorkflowStepStatus,
    payload: { outputJson?: Record<string, unknown>; errorMessage?: string } = {},
  ) {
    return apiService.patch<WorkflowExecutionStep>(`${BASE}/steps/${stepId}`, {
      status,
      ...payload,
    });
  },
  retryStep(stepId: string, maxRetries = 3) {
    return apiService.post<WorkflowExecutionStep>(`${BASE}/steps/${stepId}/retry`, {
      maxRetries,
    });
  },

  // ─── Dashboard ───────────────────────────────────────────────────────
  async dashboard(): Promise<WorkflowDashboardStats> {
    const empty = { items: [], total: 0, page: 1, pageSize: 1 };
    const safe = async <T>(p: Promise<T>, fallback: T): Promise<T> => {
      try {
        return await p;
      } catch {
        return fallback;
      }
    };

    const [all, enabled] = await Promise.all([
      safe(this.listDefinitions({ pageSize: 1 }), empty as Paginated<WorkflowDefinition>),
      safe(
        this.listDefinitions({ pageSize: 1, enabled: true }),
        empty as Paginated<WorkflowDefinition>,
      ),
    ]);

    // The backend exposes executions per definition; derive dashboard counts
    // by scanning the first page of workflows for a lightweight snapshot.
    const recentDefs = await safe(
      this.listDefinitions({ pageSize: 10 }),
      empty as Paginated<WorkflowDefinition>,
    );
    let runningCount = 0;
    let failedCount = 0;
    let completedCount = 0;
    const recent: WorkflowExecution[] = [];
    await Promise.all(
      recentDefs.items.map(async (def) => {
        const page = await safe(
          this.listExecutions(def.id, { pageSize: 5 }),
          empty as Paginated<WorkflowExecution>,
        );
        for (const ex of page.items) {
          if (ex.status === "running") runningCount += 1;
          if (ex.status === "failed") failedCount += 1;
          if (ex.status === "completed") completedCount += 1;
          recent.push(ex);
        }
      }),
    );
    recent.sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
    );

    return {
      totalWorkflows: all.total,
      enabledWorkflows: enabled.total,
      runningExecutions: runningCount,
      failedExecutions: failedCount,
      completedExecutions: completedCount,
      recentExecutions: recent.slice(0, 10),
    };
  },

  // ─── Phase 8.5 — Runtime monitoring ─────────────────────────────────
  runtimeHealth() {
    return apiService.get<RuntimeHealth>(`/v1/runtime/health`);
  },
  runtimeStatistics(params: { since?: string; topLimit?: number } = {}) {
    const search = new URLSearchParams();
    if (params.since) search.set("since", params.since);
    if (params.topLimit) search.set("topLimit", String(params.topLimit));
    const q = search.toString();
    return apiService.get<RuntimeStatistics>(
      `/v1/runtime/statistics${q ? `?${q}` : ""}`,
    );
  },
  retryHistory(executionId: string) {
    return apiService.get<RetryHistory>(
      `/v1/runtime/executions/${executionId}/retries`,
    );
  },

  // ─── Phase 9.3 — Observability ─────────────────────────────────────
  observabilityMetrics() {
    return apiService.get<Record<string, unknown>>(
      `/v1/runtime/observability/metrics`,
    );
  },
  executionTrace(executionId: string) {
    return apiService.get<Record<string, unknown>>(
      `/v1/runtime/traces/${executionId}`,
    );
  },
};
