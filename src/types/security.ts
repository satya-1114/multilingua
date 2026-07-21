export interface ActiveSession {
  id: string;
  device: string;
  browser: string;
  ip: string;
  location: string;
  createdAt: string;
  lastActiveAt: string;
  current?: boolean;
}

export interface LoginEvent {
  id: string;
  at: string;
  actor: string;
  ip: string;
  status: "success" | "failed" | "blocked";
  method: string;
  location: string;
}

export interface SecurityAlert {
  id: string;
  severity: "low" | "medium" | "high" | "critical";
  title: string;
  description: string;
  at: string;
  status: "open" | "resolved" | "acknowledged";
}

export interface PasswordPolicy {
  minLength: number;
  requireUppercase: boolean;
  requireNumber: boolean;
  requireSymbol: boolean;
  rotationDays: number;
  historyDepth: number;
}
