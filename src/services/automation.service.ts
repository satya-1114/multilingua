import type { Workflow, WorkflowTemplate } from "@/types/automation";
import { mockWorkflows, mockWorkflowTemplates } from "@/lib/mock/platform";

const delay = <T>(v: T, ms = 220): Promise<T> => new Promise((r) => setTimeout(() => r(v), ms));

let workflows: Workflow[] = [...mockWorkflows];

export const automationService = {
  async list(): Promise<Workflow[]> {
    return delay([...workflows]);
  },
  async get(id: string): Promise<Workflow | undefined> {
    return delay(workflows.find((w) => w.id === id));
  },
  async templates(): Promise<WorkflowTemplate[]> {
    return delay(mockWorkflowTemplates);
  },
  async create(input: Omit<Workflow, "id" | "createdAt" | "updatedAt" | "version" | "runsThisMonth">): Promise<Workflow> {
    const now = new Date().toISOString();
    const wf: Workflow = { ...input, id: `wf-${Date.now()}`, createdAt: now, updatedAt: now, version: 1, runsThisMonth: 0 };
    workflows = [wf, ...workflows];
    return delay(wf, 180);
  },
  async update(id: string, patch: Partial<Workflow>): Promise<Workflow> {
    workflows = workflows.map((w) =>
      w.id === id ? { ...w, ...patch, updatedAt: new Date().toISOString(), version: w.version + 1 } : w,
    );
    return delay(workflows.find((w) => w.id === id) as Workflow);
  },
  async publish(id: string): Promise<void> {
    workflows = workflows.map((w) => (w.id === id ? { ...w, status: "published" } : w));
    return delay(undefined, 200);
  },
  async archive(id: string): Promise<void> {
    workflows = workflows.map((w) => (w.id === id ? { ...w, status: "archived" } : w));
    return delay(undefined, 160);
  },
  async clone(id: string): Promise<Workflow> {
    const src = workflows.find((w) => w.id === id);
    if (!src) throw new Error("Workflow not found");
    const cloned: Workflow = { ...src, id: `wf-${Date.now()}`, name: `${src.name} (copy)`, status: "draft", version: 1, runsThisMonth: 0, updatedAt: new Date().toISOString() };
    workflows = [cloned, ...workflows];
    return delay(cloned, 160);
  },
};
