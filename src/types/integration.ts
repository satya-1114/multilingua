export type IntegrationCategory =
  | "email"
  | "sms"
  | "whatsapp"
  | "push"
  | "social"
  | "api";

export type IntegrationStatus = "connected" | "disconnected" | "error" | "pending";

export interface Integration {
  id: string;
  provider: string;
  category: IntegrationCategory;
  description: string;
  status: IntegrationStatus;
  logoInitials: string;
  color: string;
  lastSyncAt?: string;
  requestsThisMonth: number;
  errorRate: number;
  environment: "production" | "staging";
  authType: "api_key" | "oauth" | "bearer" | "smtp";
}

export interface Webhook {
  id: string;
  name: string;
  direction: "incoming" | "outgoing";
  url: string;
  event: string;
  secretMasked: string;
  active: boolean;
  successCount: number;
  failureCount: number;
  lastDeliveryAt?: string;
}

export interface WebhookDelivery {
  id: string;
  webhookId: string;
  status: "success" | "failed" | "retrying";
  responseCode: number;
  attempt: number;
  at: string;
  latencyMs: number;
}
