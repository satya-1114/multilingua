export type WorkflowNodeKind =
  | "trigger"
  | "approval"
  | "delay"
  | "condition"
  | "audience"
  | "template"
  | "communication"
  | "notification"
  | "ai"
  | "end";

export interface WorkflowNode {
  id: string;
  kind: WorkflowNodeKind;
  title: string;
  description?: string;
  x: number;
  y: number;
  config?: Record<string, string | number | boolean>;
}

export interface WorkflowEdge {
  id: string;
  from: string;
  to: string;
  label?: string;
}

export type WorkflowStatus = "draft" | "published" | "archived";

export interface Workflow {
  id: string;
  name: string;
  description: string;
  status: WorkflowStatus;
  version: number;
  category: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  updatedAt: string;
  updatedBy: string;
  createdAt: string;
  runsThisMonth: number;
}

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}
