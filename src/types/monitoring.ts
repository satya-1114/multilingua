export interface ServiceStatus {
  id: string;
  name: string;
  status: "operational" | "degraded" | "outage" | "maintenance";
  latencyMs: number;
  uptimePercent: number;
  region: string;
}

export interface QueueSnapshot {
  name: string;
  pending: number;
  running: number;
  completed24h: number;
  failed24h: number;
}

export interface HealthMetric {
  id: string;
  label: string;
  value: number;
  unit: string;
  threshold: number;
  status: "healthy" | "warning" | "critical";
}

export type LogLevel = "info" | "warning" | "error" | "debug";

export interface LogEntry {
  id: string;
  at: string;
  level: LogLevel;
  service: string;
  message: string;
  actor?: string;
  requestId?: string;
}
