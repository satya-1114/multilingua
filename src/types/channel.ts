export type ChannelKind =
  | "email"
  | "sms"
  | "whatsapp"
  | "push"
  | "web_broadcast"
  | "social_broadcast"
  | "voice";

export type ChannelStatus = "active" | "paused" | "degraded" | "offline" | "planned";

export interface ChannelLimits {
  perMinute: number;
  perHour: number;
  perDay: number;
  perMonth: number;
}

export interface ChannelUsage {
  dailySent: number;
  dailyCap: number;
  monthlySent: number;
  monthlyCap: number;
}

export interface ChannelRetryPolicyRef {
  policyId: string;
  maxAttempts: number;
  intervalSeconds: number;
}

export interface ChannelHealth {
  score: number; // 0-100
  latencyMs: number;
  successRate: number;
  errorRate: number;
  lastCheckedAt: string;
  incidents24h: number;
}

export interface Channel {
  id: string;
  kind: ChannelKind;
  name: string;
  provider: string;
  status: ChannelStatus;
  sender: {
    displayName: string;
    address: string;
    verified: boolean;
  };
  limits: ChannelLimits;
  usage: ChannelUsage;
  queueDepth: number;
  retry: ChannelRetryPolicyRef;
  health: ChannelHealth;
  configuration: Record<string, string>;
  createdAt: string;
  updatedAt: string;
}

export interface ChannelTestInput {
  channelId: string;
  recipient: string;
  message: string;
}

export interface ChannelTestResult {
  ok: boolean;
  latencyMs: number;
  providerMessageId?: string;
  error?: string;
}
