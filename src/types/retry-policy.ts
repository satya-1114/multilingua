import type { ChannelKind } from "./channel";
import type { FailureCategory } from "./delivery";

export type BackoffStrategy = "fixed" | "linear" | "exponential";

export interface RetryPolicy {
  id: string;
  name: string;
  description?: string;
  maxAttempts: number;
  intervalSeconds: number;
  backoff: BackoffStrategy;
  backoffMultiplier: number;
  maxIntervalSeconds: number;
  channels: ChannelKind[];
  retryOn: FailureCategory[];
  isDefault: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface RetryPolicyInput {
  name: string;
  description?: string;
  maxAttempts: number;
  intervalSeconds: number;
  backoff: BackoffStrategy;
  backoffMultiplier: number;
  maxIntervalSeconds: number;
  channels: ChannelKind[];
  retryOn: FailureCategory[];
}
